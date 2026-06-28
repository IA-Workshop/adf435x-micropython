"""
Frequency-to-register solver for ADF435x PLLs.

Given a target output frequency, reference frequency, and device profile,
``solve()`` returns register field values for the PLL path. Validation runs
in ``ADF435xRegisterMapper`` when fields are applied to a register file.

Glossary
--------
PFD : Phase-frequency detector
fPFD : PFD comparison frequency, REFIN * (1 + D) / (R * (1 + T))
VCO : Voltage-controlled oscillator
INT : Integer part of the feedback division factor N
FRAC : Fractional numerator of N, with 0 <= FRAC < MOD
MOD : Fractional modulus; the channel-step divisor
N : Feedback divider, N = INT + FRAC / MOD, with f_VCO = N * fPFD
RF divider : Output divider (1, 2, 4, ... 64) that divides f_VCO to RFout
"""

from . import consts
from .profiles import ADF435xDeviceProfile, _log2_power_of_two

# Device-agnostic limits shared by ADF4350 and ADF4351 (integer Hz).
VCO_MIN_HZ = 2_200_000_000
VCO_MAX_HZ = 4_400_000_000
BANDSEL_MAX_HZ_NORMAL = 125_000
BANDSEL_MAX_HZ_FAST = 500_000
PFD_MAX_FRAC_HZ = 32_000_000
PFD_MAX_INT_HZ = 90_000_000
REF_MAX_DOUBLER_HZ = 30_000_000
_BAND_CLK_DIV_MAX = 255


class FrequencyOutOfRangeError(ValueError):
    """Target frequency is outside the reachable output range."""


class NoSolutionError(ValueError):
    """No valid PLL divider and MOD combination exists."""


class ExactFrequencyError(ValueError):
    """Exact frequency was requested but the target is not achievable."""


class SolveOptions:
    """
    Optional policy overrides for ``solve()``.

    Parameters
    ----------
    r_counter : int
        R-counter divide ratio (1..1023).
    doubler : bool
        Enable the reference doubler.
    rdiv2 : bool
        Enable the reference divide-by-two.
    mod : int or None
        Fixed MOD; skips MOD search when set.
    channel_spacing_hz : int or None
        Derive MOD from ``f_pfd // channel_spacing_hz`` when set.
    exact : bool
        Raise ``ExactFrequencyError`` when the residual error is not zero.
    """

    def __init__(
        self,
        r_counter=1,
        doubler=False,
        rdiv2=False,
        mod=None,
        channel_spacing_hz=None,
        exact=False,
    ):
        """Store reference-path and MOD policy overrides."""
        self.r_counter = r_counter
        self.doubler = doubler
        self.rdiv2 = rdiv2
        self.mod = mod
        self.channel_spacing_hz = channel_spacing_hz
        self.exact = exact


class SolveResult:
    """
    Result of a frequency solve.

    Parameters
    ----------
    fields : dict
        Frequency-determining config fields for ``register_file.configure()``.
    achieved_hz : int
        Actual output frequency in hertz.
    error_hz : int
        Signed residual ``target_hz - achieved_hz``.
    f_pfd_hz : int
        Computed PFD frequency in hertz.
    vco_hz : int
        Achieved VCO frequency before the RF output divider.
    """

    def __init__(self, fields, achieved_hz, error_hz, f_pfd_hz, vco_hz):
        """Store solver output fields and achieved frequencies."""
        self.fields = fields
        self.achieved_hz = achieved_hz
        self.error_hz = error_hz
        self.f_pfd_hz = f_pfd_hz
        self.vco_hz = vco_hz


def _round_div(num: int, den: int) -> int:
    """
    Divide two non-negative integers, rounding to the nearest integer.

    Ties are rounded up.

    Parameters
    ----------
    num : int
        Non-negative numerator.
    den : int
        Positive denominator.

    Returns
    -------
    int
        ``num / den`` rounded to the nearest integer.
    """
    return (num + den // 2) // den


def _ceil_div(num: int, den: int) -> int:
    """
    Divide two non-negative integers, rounding up.

    Parameters
    ----------
    num : int
        Non-negative numerator.
    den : int
        Positive denominator.

    Returns
    -------
    int
        The smallest integer not less than ``num / den``.
    """
    return (num + den - 1) // den


def _gcd(a: int, b: int) -> int:
    """
    Greatest common divisor (Euclidean algorithm).

    MicroPython-safe: does not use ``math.gcd``.

    Parameters
    ----------
    a, b : int
        Operands; negative values use absolute value.

    Returns
    -------
    int
        ``gcd(a, b)``; zero if both inputs are zero.
    """
    a = abs(a)
    b = abs(b)
    while b:
        a, b = b, a % b
    return a


def _rf_dividers(profile: ADF435xDeviceProfile) -> tuple[int, ...]:
    """Return ascending RF output dividers legal for *profile*."""
    count = _log2_power_of_two(profile.rf_divider_max) + 1
    return tuple(1 << i for i in range(count))


def _output_min_hz(profile: ADF435xDeviceProfile) -> int:
    """Lowest reachable output frequency for *profile*."""
    return _round_div(VCO_MIN_HZ, profile.rf_divider_max)


def _output_max_hz(profile: ADF435xDeviceProfile) -> int:
    """Highest reachable output frequency for *profile*."""
    return VCO_MAX_HZ


def _compute_f_pfd(
    ref_hz: int,
    r_counter: int,
    doubler: bool,
    rdiv2: bool,
) -> int:
    """
    Compute PFD frequency from the reference path.

    Parameters
    ----------
    ref_hz : int
        Reference input frequency in hertz.
    r_counter : int
        R-counter divide ratio.
    doubler : bool
        Reference doubler enabled.
    rdiv2 : bool
        Reference divide-by-two enabled.

    Returns
    -------
    int
        PFD frequency in hertz.

    Raises
    ------
    ValueError
        If *r_counter* is out of range or the doubler limit is exceeded.
    """
    r_max = (1 << consts.REG2_R_COUNTER_WIDTH) - 1
    if r_counter < consts.REG2_R_COUNTER_MIN or r_counter > r_max:
        raise ValueError("r_counter=%d out of range [1, %d]" % (r_counter, r_max))
    if doubler and ref_hz > REF_MAX_DOUBLER_HZ:
        raise ValueError(
            "ref_hz=%d exceeds doubler limit %d" % (ref_hz, REF_MAX_DOUBLER_HZ)
        )
    num = ref_hz * (2 if doubler else 1)
    den = r_counter * (2 if rdiv2 else 1)
    return num // den


def _compute_vco_hz(int_n: int, frac: int, mod: int, f_pfd: int) -> int:
    """Compute VCO frequency from INT, FRAC, MOD, and fPFD."""
    return ((int_n * mod + frac) * f_pfd) // mod


def _compute_achieved_hz(
    int_n: int,
    frac: int,
    mod: int,
    f_pfd: int,
    rf_divider: int,
) -> int:
    """Compute RF output frequency after the output divider."""
    return _compute_vco_hz(int_n, frac, mod, f_pfd) // rf_divider


def _normalize_frac_mod(frac: int, mod: int) -> tuple[int, int]:
    """Reduce FRAC/MOD by their gcd to limit fractional spurs."""
    if frac == 0:
        return frac, mod
    g = _gcd(frac, mod)
    if g > 1:
        return frac // g, mod // g
    return frac, mod


def _int_frac_for_mod(
    vco_hz: int,
    f_pfd: int,
    mod: int,
):
    """
    Solve INT and FRAC for a fixed MOD and target VCO frequency.

    Returns
    -------
    tuple of (int, int, int) or None
        ``(int_n, frac, mod)`` after carry and gcd reduction, or None if
        ``frac >= mod`` after normalization (MOD too small).
    """
    int_n = vco_hz // f_pfd
    remainder = vco_hz - int_n * f_pfd
    frac = _round_div(remainder * mod, f_pfd)
    if frac >= mod:
        frac -= mod
        int_n += 1
    frac, mod = _normalize_frac_mod(frac, mod)
    if frac >= mod or mod < 2:
        return None
    return int_n, frac, mod


def _pick_prescaler(vco_hz: int, profile: ADF435xDeviceProfile) -> int:
    """Select dual-modulus prescaler from achieved VCO frequency."""
    if vco_hz <= profile.prescaler_4_5_max_hz:
        return consts.REG1_PRESCALER_4_5
    return consts.REG1_PRESCALER_8_9


def _int_min_for_prescaler(prescaler: int, profile: ADF435xDeviceProfile) -> int:
    """Return the datasheet INT minimum for *prescaler*."""
    if prescaler == consts.REG1_PRESCALER_4_5:
        return profile.int_min_4_5
    return profile.int_min_8_9


def _pick_rf_divider(target_hz: int, profile: ADF435xDeviceProfile) -> int:
    """
    Pick the smallest RF divider that places VCO in the tuning band.

    Raises
    ------
    NoSolutionError
        If no legal divider yields an in-band VCO frequency.
    """
    for div in _rf_dividers(profile):
        vco = target_hz * div
        if VCO_MIN_HZ <= vco <= VCO_MAX_HZ:
            return div
    raise NoSolutionError(
        "no RF divider places VCO in [%d, %d] Hz for target %d"
        % (VCO_MIN_HZ, VCO_MAX_HZ, target_hz)
    )


def _pick_band_clk(
    f_pfd: int,
    profile: ADF435xDeviceProfile,
) -> tuple[int, int]:
    """
    Compute band-select clock divider and mode.

    Returns
    -------
    tuple of (int, int)
        ``(band_clk_div, band_clk_mode)``.

    Raises
    ------
    NoSolutionError
        If the required divider exceeds 255 or fPFD is too high.
    """
    if not profile.has_fast_band_select:
        div = _ceil_div(f_pfd, BANDSEL_MAX_HZ_NORMAL)
        if div > _BAND_CLK_DIV_MAX:
            raise NoSolutionError(
                "band_clk_div=%d exceeds maximum %d" % (div, _BAND_CLK_DIV_MAX)
            )
        return div, consts.REG3_BAND_CLK_LOW

    if f_pfd > BANDSEL_MAX_HZ_NORMAL * _BAND_CLK_DIV_MAX:
        raise NoSolutionError("f_pfd=%d too high for band-select clock" % f_pfd)

    # ADF4351: use fast mode when normal mode would exceed ~125 kHz.
    if f_pfd > BANDSEL_MAX_HZ_NORMAL:
        div = _ceil_div(f_pfd, BANDSEL_MAX_HZ_FAST)
        if div > _BAND_CLK_DIV_MAX:
            raise NoSolutionError(
                "band_clk_div=%d exceeds maximum %d" % (div, _BAND_CLK_DIV_MAX)
            )
        return div, consts.REG3_BAND_CLK_HIGH

    div = _ceil_div(f_pfd, BANDSEL_MAX_HZ_NORMAL)
    return div, consts.REG3_BAND_CLK_LOW


def _clamp_mod(mod: int, profile: ADF435xDeviceProfile) -> int:
    """Clamp MOD to the profile's legal range."""
    if mod < profile.mod_min:
        return profile.mod_min
    if mod > profile.mod_max:
        return profile.mod_max
    return mod


def _mod_candidates(
    f_pfd: int,
    profile: ADF435xDeviceProfile,
    options: SolveOptions,
) -> range:
    """Return the MOD values to evaluate for this solve."""
    if options.mod is not None:
        return range(options.mod, options.mod + 1)
    if options.channel_spacing_hz is not None:
        spacing = options.channel_spacing_hz
        if spacing <= 0:
            raise ValueError("channel_spacing_hz must be positive")
        mod = _clamp_mod(f_pfd // spacing, profile)
        return range(mod, mod + 1)
    return range(profile.mod_min, profile.mod_max + 1)


def _candidate_valid(
    int_n: int,
    frac: int,
    mod: int,
    vco_hz: int,
    profile: ADF435xDeviceProfile,
) -> bool:
    """Return True if INT, FRAC, MOD, and VCO satisfy PLL constraints."""
    if not (VCO_MIN_HZ <= vco_hz <= VCO_MAX_HZ):
        return False
    if frac >= mod:
        return False
    prescaler = _pick_prescaler(vco_hz, profile)
    int_min = _int_min_for_prescaler(prescaler, profile)
    return int_min <= int_n <= profile.int_max


def _best_pll(
    target_hz: int,
    vco_target: int,
    f_pfd: int,
    rf_divider: int,
    profile: ADF435xDeviceProfile,
    options: SolveOptions,
):
    """
    Find the best MOD, INT, FRAC, and prescaler for *vco_target*.

    Scores by ``(abs(error_hz), mod)`` so equal error prefers smaller MOD.

    Returns
    -------
    tuple of (int, int, int, int) or None
        ``(mod, int_n, frac, prescaler)`` or None when no candidate fits.
    """
    best = None
    best_score = None

    for mod in _mod_candidates(f_pfd, profile, options):
        solved = _int_frac_for_mod(vco_target, f_pfd, mod)
        if solved is None:
            continue
        int_n, frac, mod = solved
        vco_hz = _compute_vco_hz(int_n, frac, mod, f_pfd)
        if not _candidate_valid(int_n, frac, mod, vco_hz, profile):
            continue
        prescaler = _pick_prescaler(vco_hz, profile)
        achieved = vco_hz // rf_divider
        error = abs(target_hz - achieved)
        score = (error, mod)
        if best_score is None or score < best_score:
            best_score = score
            best = (mod, int_n, frac, prescaler)

    return best


def _apply_int_n_fields(fields, profile):
    """Add integer-N register optimizations when FRAC is zero."""
    fields["ldf"] = consts.REG2_LDF_INT_N
    if profile.has_programmable_abp:
        fields["abp"] = consts.REG3_ABP_3NS
    if profile.has_charge_cancel:
        fields["charge_cancel"] = True


def solve(
    target_hz,
    ref_hz,
    profile,
    *,
    options=None,
):
    """
    Solve register fields for a target output frequency.

    Parameters
    ----------
    target_hz : int
        Desired RF output frequency in hertz (integer only).
    ref_hz : int
        Reference input frequency in hertz.
    profile : ADF435xDeviceProfile
        Device profile (ADF4350 or ADF4351).
    options : SolveOptions or None
        Optional reference path and MOD policy overrides.

    Returns
    -------
    SolveResult
        Field dict, achieved frequency, signed error, fPFD, and VCO frequency.

    Raises
    ------
    FrequencyOutOfRangeError
        If *target_hz* is outside the reachable output range.
    NoSolutionError
        If no valid PLL configuration exists.
    ExactFrequencyError
        If ``options.exact`` is True and the residual error is not zero.
    ValueError
        If reference-path parameters are invalid.
    """
    opts = options if options is not None else SolveOptions()

    out_min = _output_min_hz(profile)
    out_max = _output_max_hz(profile)
    if target_hz < out_min or target_hz > out_max:
        raise FrequencyOutOfRangeError(
            "target_hz=%d outside [%d, %d]" % (target_hz, out_min, out_max)
        )

    f_pfd = _compute_f_pfd(ref_hz, opts.r_counter, opts.doubler, opts.rdiv2)
    if f_pfd > PFD_MAX_FRAC_HZ:
        raise NoSolutionError(
            "f_pfd=%d exceeds fractional-N maximum %d"
            % (f_pfd, PFD_MAX_FRAC_HZ)
        )

    rf_divider = _pick_rf_divider(target_hz, profile)
    vco_target = target_hz * rf_divider

    pll = _best_pll(
        target_hz, vco_target, f_pfd, rf_divider, profile, opts
    )
    if pll is None:
        raise NoSolutionError(
            "no MOD/INT/FRAC solution for target %d Hz" % target_hz
        )

    mod, int_n, frac, prescaler = pll
    vco_hz = _compute_vco_hz(int_n, frac, mod, f_pfd)
    band_clk_div, band_clk_mode = _pick_band_clk(f_pfd, profile)

    fields = {
        "int_n": int_n,
        "frac": frac,
        "mod": mod,
        "prescaler": prescaler,
        "r_counter": opts.r_counter,
        "doubler": opts.doubler,
        "rdiv2": opts.rdiv2,
        "rf_divider": rf_divider,
        "band_clk_div": band_clk_div,
        "band_clk_mode": band_clk_mode,
        "feedback": consts.REG4_FEEDBACK_FUNDAMENTAL,
    }
    if frac == 0:
        _apply_int_n_fields(fields, profile)

    achieved_hz = _compute_achieved_hz(
        int_n, frac, mod, f_pfd, rf_divider
    )
    error_hz = target_hz - achieved_hz

    if opts.exact and error_hz != 0:
        raise ExactFrequencyError(
            "target_hz=%d not exactly achievable (error %d Hz)"
            % (target_hz, error_hz)
        )

    return SolveResult(
        fields=fields,
        achieved_hz=achieved_hz,
        error_hz=error_hz,
        f_pfd_hz=f_pfd,
        vco_hz=vco_hz,
    )
