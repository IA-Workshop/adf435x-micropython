"""Host tests for the ADF435x frequency solver."""

import pytest

from adf435x import consts
from adf435x.profiles import ADF4350, ADF4351
from adf435x.solver import (
    ExactFrequencyError,
    FrequencyOutOfRangeError,
    NoSolutionError,
    SolveOptions,
    VCO_MAX_HZ,
    VCO_MIN_HZ,
    _compute_achieved_hz,
    _compute_f_pfd,
    _normalize_frac_mod,
    _output_min_hz,
    _pick_band_clk,
    _pick_prescaler,
    _pick_rf_divider,
    _round_div,
    build_frequency_table,
    solve,
)

from conftest import WORKED_FIELDS, WORKED_WORDS, make_config

REF_HZ = 10_000_000
GOLDEN_TARGET_HZ = 2_112_600_000


@pytest.mark.parametrize(
    "num, den, expected",
    [
        (5, 2, 3),
        (3, 2, 2),
        (1, 2, 1),
        (10, 5, 2),
        (0, 5, 0),
        (7, 3, 2),
        (8, 3, 3),
    ],
)
def test_round_div(num, den, expected):
    """Nearest-int division matches the expected rounded quotient."""
    assert _round_div(num, den) == expected


class TestComputeFPfd:
    """PFD frequency from the reference path."""

    def test_r_counter_one(self):
        """R=1 with no doubler or div-2 passes REFIN through."""
        assert _compute_f_pfd(REF_HZ, 1, False, False) == REF_HZ

    def test_r_counter_ten(self):
        """R=10 divides REFIN by ten."""
        assert _compute_f_pfd(REF_HZ, 10, False, False) == 1_000_000

    def test_doubler(self):
        """The reference doubler doubles REFIN before the R divider."""
        assert _compute_f_pfd(REF_HZ, 1, True, False) == 2 * REF_HZ

    def test_rdiv2(self):
        """Reference div-2 halves REFIN before the R divider."""
        assert _compute_f_pfd(REF_HZ, 1, False, True) == REF_HZ // 2

    def test_invalid_r_counter(self):
        """An out-of-range R counter is rejected."""
        with pytest.raises(ValueError, match="r_counter="):
            _compute_f_pfd(REF_HZ, 0, False, False)


class TestComputeAchieved:
    """Forward frequency from PLL register values."""

    def test_golden_vector(self):
        """Worked-example INT/FRAC/MOD reproduces 2112.6 MHz out."""
        achieved = _compute_achieved_hz(422, 13, 25, REF_HZ, 2)
        assert achieved == GOLDEN_TARGET_HZ


class TestGcdNormalize:
    """FRAC/MOD gcd reduction for spur reduction."""

    @pytest.mark.parametrize(
        "frac, mod, expected",
        [
            (26, 50, (13, 25)),
            (13, 25, (13, 25)),
            (0, 2, (0, 2)),
        ],
    )
    def test_normalize_frac_mod(self, frac, mod, expected):
        """gcd reduction lowers MOD when FRAC and MOD share a factor."""
        assert _normalize_frac_mod(frac, mod) == expected


class TestOutputRange:
    """Reachable output frequency bounds per profile."""

    @pytest.mark.parametrize(
        "profile, max_div, expected_min",
        [
            (ADF4351, 64, _round_div(VCO_MIN_HZ, 64)),
            (ADF4350, 16, _round_div(VCO_MIN_HZ, 16)),
        ],
    )
    def test_output_min_hz(self, profile, max_div, expected_min):
        """Minimum output is VCO minimum over the largest RF divider."""
        assert _output_min_hz(profile) == expected_min

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351])
    def test_output_max_is_vco_max(self, profile):
        """Maximum output equals the VCO maximum."""
        result = solve(VCO_MAX_HZ, REF_HZ, profile)
        assert result.achieved_hz == VCO_MAX_HZ


class TestPickRfDivider:
    """RF output divider selection."""

    def test_golden_uses_divide_by_two(self):
        """2112.6 MHz uses RF divide-by-2."""
        assert _pick_rf_divider(GOLDEN_TARGET_HZ, ADF4351) == 2

    def test_vco_max_uses_unity_divider(self):
        """4.4 GHz out uses RF divide-by-1."""
        assert _pick_rf_divider(VCO_MAX_HZ, ADF4351) == 1

    def test_minimum_output_uses_largest_divider(self):
        """Lowest output uses the profile's largest RF divider."""
        assert _pick_rf_divider(_output_min_hz(ADF4351), ADF4351) == 64

    def test_out_of_band_raises(self):
        """An unreachable target raises NoSolutionError."""
        with pytest.raises(NoSolutionError):
            _pick_rf_divider(VCO_MIN_HZ // 128, ADF4351)


class TestPickPrescaler:
    """Dual-modulus prescaler selection."""

    @pytest.mark.parametrize(
        "profile, vco_hz, expected",
        [
            (ADF4351, 3_000_000_000, consts.REG1_PRESCALER_4_5),
            (ADF4351, 3_600_000_000, consts.REG1_PRESCALER_4_5),
            (ADF4351, 3_600_000_001, consts.REG1_PRESCALER_8_9),
            (ADF4350, 3_000_000_000, consts.REG1_PRESCALER_4_5),
            (ADF4350, 3_000_000_001, consts.REG1_PRESCALER_8_9),
        ],
    )
    def test_prescaler_threshold(self, profile, vco_hz, expected):
        """Prescaler follows each profile's 4/5 vs 8/9 VCO threshold."""
        assert _pick_prescaler(vco_hz, profile) == expected


class TestPickBandClk:
    """Band-select clock divider and mode."""

    def test_adf4351_high_pfd_uses_fast_mode(self):
        """10 MHz fPFD uses fast band select with divide 20."""
        div, mode = _pick_band_clk(REF_HZ, ADF4351)
        assert div == 20
        assert mode == consts.REG3_BAND_CLK_HIGH

    def test_adf4351_low_pfd_uses_normal_mode(self):
        """100 kHz fPFD uses normal band select."""
        div, mode = _pick_band_clk(100_000, ADF4351)
        assert div == 1
        assert mode == consts.REG3_BAND_CLK_LOW

    def test_adf4350_always_normal(self):
        """ADF4350 has no fast band-select mode."""
        div, mode = _pick_band_clk(REF_HZ, ADF4350)
        assert mode == consts.REG3_BAND_CLK_LOW


class TestGoldenVector:
    """Datasheet worked example (2112.6 MHz, ADF4351)."""

    def test_fields_match_worked_example(self):
        """Solver fields match the conftest golden vector."""
        result = solve(GOLDEN_TARGET_HZ, REF_HZ, ADF4351)
        for key, value in WORKED_FIELDS.items():
            assert result.fields[key] == value

    def test_encode_matches_worked_words(self, mapper):
        """Encoded registers match the datasheet golden words."""
        result = solve(GOLDEN_TARGET_HZ, REF_HZ, ADF4351)
        words = mapper.encode_config(make_config(**result.fields))
        assert words == WORKED_WORDS

    def test_configure_round_trip(self, worked_regfile):
        """configure() accepts solver output without changing words."""
        result = solve(GOLDEN_TARGET_HZ, REF_HZ, ADF4351)
        before = worked_regfile.current_words()
        worked_regfile.configure(**result.fields)
        assert worked_regfile.current_words() == before

    def test_zero_error(self):
        """The golden target is achieved exactly."""
        result = solve(GOLDEN_TARGET_HZ, REF_HZ, ADF4351)
        assert result.error_hz == 0
        assert result.achieved_hz == GOLDEN_TARGET_HZ


class TestSolveIntegerN:
    """Integer-N solutions and register optimizations."""

    def test_frac_zero_at_vco_min(self):
        """2200 MHz out with divide-by-1 yields FRAC=0."""
        result = solve(VCO_MIN_HZ, REF_HZ, ADF4351)
        assert result.fields["frac"] == 0
        assert result.fields["rf_divider"] == 1

    def test_int_n_register_optimizations(self):
        """Integer-N sets LDF, ABP, and charge cancel on ADF4351."""
        result = solve(VCO_MIN_HZ, REF_HZ, ADF4351)
        assert result.fields["ldf"] == consts.REG2_LDF_INT_N
        assert result.fields["abp"] == consts.REG3_ABP_3NS
        assert result.fields["charge_cancel"] is True

    def test_fractional_n_clears_int_n_fields(self):
        """Fractional-N after integer-N sets frac-N register mode."""
        int_n = solve(VCO_MIN_HZ, REF_HZ, ADF4351)
        frac_n = solve(GOLDEN_TARGET_HZ, REF_HZ, ADF4351)
        assert int_n.fields["ldf"] == consts.REG2_LDF_INT_N
        assert frac_n.fields["ldf"] == consts.REG2_LDF_FRAC_N
        assert frac_n.fields["abp"] == consts.REG3_ABP_6NS
        assert frac_n.fields["charge_cancel"] is False


class TestSolveNearest:
    """Nearest-frequency fit with signed error."""

    def test_nonzero_error_reported(self):
        """A slightly off target returns a non-zero signed error."""
        target = GOLDEN_TARGET_HZ + 1
        result = solve(target, REF_HZ, ADF4351)
        assert result.error_hz != 0


class TestSolveModTieBreak:
    """MOD search prefers smaller MOD at equal error."""

    def test_search_picks_smallest_mod(self):
        """Default search returns MOD=25 for the golden frequency."""
        result = solve(GOLDEN_TARGET_HZ, REF_HZ, ADF4351)
        assert result.fields["mod"] == 25

    def test_explicit_mod_gcd_reduces(self):
        """MOD=50 gcd-reduces to the same FRAC/MOD as MOD=25."""
        result = solve(
            GOLDEN_TARGET_HZ,
            REF_HZ,
            ADF4351,
            options=SolveOptions(mod=50),
        )
        assert result.fields["mod"] == 25
        assert result.fields["frac"] == 13


class TestSolveOutOfRange:
    """Target frequency range checks."""

    def test_below_minimum(self):
        """Output below the profile minimum raises."""
        with pytest.raises(FrequencyOutOfRangeError):
            solve(_output_min_hz(ADF4351) - 1, REF_HZ, ADF4351)

    def test_above_maximum(self):
        """Output above the VCO maximum raises."""
        with pytest.raises(FrequencyOutOfRangeError):
            solve(VCO_MAX_HZ + 1, REF_HZ, ADF4351)


class TestSolveADF4350:
    """ADF4350-specific divider and prescaler limits."""

    def test_maximum_divider_is_sixteen(self):
        """Lowest ADF4350 output uses divide-by-16."""
        result = solve(_output_min_hz(ADF4350), REF_HZ, ADF4350)
        assert result.fields["rf_divider"] == 16

    def test_prescaler_threshold_three_ghz(self):
        """3.0 GHz VCO uses the 4/5 prescaler on ADF4350."""
        target = 3_000_000_000
        result = solve(target, REF_HZ, ADF4350)
        assert result.fields["prescaler"] == consts.REG1_PRESCALER_4_5


class TestSolveBandEdges:
    """VCO band and divider boundary frequencies."""

    def test_vco_max_output(self):
        """4.4 GHz out uses unity RF divider."""
        result = solve(VCO_MAX_HZ, REF_HZ, ADF4351)
        assert result.fields["rf_divider"] == 1
        assert result.achieved_hz == VCO_MAX_HZ

    def test_vco_min_over_max_divider(self):
        """Minimum output uses the largest RF divider."""
        result = solve(_output_min_hz(ADF4351), REF_HZ, ADF4351)
        assert result.fields["rf_divider"] == 64
        assert result.achieved_hz == _output_min_hz(ADF4351)


class TestBuildFrequencyTable:
    """Sweep table planning."""

    def test_example_band_has_multiple_entries(self):
        """190–210 MHz with 2 MHz step yields a multi-point table."""
        table, step = build_frequency_table(
            190_000_000, 210_000_000, 2_000_000, REF_HZ, ADF4351
        )
        assert step > 0
        assert len(table) >= 3
        assert table[0].achieved_hz <= table[-1].achieved_hz


class TestSolveExact:
    """Exact-frequency mode."""

    def test_exact_match_succeeds(self):
        """exact=True succeeds when the target is achievable."""
        result = solve(
            GOLDEN_TARGET_HZ,
            REF_HZ,
            ADF4351,
            options=SolveOptions(exact=True),
        )
        assert result.error_hz == 0

    def test_exact_mismatch_raises(self):
        """exact=True raises when the target cannot be hit exactly."""
        with pytest.raises(ExactFrequencyError):
            solve(
                GOLDEN_TARGET_HZ + 1,
                REF_HZ,
                ADF4351,
                options=SolveOptions(exact=True),
            )
