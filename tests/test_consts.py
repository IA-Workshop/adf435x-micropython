"""
Host tests for consts.py: the const override must be invoked when running on
the host under CPython, and the field positions must reconstruct known-good
register words (Datasheet worked example, 2112.6 MHz).
"""
from adf435x import consts as c


def test_const_imports_on_host():
    # If the micropython->CPython shim were missing, importing this module
    # would already have raised. This test spot-checks that a folded value
    # survived.
    assert c.WORD_SIZE_BYTES == 4
    assert c.NUM_REGISTERS == 6


def test_dbr_register_indices():
    assert c.DBR_REGISTER_INDICES == (c.REG1_ADDR, c.REG2_ADDR)


def test_r0_layout_worked_example():
    # INT=422, FRAC=13 -> R0 = 0x00D30068
    r0 = (422 << c.REG0_INT_POS) | (13 << c.REG0_FRAC_POS) | c.REG0_ADDR
    assert r0 == 0x00D30068


def test_r1_layout_worked_example():
    # prescaler 8/9, phase=1, MOD=25 -> R1 = 0x080080C9
    r1 = ((c.REG1_PRESCALER_8_9 << c.REG1_PRESCALER_POS)
          | (1 << c.REG1_PHASE_POS)
          | (25 << c.REG1_MOD_POS)
          | c.REG1_ADDR)
    assert r1 == 0x080080C9


def test_r5_reserved_ones():
    assert c.REG5_RESERVED_ONES == (1 << 20) | (1 << 19)


def test_muxout_digital_lock_value():
    assert c.REG2_MUX_DIGITALLOCK == 0b110


def test_output_power_levels_ascending():
    assert (c.REG4_POWER_MINUS_4DBM, c.REG4_POWER_MINUS_1DBM,
            c.REG4_POWER_PLUS_2DBM, c.REG4_POWER_PLUS_5DBM) == (0, 1, 2, 3)