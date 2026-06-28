"""Host tests for PLL and per-register encode validation."""

import pytest

from adf435x import consts
from adf435x.config import ADF435xConfig
from adf435x.profiles import ADF4351
from adf435x.register_file import ADF435xRegisterFile
from adf435x.register_mapper import ADF435xRegisterMapper

WORKED = [0x00D30068, 0x080080C9, 0x18004E42, 0x00800003, 0x0091403C, 0x00580005]


def _config(**fields):
    """Build a config with optional field overrides."""
    c = ADF435xConfig()
    for name, value in fields.items():
        setattr(c, name, value)
    return c


@pytest.fixture
def mapper():
    return ADF435xRegisterMapper(ADF4351)


class TestCheckPll:
    def test_worked_example_passes(self, mapper):
        mapper.validate_config(
            _config(
                int_n=422,
                frac=13,
                mod=25,
                prescaler=consts.REG1_PRESCALER_8_9,
            ),
            only=frozenset(("int_n", "frac", "mod", "prescaler")),
        )

    def test_int_below_minimum_rejected(self, mapper):
        with pytest.raises(ValueError, match="below minimum"):
            mapper.validate_config(
                _config(
                    int_n=0,
                    frac=0,
                    mod=2,
                    prescaler=consts.REG1_PRESCALER_8_9,
                ),
                only=frozenset(("int_n", "frac", "mod", "prescaler")),
            )

    def test_frac_ge_mod_rejected(self, mapper):
        with pytest.raises(ValueError, match="FRAC=50 must be less than MOD=25"):
            mapper.validate_config(
                _config(
                    int_n=100,
                    frac=50,
                    mod=25,
                    prescaler=consts.REG1_PRESCALER_8_9,
                ),
                only=frozenset(("int_n", "frac", "mod", "prescaler")),
            )


class TestRegister1:
    def test_mod_below_minimum_rejected(self, mapper):
        with pytest.raises(ValueError, match="MOD=1 below minimum"):
            mapper.validate_config(
                _config(mod=1, prescaler=consts.REG1_PRESCALER_8_9),
                only=frozenset(("mod",)),
            )

    def test_prescaler_out_of_range_rejected(self, mapper):
        with pytest.raises(ValueError, match="prescaler=2"):
            mapper.validate_config(
                _config(mod=25, prescaler=2),
                only=frozenset(("prescaler",)),
            )


class TestRegister2:
    def test_r_counter_zero_rejected(self, mapper):
        with pytest.raises(ValueError, match="R=0 below minimum"):
            mapper.validate_config(
                _config(r_counter=0),
                only=frozenset(("r_counter",)),
            )


class TestRegisterFileValidation:
    def test_configure_int_zero_rejected(self):
        f = ADF435xRegisterFile(ADF4351)
        with pytest.raises(ValueError, match="below minimum"):
            f.configure(int_n=0)

    def test_worked_example_still_encodes(self):
        f = ADF435xRegisterFile(ADF4351)
        f.configure(
            int_n=422,
            frac=13,
            mod=25,
            band_clk_mode=consts.REG3_BAND_CLK_HIGH,
            rf_divider=2,
            band_clk_div=20,
        )
        assert f.current_words() == WORKED

    def test_default_config_is_pll_valid(self):
        f = ADF435xRegisterFile(ADF4351)
        assert f.config.int_n == 75
        assert f.config.frac < f.config.mod
        assert len(f.current_words()) == 6
