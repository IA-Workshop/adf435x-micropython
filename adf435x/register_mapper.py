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
from .config import (
    ADF435xConfig,
    FIELD_ENUM_VALUES,
    FIELD_NAMES,
    FIELD_RANGE_MIN,
    FIELD_WIDTH,
)
from .profiles import ADF435xDeviceProfile

_PLL_FIELDS = frozenset(("int_n", "frac", "mod", "prescaler"))
# Error-message labels where they differ from the config field name.
_FIELD_LABELS = {
    "int_n": "INT",
    "frac": "FRAC",
    "mod": "MOD",
    "r_counter": "R",
    "cp_current_code": "CP current",
    "muxout": "MUXOUT",
    "noise_mode": "noise mode",
    "clockdiv_value": "clock divider",
    "band_clk_div": "band select clock divider",
    "output_power": "output power",
    "aux_power": "aux power",
}
_PROFILE_BOOL_GATES = {
    "phase_adjust": ("has_phase_adjust", "does not support phase adjust"),
    "charge_cancel": ("has_charge_cancel", "does not support charge cancellation"),
}


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

    @property
    def profile(self) -> ADF435xDeviceProfile:
        """The device profile this mapper encodes for."""
        return self._profile

    def _pack(self, value: int, pos: int, width: int) -> int:
        """Mask *value* to *width* bits and shift to bit position *pos*."""
        return (value & ((1 << width) - 1)) << pos

    def _bit(self, flag: bool, pos: int) -> int:
        """Encode a single control bit."""
        return int(flag) << pos

    def _check_width(self, value: int, bits: int, label: str) -> None:
        """Raise ValueError if *value* is outside an unsigned *bits*-wide field."""
        if value < 0 or value >= 1 << bits:
            raise ValueError("%s=%d does not fit in %d bits" % (label, value, bits))

    def _check_pll(self, int_n: int, frac: int, mod: int, prescaler: int) -> None:
        """Validate cross-field PLL constraints (INT/FRAC/MOD/prescaler)."""
        profile = self._profile
        if frac >= mod:
            raise ValueError("FRAC=%d must be less than MOD=%d" % (frac, mod))
        if prescaler == consts.REG1_PRESCALER_4_5:
            int_min = profile.int_min_4_5
        elif prescaler == consts.REG1_PRESCALER_8_9:
            int_min = profile.int_min_8_9
        else:
            raise ValueError("prescaler=%d invalid" % prescaler)
        if int_n < int_min:
            raise ValueError("INT=%d below minimum %d for prescaler" % (int_n, int_min))
        if int_n > profile.int_max:
            raise ValueError("INT=%d above maximum %d" % (int_n, profile.int_max))

    def _validate_one_field(self, config: ADF435xConfig, name: str) -> None:
        """Validate a single configuration field on *config*.

        Parameters
        ----------
        config : ADF435xConfig
            Configuration supplying field values.
        name : str
            Field name from ``config._FIELDS``.

        Raises
        ------
        ValueError
            If the field value violates width, range, enum, profile, or
            divider rules.
        """
        value = getattr(config, name)
        profile = self._profile
        label = _FIELD_LABELS.get(name, name)
        if name in FIELD_WIDTH:
            self._check_width(value, FIELD_WIDTH[name], label)
        if name == "mod":
            if value < profile.mod_min:
                raise ValueError("MOD=%d below minimum %d" % (value, profile.mod_min))
            if value > profile.mod_max:
                raise ValueError("MOD=%d above maximum %d" % (value, profile.mod_max))
        elif name in FIELD_RANGE_MIN:
            lo = FIELD_RANGE_MIN[name]
            if value < lo:
                raise ValueError("%s=%d below minimum %d" % (label, value, lo))
        elif name in FIELD_ENUM_VALUES:
            if value not in FIELD_ENUM_VALUES[name]:
                raise ValueError("%s=%d invalid" % (label, value))
            if (
                name == "band_clk_mode"
                and value == consts.REG3_BAND_CLK_HIGH
                and (not profile.has_fast_band_select)
            ):
                raise ValueError("%s does not support fast band select" % profile.name)
        elif name == "rf_divider":
            profile.divider_code(value)
        elif name in _PROFILE_BOOL_GATES:
            attr, msg = _PROFILE_BOOL_GATES[name]
            if value and (not getattr(profile, attr)):
                raise ValueError("%s %s" % (profile.name, msg))

    def validate_config(
        self, config: ADF435xConfig, *, only: frozenset[str] | None = None
    ) -> None:
        """Raise ValueError on any configuration violation. Never encodes.

        Parameters
        ----------
        config : ADF435xConfig
            Configuration to validate.
        only : frozenset of str or None, optional
            When ``None``, every field in ``config._FIELDS`` is checked.
            Otherwise only the named fields are checked. If *only* intersects
            the PLL fields ``{int_n, frac, mod, prescaler}``, the cross-field
            PLL check runs as well.

        Raises
        ------
        ValueError
            On any width, range, enum, profile-capability, divider, or PLL
            violation.
        """
        if only is None:
            names = FIELD_NAMES
            check_pll = True
        else:
            names = only
            check_pll = bool(only & _PLL_FIELDS)
        for name in names:
            self._validate_one_field(config, name)
        if check_pll:
            self._check_pll(config.int_n, config.frac, config.mod, config.prescaler)

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
        return (
            self._pack(int_n, consts.REG0_INT_POS, consts.REG0_INT_WIDTH)
            | self._pack(frac, consts.REG0_FRAC_POS, consts.REG0_FRAC_WIDTH)
            | consts.REG0_ADDR
        )

    def register_1(
        self, mod: int, prescaler: int, phase: int = 1, phase_adjust: bool = False
    ) -> int:
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
        if phase_adjust and (not self._profile.has_phase_adjust):
            raise ValueError("%s does not support phase adjust" % self._profile.name)
        return (
            self._bit(phase_adjust, consts.REG1_PHASE_ADJUST_POS)
            | self._pack(prescaler, consts.REG1_PRESCALER_POS, 1)
            | self._pack(phase, consts.REG1_PHASE_POS, consts.REG1_PHASE_WIDTH)
            | self._pack(mod, consts.REG1_MOD_POS, consts.REG1_MOD_WIDTH)
            | consts.REG1_ADDR
        )

    def register_2(
        self,
        r_counter: int,
        cp_current_code: int,
        *,
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
        counter_reset: bool = False,
    ) -> int:
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
        c = consts
        return (
            self._pack(noise_mode, c.REG2_NOISE_MODE_POS, c.REG2_NOISE_MODE_WIDTH)
            | self._pack(muxout, c.REG2_MUXOUT_POS, c.REG2_MUXOUT_WIDTH)
            | self._bit(doubler, c.REG2_DOUBLER_POS)
            | self._bit(rdiv2, c.REG2_RDIV2_POS)
            | self._pack(r_counter, c.REG2_R_COUNTER_POS, c.REG2_R_COUNTER_WIDTH)
            | self._bit(double_buffer, c.REG2_DOUBLE_BUFFER_POS)
            | self._pack(
                cp_current_code, c.REG2_CP_CURRENT_POS, c.REG2_CP_CURRENT_WIDTH
            )
            | self._pack(ldf, c.REG2_LDF_POS, 1)
            | self._pack(ldp, c.REG2_LDP_POS, 1)
            | self._pack(pd_polarity, c.REG2_PD_POLARITY_POS, 1)
            | self._bit(power_down, c.REG2_POWER_DOWN_POS)
            | self._bit(cp_threestate, c.REG2_CP_THREESTATE_POS)
            | self._bit(counter_reset, c.REG2_COUNTER_RESET_POS)
            | c.REG2_ADDR
        )

    def register_3(
        self,
        *,
        band_clk_mode: int = consts.REG3_BAND_CLK_LOW,
        abp: int = consts.REG3_ABP_6NS,
        charge_cancel: bool = False,
        csr: bool = False,
        clockdiv_mode: int = consts.REG3_CLOCKDIV_OFF,
        clockdiv_value: int = 0,
    ) -> int:
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
        if band_clk_mode == consts.REG3_BAND_CLK_HIGH and (
            not self._profile.has_fast_band_select
        ):
            raise ValueError(
                "%s does not support fast band select" % self._profile.name
            )
        if charge_cancel and (not self._profile.has_charge_cancel):
            raise ValueError(
                "%s does not support charge cancellation" % self._profile.name
            )
        abp_bit = abp if self._profile.has_programmable_abp else 0
        c = consts
        return (
            self._pack(band_clk_mode, c.REG3_BAND_CLK_MODE_POS, 1)
            | self._pack(abp_bit, c.REG3_ABP_POS, 1)
            | self._bit(charge_cancel, c.REG3_CHARGE_CANCEL_POS)
            | self._bit(csr, c.REG3_CSR_POS)
            | self._pack(
                clockdiv_mode, c.REG3_CLOCKDIV_MODE_POS, c.REG3_CLOCKDIV_MODE_WIDTH
            )
            | self._pack(
                clockdiv_value, c.REG3_CLOCKDIV_VALUE_POS, c.REG3_CLOCKDIV_VALUE_WIDTH
            )
            | c.REG3_ADDR
        )

    def register_4(
        self,
        rf_divider: int,
        band_clk_div: int,
        *,
        feedback: int = consts.REG4_FEEDBACK_FUNDAMENTAL,
        output_power: int = consts.REG4_POWER_PLUS_5DBM,
        rf_enable: bool = True,
        mtld: bool = False,
        vco_power_down: bool = False,
        aux_select: int = consts.REG4_AUX_DIVIDED,
        aux_enable: bool = False,
        aux_power: int = consts.REG4_POWER_MINUS_4DBM,
    ) -> int:
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
        c = consts
        return (
            self._pack(feedback, c.REG4_FEEDBACK_POS, 1)
            | self._pack(
                self._profile.divider_code(rf_divider),
                c.REG4_RF_DIVIDER_POS,
                c.REG4_RF_DIVIDER_WIDTH,
            )
            | self._pack(
                band_clk_div, c.REG4_BAND_CLK_DIV_POS, c.REG4_BAND_CLK_DIV_WIDTH
            )
            | self._bit(vco_power_down, c.REG4_VCO_POWER_DOWN_POS)
            | self._bit(mtld, c.REG4_MTLD_POS)
            | self._pack(aux_select, c.REG4_AUX_SELECT_POS, 1)
            | self._bit(aux_enable, c.REG4_AUX_ENABLE_POS)
            | self._pack(aux_power, c.REG4_AUX_POWER_POS, c.REG4_AUX_POWER_WIDTH)
            | self._bit(rf_enable, c.REG4_RF_ENABLE_POS)
            | self._pack(
                output_power, c.REG4_OUTPUT_POWER_POS, c.REG4_OUTPUT_POWER_WIDTH
            )
            | c.REG4_ADDR
        )

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
        return (
            self._pack(lock_pin, consts.REG5_LOCK_PIN_POS, consts.REG5_LOCK_PIN_WIDTH)
            | consts.REG5_RESERVED_ONES
            | consts.REG5_ADDR
        )

    def encode_register(self, index: int, config: ADF435xConfig) -> int:
        """Encode one register word from *config*.

        Parameters
        ----------
        index : int
            Register index (0..5).
        config : ADF435xConfig
            Configuration supplying field values.

        Returns
        -------
        int
            The 32-bit register word.

        Raises
        ------
        ValueError
            If *index* is invalid, or a structural encode rule fails (profile
            capability gate or RF divider mapping).
        """
        c = config
        if index == consts.REG0_ADDR:
            return self.register_0(c.int_n, c.frac)
        if index == consts.REG1_ADDR:
            return self.register_1(c.mod, c.prescaler, c.phase, c.phase_adjust)
        if index == consts.REG2_ADDR:
            return self.register_2(
                c.r_counter,
                c.cp_current_code,
                muxout=c.muxout,
                noise_mode=c.noise_mode,
                doubler=c.doubler,
                rdiv2=c.rdiv2,
                ldf=c.ldf,
                ldp=c.ldp,
                pd_polarity=c.pd_polarity,
                double_buffer=c.double_buffer,
                power_down=c.power_down,
                cp_threestate=c.cp_threestate,
                counter_reset=c.counter_reset,
            )
        if index == consts.REG3_ADDR:
            return self.register_3(
                band_clk_mode=c.band_clk_mode,
                abp=c.abp,
                charge_cancel=c.charge_cancel,
                csr=c.csr,
                clockdiv_mode=c.clockdiv_mode,
                clockdiv_value=c.clockdiv_value,
            )
        if index == consts.REG4_ADDR:
            return self.register_4(
                c.rf_divider,
                c.band_clk_div,
                feedback=c.feedback,
                output_power=c.output_power,
                rf_enable=c.rf_enable,
                mtld=c.mtld,
                vco_power_down=c.vco_power_down,
                aux_select=c.aux_select,
                aux_enable=c.aux_enable,
                aux_power=c.aux_power,
            )
        if index == consts.REG5_ADDR:
            return self.register_5(c.lock_pin)
        raise ValueError("invalid register index: %d" % index)

    def encode_config(self, config: ADF435xConfig) -> list:
        """Encode all six registers from *config*.

        Parameters
        ----------
        config : ADF435xConfig
            Configuration supplying field values.

        Returns
        -------
        list of int
            Register words R0 through R5.
        """
        return [self.encode_register(i, config) for i in range(consts.NUM_REGISTERS)]
