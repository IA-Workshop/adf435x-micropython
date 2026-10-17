"""
Frequency-to-register solver for ADF435x PLLs.

Given a target output frequency, reference frequency, and device profile,
``solve()`` returns register field values for the PLL path. Validation runs
in ``ADF435xRegisterMapper`` when fields are applied to a register file.

All arithmetic is exact integer math: fPFD is carried as a fraction
``pfd_num / pfd_den`` and never rounded, so reported frequencies and errors
match the hardware. (MicroPython has no ``fractions`` module; plain integer
pairs are used instead.)

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
_FAST_BAND_CLK_DIV_MAX = 254  # data sheet p.19
LOW_SPUR_MOD_MIN = 50  # data sheet p.23


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
        Fixed MOD; skips the MOD search and is never reduced.
    rf_divider : int or None
        Fixed RF output divider; skips the divider choice.
    channel_step_hz : int or None
        Fixed RF *output* channel step. MOD = fPFD / (step * RF divider),
        which must be a whole number in the profile's MOD range.
    exact : bool
        Raise ``ExactFrequencyError`` when the output is not exactly the
        target.
    mod_min : int or None
        Smallest MOD to use (default: the profile minimum). The synthesizer
        passes 50 in low-spur noise mode (data sheet p.23).
    """

    def __init__(
        self,
        r_counter=1,
        doubler=False,
        rdiv2=False,
        mod=None,
        rf_divider=None,
        channel_step_hz=None,
        exact=False,
        mod_min=None,
    ):
        """Store reference-path and MOD policy overrides."""
        self.r_counter = r_counter
        self.doubler = doubler
        self.rdiv2 = rdiv2
        self.mod = mod
        self.rf_divider = rf_divider
        self.channel_step_hz = channel_step_hz
        self.exact = exact
        self.mod_min = mod_min

    def copy(self, **overrides):
        """
        Return a copy with some options replaced.

        Parameters
        ----------
        **overrides
            Option name/value pairs to change in the copy.

        Returns
        -------
        SolveOptions
        """
        values = {
            "r_counter": self.r_counter,
            "doubler": self.doubler,
            "rdiv2": self.rdiv2,
            "mod": self.mod,
            "rf_divider": self.rf_divider,
            "channel_step_hz": self.channel_step_hz,
            "exact": self.exact,
            "mod_min": self.mod_min,
        }
        for name in overrides:
            if name not in values:
                raise TypeError("unknown solve option: %s" % name)
        values.update(overrides)
        return SolveOptions(**values)

    def with_locked_pll(self, mod, rf_divider=None):
        """Copy with MOD (and optionally the RF divider) fixed."""
        return self.copy(mod=mod, rf_divider=rf_divider)


def _resolve_options(options):
    """Return *options* or default ``SolveOptions()``."""
    return options if options is not None else SolveOptions()


class SolveResult:
    """
    Result of a frequency solve.

    Parameters
    ----------
    fields : dict
        Register fields the solver owns, for ``register_file.configure()``:
        ``int_n``, ``frac``, ``mod``, ``prescaler``, ``r_counter``,
        ``doubler``, ``rdiv2``, ``rf_divider``, ``band_clk_div``,
        ``band_clk_mode``, ``feedback``, ``ldf``, ``ldp``, and (where the part
        has them) ``abp`` and ``charge_cancel``. All other fields keep the
        caller's settings.
    achieved_hz : int
        Output frequency rounded to the nearest hertz.
    error_hz : int
        ``target_hz - achieved_hz``.
    f_pfd_hz : int
        PFD frequency, rounded to the nearest hertz (display only).
    vco_hz : int
        VCO frequency, rounded to the nearest hertz.
    exact : bool
        True only when the output is exactly the target (no sub-hertz
        residual).
    f_pfd_fraction : tuple of (int, int)
        Exact PFD frequency as ``(numerator, denominator)``.
    """

    def __init__(
        self, fields, achieved_hz, error_hz, f_pfd_hz, vco_hz, exact, f_pfd_fraction
    ):
        """Store solver output fields and achieved frequencies."""
        self.fields = fields
        self.achieved_hz = achieved_hz
        self.error_hz = error_hz
        self.f_pfd_hz = f_pfd_hz
        self.vco_hz = vco_hz
        self.exact = exact
        self.f_pfd_fraction = f_pfd_fraction


def _round_div(num: int, den: int) -> int:
    """Divide non-negative integers, rounding to nearest (ties up)."""
    return (num + den // 2) // den


def _ceil_div(num: int, den: int) -> int:
    """Divide non-negative integers, rounding up."""
    return (num + den - 1) // den


def _require_int(name, value, minimum=None):
    """Raise unless *value* is an int (and >= *minimum* when given)."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("%s must be an integer number of hertz, got %r" % (name, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s=%d must be at least %d" % (name, value, minimum))


def _output_min_hz(profile: ADF435xDeviceProfile) -> int:
    """Lowest reachable output frequency for *profile*."""
    return _ceil_div(VCO_MIN_HZ, profile.rf_divider_max)


def _compute_f_pfd(ref_hz, r_counter, doubler, rdiv2):
    """
    PFD frequency as an exact fraction.

    Returns
    -------
    tuple of (int, int)
        ``(pfd_num, pfd_den)`` with fPFD = pfd_num / pfd_den.

    Raises
    ------
    ValueError
        If *r_counter* is out of range or the doubler limit is exceeded.
    """
    r_max = (1 << consts.REG2_R_COUNTER_WIDTH) - 1
    if not isinstance(r_counter, int) or not (
        consts.REG2_R_COUNTER_MIN <= r_counter <= r_max
    ):
        raise ValueError("r_counter=%s out of range [1, %d]" % (r_counter, r_max))
    if doubler and ref_hz > REF_MAX_DOUBLER_HZ:
        raise ValueError(
            "ref_hz=%d exceeds doubler limit %d" % (ref_hz, REF_MAX_DOUBLER_HZ)
        )
    return ref_hz * (2 if doubler else 1), r_counter * (2 if rdiv2 else 1)


def _pick_rf_divider(target_hz: int, profile: ADF435xDeviceProfile) -> int:
    """
    Pick the smallest RF divider that places VCO in the tuning band.

    Raises
    ------
    NoSolutionError
        If no legal divider yields an in-band VCO frequency.
    """
    for div in profile.legal_rf_dividers():
        if VCO_MIN_HZ <= target_hz * div <= VCO_MAX_HZ:
            return div
    raise NoSolutionError(
        "no RF divider places VCO in [%d, %d] Hz for target %d"
        % (VCO_MIN_HZ, VCO_MAX_HZ, target_hz)
    )


def _pick_band_clk(pfd_num, pfd_den, profile):
    """
    Band-select clock divider and mode for an exact fPFD.

    Normal mode keeps the band-select clock at or below 125 kHz. On the
    ADF4351, fPFD above 125 kHz uses fast mode (<= 500 kHz, divider <= 254;
    data sheet p.19).

    Returns
    -------
    tuple of (int, int)
        ``(band_clk_div, band_clk_mode)``.

    Raises
    ------
    NoSolutionError
        If the required divider exceeds the mode's maximum.
    """
    fast = profile.has_fast_band_select and pfd_num > BANDSEL_MAX_HZ_NORMAL * pfd_den
    if fast:
        div = _ceil_div(pfd_num, BANDSEL_MAX_HZ_FAST * pfd_den)
        limit, mode = _FAST_BAND_CLK_DIV_MAX, consts.REG3_BAND_CLK_HIGH
    else:
        div = _ceil_div(pfd_num, BANDSEL_MAX_HZ_NORMAL * pfd_den)
        limit, mode = _BAND_CLK_DIV_MAX, consts.REG3_BAND_CLK_LOW
    if div > limit:
        raise NoSolutionError("band_clk_div=%d exceeds maximum %d" % (div, limit))
    return div, mode


def reference_fields(ref_hz, profile, options=None):
    """
    Reference-path and band-select fields for a reference and options.

    These do not depend on the output frequency, so the synthesizer applies
    them at construction.

    Parameters
    ----------
    ref_hz : int
        Reference input frequency in hertz.
    profile : ADF435xDeviceProfile
        Device profile.
    options : SolveOptions or None
        Supplies ``r_counter``, ``doubler`` and ``rdiv2``.

    Returns
    -------
    dict
        ``r_counter``, ``doubler``, ``rdiv2``, ``band_clk_div``,
        ``band_clk_mode``.

    Raises
    ------
    TypeError
        If *ref_hz* is not an integer.
    ValueError
        If the reference path is invalid.
    NoSolutionError
        If fPFD is above the fractional-N maximum or too high for the
        band-select clock.
    """
    opts = _resolve_options(options)
    _require_int("ref_hz", ref_hz, 1)
    pfd_num, pfd_den = _compute_f_pfd(ref_hz, opts.r_counter, opts.doubler, opts.rdiv2)
    if pfd_num > PFD_MAX_FRAC_HZ * pfd_den:
        raise NoSolutionError(
            "f_pfd=%d exceeds fractional-N maximum %d"
            % (_round_div(pfd_num, pfd_den), PFD_MAX_FRAC_HZ)
        )
    band_clk_div, band_clk_mode = _pick_band_clk(pfd_num, pfd_den, profile)
    return {
        "r_counter": opts.r_counter,
        "doubler": opts.doubler,
        "rdiv2": opts.rdiv2,
        "band_clk_div": band_clk_div,
        "band_clk_mode": band_clk_mode,
    }


def _farey_neighbors(num, den, qmax):
    """
    Closest fractions to ``num/den`` with denominators up to *qmax*.

    Walks the continued fraction of ``num/den``. If it is itself such a
    fraction, returns just that; otherwise returns the last convergent and the
    best semiconvergent, which bracket ``num/den`` and are its neighbours in
    the Farey sequence of order *qmax*.

    Returns
    -------
    list of (int, int)
        One or two ``(p, q)`` pairs.
    """
    p0, q0, p1, q1 = 0, 1, 1, 0
    n, d = num, den
    while d:
        t = n // d
        p2, q2 = t * p1 + p0, t * q1 + q0
        if q2 > qmax:
            k = (qmax - q0) // q1
            return [(p1, q1), (k * p1 + p0, k * q1 + q0)]
        p0, q0, p1, q1 = p1, q1, p2, q2
        n, d = d, n - t * d
    return [(p1, q1)]


def _simplest_between(lo_num, lo_den, hi_num, hi_den):
    """
    The fraction with the smallest denominator strictly between two bounds.

    Requires ``0 < lo_num/lo_den < hi_num/hi_den``. Uses the Stern-Brocot
    recursion: take the integer part shared by both bounds, then recurse on
    the reciprocals of the remainders.

    Returns
    -------
    tuple of (int, int)
        ``(p, q)`` in lowest terms.
    """
    p0, q0, p1, q1 = 0, 1, 1, 0
    while True:
        t = lo_num // lo_den
        if (t + 1) * hi_den < hi_num:
            # An integer lies strictly inside: t + 1 is the simplest.
            return (t + 1) * p1 + p0, (t + 1) * q1 + q0
        p0, q0, p1, q1 = p1, q1, t * p1 + p0, t * q1 + q0
        # New bounds: 1/(hi - t) < y < 1/(lo - t).
        lo_num, lo_den, hi_num, hi_den = (
            hi_den,
            hi_num - t * hi_den,
            lo_den,
            lo_num - t * lo_den,
        )
        if hi_den == 0:
            # lo was exactly t, so the upper bound is unbounded.
            t = lo_num // lo_den + 1
            return t * p1 + p0, t * q1 + q0


class _Plan:
    """Evaluates candidate N = n_num / mod for one solve request."""

    def __init__(self, target_hz, pfd_num, pfd_den, rf_divider, profile):
        self.target_hz = target_hz
        self.pfd_num = pfd_num
        self.pfd_den = pfd_den
        self.profile = profile
        # N = target * D / B, and output = N * B / D.
        self.big_d = pfd_den * rf_divider
        self.big_b = pfd_num
        self.n_target = target_hz * self.big_d

    def error(self, n_num, mod):
        """Exact |target - output| in hertz as ``(num, den)``."""
        return abs(self.n_target * mod - n_num * self.big_b), mod * self.big_d

    def prescaler(self, n_num, mod):
        """Prescaler for the exact VCO of this candidate."""
        vco_num = n_num * self.pfd_num
        if vco_num <= self.profile.prescaler_4_5_max_hz * mod * self.pfd_den:
            return consts.REG1_PRESCALER_4_5
        return consts.REG1_PRESCALER_8_9

    def valid(self, n_num, mod):
        """True if the VCO is in band and INT fits the prescaler's range."""
        vco_num, vco_den = n_num * self.pfd_num, mod * self.pfd_den
        if not VCO_MIN_HZ * vco_den <= vco_num <= VCO_MAX_HZ * vco_den:
            return False
        if self.prescaler(n_num, mod) == consts.REG1_PRESCALER_4_5:
            int_min = self.profile.int_min_4_5
        else:
            int_min = self.profile.int_min_8_9
        return int_min <= n_num // mod <= self.profile.int_max

    def fixed(self, mod):
        """Nearest N for a fixed MOD, as ``(n_num, mod)``."""
        return _round_div(self.n_target * mod, self.big_b), mod

    def search(self, mod_max):
        """
        Best N with MOD <= *mod_max*, preferring the smallest MOD among
        candidates whose error rounds to the same whole hertz.

        Returns
        -------
        tuple of (int, int) or None
            ``(n_num, mod)`` in lowest terms, or None if nothing is valid.
        """
        best = None
        for p, q in _farey_neighbors(self.n_target, self.big_b, mod_max):
            if not self.valid(p, q):
                continue
            if best is None or _less(self.error(p, q), self.error(*best), q, best[1]):
                best = (p, q)
        if best is None:
            return None
        err_num, err_den = self.error(*best)
        if err_num == 0:
            return best
        # Errors under (R + 1/2) Hz round to R Hz or better, R = round(best).
        whole = (2 * err_num + err_den) // (2 * err_den)
        slack = (2 * whole + 1) * self.big_d
        two_b = 2 * self.big_b
        p, q = _simplest_between(
            2 * self.n_target - slack, two_b, 2 * self.n_target + slack, two_b
        )
        if q <= mod_max and self.valid(p, q):
            return p, q
        return best


def _less(err_a, err_b, mod_a, mod_b):
    """True if error *a* (then MOD) is smaller than error *b*."""
    left = err_a[0] * err_b[1]
    right = err_b[0] * err_a[1]
    return left < right or (left == right and mod_a < mod_b)


def pll_mode_fields(integer_n, profile):
    """
    Lock detect, ABP, and charge-cancel fields for integer-N or fractional-N.

    Data sheet p.19-20: fractional-N uses LDF/LDP = 00, ABP 6 ns, charge
    cancel off; integer-N uses LDF/LDP = 11, ABP 3 ns, charge cancel on.
    Fractional-N settings also work at FRAC = 0, so a table may keep them for
    the integer channels of a fractional sweep.

    Parameters
    ----------
    integer_n : bool
        True for integer-N (FRAC = 0) settings.
    profile : ADF435xDeviceProfile
        Device profile; ABP and charge cancel are set only where present.

    Returns
    -------
    dict
    """
    fields = {
        "ldf": consts.REG2_LDF_INT_N if integer_n else consts.REG2_LDF_FRAC_N,
        "ldp": consts.REG2_LDP_6NS if integer_n else consts.REG2_LDP_10NS,
    }
    if profile.has_programmable_abp:
        fields["abp"] = consts.REG3_ABP_3NS if integer_n else consts.REG3_ABP_6NS
    if profile.has_charge_cancel:
        fields["charge_cancel"] = integer_n
    return fields


def _fixed_mod(opts, pfd_num, pfd_den, rf_divider, profile):
    """MOD from ``options.mod`` or ``options.channel_step_hz``, or None."""
    if opts.mod is not None:
        mod = opts.mod
    elif opts.channel_step_hz is not None:
        step = opts.channel_step_hz
        _require_int("channel_step_hz", step, 1)
        den = pfd_den * step * rf_divider
        if pfd_num % den:
            raise ValueError(
                "channel_step_hz=%d does not divide fPFD / RF divider evenly"
                % step
            )
        mod = pfd_num // den
    else:
        return None
    if not isinstance(mod, int) or not profile.mod_min <= mod <= profile.mod_max:
        raise ValueError(
            "MOD=%s out of range [%d, %d]" % (mod, profile.mod_min, profile.mod_max)
        )
    return mod


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
        Field dict, achieved frequency, signed error, fPFD, VCO frequency,
        and whether the result is exact.

    Raises
    ------
    TypeError
        If *target_hz* or *ref_hz* is not an integer.
    FrequencyOutOfRangeError
        If *target_hz* is outside the reachable output range.
    NoSolutionError
        If no valid PLL configuration exists.
    ExactFrequencyError
        If ``options.exact`` is True and the output is not exactly the target.
    ValueError
        If reference-path parameters or options are invalid.
    """
    opts = _resolve_options(options)
    _require_int("target_hz", target_hz)
    reference = reference_fields(ref_hz, profile, opts)

    out_min = _output_min_hz(profile)
    if target_hz < out_min or target_hz > VCO_MAX_HZ:
        raise FrequencyOutOfRangeError(
            "target_hz=%d outside [%d, %d]" % (target_hz, out_min, VCO_MAX_HZ)
        )

    pfd_num, pfd_den = _compute_f_pfd(ref_hz, opts.r_counter, opts.doubler, opts.rdiv2)

    if opts.rf_divider is not None:
        profile.divider_code(opts.rf_divider)  # raises naming rf_divider
        rf_divider = opts.rf_divider
    else:
        rf_divider = _pick_rf_divider(target_hz, profile)

    plan = _Plan(target_hz, pfd_num, pfd_den, rf_divider, profile)
    mod = _fixed_mod(opts, pfd_num, pfd_den, rf_divider, profile)
    if mod is not None:
        candidate = plan.fixed(mod)
        if not plan.valid(*candidate):
            candidate = None
    else:
        candidate = plan.search(profile.mod_max)
    if candidate is None:
        raise NoSolutionError(
            "no MOD/INT/FRAC solution for target %d Hz with RF divider %d"
            % (target_hz, rf_divider)
        )
    n_num, mod = candidate

    # Raise MOD to the requested minimum without changing N.
    mod_min = max(profile.mod_min, opts.mod_min or 0)
    if mod < mod_min:
        if opts.mod is not None or opts.channel_step_hz is not None:
            raise ValueError("MOD=%d below required minimum %d" % (mod, mod_min))
        scale = _ceil_div(mod_min, mod)
        n_num, mod = n_num * scale, mod * scale

    int_n, frac = n_num // mod, n_num % mod
    fields = {
        "int_n": int_n,
        "frac": frac,
        "mod": mod,
        "prescaler": plan.prescaler(n_num, mod),
        "rf_divider": rf_divider,
        "feedback": consts.REG4_FEEDBACK_FUNDAMENTAL,
    }
    fields.update(reference)
    fields.update(pll_mode_fields(frac == 0, profile))

    err_num, _ = plan.error(n_num, mod)
    achieved_hz = _round_div(n_num * pfd_num, mod * plan.big_d)
    if opts.exact and err_num:
        raise ExactFrequencyError(
            "target_hz=%d not exactly achievable (nearest %d Hz)"
            % (target_hz, achieved_hz)
        )

    return SolveResult(
        fields=fields,
        achieved_hz=achieved_hz,
        error_hz=target_hz - achieved_hz,
        f_pfd_hz=_round_div(pfd_num, pfd_den),
        vco_hz=_round_div(n_num * pfd_num, mod * pfd_den),
        exact=err_num == 0,
        f_pfd_fraction=(pfd_num, pfd_den),
    )


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
