"""Host tests for ADF435xRegisterMapper: register encoding, structural gates,
divider mapping, and trusted (masked) encode behavior.
"""

import pytest

from adf435x import consts
from adf435x.config import ADF435xConfig
from adf435x.profiles import ADF4350, ADF4351
from adf435x.register_mapper import ADF435xRegisterMapper

from conftest import WORKED_FIELDS, WORKED_WORDS, make_config


class TestWorkedExample:
    """Each register encoder reproduces the datasheet worked-example word."""

    def test_reg0(self, mapper):
        """R0 encodes INT and FRAC into the known-good word."""
        assert mapper.register_0(422, 13) == WORKED_WORDS[0]

    def test_reg1(self, mapper):
        """R1 encodes prescaler, phase, and MOD into the known-good word."""
        assert (
            mapper.register_1(25, consts.REG1_PRESCALER_8_9, phase=1)
            == WORKED_WORDS[1]
        )

    def test_reg2(self, mapper):
        """R2 encodes the R counter and CP current into the known-good word."""
        assert mapper.register_2(1, 7) == WORKED_WORDS[2]

    def test_reg3(self, mapper):
        """R3 with fast band select encodes to the known-good word."""
        assert (
            mapper.register_3(band_clk_mode=consts.REG3_BAND_CLK_HIGH)
            == WORKED_WORDS[3]
        )

    def test_reg4(self, mapper):
        """R4 encodes the RF divider and band-clk divider to the known word."""
        assert mapper.register_4(2, 20) == WORKED_WORDS[4]

    def test_reg5(self, mapper):
        """R5 defaults encode to the known-good word."""
        assert mapper.register_5() == WORKED_WORDS[5]


class TestEncodeConfig:
    """Whole-config encoding matches the per-register encoders."""

    def test_encode_config_worked_example(self, mapper):
        """A worked-example config encodes to all six known-good words."""
        assert mapper.encode_config(make_config(**WORKED_FIELDS)) == WORKED_WORDS

    def test_encode_register_matches_encode_config(self, mapper):
        """``encode_register`` agrees with ``encode_config`` for each index."""
        c = ADF435xConfig()
        words = mapper.encode_config(c)
        # encode_config is just encode_register over every index; verify the
        # two paths produce identical words.
        for index in range(consts.NUM_REGISTERS):
            assert mapper.encode_register(index, c) == words[index]


class TestStructure:
    """Encoded words carry the correct address and reserved bits."""

    @pytest.mark.parametrize(
        "index, word_fn",
        [
            (0, lambda m: m.register_0(0, 0)),
            (1, lambda m: m.register_1(2, 0)),
            (2, lambda m: m.register_2(1, 0)),
            (3, lambda m: m.register_3()),
            (4, lambda m: m.register_4(1, 20)),
            (5, lambda m: m.register_5()),
        ],
    )
    def test_control_bits(self, mapper, index, word_fn):
        """Each register's low 3 bits (DB2:DB0) equal its address."""
        assert word_fn(mapper) & 0b111 == index

    def test_reg5_reserved_ones(self, mapper):
        """R5 always sets the reserved DB20 and DB19 bits."""
        assert mapper.register_5() & 0x180000 == 0x180000


class TestDividerCode:
    """The RF divider maps through the profile during R4 encode."""

    def test_4351_divider_64(self):
        """On the ADF4351, /64 encodes to divider code 6 in R4."""
        m = ADF435xRegisterMapper(ADF4351)
        assert (m.register_4(64, 20) >> consts.REG4_RF_DIVIDER_POS) & 0b111 == 6

    def test_4350_rejects_divider_32(self):
        """On the ADF4350, /32 exceeds the /16 max and is rejected at encode."""
        m = ADF435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.register_4(32, 20)


class TestCapabilityGating:
    """Profile capability gates stay in the encoder (not maskable)."""

    def test_4350_rejects_phase_adjust(self):
        """Phase adjust is unsupported on the ADF4350 and raises."""
        m = ADF435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.register_1(2, 0, phase_adjust=True)

    def test_4351_allows_phase_adjust(self):
        """Phase adjust sets DB28 on the ADF4351."""
        m = ADF435xRegisterMapper(ADF4351)
        assert (
            m.register_1(2, 0, phase_adjust=True) >> consts.REG1_PHASE_ADJUST_POS
        ) & 1 == 1

    def test_4350_rejects_fast_band_select(self):
        """Fast band select is unsupported on the ADF4350 and raises."""
        m = ADF435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.register_3(band_clk_mode=consts.REG3_BAND_CLK_HIGH)

    def test_4350_rejects_charge_cancel(self):
        """Charge cancellation is unsupported on the ADF4350 and raises."""
        m = ADF435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.register_3(charge_cancel=True)

    def test_4350_forces_abp_reserved_zero(self):
        """On the ADF4350 the reserved ABP bit (DB22) is forced to 0."""
        m = ADF435xRegisterMapper(ADF4350)
        # Request the 3 ns setting; the part lacks programmable ABP, so the
        # encoder must clear DB22 regardless.
        word = m.register_3(abp=consts.REG3_ABP_3NS)
        assert (word >> consts.REG3_ABP_POS) & 1 == 0


class TestTrustedEncode:
    """Width-limited fields are masked, not validated, in the encoder."""

    def test_int_out_of_range_is_masked(self, mapper):
        """An INT one bit too wide masks to 0, matching register_0(0, ...)."""
        # 1 << 16 is one bit above the 16-bit INT field; the high bit is masked
        # off, leaving 0.
        assert mapper.register_0(1 << 16, 0) == mapper.register_0(0, 0)

    def test_frac_out_of_range_is_masked(self, mapper):
        """A FRAC one bit too wide masks to 0, matching register_0(..., 0)."""
        assert mapper.register_0(0, 1 << 12) == mapper.register_0(0, 0)

    def test_worked_example_unchanged(self, mapper):
        """Masking does not perturb in-range worked-example values."""
        assert mapper.register_0(422, 13) == WORKED_WORDS[0]
