"""Self-tests for the FakeChip latching model in conftest."""

from fractions import Fraction

from adf435x import consts
from conftest import WORKED_WORDS, FakeChip

# Golden example output: 2112.6 MHz from a 10 MHz reference.
REF_HZ = 10_000_000


def _with_field(word, pos, width, value):
    """Return *word* with a bit field replaced."""
    mask = ((1 << width) - 1) << pos
    return (word & ~mask) | ((value << pos) & mask)


class TestFakeChipLatching:
    """Double-buffer behaviour per data sheet p.12 / Figure 23."""

    def test_full_write_latches_worked_words(self):
        """R5..R0 of the golden example makes every register active."""
        chip = FakeChip()
        chip.write_registers(list(reversed(WORKED_WORDS)))
        assert chip.active_words == WORKED_WORDS

    def test_golden_output_frequency(self):
        """The decoded golden example is exactly 2112.6 MHz."""
        chip = FakeChip()
        chip.write_registers(list(reversed(WORKED_WORDS)))
        assert chip.output_hz(REF_HZ) == Fraction(2_112_600_000)

    def test_r1_mod_waits_for_r0(self):
        """A MOD change in R1 is not active until R0 is written."""
        chip = FakeChip()
        chip.write_registers(list(reversed(WORKED_WORDS)))
        new_r1 = _with_field(WORKED_WORDS[1], consts.REG1_MOD_POS, 12, 50)
        chip.write_registers([new_r1])
        assert chip.active_words[1] == WORKED_WORDS[1]

    def test_r1_mod_latches_on_r0(self):
        """Writing R0 latches the pending R1 MOD."""
        chip = FakeChip()
        chip.write_registers(list(reversed(WORKED_WORDS)))
        new_r1 = _with_field(WORKED_WORDS[1], consts.REG1_MOD_POS, 12, 50)
        chip.write_registers([new_r1, WORKED_WORDS[0]])
        assert chip.active_words[1] == new_r1

    def test_r1_prescaler_is_immediate(self):
        """The prescaler bit is not double-buffered."""
        chip = FakeChip()
        chip.write_registers(list(reversed(WORKED_WORDS)))
        new_r1 = WORKED_WORDS[1] ^ (1 << consts.REG1_PRESCALER_POS)
        chip.write_registers([new_r1])
        assert chip.active_words[1] == new_r1

    def test_r4_divider_immediate_without_db13(self):
        """With R2 DB13 clear, the R4 divider takes effect on write."""
        chip = FakeChip()
        chip.write_registers(list(reversed(WORKED_WORDS)))
        new_r4 = _with_field(WORKED_WORDS[4], consts.REG4_RF_DIVIDER_POS, 3, 2)
        chip.write_registers([new_r4])
        assert chip.active_words[4] == new_r4

    def test_r4_divider_buffered_with_db13(self):
        """With R2 DB13 set, the R4 divider waits for R0."""
        chip = FakeChip()
        r2_dbb = WORKED_WORDS[2] | (1 << consts.REG2_DOUBLE_BUFFER_POS)
        words = list(WORKED_WORDS)
        words[2] = r2_dbb
        chip.write_registers(list(reversed(words)))
        new_r4 = _with_field(WORKED_WORDS[4], consts.REG4_RF_DIVIDER_POS, 3, 2)
        chip.write_registers([new_r4])
        assert chip.active_words[4] == WORKED_WORDS[4]
