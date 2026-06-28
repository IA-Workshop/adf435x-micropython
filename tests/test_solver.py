"""Host tests for solver stubs (full solver logic deferred)."""

import pytest

from adf435x import consts
from adf435x.solver import ADF4351_LIMITS, DeviceLimits, _round_div


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
    assert _round_div(num, den) == expected


@pytest.mark.parametrize(
    "vco_min_hz, max_divider, expected",
    [
        (2_200_000_000, 64, _round_div(2_200_000_000, 64)),
        (2_200_000_000, 32, _round_div(2_200_000_000, 32)),
        (3_000_000_000, 64, _round_div(3_000_000_000, 64)),
    ],
)
def test_device_limits_output_min_hz(vco_min_hz, max_divider, expected):
    limits = DeviceLimits(
        vco_min_hz=vco_min_hz,
        rf_dividers=(1, 2, 4, max_divider),
    )
    assert limits.output_min_hz == expected


@pytest.mark.parametrize(
    "vco_max_hz",
    [4_400_000_000, 3_600_000_000, 2_800_000_000],
)
def test_device_limits_output_max_hz(vco_max_hz):
    limits = DeviceLimits(vco_max_hz=vco_max_hz)
    assert limits.output_max_hz == vco_max_hz


@pytest.mark.parametrize(
    "attr, expected",
    [
        ("prescaler_4_5_max_hz", 3_600_000_000),
        ("vco_min_hz", 2_200_000_000),
        ("vco_max_hz", 4_400_000_000),
        ("int_min_4_5", 23),
        ("int_min_8_9", 75),
        ("int_max", 65535),
        ("mod_min", 2),
        ("mod_max", 4095),
    ],
)
def test_adf4351_limits_defaults(attr, expected):
    assert getattr(ADF4351_LIMITS, attr) == expected


@pytest.mark.parametrize(
    "name, value",
    [
        ("PRESCALER_4_5", consts.REG1_PRESCALER_4_5),
        ("PRESCALER_8_9", consts.REG1_PRESCALER_8_9),
    ],
)
def test_prescaler_constants_match_consts(name, value):
    from adf435x import solver

    assert getattr(solver, name) == value
