"""Host tests for validate_config and register-file setup validation."""

import pytest

from adf435x import consts
from adf435x.config import FIELD_WIDTH
from adf435x.profiles import ADF4350, ADF4351, ADF435xDeviceProfile
from adf435x.register_file import ADF435xRegisterFile
from adf435x.register_mapper import ADF435xRegisterMapper

from conftest import WORKED_FIELDS, WORKED_WORDS, make_config


_PLL_ONLY = frozenset(("int_n", "frac", "mod", "prescaler"))


class TestCheckPll:
    def test_worked_example_passes(self, mapper):
        mapper.validate_config(
            make_config(
                int_n=422,
                frac=13,
                mod=25,
                prescaler=consts.REG1_PRESCALER_8_9,
            ),
            only=_PLL_ONLY,
        )

    def test_int_below_minimum_rejected(self, mapper):
        with pytest.raises(ValueError, match="below minimum"):
            mapper.validate_config(
                make_config(
                    int_n=0,
                    frac=0,
                    mod=2,
                    prescaler=consts.REG1_PRESCALER_8_9,
                ),
                only=_PLL_ONLY,
            )

    def test_frac_ge_mod_rejected(self, mapper):
        with pytest.raises(ValueError, match="FRAC=50 must be less than MOD=25"):
            mapper.validate_config(
                make_config(
                    int_n=100,
                    frac=50,
                    mod=25,
                    prescaler=consts.REG1_PRESCALER_8_9,
                ),
                only=_PLL_ONLY,
            )

    def test_prescaler_change_rechecks_int(self, mapper):
        c = make_config(int_n=50, prescaler=consts.REG1_PRESCALER_4_5)
        mapper.validate_config(c)
        c.prescaler = consts.REG1_PRESCALER_8_9
        with pytest.raises(ValueError, match="below minimum"):
            mapper.validate_config(c, only=frozenset(("prescaler",)))

    def test_int_above_maximum_rejected(self):
        profile = ADF435xDeviceProfile(
            "test",
            rf_divider_max=64,
            has_phase_adjust=True,
            has_fast_band_select=True,
            has_programmable_abp=True,
            has_charge_cancel=True,
            prescaler_4_5_max_hz=3_600_000_000,
            int_max=100,
        )
        mapper = ADF435xRegisterMapper(profile)
        with pytest.raises(ValueError, match="above maximum"):
            mapper.validate_config(
                make_config(
                    int_n=101,
                    frac=0,
                    mod=2,
                    prescaler=consts.REG1_PRESCALER_8_9,
                ),
                only=_PLL_ONLY,
            )

    def test_invalid_prescaler_rejected(self, mapper):
        with pytest.raises(ValueError, match="prescaler=2 invalid"):
            mapper.validate_config(
                make_config(
                    int_n=75,
                    frac=0,
                    mod=2,
                    prescaler=2,
                ),
                only=frozenset(("prescaler",)),
            )


class TestRegister1:
    def test_mod_below_minimum_rejected(self, mapper):
        with pytest.raises(ValueError, match="MOD=1 below minimum"):
            mapper.validate_config(
                make_config(mod=1, prescaler=consts.REG1_PRESCALER_8_9),
                only=frozenset(("mod",)),
            )

    def test_prescaler_out_of_range_rejected(self, mapper):
        with pytest.raises(ValueError, match="prescaler=2"):
            mapper.validate_config(
                make_config(mod=25, prescaler=2),
                only=frozenset(("prescaler",)),
            )


class TestRegister2:
    def test_r_counter_zero_rejected(self, mapper):
        with pytest.raises(ValueError, match="R=0 below minimum"):
            mapper.validate_config(
                make_config(r_counter=0),
                only=frozenset(("r_counter",)),
            )


class TestWidthFields:
    @pytest.mark.parametrize(
        "field, bad_value, match",
        [
            ("int_n", 1 << 16, "INT="),
            ("frac", 1 << 12, "FRAC="),
            ("phase", 1 << 12, "phase="),
            ("mod", 1 << 12, "MOD="),
            ("r_counter", 1 << 10, "R="),
            ("cp_current_code", 1 << 4, "CP current="),
            ("clockdiv_value", 1 << 12, "clock divider="),
            ("band_clk_div", 1 << 8, "band select clock divider="),
        ],
    )
    def test_width_limited_fields(self, mapper, field, bad_value, match):
        with pytest.raises(ValueError, match=match):
            mapper.validate_config(
                make_config(**{field: bad_value}),
                only=frozenset((field,)),
            )

    def test_band_clk_div_zero_rejected(self, mapper):
        with pytest.raises(ValueError, match="below minimum"):
            mapper.validate_config(
                make_config(band_clk_div=0),
                only=frozenset(("band_clk_div",)),
            )


class TestModRange:
    def test_mod_above_profile_max_rejected(self):
        profile = ADF435xDeviceProfile(
            "test",
            rf_divider_max=64,
            has_phase_adjust=True,
            has_fast_band_select=True,
            has_programmable_abp=True,
            has_charge_cancel=True,
            prescaler_4_5_max_hz=3_600_000_000,
            mod_max=100,
        )
        mapper = ADF435xRegisterMapper(profile)
        with pytest.raises(ValueError, match="above maximum"):
            mapper.validate_config(
                make_config(mod=101),
                only=frozenset(("mod",)),
            )


class TestEnumFields:
    @pytest.mark.parametrize(
        "field, bad_value",
        [
            ("prescaler", 2),
            ("muxout", 7),
            ("noise_mode", 1),
            ("ldf", 2),
            ("ldp", 2),
            ("pd_polarity", 2),
            ("band_clk_mode", 2),
            ("abp", 2),
            ("clockdiv_mode", 3),
            ("feedback", 2),
            ("output_power", 4),
            ("aux_select", 2),
            ("aux_power", 4),
            ("lock_pin", 2),
        ],
    )
    def test_invalid_enum_rejected(self, mapper, field, bad_value):
        with pytest.raises(ValueError, match="invalid"):
            mapper.validate_config(
                make_config(**{field: bad_value}),
                only=frozenset((field,)),
            )


class TestProfileGates:
    def test_4350_phase_adjust_rejected(self):
        m = ADF435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError, match="phase adjust"):
            m.validate_config(
                make_config(phase_adjust=True),
                only=frozenset(("phase_adjust",)),
            )

    def test_4350_fast_band_select_rejected(self):
        m = ADF435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError, match="fast band select"):
            m.validate_config(
                make_config(band_clk_mode=consts.REG3_BAND_CLK_HIGH),
                only=frozenset(("band_clk_mode",)),
            )

    def test_4350_charge_cancel_rejected(self):
        m = ADF435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError, match="charge cancellation"):
            m.validate_config(
                make_config(charge_cancel=True),
                only=frozenset(("charge_cancel",)),
            )


class TestRfDivider:
    def test_invalid_divider_rejected(self, mapper):
        with pytest.raises(ValueError, match="rf_divider=3"):
            mapper.validate_config(
                make_config(rf_divider=3),
                only=frozenset(("rf_divider",)),
            )


class TestValidateConfigFull:
    def test_default_config_passes_full_check(self, mapper):
        mapper.validate_config(make_config())

    def test_mapper_exposes_profile(self, mapper):
        assert mapper.profile is ADF4351


class TestRegisterFileValidation:
    def test_configure_int_zero_rejected(self):
        f = ADF435xRegisterFile(ADF4351)
        with pytest.raises(ValueError, match="below minimum"):
            f.configure(int_n=0)

    def test_worked_example_still_encodes(self, worked_regfile):
        assert worked_regfile.current_words() == WORKED_WORDS

    def test_default_config_is_pll_valid(self):
        f = ADF435xRegisterFile(ADF4351)
        assert f.config.int_n == 75
        assert f.config.frac < f.config.mod
        assert len(f.current_words()) == 6

    def test_configure_band_clk_div_zero_rolls_back(self, worked_regfile):
        before = worked_regfile.config.band_clk_div
        words = worked_regfile.current_words()
        with pytest.raises(ValueError, match="below minimum"):
            worked_regfile.configure(band_clk_div=0)
        assert worked_regfile.config.band_clk_div == before
        assert worked_regfile.current_words() == words

    def test_configure_frac_valid_reencodes(self, worked_regfile):
        worked_regfile.commit()
        before = worked_regfile.current_words()
        worked_regfile.configure(frac=14)
        after = worked_regfile.current_words()
        assert after[0] != before[0]
        assert after[0] == worked_regfile._mapper.register_0(
            worked_regfile.config.int_n, 14
        )


class TestTrustedEncode:
    def test_oversized_int_rejected_by_validate(self, mapper):
        with pytest.raises(ValueError, match="INT="):
            mapper.validate_config(
                make_config(int_n=1 << 16),
                only=frozenset(("int_n",)),
            )

    def test_oversized_int_masked_at_encode(self, mapper):
        assert mapper.register_0(1 << 16, 0) == mapper.register_0(0, 0)

    def test_worked_words_still_match(self, mapper):
        assert mapper.encode_config(make_config(**WORKED_FIELDS)) == WORKED_WORDS

    def test_invalid_register_index(self, mapper):
        with pytest.raises(ValueError, match="invalid register index"):
            mapper.encode_register(6, make_config())

    def test_all_width_fields_have_rules(self):
        assert set(FIELD_WIDTH) <= {
            "int_n",
            "frac",
            "phase",
            "mod",
            "r_counter",
            "cp_current_code",
            "clockdiv_value",
            "band_clk_div",
        }
