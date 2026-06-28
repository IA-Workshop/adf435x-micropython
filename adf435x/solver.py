"""
Frequency-to-register solver for ADF435x PLLs (not yet implemented).

Future work: given a target output frequency and fixed fPFD, solve for INT,
FRAC, MOD, prescaler, and RF output divider. Shared limits, rounding helpers,
and ``limits_for_profile()`` are defined for tests and downstream callers.

Glossary
--------
PFD : Phase-frequency detector
fPFD : PFD comparison frequency, REFIN * (1 + D) / (R * (1 + T))
VCO : Voltage-controlled oscillator
INT : Integer part of the feedback division factor N
FRAC : Fractional numerator of N, with 0 <= FRAC < MOD
MOD : Fractional modulus; the channel-step divisor
N : Feedback divider, N = INT + FRAC / MOD, with f_VCO = N * fPFD
RF divider : Output divider (1, 2, 4, ... 64) that divides f_VCO down to the
    requested output, used to reach frequencies below the VCO band
"""

from . import consts
from .profiles import ADF435xDeviceProfile

# Device-agnostic limits shared by ADF4350 and ADF4351 (integer Hz).
VCO_MIN_HZ = 2_200_000_000
VCO_MAX_HZ = 4_400_000_000
BANDSEL_MAX_HZ_NORMAL = 125_000
BANDSEL_MAX_HZ_FAST = 500_000
PFD_MAX_FRAC_HZ = 32_000_000
PFD_MAX_INT_HZ = 90_000_000
REF_MAX_DOUBLER_HZ = 30_000_000


def _round_div(num: int, den: int) -> int:
    """
    Divide two non-negative integers, rounding to the nearest integer. Ties
    are rounded up (toward positive infinity).

    Parameters
    ----------
    num : int
        Non-negative numerator.
    den : int
        Non-negative denominator.

    Returns
    -------
    int
        The value of ``num / den`` rounded to the nearest integer.
    """
    return (num + den // 2) // den


def _ceil_div(num: int, den: int) -> int:
    """
    Divide two non-negative integers, rounding up to the next integer.

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
    Greatest common divisor of two integers (Euclidean algorithm).

    MicroPython-safe: does not rely on ``math.gcd``.

    Parameters
    ----------
    a, b : int
        Operands; negative values are handled via absolute value.

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


class DeviceLimits:
    """
    Parameter bounds for an ADF435x fractional-N frequency synthesizer.

    Construct via ``limits_for_profile()``; profile-specific fields
    (``rf_dividers``, ``prescaler_4_5_max_hz``) have no defaults.

    Parameters
    ----------
    rf_dividers : tuple of int
        Available RF output divider values, ascending.
    prescaler_4_5_max_hz : int
        Highest VCO frequency permitted with the 4/5 prescaler; above this the
        8/9 prescaler is mandatory.
    vco_min_hz, vco_max_hz : int
        Fundamental VCO tuning range in hertz.
    int_min_4_5, int_min_8_9 : int
        Minimum allowed INT value for the 4/5 and 8/9 prescalers.
    int_max : int
        Maximum allowed INT value.
    mod_min, mod_max : int
        Inclusive bounds on the fractional modulus MOD.
    pfd_max_frac_hz, pfd_max_int_hz : int
        Maximum fPFD in fractional-N and integer-N operation.
    ref_max_doubler_hz : int
        Maximum reference input frequency when the reference doubler is enabled.
    """

    def __init__(
        self,
        *,
        rf_dividers: tuple[int, ...],
        prescaler_4_5_max_hz: int,
        vco_min_hz: int = VCO_MIN_HZ,
        vco_max_hz: int = VCO_MAX_HZ,
        int_min_4_5: int = 23,
        int_min_8_9: int = 75,
        int_max: int = 65535,
        mod_min: int = 2,
        mod_max: int = 4095,
        pfd_max_frac_hz: int = PFD_MAX_FRAC_HZ,
        pfd_max_int_hz: int = PFD_MAX_INT_HZ,
        ref_max_doubler_hz: int = REF_MAX_DOUBLER_HZ,
    ):
        self.vco_min_hz = vco_min_hz
        self.vco_max_hz = vco_max_hz
        self.int_min_4_5 = int_min_4_5
        self.int_min_8_9 = int_min_8_9
        self.int_max = int_max
        self.mod_min = mod_min
        self.mod_max = mod_max
        self.rf_dividers = rf_dividers
        self.prescaler_4_5_max_hz = prescaler_4_5_max_hz
        self.pfd_max_frac_hz = pfd_max_frac_hz
        self.pfd_max_int_hz = pfd_max_int_hz
        self.ref_max_doubler_hz = ref_max_doubler_hz

    @property
    def output_min_hz(self) -> int:
        """Lowest reachable output frequency, VCO minimum over the largest divider."""
        return _round_div(self.vco_min_hz, self.rf_dividers[-1])

    @property
    def output_max_hz(self) -> int:
        """Highest reachable output frequency, equal to the VCO maximum."""
        return self.vco_max_hz


def limits_for_profile(profile: ADF435xDeviceProfile) -> DeviceLimits:
    """
    Build solver limits from a device profile and shared VCO/PFD constants.

    Parameters
    ----------
    profile : ADF435xDeviceProfile
        Device profile supplying INT/MOD bounds, prescaler threshold, and
        maximum RF output divider.

    Returns
    -------
    DeviceLimits
        Limits tailored to *profile* with device-agnostic VCO and PFD caps.
    """
    dividers = tuple(
        1 << i for i in range(profile.rf_divider_max.bit_length())
    )
    return DeviceLimits(
        rf_dividers=dividers,
        prescaler_4_5_max_hz=profile.prescaler_4_5_max_hz,
        int_min_4_5=profile.int_min_4_5,
        int_min_8_9=profile.int_min_8_9,
        int_max=profile.int_max,
        mod_min=profile.mod_min,
        mod_max=profile.mod_max,
    )


# Prescaler register values (same encoding as consts.REG1_PRESCALER_*).
PRESCALER_4_5 = consts.REG1_PRESCALER_4_5
PRESCALER_8_9 = consts.REG1_PRESCALER_8_9
