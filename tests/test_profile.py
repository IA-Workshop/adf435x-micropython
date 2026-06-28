import pytest

from adf435x.profiles import ADF4350, ADF4351, ADF435xDeviceProfile

# Capability flags the ADF4351 implements and the ADF4350 does not.
CAPABILITY_FLAGS = [
    "has_phase_adjust",
    "has_fast_band_select",
    "has_programmable_abp",
    "has_charge_cancel",
]


class TestDividerRange:
    def test_adf4350_max(self):
        assert ADF4350.rf_divider_max == 16

    def test_adf4351_max(self):
        assert ADF4351.rf_divider_max == 64


class TestCapabilityFlags:
    @pytest.mark.parametrize("flag", CAPABILITY_FLAGS, ids=CAPABILITY_FLAGS)
    def test_adf4351_implements(self, flag):
        assert getattr(ADF4351, flag) is True

    @pytest.mark.parametrize("flag", CAPABILITY_FLAGS, ids=CAPABILITY_FLAGS)
    def test_adf4350_lacks(self, flag):
        assert getattr(ADF4350, flag) is False


class TestPrescalerCeiling:
    def test_adf4350(self):
        assert ADF4350.prescaler_4_5_max_hz == 3_000_000_000

    def test_adf4351(self):
        assert ADF4351.prescaler_4_5_max_hz == 3_600_000_000


class TestPllLimits:
    """Datasheet INT/MOD bounds (ADF4350 and ADF4351 share these)."""

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_int_minimums(self, profile):
        assert profile.int_min_4_5 == 23
        assert profile.int_min_8_9 == 75
        assert profile.int_max == 65535

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_mod_range(self, profile):
        assert profile.mod_min == 2
        assert profile.mod_max == 4095


class TestDividerCode:
    @pytest.mark.parametrize(
        "divider, code",
        [
            (1, 0),
            (2, 1),
            (4, 2),
            (64, 6),
        ],
    )
    def test_adf4351_mapping(self, divider, code):
        assert ADF4351.divider_code(divider) == code

    def test_adf4350_max_divider(self):
        assert ADF4350.divider_code(16) == 4

    def test_adf4351_allows_32(self):
        assert ADF4351.divider_code(32) == 5

    def test_adf4350_rejects_above_max(self):
        # /32 exists on the 4351 but exceeds the 4350's /16 maximum.
        with pytest.raises(ValueError):
            ADF4350.divider_code(32)

    def test_rejects_non_power_of_two(self):
        with pytest.raises(ValueError):
            ADF4351.divider_code(3)


class TestCustomProfile:
    @pytest.fixture
    def profile(self):
        return ADF435xDeviceProfile(
            "X",
            rf_divider_max=8,
            has_phase_adjust=True,
            has_fast_band_select=False,
            has_programmable_abp=True,
            has_charge_cancel=False,
            prescaler_4_5_max_hz=4_000_000_000,
        )

    def test_divider_code_within_range(self, profile):
        assert profile.divider_code(8) == 3

    def test_divider_code_above_range_rejected(self, profile):
        with pytest.raises(ValueError):
            profile.divider_code(16)
