"""Regression tests for confirmed defects (code review, 2026-10-15).

Each test asserts the *correct* behaviour and is marked ``known_bug``: a
strict xfail. When a fix lands the test starts passing, strict mode turns
that into a failure, and the marker must be removed in the same change.
The finding ID in each reason (C1, C2, ...) refers to the review findings
and the remediation plan.

Tests that pin a private helper (``_pick_step_grid``) go away with the
helper when the sweep code is rewritten; port the intent, not the call.
"""

import ast
import pathlib
import re
from fractions import Fraction

import pytest

from adf435x import consts
from adf435x.profiles import ADF4351
from adf435x.register_file import ADF435xRegisterFile
from adf435x.solver import (
    DividerOctaveCrossingError,
    ExactFrequencyError,
    SolveOptions,
    _pick_step_grid,
    build_frequency_table,
    solve,
)
from adf435x.sweep import ADF435xSweeper, FrequencyTable
from adf435x.synthesizer import ADF435xSynthesizer
from conftest import WORKED_FIELDS, FakeChip, FakeDevice

REF_HZ = 10_000_000
EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"


def known_bug(finding, why, raises=None):
    """Strict xfail tagged with a review finding ID."""
    return pytest.mark.xfail(
        strict=True, raises=raises, reason="%s: %s" % (finding, why)
    )


def _field(word, pos, width):
    """Extract a bit field from a register word."""
    return (word >> pos) & ((1 << width) - 1)


def _exact_output_hz(fields, ref_hz, r_counter=1, doubler=False, rdiv2=False):
    """Exact RF output (Fraction) for solver *fields*."""
    f_pfd = Fraction(ref_hz * (2 if doubler else 1), r_counter * (2 if rdiv2 else 1))
    n = fields["int_n"] + Fraction(fields["frac"], fields["mod"])
    return n * f_pfd / fields["rf_divider"]


def _powered_chip_synth(ref_hz=REF_HZ, muxout=1):
    """Synthesizer on a FakeChip, powered up at 200 MHz."""
    chip = FakeChip(muxout=muxout)
    synth = ADF435xSynthesizer(chip, ADF4351, ref_hz)
    synth.power_up(frequency_hz=200_000_000)
    return chip, synth


# --- C1: sweep plans are encoded from defaults, not the synth config --------


class TestSweepUsesSynthConfig:
    """Sweep writes must carry the synthesizer's own settings (C1)."""

    @known_bug("C1", "sweep plans encode a default config", AssertionError)
    def test_output_power_preserved(self):
        """A user-set -4 dBm survives the first sweep hop."""
        chip, synth = _powered_chip_synth()
        synth.set_output_power(consts.REG4_POWER_MINUS_4DBM)
        table = FrequencyTable.from_range(
            synth, 190_000_000, 210_000_000, 2_000_000
        )
        ADF435xSweeper(synth, table).step()
        r4 = chip.active_words[consts.REG4_ADDR]
        power = _field(r4, consts.REG4_OUTPUT_POWER_POS, 2)
        assert power == consts.REG4_POWER_MINUS_4DBM

    @known_bug("C1", "sweep plans encode a default config", AssertionError)
    def test_charge_pump_current_preserved(self):
        """A user-set CP current survives the first sweep hop."""
        chip, synth = _powered_chip_synth()
        synth.regfile.configure(cp_current_code=3)
        synth.set_frequency(200_000_000)
        table = FrequencyTable.from_range(
            synth, 190_000_000, 210_000_000, 2_000_000
        )
        ADF435xSweeper(synth, table).step()
        r2 = chip.active_words[consts.REG2_ADDR]
        assert _field(r2, consts.REG2_CP_CURRENT_POS, 4) == 3

    @known_bug("C1", "fast-hop double buffer never reaches the chip", AssertionError)
    def test_fast_hop_double_buffer_written(self):
        """Fast-hop mode's R2 DB13 is set on the chip after playback."""
        chip, synth = _powered_chip_synth()
        table = FrequencyTable.from_range(
            synth, 190_000_000, 210_000_000, 2_000_000
        )
        ADF435xSweeper(synth, table).step()
        r2 = chip.active_words[consts.REG2_ADDR]
        assert _field(r2, consts.REG2_DOUBLE_BUFFER_POS, 1) == 1

    @known_bug("C1", "write cache diverges from the chip", AssertionError)
    def test_cache_matches_chip_after_hop(self):
        """After a hop, last-written words equal what the chip holds."""
        chip, synth = _powered_chip_synth()
        synth.set_output_power(consts.REG4_POWER_MINUS_4DBM)
        table = FrequencyTable.from_range(
            synth, 190_000_000, 210_000_000, 2_000_000
        )
        ADF435xSweeper(synth, table).step()
        cached = [r["last_written"] for r in synth.regfile.dump()["registers"]]
        assert cached == chip.input_words


# --- C2: range tables are far coarser than requested ------------------------


class TestRangeTableCoverage:
    """from_range must honour the requested step and bounds (C2)."""

    @known_bug("C2", "MOD locked from the lower endpoint's exact solve", AssertionError)
    def test_entry_count_matches_step(self, synth):
        """100-101 MHz in 10 kHz steps has 101 entries."""
        table = FrequencyTable.from_range(
            synth, 100_000_000, 101_000_000, 10_000
        )
        assert len(table) == 101

    @known_bug("C2", "grid too coarse to land on the requested points", AssertionError)
    def test_points_land_on_requested_grid(self, synth):
        """190-210 MHz in 2 MHz steps hits 190, 192, ... 210 MHz."""
        table = FrequencyTable.from_range(
            synth, 190_000_000, 210_000_000, 2_000_000
        )
        achieved = [table[i].achieved_hz for i in range(len(table))]
        assert achieved == list(range(190_000_000, 210_000_001, 2_000_000))

    @known_bug("C2", "_pick_step_grid drops interior grid points", AssertionError)
    def test_step_grid_keeps_interior_points(self):
        """A step finer than the grid keeps every grid point."""
        assert _pick_step_grid([0, 10, 20, 30, 40], 3) == [0, 10, 20, 30, 40]

    @known_bug("C2", "n_high mixes locked and gcd-reduced MOD", AssertionError)
    def test_reaches_upper_bound(self, synth):
        """190.01-190.1 MHz ends at 190.1 MHz, not 190.02 MHz."""
        table = FrequencyTable.from_range(
            synth, 190_010_000, 190_100_000, 10_000
        )
        assert table[len(table) - 1].achieved_hz == 190_100_000

    @known_bug("C2", "upper endpoint rounds past the requested bound", AssertionError)
    def test_stays_within_bounds(self, synth):
        """No entry of a 433.05-434.79 MHz table exceeds 434.79 MHz."""
        table = FrequencyTable.from_range(
            synth, 433_050_000, 434_790_000, 25_000
        )
        assert max(table[i].achieved_hz for i in range(len(table))) <= 434_790_000


# --- C3: explicit frequency lists silently lose accuracy --------------------


class TestFrequencyListAccuracy:
    """from_frequencies must not trade accuracy silently (C3)."""

    @known_bug("C3", "MOD locked from the first frequency", AssertionError)
    def test_independently_exact_targets_stay_exact(self, synth):
        """Targets that each solve exactly keep zero error in a table."""
        freqs = [100_000_000, 100_010_000, 100_123_456]
        table = FrequencyTable.from_frequencies(synth, freqs)
        errors = [table[i].error_hz for i in range(len(table))]
        assert errors == [0, 0, 0]


# --- C4: "locked" MOD is not locked -----------------------------------------


class TestLockedMod:
    """A locked MOD must stay locked (C4)."""

    @known_bug("C4", "gcd reduction changes MOD inside a segment", AssertionError)
    def test_mod_constant_across_table(self, synth):
        """Every entry of a single-divider table shares one MOD."""
        table = FrequencyTable.from_range(
            synth, 433_050_000, 434_790_000, 25_000
        )
        mods = {table[i].fields["mod"] for i in range(len(table))}
        assert len(mods) == 1

    @known_bug("C4", "MOD changes force R1 rewrites mid-sweep", AssertionError)
    def test_in_band_hops_are_single_r0_writes(self, synth):
        """Hops after the first write only R0."""
        table = FrequencyTable.from_range(
            synth, 433_050_000, 434_790_000, 25_000
        )
        lengths = {len(table[i].plan) for i in range(1, len(table))}
        assert lengths == {1}

    @known_bug("C4", "explicit MOD is gcd-reduced", AssertionError)
    def test_explicit_mod_is_kept(self):
        """SolveOptions(mod=50) returns MOD 50 (inverts test_explicit_mod_gcd_reduces)."""
        result = solve(
            2_112_600_000, REF_HZ, ADF4351, options=SolveOptions(mod=50)
        )
        assert result.fields["mod"] == 50


# --- C5 / C6: PFD truncation and floored achieved frequency ------------------


class TestExactArithmetic:
    """Solver reporting must use exact arithmetic (C5, C6)."""

    @known_bug("C5", "fPFD truncated to whole hertz", AssertionError)
    def test_non_integer_pfd_reports_true_error(self):
        """25 MHz / R=3 reaches 1 GHz exactly; no phantom 40 Hz error."""
        result = solve(
            1_000_000_000,
            25_000_000,
            ADF4351,
            options=SolveOptions(r_counter=3),
        )
        assert result.error_hz == 0

    @known_bug("C5", "exact=True rejects an exactly reachable target")
    def test_non_integer_pfd_exact_accepted(self):
        """exact=True accepts 1 GHz from 25 MHz / R=3."""
        result = solve(
            1_000_000_000,
            25_000_000,
            ADF4351,
            options=SolveOptions(r_counter=3, exact=True),
        )
        assert _exact_output_hz(result.fields, 25_000_000, r_counter=3) == 1_000_000_000

    @known_bug("C6", "floored achieved_hz hides a 0.62 Hz residual")
    def test_exact_rejects_sub_hertz_residual(self):
        """100,000,399 Hz is not exactly reachable; exact=True must raise."""
        with pytest.raises(ExactFrequencyError):
            solve(100_000_399, REF_HZ, ADF4351, options=SolveOptions(exact=True))


# --- C7 / C17 / C21 / C8: validation gaps ------------------------------------


class TestValidationGaps:
    """configure() must reject values the chip cannot use.

    Fixed in remediation step A2 (C7, C17, C21, C8 divider limit).
    """

    @pytest.mark.parametrize(
        "field, value",
        [("mtld", 2), ("rf_enable", 2), ("doubler", 5)],
    )
    def test_boolean_field_rejects_non_bool(self, field, value):
        """Non-0/1 values for on/off fields raise ValueError."""
        regfile = ADF435xRegisterFile(ADF4351)
        with pytest.raises(ValueError):
            regfile.configure(**{field: value})

    def test_phase_must_be_below_mod(self):
        """Phase 30 with MOD 25 raises (data sheet p.18)."""
        regfile = ADF435xRegisterFile(ADF4351)
        regfile.configure(**WORKED_FIELDS)
        with pytest.raises(ValueError):
            regfile.configure(phase=30)

    def test_low_spur_requires_mod_50(self):
        """Low-spur noise mode with MOD 25 raises (data sheet p.23)."""
        regfile = ADF435xRegisterFile(ADF4351)
        regfile.configure(**WORKED_FIELDS)
        with pytest.raises(ValueError):
            regfile.configure(noise_mode=consts.REG2_LOW_SPUR)

    def test_muxout_n_divider_rejected(self):
        """MUXOUT = N divider output raises (data sheet p.18)."""
        regfile = ADF435xRegisterFile(ADF4351)
        with pytest.raises(ValueError):
            regfile.configure(muxout=consts.REG2_MUX_NDIVIDER)

    def test_fast_band_select_divider_max_254(self):
        """band_clk_div 255 with fast mode raises (data sheet p.19)."""
        regfile = ADF435xRegisterFile(ADF4351)
        regfile.configure(band_clk_mode=consts.REG3_BAND_CLK_HIGH)
        with pytest.raises(ValueError):
            regfile.configure(band_clk_div=255)


class TestLowSpurSolve:
    """The solver must honour the low-spur MOD minimum (C21, solver side)."""

    @known_bug("C21", "solver picks MOD < 50 in low-spur mode", ValueError)
    def test_set_frequency_in_low_spur_mode(self, synth):
        """A low-spur retune picks a MOD of at least 50."""
        synth.regfile.configure(noise_mode=consts.REG2_LOW_SPUR, mod=50)
        synth.set_frequency(2_112_600_000)
        assert synth.regfile.config.mod >= 50


# --- C8: valid ADF4351 PFD range rejected -------------------------------------


class TestBandSelectRange:
    """ADF4351 fast band select covers fPFD up to 32 MHz (C8)."""

    @known_bug("C8", "normal-mode cap applied before fast mode")
    def test_32_mhz_pfd_solves(self):
        """A 32 MHz PFD solves on the ADF4351 in fast mode."""
        result = solve(1_000_000_000, 32_000_000, ADF4351)
        assert result.fields["band_clk_mode"] == consts.REG3_BAND_CLK_HIGH


# --- C9: lock-detect settings -------------------------------------------------


class TestLockDetectSettings:
    """LDF/LDP follow data sheet p.19: frac-N 00, int-N 11 (C9)."""

    @known_bug("C9", "solver never sets LDP", AssertionError)
    def test_fractional_n_uses_10ns_window(self):
        """Fractional-N solve sets LDP to 10 ns."""
        result = solve(2_112_600_000, REF_HZ, ADF4351)
        assert result.fields.get("ldp") == consts.REG2_LDP_10NS

    @known_bug("C9", "solver never sets LDP", AssertionError)
    def test_integer_n_uses_6ns_window(self):
        """Integer-N solve sets LDP to 6 ns."""
        result = solve(200_000_000, REF_HZ, ADF4351)
        assert result.fields.get("ldp") == consts.REG2_LDP_6NS

    @known_bug("C9", "fast-hop forces 6 ns in fractional-N", AssertionError)
    def test_fast_hop_keeps_fractional_n_window(self, synth):
        """Fast-hop mode does not force LDP 6 ns on a fractional-N tune."""
        synth.set_frequency(2_112_600_000)
        synth._enable_fast_hop_mode()
        assert synth.regfile.config.ldp == consts.REG2_LDP_10NS


# --- C10 / C16: synthesizer power-up and unpowered writes ---------------------


class TestPowerUp:
    """Power-up must never program an unusable configuration (C10)."""

    @known_bug("C10", "power_up() without a frequency writes placeholders")
    def test_power_up_requires_frequency(self, synth):
        """power_up() with no frequency ever set raises."""
        with pytest.raises(ValueError):
            synth.power_up()

    @known_bug("C10", "reference path applied only by a solve", AssertionError)
    def test_constructor_applies_r_counter(self):
        """The R counter passed to the constructor is in the register file."""
        synth = ADF435xSynthesizer(
            FakeDevice(), ADF4351, 25_000_000, r_counter=5
        )
        assert synth.regfile.config.r_counter == 5

    @known_bug("C10", "CE raised before the solve", AssertionError)
    def test_failed_solve_leaves_chip_disabled(self, fake_device, synth):
        """An out-of-range power-up frequency leaves CE low."""
        with pytest.raises(ValueError):
            synth.power_up(frequency_hz=1)
        assert fake_device.ce == 0

    @known_bug("C16", "set_frequency writes SPI while CE is low", AssertionError)
    def test_set_frequency_unpowered_does_not_write(self, fake_device, synth):
        """Before power-up, set_frequency stores settings without SPI."""
        synth.set_frequency(200_000_000)
        assert fake_device.writes == []


# --- C11: divider-boundary sweeps without MUXOUT ------------------------------


class TestSweepWithoutMuxout:
    """Boards without MUXOUT can still sweep across dividers (C11)."""

    @known_bug("C11", "boundary hops always read MUXOUT", RuntimeError)
    def test_boundary_sweep_completes(self):
        """A divider-crossing sweep runs to completion with no MUXOUT."""
        synth = ADF435xSynthesizer(FakeDevice(muxout=None), ADF4351, REF_HZ)
        table = FrequencyTable.from_range(
            synth,
            130_000_000,
            140_000_000,
            5_000_000,
            allow_divider_change=True,
        )
        player = ADF435xSweeper(synth, table)
        player.run()
        assert player.index == len(table)


# --- C12: lock polling starts before band select can finish -------------------


class TestLockSettle:
    """wait_locked must not sample MUXOUT during band select (C12)."""

    @known_bug("C12", "first MUXOUT poll is immediate", AssertionError)
    def test_first_poll_after_band_select_time(self, synth, monkeypatch):
        """First read happens >= 10 band-select clocks after the call."""
        import adf435x.synthesizer as synth_mod

        clock = [0]
        monkeypatch.setattr(synth_mod, "_ticks_us", lambda: clock[0])
        monkeypatch.setattr(
            synth_mod, "_sleep_us", lambda us: clock.__setitem__(0, clock[0] + us)
        )
        synth.power_up(frequency_hz=2_112_600_000)
        first_read = []
        monkeypatch.setattr(
            synth._device,
            "read_muxout",
            lambda: first_read.append(clock[0]) or 1,
        )
        start = clock[0]
        synth.wait_locked()
        # 10 cycles of a 10 MHz / 20 = 500 kHz band-select clock = 20 us.
        assert first_read[0] - start >= 20


# --- C13: divider-crossing error suggestions ----------------------------------


_NARROW = re.compile(r"Narrow to \[(\d+), (\d+)\] or \[(\d+), (\d+)\]")


def _narrow_ranges(err):
    """Parse the two suggested ranges from the crossing message."""
    a, b, c, d = (int(x) for x in _NARROW.search(str(err)).groups())
    return (a, b), (c, d)


class TestCrossingSuggestions:
    """Suggested ranges must not themselves cross a divider (C13)."""

    @known_bug("C13", "suggested upper bound is one hertz too high", AssertionError)
    def test_low_range_uses_one_divider(self):
        """The suggested low range stays on the low endpoint's divider."""
        with pytest.raises(DividerOctaveCrossingError) as exc:
            build_frequency_table(
                100_000_000, 200_000_000, 1_000_000, REF_HZ, ADF4351
            )
        (_, low_hi), _ = _narrow_ranges(exc.value)
        divider = solve(low_hi, REF_HZ, ADF4351).fields["rf_divider"]
        assert divider == exc.value.lower_divider

    @known_bug("C13", "descending lists give reversed ranges", AssertionError)
    def test_descending_list_ranges_are_ordered(self, synth):
        """Suggested ranges are ascending for a descending list."""
        with pytest.raises(DividerOctaveCrossingError) as exc:
            FrequencyTable.from_frequencies(synth, [300_000_000, 100_000_000])
        (a, b), (c, d) = _narrow_ranges(exc.value)
        assert a <= b and c <= d


# --- C14: input validation ----------------------------------------------------


class TestSolverInputs:
    """solve() rejects invalid inputs with clear errors (C14)."""

    @known_bug("C14", "zero reference divides by zero", ZeroDivisionError)
    def test_zero_reference_raises_value_error(self):
        """ref_hz=0 raises ValueError, not ZeroDivisionError."""
        with pytest.raises(ValueError):
            solve(200_000_000, 0, ADF4351)

    @known_bug("C14", "float frequencies are accepted")
    def test_float_target_rejected(self):
        """A float target raises TypeError or ValueError."""
        with pytest.raises((TypeError, ValueError)):
            solve(200e6, REF_HZ, ADF4351)

    @known_bug("C14", "out-of-range MOD returned as a field")
    def test_mod_out_of_range_rejected(self):
        """SolveOptions(mod=5000) raises at solve time."""
        with pytest.raises(ValueError):
            solve(200_000_000, REF_HZ, ADF4351, options=SolveOptions(mod=5000))

    @known_bug("C14", "illegal divider gives a misleading error", AssertionError)
    def test_illegal_divider_message(self):
        """SolveOptions(rf_divider=3) names the divider in the error."""
        with pytest.raises(ValueError, match="rf_divider"):
            solve(200_000_000, REF_HZ, ADF4351, options=SolveOptions(rf_divider=3))


# --- C15: playback after interleaved writes -----------------------------------


class TestInterleavedPlayback:
    """Hops stay correct after other writes between steps (C15)."""

    @known_bug("C15", "delta plans assume the previous table entry", AssertionError)
    def test_step_after_set_frequency(self):
        """After set_frequency between steps, the chip matches the cache."""
        chip, synth = _powered_chip_synth()
        table = FrequencyTable.from_range(
            synth, 190_000_000, 210_000_000, 2_000_000
        )
        player = ADF435xSweeper(synth, table)
        player.step()
        synth.set_frequency(200_100_000)
        player.step()
        cached = [r["last_written"] for r in synth.regfile.dump()["registers"]]
        assert cached == chip.input_words


# --- C19: example arithmetic --------------------------------------------------


class TestExampleConstants:
    """Example scripts state correct expected values (C19)."""

    @known_bug("C19", "registers.py expects 131.9125 MHz", AssertionError)
    def test_registers_example_expected_output(self):
        """4225.2 MHz / 32 = 132,037,500 Hz."""
        tree = ast.parse((EXAMPLES / "registers.py").read_text())
        values = {
            node.targets[0].id: node.value.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
        }
        assert values["EXPECTED_RFOUT_HZ"] == 132_037_500


# --- Q6: public error classes -------------------------------------------------


class TestPublicErrors:
    """Solver error classes are importable from the package root (Q6)."""

    @known_bug("Q6", "only DividerOctaveCrossingError is exported", AssertionError)
    @pytest.mark.parametrize(
        "name",
        ["FrequencyOutOfRangeError", "NoSolutionError", "ExactFrequencyError"],
    )
    def test_error_exported(self, name):
        """Each solver error is an attribute of ``adf435x``."""
        import adf435x

        assert hasattr(adf435x, name)
