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
from .profiles import ADF435xDeviceProfile

# Device-agnostic limits shared by ADF4350 and ADF4351 (integer Hz).
VCO_MIN_HZ = 2_200_000_000
VCO_MAX_HZ = 4_400_000_000
BANDSEL_MAX_HZ_NORMAL = 125_000
BANDSEL_MAX_HZ_FAST = 500_000
PFD_MAX_FRAC_HZ = 32_000_000
REF_MAX_DOUBLER_HZ = 30_000_000
_BAND_CLK_DIV_MAX = 255


class FrequencyOutOfRangeError(ValueError):
    """Target frequency is outside the reachable output range."""


class NoSolutionError(ValueError):
    """No valid PLL divider and MOD combination exists."""


class ExactFrequencyError(ValueError):
    """Exact frequency was requested but the target is not achievable."""


class DividerOctaveCrossingError(ValueError):
    """
    A frequency table span requires more than one RF output divider.

    Attributes
    ----------
    lower_hz, upper_hz : int
        Requested bounds or offending frequency pair.
    lower_divider, upper_divider : int
        RF dividers assigned to the low and high endpoints.
    lower_band_hz, upper_band_hz : tuple of (int, int)
        ``(min_hz, max_hz)`` output band for each divider.
    """

    def __init__(
        self,
        message,
        *,
        lower_hz,
        upper_hz,
        lower_divider,
        upper_divider,
        lower_band_hz,
        upper_band_hz,
    ):
        """Store the crossing details and message."""
        super().__init__(message)
        self.lower_hz = lower_hz
        self.upper_hz = upper_hz
        self.lower_divider = lower_divider
        self.upper_divider = upper_divider
        self.lower_band_hz = lower_band_hz
        self.upper_band_hz = upper_band_hz


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
    rf_divider : int or None
        Fixed RF output divider; skips divider search when set.
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
        rf_divider=None,
        channel_spacing_hz=None,
        exact=False,
    ):
        """Store reference-path and MOD policy overrides."""
        self.r_counter = r_counter
        self.doubler = doubler
        self.rdiv2 = rdiv2
        self.mod = mod
        self.rf_divider = rf_divider
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


def _output_min_hz(profile: ADF435xDeviceProfile) -> int:
    """Lowest reachable output frequency for *profile*."""
    return _round_div(VCO_MIN_HZ, profile.rf_divider_max)


def achieved_hz_from_n_num(n_num, mod, f_pfd, rf_divider):
    """
    RF output in hertz for fractional-N numerator *n_num* (N = n_num / mod).

    Parameters
    ----------
    n_num : int
        Combined numerator INT * MOD + FRAC.
    mod : int
        Fractional modulus.
    f_pfd : int
        PFD frequency in hertz.
    rf_divider : int
        RF output divider.

    Returns
    -------
    int
        Achieved RF output frequency in hertz.
    """
    return ((n_num * f_pfd) // mod) // rf_divider


def rf_channel_step_hz(f_pfd, mod, rf_divider):
    """
    Minimum RF output spacing for fixed MOD and dividers.

    Parameters
    ----------
    f_pfd : int
        PFD frequency in hertz.
    mod : int
        Fractional modulus.
    rf_divider : int
        RF output divider.

    Returns
    -------
    int
        Channel step at the RF output in hertz.
    """
    return f_pfd // mod // rf_divider


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


def output_band_hz(rf_divider):
    """
    Return the RF output frequency band for an RF divider.

    Parameters
    ----------
    rf_divider : int
        Power-of-two output divider (1, 2, 4, ...).

    Returns
    -------
    tuple of (int, int)
        ``(min_hz, max_hz)`` achievable at this divider with VCO in band.
    """
    return (_ceil_div(VCO_MIN_HZ, rf_divider), VCO_MAX_HZ // rf_divider)


def max_hz_for_rf_divider(rf_divider, profile):
    """
    Highest frequency where ``_pick_rf_divider`` still selects *rf_divider*.

    ``_pick_rf_divider`` tries dividers in ascending order, so *rf_divider*
    is only chosen while the next-smaller divider does not fit the VCO band.

    Parameters
    ----------
    rf_divider : int
        Power-of-two output divider.
    profile : ADF435xDeviceProfile
        Device profile.

    Returns
    -------
    int
        Maximum hertz for this divider selection.
    """
    _, band_hi = output_band_hz(rf_divider)
    if rf_divider <= 1:
        return band_hi
    smaller = rf_divider // 2
    if smaller not in profile.legal_rf_dividers():
        return band_hi
    # Next-smaller divider wins at ceil(VCO_MIN / smaller) and above.
    return min(band_hi, _ceil_div(VCO_MIN_HZ, smaller) - 1)


def divider_octave_crossing_message(
    lower_hz,
    upper_hz,
    lower_divider,
    upper_divider,
):
    """
    Build a user-facing error string for an RF divider octave crossing.

    Parameters
    ----------
    lower_hz, upper_hz : int
        Endpoint frequencies in hertz.
    lower_divider, upper_divider : int
        RF dividers the solver chose for each endpoint.

    Returns
    -------
    str
    """
    low_band = output_band_hz(lower_divider)
    high_band = output_band_hz(upper_divider)
    narrow_low_hi = min(upper_hz, low_band[1])
    narrow_high_lo = max(lower_hz, high_band[0])
    return (
        "RF divider octave crossing: %d Hz uses divide-by-%d "
        "(band %d–%d Hz), %d Hz needs divide-by-%d (band %d–%d Hz). "
        "Narrow to [%d, %d] or [%d, %d], or set allow_divider_change=True."
        % (
            lower_hz,
            lower_divider,
            low_band[0],
            low_band[1],
            upper_hz,
            upper_divider,
            high_band[0],
            high_band[1],
            lower_hz,
            narrow_low_hi,
            narrow_high_lo,
            upper_hz,
        )
    )


def _raise_divider_crossing(lower_hz, upper_hz, low_div, high_div):
    """Raise ``DividerOctaveCrossingError`` with band details."""
    low_band = output_band_hz(low_div)
    high_band = output_band_hz(high_div)
    raise DividerOctaveCrossingError(
        divider_octave_crossing_message(
            lower_hz, upper_hz, low_div, high_div
        ),
        lower_hz=lower_hz,
        upper_hz=upper_hz,
        lower_divider=low_div,
        upper_divider=high_div,
        lower_band_hz=low_band,
        upper_band_hz=high_band,
    )


def _pick_rf_divider(target_hz: int, profile: ADF435xDeviceProfile) -> int:
    """
    Pick the smallest RF divider that places VCO in the tuning band.

    Raises
    ------
    NoSolutionError
        If no legal divider yields an in-band VCO frequency.
    """
    for div in profile.legal_rf_dividers():
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


def _candidate_valid(int_n, frac, mod, vco_hz, profile, prescaler):
    """Return True if INT, FRAC, MOD, and VCO satisfy PLL constraints."""
    if not (VCO_MIN_HZ <= vco_hz <= VCO_MAX_HZ):
        return False
    if frac >= mod:
        return False
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
        prescaler = _pick_prescaler(vco_hz, profile)
        if not _candidate_valid(int_n, frac, mod, vco_hz, profile, prescaler):
            continue
        achieved = vco_hz // rf_divider
        error = abs(target_hz - achieved)
        score = (error, mod)
        if best_score is None or score < best_score:
            best_score = score
            best = (mod, int_n, frac, prescaler)
        if error == 0:
            break

    return best


def _set_pll_mode_fields(fields, frac, profile):
    """Set LDF, ABP, and charge-cancel for integer-N or fractional-N."""
    if frac == 0:
        fields["ldf"] = consts.REG2_LDF_INT_N
        if profile.has_programmable_abp:
            fields["abp"] = consts.REG3_ABP_3NS
        if profile.has_charge_cancel:
            fields["charge_cancel"] = True
    else:
        fields["ldf"] = consts.REG2_LDF_FRAC_N
        if profile.has_programmable_abp:
            fields["abp"] = consts.REG3_ABP_6NS
        if profile.has_charge_cancel:
            fields["charge_cancel"] = False


def _enumerate_achievable_hz(n_low, n_high, mod, f_pfd, rf_divider):
    """
    List achievable RF frequencies on the PLL grid from *n_low* to *n_high*.

    Parameters
    ----------
    n_low, n_high : int
        Inclusive fractional-N numerators (INT * MOD + FRAC).
    mod : int
        Fractional modulus.
    f_pfd : int
        PFD frequency in hertz.
    rf_divider : int
        RF output divider.

    Returns
    -------
    list of int
        Sorted unique achievable RF frequencies in hertz.
    """
    freqs = []
    prev = None
    for n_num in range(n_low, n_high + 1):
        rf_hz = achieved_hz_from_n_num(n_num, mod, f_pfd, rf_divider)
        if rf_hz != prev:
            freqs.append(rf_hz)
            prev = rf_hz
    return freqs


def _pick_step_grid(achievable_hz, step_hz):
    """
    Select grid points closest to each ``start + n * step`` target.

    Always includes the first and last achievable frequencies in the range.

    Parameters
    ----------
    achievable_hz : list of int
        Sorted achievable frequencies (ascending).
    step_hz : int
        Desired spacing between table entries in hertz.

    Returns
    -------
    list of int
        Selected RF frequencies for the sweep table.
    """
    if not achievable_hz:
        return []
    if step_hz <= 0:
        raise ValueError("step_hz must be positive")

    selected = [achievable_hz[0]]
    while True:
        goal = selected[-1] + step_hz
        if goal > achievable_hz[-1]:
            break
        best = min(achievable_hz, key=lambda f: abs(f - goal))
        if best <= selected[-1]:
            break
        selected.append(best)

    if selected[-1] != achievable_hz[-1]:
        selected.append(achievable_hz[-1])
    return selected


def build_frequency_table(
    lower_hz,
    upper_hz,
    step_hz,
    ref_hz,
    profile,
    *,
    allow_divider_change=False,
):
    """
    Build a sweep table between *lower_hz* and *upper_hz*.

    Solves the endpoints, locks MOD from the lower solve, verifies both ends
    share the same RF divider (unless *allow_divider_change*), enumerates the
    PLL grid, and picks entries nearest the requested step.

    Parameters
    ----------
    lower_hz, upper_hz : int
        Frequency bounds in hertz (lower must not exceed upper).
    step_hz : int
        Desired table spacing in hertz.
    ref_hz : int
        Reference input frequency in hertz.
    profile : ADF435xDeviceProfile
        Device profile (ADF4350 or ADF4351).
    allow_divider_change : bool
        When True, split the span at RF divider octaves and build an
        optimized sub-table per band (locked MOD within each segment).

    Returns
    -------
    tuple of (list, int, frozenset)
        ``(entries, channel_step_hz, boundary_indices)`` where each entry
        is a ``SolveResult``, ``channel_step_hz`` is the RF channel spacing
        (0 when the span crosses divider bands), and *boundary_indices*
        marks the first entry of each segment after the first.

    Raises
    ------
    ValueError
        If bounds are invalid or the range crosses an RF divider octave.
    DividerOctaveCrossingError
        Subclass of ``ValueError`` with ``lower_band_hz`` / ``upper_band_hz``.
    """
    if lower_hz > upper_hz:
        raise ValueError("lower_hz must not exceed upper_hz")

    low = solve(lower_hz, ref_hz, profile)
    high = solve(upper_hz, ref_hz, profile)
    if high.fields["rf_divider"] != low.fields["rf_divider"]:
        if not allow_divider_change:
            _raise_divider_crossing(
                lower_hz,
                upper_hz,
                low.fields["rf_divider"],
                high.fields["rf_divider"],
            )
        return _build_frequency_table_segmented(
            lower_hz, upper_hz, step_hz, ref_hz, profile
        )

    return _build_single_divider_table(
        lower_hz, upper_hz, step_hz, ref_hz, profile
    )


def _divider_segments(lower_hz, upper_hz, ref_hz, profile):
    """
    Split *lower_hz*..*upper_hz* into contiguous RF-divider bands.

    Returns
    -------
    list of tuple
        ``(seg_lower_hz, seg_upper_hz, rf_divider)`` in ascending order.
    """
    segments = []
    pos = lower_hz
    while pos <= upper_hz:
        div = solve(pos, ref_hz, profile).fields["rf_divider"]
        seg_hi = min(upper_hz, max_hz_for_rf_divider(div, profile))
        segments.append((pos, seg_hi, div))
        if seg_hi >= upper_hz:
            break
        pos = seg_hi + 1
    return segments


def _build_single_divider_table(lower_hz, upper_hz, step_hz, ref_hz, profile):
    """
    Build an optimized table within one RF divider band.

    Locks MOD from the lower endpoint, enumerates the PLL grid, and picks
    entries nearest the requested step.

    Returns
    -------
    tuple of (list, int, frozenset)
        ``(entries, channel_step_hz, boundary_indices)`` where
        *boundary_indices* is empty for a single-band table.
    """
    if step_hz <= 0:
        raise ValueError("step_hz must be positive")

    low = solve(lower_hz, ref_hz, profile)
    mod = low.fields["mod"]
    rf_divider = low.fields["rf_divider"]
    opts = SolveOptions(mod=mod, rf_divider=rf_divider)

    high = solve(upper_hz, ref_hz, profile, options=opts)
    if high.fields["rf_divider"] != rf_divider:
        raise ValueError(
            "internal error: segment %d–%d spans RF dividers %d and %d"
            % (
                lower_hz,
                upper_hz,
                rf_divider,
                high.fields["rf_divider"],
            )
        )

    f_pfd = low.f_pfd_hz
    channel_step_hz = rf_channel_step_hz(f_pfd, mod, rf_divider)

    n_low = low.fields["int_n"] * mod + low.fields["frac"]
    n_high = high.fields["int_n"] * mod + high.fields["frac"]
    if n_low > n_high:
        n_low, n_high = n_high, n_low

    achievable = _enumerate_achievable_hz(
        n_low, n_high, mod, f_pfd, rf_divider
    )
    table_hz = _pick_step_grid(achievable, step_hz)

    entries = []
    for hz in table_hz:
        entries.append(solve(hz, ref_hz, profile, options=opts))
    return entries, channel_step_hz, frozenset()


def _build_frequency_table_segmented(
    lower_hz,
    upper_hz,
    step_hz,
    ref_hz,
    profile,
):
    """
    Build a crossing span as optimized sub-tables, one per RF divider band.

    Each segment uses locked MOD and PLL grid planning. The first entry of
    every segment after the first is a divider boundary (full register write,
    longer dwell, and lock wait at playback).

    Returns
    -------
    tuple of (list, int, frozenset)
        ``(entries, 0, boundary_indices)`` — channel step is not uniform.
    """
    segments = _divider_segments(lower_hz, upper_hz, ref_hz, profile)
    all_entries = []
    boundary_indices = set()

    for i, (seg_lo, seg_hi, _div) in enumerate(segments):
        seg_entries, _, _ = _build_single_divider_table(
            seg_lo, seg_hi, step_hz, ref_hz, profile
        )
        if i > 0 and seg_entries:
            if (
                all_entries
                and seg_entries[0].achieved_hz
                == all_entries[-1].achieved_hz
            ):
                all_entries.pop()
            boundary_indices.add(len(all_entries))
        all_entries.extend(seg_entries)

    return all_entries, 0, frozenset(boundary_indices)


def _build_frequency_table_divided(
    lower_hz,
    upper_hz,
    step_hz,
    ref_hz,
    profile,
):
    """
    Deprecated naive divider crossing (independent solves per step).

    Kept for regression comparison; production code uses
    ``_build_frequency_table_segmented``.
    """
    if step_hz <= 0:
        raise ValueError("step_hz must be positive")

    entries = []
    hz = lower_hz
    while hz <= upper_hz:
        entries.append(solve(hz, ref_hz, profile))
        hz += step_hz

    last = entries[-1]
    if last.achieved_hz + last.error_hz != upper_hz:
        upper = solve(upper_hz, ref_hz, profile)
        if upper.achieved_hz != last.achieved_hz:
            entries.append(upper)

    boundaries = set()
    prev_div = entries[0].fields["rf_divider"]
    for i in range(1, len(entries)):
        div = entries[i].fields["rf_divider"]
        if div != prev_div:
            boundaries.add(i)
        prev_div = div
    return entries, 0, frozenset(boundaries)


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
    if target_hz < out_min or target_hz > VCO_MAX_HZ:
        raise FrequencyOutOfRangeError(
            "target_hz=%d outside [%d, %d]" % (target_hz, out_min, VCO_MAX_HZ)
        )

    f_pfd = _compute_f_pfd(ref_hz, opts.r_counter, opts.doubler, opts.rdiv2)
    if f_pfd > PFD_MAX_FRAC_HZ:
        raise NoSolutionError(
            "f_pfd=%d exceeds fractional-N maximum %d"
            % (f_pfd, PFD_MAX_FRAC_HZ)
        )

    rf_divider = _pick_rf_divider(target_hz, profile)
    if opts.rf_divider is not None:
        rf_divider = opts.rf_divider
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
    _set_pll_mode_fields(fields, frac, profile)

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
