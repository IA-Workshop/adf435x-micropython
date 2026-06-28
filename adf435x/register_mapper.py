"""
Profile-aware register encoder for the ADF435x family.

An ADF435xRegisterMapper turns field values into the six 32-bit register words used in
the ADF435x devices. It uses the shared bit layout in ``consts`` along with a
``ADF435xDeviceProfile`` to handle the fields that differ between the ADF4350 and
ADF4351.

Notes
-----
Register field positions and encodings are defined in the register maps that
begin at Figure 23 (p. 14) of both the ADF4350 and ADF4351 datasheets. Each
method below cites the figure for the register it encodes.
"""
from . import consts
from .profiles import ADF435xDeviceProfile


class ADF435xRegisterMapper:
    """
    Encode ADF435x register words for a specific device profile.

    Parameters
    ----------
    profile : ADF435xDeviceProfile
        The target device. Selects the capability-gated fields and the
        RF-divider code mapping.
    """

    def __init__(self, profile: ADF435xDeviceProfile):
        self._profile = profile

    def _check_field(self, value: int, bits: int, name: str) -> int:
        """Validate that an unsigned value fits in a fixed-width field.

        Parameters
        ----------
        value : int
            The value to place in the field.
        bits : int
            Field width in bits.
        name : str
            Field name, used in the error message.

        Returns
        -------
        int
            The validated value, unchanged.

        Raises
        ------
        ValueError
            If ``value`` is negative or does not fit in ``bits`` bits.
        """
        if value < 0 or value >= (1 << bits):
            raise ValueError(f"{name}={value} does not fit in {bits} bits")
        return value

    @property
    def profile(self) -> ADF435xDeviceProfile:
        """The device profile this mapper encodes for."""
        return self._profile

    def register_0(self, int_n: int, frac: int) -> int:
        """Encode register 0 (R0) from the INT and FRAC divider values.

        Parameters
        ----------
        int_n : int
            16-bit integer division value (INT), bit field DB30:DB15. Sets the
            integer part of the feedback division factor.
        frac : int
            12-bit fractional division value (FRAC), bit field DB14:DB3. The
            numerator of the fractional division; must be less than MOD.

        Returns
        -------
        int
            The 32-bit R0 word, with control bits DB2:DB0 = 0b000.

        Notes
        -----
        See datasheet Figure 24 (Register 0).
        """
        self._check_field(int_n, consts.REG0_INT_WIDTH, "INT")
        self._check_field(frac, consts.REG0_FRAC_WIDTH, "FRAC")
        word = 0
        word |= int_n << consts.REG0_INT_POS
        word |= frac << consts.REG0_FRAC_POS
        word |= consts.REG0_ADDR
        return word

    def register_1(self,
                   mod: int,
                   prescaler: int,
                   phase: int = 1,
                   phase_adjust: bool = False) -> int:
        """Encode register 1 (R1): prescaler, phase, and modulus.

        Parameters
        ----------
        mod : int
            12-bit modulus value (MOD), bit field DB14:DB3. Sets the fractional
            modulus, the ratio of PFD frequency to channel step resolution.
        prescaler : int
            1-bit dual-modulus prescaler select, bit field DB27.
            ``consts.REG1_PRESCALER_4_5`` (0) or ``consts.REG1_PRESCALER_8_9``
            (1).
        phase : int, optional
            12-bit phase value, bit field DB26:DB15. Sets the RF output phase
            word; 1 is recommended when phase resync and spur optimization are
            unused.
        phase_adjust : bool, optional
            Phase-adjust enable, bit field DB28 (ADF4351 only; reserved on the
            ADF4350). When True, a subsequent write to R0 increments the output
            phase.

        Returns
        -------
        int
            The 32-bit R1 word, with control bits DB2:DB0 = 0b001.

        Raises
        ------
        ValueError
            If ``phase_adjust`` is requested on a device that does not implement
            it.

        Notes
        -----
        See datasheet Figure 25 (Register 1).
        """
        self._check_field(mod, consts.REG1_MOD_WIDTH, "MOD")
        self._check_field(phase, consts.REG1_PHASE_WIDTH, "phase")
        if phase_adjust and not self._profile.has_phase_adjust:
            raise ValueError(
                f"{self._profile.name} does not support phase adjust")
        word = 0
        word |= int(phase_adjust) << consts.REG1_PHASE_ADJUST_POS
        word |= prescaler << consts.REG1_PRESCALER_POS
        word |= phase << consts.REG1_PHASE_POS
        word |= mod << consts.REG1_MOD_POS
        word |= consts.REG1_ADDR
        return word

    def register_2(self,
                   r_counter: int,
                   cp_current_code: int, *,
                   muxout: int = consts.REG2_MUX_DIGITALLOCK,
                   noise_mode: int = consts.REG2_LOW_NOISE,
                   doubler: bool = False,
                   rdiv2: bool = False,
                   ldf: int = consts.REG2_LDF_FRAC_N,
                   ldp: int = consts.REG2_LDP_10NS,
                   pd_polarity: int = consts.REG2_PD_POLARITY_POSITIVE,
                   double_buffer: bool = False,
                   power_down: bool = False,
                   cp_threestate: bool = False,
                   counter_reset: bool = False) -> int:
        """Encode register 2 (R2): reference path, charge pump, lock detect, MUXOUT.

        Parameters
        ----------
        r_counter : int
            10-bit R counter value, bit field DB23:DB14. Divides REFIN down to
            the PFD frequency.
        cp_current_code : int
            4-bit charge-pump current setting, bit field DB12:DB9. Must match
            the current the loop filter was designed for.
        muxout : int, optional
            3-bit MUXOUT select, bit field DB28:DB26. One of the
            ``consts.REG2_MUX_*`` values; defaults to digital lock detect.
        noise_mode : int, optional
            2-bit low-noise / low-spur mode, bit field DB30:DB29.
            ``consts.REG2_LOW_NOISE`` (default) or ``consts.REG2_LOW_SPUR``.
        doubler : bool, optional
            Reference doubler enable, bit field DB25.
        rdiv2 : bool, optional
            Reference divide-by-2 enable, bit field DB24.
        ldf : int, optional
            1-bit lock-detect function, bit field DB8.
            ``consts.REG2_LDF_FRAC_N`` (default) or ``consts.REG2_LDF_INT_N``.
        ldp : int, optional
            1-bit lock-detect precision, bit field DB7.
            ``consts.REG2_LDP_10NS`` (default) or ``consts.REG2_LDP_6NS``.
        pd_polarity : int, optional
            1-bit phase-detector polarity, bit field DB6.
            ``consts.REG2_PD_POLARITY_POSITIVE`` (default, for a passive or
            noninverting loop filter) or ``consts.REG2_PD_POLARITY_NEGATIVE``.
        double_buffer : bool, optional
            Double-buffer enable for the R4 RF-divider field, bit field DB13.
        power_down : bool, optional
            Software power-down, bit field DB5.
        cp_threestate : bool, optional
            Charge-pump three-state, bit field DB4.
        counter_reset : bool, optional
            R and N counter reset, bit field DB3.

        Returns
        -------
        int
            The 32-bit R2 word, with control bits DB2:DB0 = 0b010.

        Notes
        -----
        See datasheet Figure 26 (Register 2).
        """
        self._check_field(r_counter, consts.REG2_R_COUNTER_WIDTH, "R")
        self._check_field(cp_current_code, consts.REG2_CP_CURRENT_WIDTH,
                          "CP current")
        self._check_field(muxout, consts.REG2_MUXOUT_WIDTH, "MUXOUT")
        self._check_field(noise_mode, consts.REG2_NOISE_MODE_WIDTH,
                          "noise mode")
        word = 0
        word |= noise_mode << consts.REG2_NOISE_MODE_POS
        word |= muxout << consts.REG2_MUXOUT_POS
        word |= int(doubler) << consts.REG2_DOUBLER_POS
        word |= int(rdiv2) << consts.REG2_RDIV2_POS
        word |= r_counter << consts.REG2_R_COUNTER_POS
        word |= int(double_buffer) << consts.REG2_DOUBLE_BUFFER_POS
        word |= cp_current_code << consts.REG2_CP_CURRENT_POS
        word |= ldf << consts.REG2_LDF_POS
        word |= ldp << consts.REG2_LDP_POS
        word |= pd_polarity << consts.REG2_PD_POLARITY_POS
        word |= int(power_down) << consts.REG2_POWER_DOWN_POS
        word |= int(cp_threestate) << consts.REG2_CP_THREESTATE_POS
        word |= int(counter_reset) << consts.REG2_COUNTER_RESET_POS
        word |= consts.REG2_ADDR
        return word

    def register_3(self, *,
                   band_clk_mode: int = consts.REG3_BAND_CLK_LOW,
                   abp: int = consts.REG3_ABP_6NS,
                   charge_cancel: bool = False,
                   csr: bool = False,
                   clockdiv_mode: int = consts.REG3_CLOCKDIV_OFF,
                   clockdiv_value: int = 0) -> int:
        """Encode register 3 (R3): band-select clock, ABP, CSR, clock divider.

        Parameters
        ----------
        band_clk_mode : int, optional
            1-bit band-select clock mode, bit field DB23 (ADF4351 only).
            ``consts.REG3_BAND_CLK_LOW`` (default) or
            ``consts.REG3_BAND_CLK_HIGH`` (fast band select).
        abp : int, optional
            1-bit antibacklash pulse width, bit field DB22 (ADF4351 only;
            forced to 0 on parts with a fixed 3 ns pulse).
            ``consts.REG3_ABP_6NS`` (default, fractional-N) or
            ``consts.REG3_ABP_3NS`` (integer-N).
        charge_cancel : bool, optional
            Charge-pump charge-cancellation enable, bit field DB21 (ADF4351
            only).
        csr : bool, optional
            Cycle-slip-reduction enable, bit field DB18.
        clockdiv_mode : int, optional
            2-bit clock-divider mode, bit field DB16:DB15. One of the
            ``consts.REG3_CLOCKDIV_*`` values.
        clockdiv_value : int, optional
            12-bit clock-divider value, bit field DB14:DB3. The timeout counter
            for fast lock and phase resync.

        Returns
        -------
        int
            The 32-bit R3 word, with control bits DB2:DB0 = 0b011.

        Raises
        ------
        ValueError
            If fast band select or charge cancellation is requested on a device
            that does not implement it.

        Notes
        -----
        Fast band-select clock mode and charge cancellation are ADF4351-only.
        The antibacklash pulse width is programmable only on parts that support
        it; elsewhere DB22 is reserved and the part uses a fixed 3 ns pulse, so
        the bit is forced to 0. See datasheet Figure 27 (Register 3).
        """
        self._check_field(clockdiv_value, consts.REG3_CLOCKDIV_VALUE_WIDTH,
                          "clock divider")
        if band_clk_mode == consts.REG3_BAND_CLK_HIGH \
                and not self._profile.has_fast_band_select:
            raise ValueError(
                f"{self._profile.name} does not support fast band select")
        if charge_cancel and not self._profile.has_charge_cancel:
            raise ValueError(
                f"{self._profile.name} does not support charge cancellation")
        abp_bit = abp if self._profile.has_programmable_abp else 0
        word = 0
        word |= band_clk_mode << consts.REG3_BAND_CLK_MODE_POS
        word |= abp_bit << consts.REG3_ABP_POS
        word |= int(charge_cancel) << consts.REG3_CHARGE_CANCEL_POS
        word |= int(csr) << consts.REG3_CSR_POS
        word |= clockdiv_mode << consts.REG3_CLOCKDIV_MODE_POS
        word |= clockdiv_value << consts.REG3_CLOCKDIV_VALUE_POS
        word |= consts.REG3_ADDR
        return word

    def register_4(self, rf_divider: int, band_clk_div: int, *,
                   feedback: int = consts.REG4_FEEDBACK_FUNDAMENTAL,
                   output_power: int = consts.REG4_POWER_PLUS_5DBM,
                   rf_enable: bool = True,
                   mtld: bool = False,
                   vco_power_down: bool = False,
                   aux_select: int = consts.REG4_AUX_DIVIDED,
                   aux_enable: bool = False,
                   aux_power: int = consts.REG4_POWER_MINUS_4DBM) -> int:
        """Encode register 4 (R4): feedback, dividers, and the output stage.

        Parameters
        ----------
        rf_divider : int
            RF output divider (a power of two), encoded as a 3-bit select code
            in bit field DB22:DB20 via the profile's ``divider_code``.
        band_clk_div : int
            8-bit band-select clock divider, bit field DB19:DB12. Divides the R
            counter output to keep the band-select clock within range.
        feedback : int, optional
            1-bit feedback select, bit field DB23.
            ``consts.REG4_FEEDBACK_FUNDAMENTAL`` (default, feedback taken from
            the VCO) or ``consts.REG4_FEEDBACK_DIVIDED``.
        output_power : int, optional
            2-bit primary output power, bit field DB4:DB3. One of the
            ``consts.REG4_POWER_*`` values; defaults to +5 dBm.
        rf_enable : bool, optional
            Primary RF output enable, bit field DB5.
        mtld : bool, optional
            Mute-till-lock-detect, bit field DB10.
        vco_power_down : bool, optional
            VCO power-down, bit field DB11 (1 powers the VCO down).
        aux_select : int, optional
            1-bit auxiliary output select, bit field DB9.
            ``consts.REG4_AUX_DIVIDED`` (default) or
            ``consts.REG4_AUX_FUNDAMENTAL``.
        aux_enable : bool, optional
            Auxiliary RF output enable, bit field DB8.
        aux_power : int, optional
            2-bit auxiliary output power, bit field DB7:DB6. One of the
            ``consts.REG4_POWER_*`` values.

        Returns
        -------
        int
            The 32-bit R4 word, with control bits DB2:DB0 = 0b100.

        Raises
        ------
        ValueError
            If ``rf_divider`` is not a power of two within range for the device.

        Notes
        -----
        See datasheet Figure 28 (Register 4).
        """
        rf_divider_code = self._profile.divider_code(rf_divider)
        self._check_field(band_clk_div, consts.REG4_BAND_CLK_DIV_WIDTH,
                          "band select clock divider")
        self._check_field(output_power, consts.REG4_OUTPUT_POWER_WIDTH,
                          "output power")
        self._check_field(aux_power, consts.REG4_AUX_POWER_WIDTH, "aux power")
        word = 0
        word |= feedback << consts.REG4_FEEDBACK_POS
        word |= rf_divider_code << consts.REG4_RF_DIVIDER_POS
        word |= band_clk_div << consts.REG4_BAND_CLK_DIV_POS
        word |= int(vco_power_down) << consts.REG4_VCO_POWER_DOWN_POS
        word |= int(mtld) << consts.REG4_MTLD_POS
        word |= aux_select << consts.REG4_AUX_SELECT_POS
        word |= int(aux_enable) << consts.REG4_AUX_ENABLE_POS
        word |= aux_power << consts.REG4_AUX_POWER_POS
        word |= int(rf_enable) << consts.REG4_RF_ENABLE_POS
        word |= output_power << consts.REG4_OUTPUT_POWER_POS
        word |= consts.REG4_ADDR
        return word

    def register_5(self, lock_pin: int = consts.REG5_LOCK_DIGITAL) -> int:
        """Encode register 5 (R5): the lock-detect pin mode.

        Parameters
        ----------
        lock_pin : int, optional
            2-bit lock-detect pin operation, bit field DB23:DB22. One of the
            ``consts.REG5_LOCK_*`` values; defaults to digital lock detect.

        Returns
        -------
        int
            The 32-bit R5 word, with control bits DB2:DB0 = 0b101. Bits DB20 and
            DB19 are reserved and always programmed to 1.

        Notes
        -----
        See datasheet Figure 29 (Register 5).
        """
        word = 0
        word |= lock_pin << consts.REG5_LOCK_PIN_POS
        word |= consts.REG5_RESERVED_ONES
        word |= consts.REG5_ADDR
        return word