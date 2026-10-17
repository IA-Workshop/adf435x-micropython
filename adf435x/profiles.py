"""Device profiles: what differs between the ADF4350 and the ADF4351.

A profile holds the features each part has and its RF divider range. The
register layout both parts share is in ``consts``. Other ADF435x parts have
a different register map and are not supported.
"""


def _is_power_of_two(value: int) -> bool:
    """True if *value* is 1, 2, 4, 8, ...; False for 0 and negatives."""
    return value > 0 and (value & (value - 1)) == 0


def _log2_power_of_two(value: int) -> int:
    """Return *n* where ``value == 2 ** n``; for example 8 gives 3.

    MicroPython's ``int`` has no ``bit_length()``, so this counts shifts.
    """
    code = 0
    while value > 1:
        value >>= 1
        code += 1
    return code


class ADF435xDeviceProfile:
    """
    Features and limits of one ADF435x part.

    Use the ready-made ``ADF4350`` and ``ADF4351`` profiles. The ``has_*``
    flags are all False on the ADF4350 and True on the ADF4351.

    Parameters
    ----------
    name : str
        Part name.
    rf_divider_max : int
        Largest RF divider: 16 (ADF4350) or 64 (ADF4351). Every power of two
        from 1 up to it is legal.
    has_phase_adjust : bool
        Phase adjust bit, R1 DB28.
    has_fast_band_select : bool
        Fast band-select clock mode, R3 DB23.
    has_programmable_abp : bool
        Settable antibacklash pulse, R3 DB22. Without it the pulse is 3 ns.
    has_charge_cancel : bool
        Charge-pump charge cancellation, R3 DB21.
    prescaler_4_5_max_hz : int
        Highest VCO frequency for the 4/5 prescaler; above it the solver
        uses 8/9.
    int_min_4_5, int_min_8_9 : int
        Smallest INT with each prescaler (23 and 75).
    int_max : int
        Largest INT (65535).
    mod_min, mod_max : int
        MOD range (2 to 4095).
    """

    def __init__(
        self,
        name: str,
        rf_divider_max: int,
        has_phase_adjust: bool,
        has_fast_band_select: bool,
        has_programmable_abp: bool,
        has_charge_cancel: bool,
        prescaler_4_5_max_hz: int,
        int_min_4_5: int = 23,
        int_min_8_9: int = 75,
        int_max: int = 65535,
        mod_min: int = 2,
        mod_max: int = 4095,
    ):
        """Store the flags and limits."""
        self.name = name
        self.rf_divider_max = rf_divider_max
        self.has_phase_adjust = has_phase_adjust
        self.has_fast_band_select = has_fast_band_select
        self.has_programmable_abp = has_programmable_abp
        self.has_charge_cancel = has_charge_cancel
        self.prescaler_4_5_max_hz = prescaler_4_5_max_hz
        self.int_min_4_5 = int_min_4_5
        self.int_min_8_9 = int_min_8_9
        self.int_max = int_max
        self.mod_min = mod_min
        self.mod_max = mod_max

    def divider_code(self, rf_divider: int) -> int:
        """Return the 3-bit R4 code for *rf_divider*, which is its log2.

        For example 1 gives 0, 2 gives 1 and 32 gives 5. Raises
        ``ValueError`` if *rf_divider* is not a power of two from 1 to
        ``rf_divider_max`` (so 3 fails on both parts and 64 on the ADF4350).
        """
        if not _is_power_of_two(rf_divider) or rf_divider > self.rf_divider_max:
            raise ValueError(
                "%s: rf_divider=%d must be a power of two in [1, %d]"
                % (self.name, rf_divider, self.rf_divider_max)
            )
        return _log2_power_of_two(rf_divider)

    def legal_rf_dividers(self):
        """Return the legal RF dividers in ascending order: 1, 2, 4, ..."""
        count = _log2_power_of_two(self.rf_divider_max) + 1
        return tuple(1 << i for i in range(count))

    def __repr__(self) -> str:
        """Return ``ADF435xDeviceProfile(<name>)``."""
        return "ADF435xDeviceProfile(%s)" % self.name


ADF4350 = ADF435xDeviceProfile(
    name="ADF4350",
    rf_divider_max=16,
    has_phase_adjust=False,
    has_fast_band_select=False,
    has_programmable_abp=False,
    has_charge_cancel=False,
    prescaler_4_5_max_hz=3_000_000_000,
)

ADF4351 = ADF435xDeviceProfile(
    name="ADF4351",
    rf_divider_max=64,
    has_phase_adjust=True,
    has_fast_band_select=True,
    has_programmable_abp=True,
    has_charge_cancel=True,
    prescaler_4_5_max_hz=3_600_000_000,
)
