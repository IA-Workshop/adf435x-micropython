"""Pytest configuration: gate hardware-dependent tests behind --device.

Pure-logic tests have no mark and always run on the host. Tests that need a
physically connected ADF435x are marked ``@pytest.mark.device`` and are
skipped unless the suite is run with ``--device`` (i.e. you have asserted that
hardware is present). Those tests must assert on DIGITAL values only, e.g. a
MUXOUT lock-detect level or other GPIO-based signal. Analog behavior like
actual RF frequency and power must be verified by users' own separate test
harness.
"""

def pytest_addoption(parser):
    parser.addoption(
        "--device", action="store_true", default=False,
        help="run tests that require a connected ADF435x device")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--device"):
        return
    import pytest
    skip = pytest.mark.skip(reason="needs --device (no connected ADF435x)")
    for item in items:
        if "device" in item.keywords:
            item.add_marker(skip)