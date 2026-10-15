"""Host tests for ADF435xRegisterMapper encoding: the worked example, word
structure, divider mapping, reserved bits, and trusted (masked) encode.

Validation is covered in ``test_validation.py``.
"""

import pytest

from adf435x import consts
from adf435x.config import ADF435xConfig
from adf435x.profiles import ADF4350, ADF4351
from adf435x.register_mapper import ADF435xRegisterMapper

from conftest import WORKED_FIELDS, WORKED_WORDS, make_config


class TestWorkedExample:
    """Each register reproduces the datasheet worked-example word."""

    @pytest.mark.parametrize("index", range(6))
    def test_register_word(self, mapper, index):
        """Register *index* encodes to ``WORKED_WORDS[index]``."""
        cfg = make_config(**WORKED_FIELDS)
        assert mapper.encode_register(index, cfg) == WORKED_WORDS[index]


class TestEncodeConfig:
    """Whole-config encoding matches the per-register encoder."""

    def test_encode_config_worked_example(self, mapper):
        """A worked-example config encodes to all six known-good words."""
        assert mapper.encode_config(make_config(**WORKED_FIELDS)) == WORKED_WORDS

    @pytest.mark.parametrize("index", range(6))
    def test_encode_register_matches_encode_config(self, mapper, index):
        """``encode_register`` agrees with ``encode_config`` for each index."""
        c = ADF435xConfig()
        assert mapper.encode_register(index, c) == mapper.encode_config(c)[index]


class TestStructure:
    """Encoded words carry the correct address and reserved bits."""

    @pytest.mark.parametrize("index", range(6))
    def test_control_bits(self, mapper, index):
        """Each register's low 3 bits (DB2:DB0) equal its address."""
        assert mapper.encode_register(index, ADF435xConfig()) & 0b111 == index

    def test_reg5_reserved_ones(self, mapper):
        """R5 always sets the reserved DB20 and DB19 bits."""
        word = mapper.encode_register(consts.REG5_ADDR, ADF435xConfig())
        assert word & consts.REG5_RESERVED_ONES == consts.REG5_RESERVED_ONES

    def test_invalid_register_index(self, mapper):
        """An index outside 0..5 raises."""
        with pytest.raises(ValueError, match="invalid register index"):
            mapper.encode_register(-1, ADF435xConfig())


class TestDividerCode:
    """The RF divider maps through the profile during R4 encode."""

    def test_4351_divider_64(self):
        """On the ADF4351, /64 encodes to divider code 6 in R4."""
        m = ADF435xRegisterMapper(ADF4351)
        word = m.encode_register(consts.REG4_ADDR, make_config(rf_divider=64))
        assert (word >> consts.REG4_RF_DIVIDER_POS) & 0b111 == 6

    def test_4350_rejects_divider_32(self):
        """On the ADF4350, /32 has no divider code, so encode raises."""
        m = ADF435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.encode_register(consts.REG4_ADDR, make_config(rf_divider=32))


class TestProfileBits:
    """Profile-dependent bits at encode (capability errors are validation's)."""

    def test_4351_phase_adjust_sets_db28(self):
        """Phase adjust sets DB28 on the ADF4351."""
        m = ADF435xRegisterMapper(ADF4351)
        word = m.encode_register(consts.REG1_ADDR, make_config(phase_adjust=True))
        assert (word >> consts.REG1_PHASE_ADJUST_POS) & 1 == 1

    def test_4350_forces_abp_reserved_zero(self):
        """On the ADF4350 the reserved ABP bit (DB22) is always 0."""
        m = ADF435xRegisterMapper(ADF4350)
        word = m.encode_register(consts.REG3_ADDR, make_config(abp=consts.REG3_ABP_3NS))
        assert (word >> consts.REG3_ABP_POS) & 1 == 0

    def test_4351_abp_programmable(self):
        """On the ADF4351 the 3 ns ABP setting sets DB22."""
        m = ADF435xRegisterMapper(ADF4351)
        word = m.encode_register(consts.REG3_ADDR, make_config(abp=consts.REG3_ABP_3NS))
        assert (word >> consts.REG3_ABP_POS) & 1 == 1


class TestTrustedEncode:
    """The encoder masks rather than validates (validate-at-setup)."""

    @pytest.mark.parametrize(
        "field, oversized",
        [("int_n", 1 << 16), ("frac", 1 << 12), ("mod", 1 << 12)],
    )
    def test_oversized_value_masks_to_zero(self, mapper, field, oversized):
        """A value one bit too wide masks to the same word as 0."""
        reg = 0 if field != "mod" else 1
        big = mapper.encode_register(reg, make_config(**{field: oversized}))
        assert big == mapper.encode_register(reg, make_config(**{field: 0}))

    def test_flag_value_stays_in_its_bit(self, mapper):
        """A non-bool flag encodes as 1 and never spills into a neighbour."""
        # mtld=2 used to set DB11 (VCO power-down) instead of DB10.
        spilled = mapper.encode_register(consts.REG4_ADDR, make_config(mtld=2))
        assert spilled == mapper.encode_register(
            consts.REG4_ADDR, make_config(mtld=True)
        )
