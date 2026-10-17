"""Work out the PLL register fields for a target output frequency.

``solve()`` returns field values, which ``ADF435xRegisterFile.configure()``
then checks and encodes. All the arithmetic uses integers: fPFD is kept as
the exact fraction ``pfd_num / pfd_den`` (MicroPython has no ``fractions``
module), so the reported frequencies and errors match the chip. The
relationships it uses, with symbols as in docs/symbols.md:

    fPFD = REFIN * (1 + D) / (R * (1 + T))   D: doubler, T: divide-by-2
    fVCO = fPFD * N,  N = INT + FRAC / MOD
    fOUT = fVCO / RF divider
"""

from . import consts
from .profiles import ADF435xProfile

# Limits shared by the ADF4350 and ADF4351, in hertz.
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
    """The target frequency is outside the part's output range."""


class NoSolutionError(ValueError):
    """No legal combination of PLL settings reaches the target."""


class ExactFrequencyError(ValueError):
    """``exact=True`` was asked for, but the target is not exactly reachable."""


class SolveOptions:
    """
    Options for ``solve()``. See docs/frequency-planning.md.

    Parameters
    ----------
    r_counter : int
        Reference divider R, 1 to 1023.
    doubler : bool
        Turn on the reference doubler.
    rdiv2 : bool
        Turn on the reference divide-by-2.
    mod : int or None
        Use this MOD as given, with no search and no reduction.
    rf_divider : int or None
        Use this RF divider instead of choosing one.
    channel_step_hz : int or None
        Channel step at the RF output. MOD becomes
        fPFD / (step * RF divider), which must be a whole number in range.
    exact : bool
        Raise ``ExactFrequencyError`` unless the output is exactly the target.
    mod_min : int or None
        Smallest MOD to use. The synthesizer passes 50 in low-spur noise
        mode (data sheet p.23).
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
        """Store the options."""
        self.r_counter = r_counter
        self.doubler = doubler
        self.rdiv2 = rdiv2
        self.mod = mod
        self.rf_divider = rf_divider
        self.channel_step_hz = channel_step_hz
        self.exact = exact
        self.mod_min = mod_min

    def copy(self, **overrides):
        """Return a copy with the options in *overrides* changed.

        An unknown option name raises ``TypeError``.
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


def _resolve_options(options):
    """Return *options*, or a default ``SolveOptions()`` if it is None."""
    return options if options is not None else SolveOptions()


class SolveResult:
    """
    What ``solve()`` found.

    Parameters
    ----------
    fields : dict
        Register fields to pass to ``ADF435xRegisterFile.configure()``:
        ``int_n``, ``frac``, ``mod``, ``prescaler``, ``r_counter``,
        ``doubler``, ``rdiv2``, ``rf_divider``, ``band_clk_div``,
        ``band_clk_mode``, ``feedback``, ``ldf``, ``ldp``, and, on parts that
        have them, ``abp`` and ``charge_cancel``.
    achieved_hz : int
        Output frequency, rounded to the nearest hertz.
    error_hz : int
        ``target_hz - achieved_hz``.
    f_pfd_hz : int
        fPFD rounded to the nearest hertz, for display.
    vco_hz : int
        VCO frequency, rounded to the nearest hertz.
    exact : bool
        True only when the output is exactly the target, to the sub-hertz.
    pfd_fraction : tuple of (int, int)
        Exact fPFD as ``(numerator, denominator)``.
    """

    def __init__(
        self, fields, achieved_hz, error_hz, f_pfd_hz, vco_hz, exact, pfd_fraction
    ):
        """Store the result."""
        self.fields = fields
        self.achieved_hz = achieved_hz
        self.error_hz = error_hz
        self.f_pfd_hz = f_pfd_hz
        self.vco_hz = vco_hz
        self.exact = exact
        self.pfd_fraction = pfd_fraction


def _round_div(num: int, den: int) -> int:
    """Divide non-negative integers, rounding to nearest (ties up)."""
    return (num + den // 2) // den


def _ceil_div(num: int, den: int) -> int:
    """Divide non-negative integers, rounding up."""
    return (num + den - 1) // den


def _require_int(name, value, minimum=None):
    """Raise unless *value* is an int, and at least *minimum* if given."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("%s must be an integer number of hertz, got %r" % (name, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s=%d must be at least %d" % (name, value, minimum))


def _output_min_hz(profile: ADF435xProfile) -> int:
    """Return the lowest output frequency *profile* can reach."""
    return _ceil_div(VCO_MIN_HZ, profile.rf_divider_max)


def _compute_f_pfd(ref_hz, r_counter, doubler, rdiv2):
    """Return fPFD as ``(pfd_num, pfd_den)``, so fPFD = pfd_num / pfd_den.

    Raises ``ValueError`` if *r_counter* is out of range, or the doubler is
    on with a reference above its limit.
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


def _pick_rf_divider(target_hz: int, profile: ADF435xProfile) -> int:
    """Return the smallest RF divider that puts the VCO in its range.

    Raises ``NoSolutionError`` if no legal divider does.
    """
    for div in profile.legal_rf_dividers():
        if VCO_MIN_HZ <= target_hz * div <= VCO_MAX_HZ:
            return div
    raise NoSolutionError(
        "no RF divider places VCO in [%d, %d] Hz for target %d"
        % (VCO_MIN_HZ, VCO_MAX_HZ, target_hz)
    )


def _pick_band_clk(pfd_num, pfd_den, profile):
    """Return ``(band_clk_div, band_clk_mode)`` for the exact fPFD given.

    Normal mode keeps the band-select clock at or below 125 kHz. On the
    ADF4351 an fPFD above 125 kHz uses fast mode instead: at most 500 kHz,
    with a divider of at most 254 (data sheet p.19). Raises
    ``NoSolutionError`` if the divider would be too large.
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
    """Return the reference path and band-select fields as a dict.

    The keys are ``r_counter``, ``doubler``, ``rdiv2`` (taken from
    *options*), ``band_clk_div`` and ``band_clk_mode``. None depend on the
    output frequency, so the synthesizer sets them once, when it is created.
    Raises ``TypeError`` if *ref_hz* is not an integer, ``ValueError`` for
    an illegal reference path, and ``NoSolutionError`` if fPFD is above
    32 MHz or too high for the band-select clock.
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
    """Return the closest fractions ``(p, q)`` to num/den with q <= *qmax*.

    Walks the continued fraction of num/den. If num/den itself has a small
    enough denominator, the list holds just that fraction. Otherwise it holds
    the two fractions either side of num/den: its neighbors in the Farey
    sequence of order *qmax*.
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
    """Return the fraction ``(p, q)`` with the smallest q strictly between
    lo_num/lo_den and hi_num/hi_den, in lowest terms.

    Needs 0 < lo < hi. Works down the Stern-Brocot tree: take the integer
    part both bounds share, then repeat on the reciprocals of what is left.
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
    """Scores candidate values N = n_num / mod for one target."""

    def __init__(self, target_hz, pfd_num, pfd_den, rf_divider, profile):
        self.target_hz = target_hz
        self.pfd_num = pfd_num
        self.pfd_den = pfd_den
        self.profile = profile

        # N = target * big_d / big_b, and output = N * big_b / big_d.
        self.big_d = pfd_den * rf_divider
        self.big_b = pfd_num
        self.n_target = target_hz * self.big_d

    def error(self, n_num, mod):
        """Return the exact |target - output| in hertz as ``(num, den)``."""
        return abs(self.n_target * mod - n_num * self.big_b), mod * self.big_d

    def prescaler(self, n_num, mod):
        """Return the prescaler code this candidate's VCO frequency needs."""
        vco_num = n_num * self.pfd_num
        if vco_num <= self.profile.prescaler_4_5_max_hz * mod * self.pfd_den:
            return consts.REG1_PRESCALER_4_5
        return consts.REG1_PRESCALER_8_9

    def valid(self, n_num, mod):
        """True if the VCO is in range and INT is legal for the prescaler."""
        vco_num, vco_den = n_num * self.pfd_num, mod * self.pfd_den
        if not VCO_MIN_HZ * vco_den <= vco_num <= VCO_MAX_HZ * vco_den:
            return False
        if self.prescaler(n_num, mod) == consts.REG1_PRESCALER_4_5:
            int_min = self.profile.int_min_4_5
        else:
            int_min = self.profile.int_min_8_9
        return int_min <= n_num // mod <= self.profile.int_max

    def fixed(self, mod):
        """Return the nearest N for a fixed MOD, as ``(n_num, mod)``."""
        return _round_div(self.n_target * mod, self.big_b), mod

    def search(self, mod_max):
        """Return the best N with MOD <= *mod_max* as ``(n_num, mod)``.

        Among candidates whose errors round to the same whole hertz, the
        smallest MOD wins. The result is in lowest terms, or None if no
        candidate is legal.
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
        # Look for the smallest MOD whose error rounds to w Hz or better,
        # where w = round(best error). That is any error below w + 1/2 Hz.
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
    """True if error *a* is smaller than error *b*, or equal with a smaller MOD."""
    left = err_a[0] * err_b[1]
    right = err_b[0] * err_a[1]
    return left < right or (left == right and mod_a < mod_b)


def pll_mode_fields(integer_n, profile):
    """Return the lock-detect, ABP and charge-cancel fields for a PLL mode.

    *integer_n* picks integer-N settings (LDF and LDP 1, ABP 3 ns, charge
    cancel on) instead of fractional-N ones (LDF and LDP 0, ABP 6 ns, charge
    cancel off), as data sheet pp.19 to 20 recommend. ABP and charge cancel
    are left out on parts without them. Fractional-N settings also work at
    FRAC = 0, so a table may keep them for its integer channels.
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
    """Return the MOD set by ``opts.mod`` or ``opts.channel_step_hz``, or None."""
    if opts.mod is not None:
        mod = opts.mod
    elif opts.channel_step_hz is not None:
        step = opts.channel_step_hz
        _require_int("channel_step_hz", step, 1)
        den = pfd_den * step * rf_divider
        if pfd_num % den:
            raise ValueError(
                "channel_step_hz=%d does not divide fPFD / RF divider evenly" % step
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
    Return a ``SolveResult`` for *target_hz* from a *ref_hz* reference.

    Picks the smallest RF divider that keeps the VCO in range, then the N
    nearest the target. See docs/frequency-planning.md.

    Parameters
    ----------
    target_hz, ref_hz : int
        Output and reference frequencies, in whole hertz.
    profile : ADF435xProfile
        ``ADF4350`` or ``ADF4351``.
    options : SolveOptions or None
        Reference path and MOD options.

    Raises
    ------
    TypeError
        A frequency is not an integer.
    FrequencyOutOfRangeError
        *target_hz* is outside the part's output range.
    NoSolutionError
        No legal PLL settings reach the target.
    ExactFrequencyError
        ``options.exact`` is set and the target is not exactly reachable.
    ValueError
        The reference path or an option is illegal.
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
        profile.divider_code(opts.rf_divider)  # raises if illegal
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

    # Raise MOD to the minimum, scaling FRAC with it so N stays the same.
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
        pfd_fraction=(pfd_num, pfd_den),
    )


def output_band_hz(rf_divider):
    """Return ``(min_hz, max_hz)``, the output range of an RF divider.

    That is the VCO range divided by *rf_divider*.
    """
    return (_ceil_div(VCO_MIN_HZ, rf_divider), VCO_MAX_HZ // rf_divider)


def divider_max_hz(rf_divider, profile):
    """Return the highest output frequency at which the solver picks *rf_divider*.

    The solver tries dividers from smallest up, so *rf_divider* is chosen
    only where the next smaller divider cannot reach.
    """
    _, band_hi = output_band_hz(rf_divider)
    if rf_divider <= 1:
        return band_hi
    smaller = rf_divider // 2
    if smaller not in profile.legal_rf_dividers():
        return band_hi
    # The next smaller divider takes over at ceil(VCO_MIN / smaller).
    return min(band_hi, _ceil_div(VCO_MIN_HZ, smaller) - 1)
