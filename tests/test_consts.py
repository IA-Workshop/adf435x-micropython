"""
Host tests for consts.py: the const override must be invoked when running on
the host under CPython, and the field positions must reconstruct known-good
register words (Datasheet worked example, 2112.6 MHz).
"""

from adf435x import consts as c


def test_const_imports_on_host():
    """The CPython ``const`` shim lets folded values import under pytest."""
    # If the micropython->CPython shim were missing, importing this module
    # would already have raised. This test spot-checks that a folded value
    # survived.
    assert c.NUM_REGISTERS == 6


def test_dbr_register_indices():
    """The DBR set names exactly R1 and R2 (the R0-latched registers)."""
    assert c.DBR_REGISTER_INDICES == (c.REG1_ADDR, c.REG2_ADDR)


def test_r0_layout_worked_example():
    """R0 positions reconstruct the worked-example word from INT and FRAC."""
    # INT=422, FRAC=13 -> R0 = 0x00D30068
    r0 = (422 << c.REG0_INT_POS) | (13 << c.REG0_FRAC_POS) | c.REG0_ADDR
    assert r0 == 0x00D30068


def test_r1_layout_worked_example():
    """R1 positions reconstruct the worked-example word."""
    # prescaler 8/9, phase=1, MOD=25 -> R1 = 0x080080C9
    r1 = (
        (c.REG1_PRESCALER_8_9 << c.REG1_PRESCALER_POS)
        | (1 << c.REG1_PHASE_POS)
        | (25 << c.REG1_MOD_POS)
        | c.REG1_ADDR
    )
    assert r1 == 0x080080C9


def test_r5_reserved_ones():
    """The R5 reserved-ones mask sets exactly DB20 and DB19."""
    assert c.REG5_RESERVED_ONES == (1 << 20) | (1 << 19)


def test_muxout_digital_lock_value():
    """Digital lock detect encodes to the datasheet value 0b110."""
    assert c.REG2_MUX_DIGITALLOCK == 0b110


def test_output_power_levels_ascending():
    """Output power codes are the ascending pair encodings 0..3."""
    levels = (
        c.REG4_POWER_MINUS_4DBM,
        c.REG4_POWER_MINUS_1DBM,
        c.REG4_POWER_PLUS_2DBM,
        c.REG4_POWER_PLUS_5DBM,
    )
    assert levels == (0, 1, 2, 3)
