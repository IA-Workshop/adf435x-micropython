"""
Device profiles for the ADF435x family.

A DeviceProfile captures only the differences between the ADF4350 and ADF4351
parts from one, such as the capability bits they implement and the
output-divider range. The field positions, widths, and value encodings that
are common to both parts are implemented in ``consts`` and shared.

Notes
-----
Only ADF4530 and ADF4351 parts are supported. Support for other device
families should be implemented elsewhere.
"""

def _is_power_of_two(value: int) -> bool:
    """Return True if ``value`` is a positive power of two."""
    return value > 0 and (value & (value - 1)) == 0


class DeviceProfile:
    """
    Per-device capabilities and bounds for an ADF435x synthesizer.

    Only device-specific differences are held here; the shared field layout is
    defined in ``consts``.

    Parameters
    ----------
    name : str
        Human-readable device name.
    rf_divider_max : int
        Largest available RF output divider (16 for the ADF4350, 64 for the
        ADF4351). Valid dividers are the powers of two from 1 to this value.
    has_phase_adjust : bool
        Whether the phase-adjust bit (R1 DB28) is implemented.
    has_fast_band_select : bool
        Whether the fast band-select clock mode (R3 DB23) is available.
    has_programmable_abp : bool
        Whether the antibacklash pulse width (R3 DB22) is programmable; if not,
        the part uses a fixed 3 ns pulse.
    has_charge_cancel : bool
        Whether charge-pump charge cancellation (R3 DB21) is available.
    prescaler_4_5_max_hz : int
        Highest VCO frequency permitted with the 4/5 prescaler; above this the
        8/9 prescaler is required. Used by the solver, not the encoder.
    """
    def __init__(self,
                 name: str,
                 rf_divider_max: int,
                 has_phase_adjust: bool,
                 has_fast_band_select: bool,
                 has_programmable_abp: bool,
                 has_charge_cancel: bool,
                 prescaler_4_5_max_hz: int):
        self.name = name
        self.rf_divider_max = rf_divider_max
        self.has_phase_adjust = has_phase_adjust
        self.has_fast_band_select = has_fast_band_select
        self.has_programmable_abp = has_programmable_abp
        self.has_charge_cancel = has_charge_cancel
        self.prescaler_4_5_max_hz = prescaler_4_5_max_hz

    def divider_code(self, rf_divider: int) -> int:
        """Map an RF output divider to its 3-bit R4 code.

        The code is the base-2 logarithm of the divider: 0 for /1, 1 for /2, 2
        for /4, and so on up to the device maximum.

        Parameters
        ----------
        rf_divider : int
            Output divider; a power of two from 1 to ``rf_divider_max``.

        Returns
        -------
        int
            The divider-select code.

        Raises
        ------
        ValueError
            If ``rf_divider`` is not a power of two within range for this device.
        """
        if not _is_power_of_two(rf_divider) or rf_divider > self.rf_divider_max:
            raise ValueError(
                "%s: rf_divider=%d must be a power of two in [1, %d]"
                % (self.name, rf_divider, self.rf_divider_max))
        code = 0
        value = rf_divider
        while value > 1:
            value >>= 1
            code += 1
        return code

    def __repr__(self) -> str:
        return "DeviceProfile(%s)" % self.name


ADF4350 = DeviceProfile(
    name="ADF4350",
    rf_divider_max=16,
    has_phase_adjust=False,
    has_fast_band_select=False,
    has_programmable_abp=False,
    has_charge_cancel=False,
    prescaler_4_5_max_hz=3_000_000_000,
)

ADF4351 = DeviceProfile(
    name="ADF4351",
    rf_divider_max=64,
    has_phase_adjust=True,
    has_fast_band_select=True,
    has_programmable_abp=True,
    has_charge_cancel=True,
    prescaler_4_5_max_hz=3_600_000_000,
)
