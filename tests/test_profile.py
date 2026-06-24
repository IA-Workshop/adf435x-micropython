import pytest
from adf435x.profiles import ADF4350, ADF4351, DeviceProfile


def test_divider_range_differs():
    assert ADF4350.rf_divider_max == 16
    assert ADF4351.rf_divider_max == 64


def test_capability_flags():
    # The 4351 implements the features the 4350 lacks.
    for flag in ("has_phase_adjust", "has_fast_band_select",
                 "has_programmable_abp", "has_charge_cancel"):
        assert getattr(ADF4351, flag) is True
        assert getattr(ADF4350, flag) is False


def test_prescaler_ceiling():
    assert ADF4350.prescaler_4_5_max_hz == 3_000_000_000
    assert ADF4351.prescaler_4_5_max_hz == 3_600_000_000


def test_divider_code_mapping():
    assert ADF4351.divider_code(1) == 0
    assert ADF4351.divider_code(2) == 1
    assert ADF4351.divider_code(4) == 2
    assert ADF4351.divider_code(64) == 6
    assert ADF4350.divider_code(16) == 4


def test_divider_code_rejects_out_of_range_for_4350():
    # 32 and 64 exist on the 4351 but exceed the 4350's /16 maximum.
    with pytest.raises(ValueError):
        ADF4350.divider_code(32)
    assert ADF4351.divider_code(32) == 5  # fine on the 4351


def test_divider_code_rejects_non_power_of_two():
    with pytest.raises(ValueError):
        ADF4351.divider_code(3)


def test_profile_is_constructible():
    p = DeviceProfile("X", rf_divider_max=8, has_phase_adjust=True,
                      has_fast_band_select=False, has_programmable_abp=True,
                      has_charge_cancel=False, prescaler_4_5_max_hz=4_000_000_000)
    assert p.divider_code(8) == 3
    with pytest.raises(ValueError):
        p.divider_code(16)