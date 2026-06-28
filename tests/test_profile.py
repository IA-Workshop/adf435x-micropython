"""Host tests for ADF435xDeviceProfile: divider range, capability flags,
PLL/prescaler limits, and the divider-to-code mapping.
"""

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
    """Each profile exposes its maximum RF output divider."""

    def test_adf4350_max(self):
        """The ADF4350 tops out at a /16 output divider."""
        assert ADF4350.rf_divider_max == 16

    def test_adf4351_max(self):
        """The ADF4351 tops out at a /64 output divider."""
        assert ADF4351.rf_divider_max == 64


class TestCapabilityFlags:
    """Capability flags distinguish the ADF4351 from the ADF4350."""

    @pytest.mark.parametrize("flag", CAPABILITY_FLAGS, ids=CAPABILITY_FLAGS)
    def test_adf4351_implements(self, flag):
        """The ADF4351 implements every gated capability."""
        assert getattr(ADF4351, flag) is True

    @pytest.mark.parametrize("flag", CAPABILITY_FLAGS, ids=CAPABILITY_FLAGS)
    def test_adf4350_lacks(self, flag):
        """The ADF4350 implements none of the gated capabilities."""
        assert getattr(ADF4350, flag) is False


class TestPrescalerCeiling:
    """The 4/5 prescaler ceiling differs between the two parts."""

    def test_adf4350(self):
        """The ADF4350 requires the 8/9 prescaler above 3.0 GHz."""
        assert ADF4350.prescaler_4_5_max_hz == 3_000_000_000

    def test_adf4351(self):
        """The ADF4351 requires the 8/9 prescaler above 3.6 GHz."""
        assert ADF4351.prescaler_4_5_max_hz == 3_600_000_000


class TestPllLimits:
    """Datasheet INT/MOD bounds (ADF4350 and ADF4351 share these)."""

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_int_minimums(self, profile):
        """Both parts share the same INT minimums and maximum."""
        assert profile.int_min_4_5 == 23
        assert profile.int_min_8_9 == 75
        assert profile.int_max == 65535

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_mod_range(self, profile):
        """Both parts share the same fractional modulus bounds."""
        assert profile.mod_min == 2
        assert profile.mod_max == 4095


class TestDividerCode:
    """``divider_code`` maps a power-of-two divider to log2 of itself."""

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
        """Each valid ADF4351 divider maps to its log2 code."""
        assert ADF4351.divider_code(divider) == code

    def test_adf4350_max_divider(self):
        """The ADF4350's /16 maximum maps to code 4."""
        assert ADF4350.divider_code(16) == 4

    def test_adf4351_allows_32(self):
        """The ADF4351 accepts /32, mapping to code 5."""
        assert ADF4351.divider_code(32) == 5

    def test_adf4350_rejects_above_max(self):
        """A divider above the ADF4350 maximum is rejected."""
        # /32 exists on the 4351 but exceeds the 4350's /16 maximum.
        with pytest.raises(ValueError):
            ADF4350.divider_code(32)

    def test_rejects_non_power_of_two(self):
        """A non-power-of-two divider is rejected."""
        with pytest.raises(ValueError):
            ADF4351.divider_code(3)


class TestCustomProfile:
    """Custom profiles honor their own divider range and repr."""

    @pytest.fixture
    def profile(self):
        """A small custom profile with a /8 divider ceiling."""
        return ADF435xDeviceProfile(
            "X",
            rf_divider_max=8,
            has_phase_adjust=True,
            has_fast_band_select=False,
            has_programmable_abp=True,
            has_charge_cancel=False,
            prescaler_4_5_max_hz=4_000_000_000,
        )

    def test_repr(self):
        """repr names the device for readable debug output."""
        assert repr(ADF4351) == "ADF435xDeviceProfile(ADF4351)"

    def test_divider_code_within_range(self, profile):
        """A custom profile maps its maximum divider to the right code."""
        assert profile.divider_code(8) == 3

    def test_divider_code_above_range_rejected(self, profile):
        """A custom profile rejects dividers above its own maximum."""
        with pytest.raises(ValueError):
            profile.divider_code(16)
