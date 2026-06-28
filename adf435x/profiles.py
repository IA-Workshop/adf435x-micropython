"""
Device profiles for the ADF435x family.

An ADF435xDeviceProfile captures only what differs between the ADF4350 and
ADF4351: the capability bits each part implements and the output-divider range.
The field positions, widths, and value encodings common to both parts live in
``consts`` and are shared.

Notes
-----
Only the ADF4350 and ADF4351 are supported. Other device families have a
different register map and belong elsewhere.
"""


def _is_power_of_two(value: int) -> bool:
    """Test whether an integer is a positive power of two.

    Parameters
    ----------
    value : int
        Value to test.

    Returns
    -------
    bool
        True if *value* is 1, 2, 4, 8, ...; False otherwise (including 0 and
        negatives).
    """
    return value > 0 and (value & (value - 1)) == 0


def _log2_power_of_two(value: int) -> int:
    """Return log2 of a positive power of two.

    MicroPython-safe: does not use ``int.bit_length``.

    Parameters
    ----------
    value : int
        A power of two (1, 2, 4, 8, ...).

    Returns
    -------
    int
        Exponent *n* where ``value == 2 ** n`` (for example, 8 -> 3).
    """
    code = 0
    while value > 1:
        value >>= 1
        code += 1
    return code


class ADF435xDeviceProfile:
    """
    Per-device capabilities for an ADF435x synthesizer.

    Only device-specific differences are held here; the shared field layout is
    in ``consts``.

    Parameters
    ----------
    name : str
        Device name.
    rf_divider_max : int
        Largest RF output divider (16 for the ADF4350, 64 for the ADF4351).
        Valid dividers are the powers of two from 1 to this value.
    has_phase_adjust : bool
        Whether the phase-adjust bit (R1 DB28) is implemented. False on ADF4350;
        True on ADF4351.
    has_fast_band_select : bool
        Whether the fast band-select clock mode (R3 DB23) is available. False
        on ADF4350; True on ADF4351.
    has_programmable_abp : bool
        Whether the antibacklash pulse width (R3 DB22) is programmable. If not,
        the part uses a fixed 3 ns pulse (ADF4350).
    has_charge_cancel : bool
        Whether charge-pump charge cancellation (R3 DB21) is available. False on
        ADF4350; True on ADF4351.
    prescaler_4_5_max_hz : int
        Highest VCO frequency allowed with the 4/5 prescaler; above this the 8/9
        prescaler is required. Used by the solver, not the encoder.
    int_min_4_5 : int
        Minimum INT with the 4/5 prescaler (datasheet NMIN = 23).
    int_min_8_9 : int
        Minimum INT with the 8/9 prescaler (datasheet NMIN = 75).
    int_max : int
        Maximum INT (65,535).
    mod_min : int
        Minimum fractional modulus (2).
    mod_max : int
        Maximum fractional modulus (4,095).
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
        """Store the per-device capability flags and divider/PLL bounds."""
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
        """Map an RF output divider to its 3-bit R4 code.

        The code is log2 of the divider: 0 for /1, 1 for /2, and so on up to the
        device maximum.

        Parameters
        ----------
        rf_divider : int
            Output divider; a power of two from 1 to ``rf_divider_max``.
            Examples: 1 -> code 0, 2 -> code 1, 32 -> code 5 (ADF4351).

        Returns
        -------
        int
            The divider-select code (log2 of the divider).

        Raises
        ------
        ValueError
            If ``rf_divider`` is not a power of two within range for this
            device (for example, 64 on ADF4350, or 3 on either part).
        """
        if not _is_power_of_two(rf_divider) or rf_divider > self.rf_divider_max:
            raise ValueError(
                "%s: rf_divider=%d must be a power of two in [1, %d]"
                % (self.name, rf_divider, self.rf_divider_max)
            )
        return _log2_power_of_two(rf_divider)

    def legal_rf_dividers(self):
        """
        Return ascending legal RF output dividers for this device.

        Returns
        -------
        tuple of int
            Powers of two from 1 through ``rf_divider_max``.
        """
        count = _log2_power_of_two(self.rf_divider_max) + 1
        return tuple(1 << i for i in range(count))

    def __repr__(self) -> str:
        """Return a short debug representation naming the device.

        Returns
        -------
        str
            For example, ``ADF435xDeviceProfile(ADF4351)``.
        """
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
