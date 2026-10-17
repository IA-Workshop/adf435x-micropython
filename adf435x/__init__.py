"""
adf435x: a library for the ADF4350/ADF4351 wideband PLL synthesizers.

Importing this package is host-safe. The pure modules below run on both CPython
and MicroPython. The device handler imports ``machine`` and is reached by its
submodule path (``adf435x.device``), so the package root stays importable for
host-side testing.
"""

from . import consts, config, profiles, register_mapper, register_file
from .config import ADF435xConfig
from .profiles import ADF435xDeviceProfile, ADF4350, ADF4351
from .register_mapper import ADF435xRegisterMapper
from .register_file import ADF435xRegisterFile
from .solver import (
    DividerOctaveCrossingError,
    ExactFrequencyError,
    FrequencyOutOfRangeError,
    NoSolutionError,
    SolveOptions,
    SolveResult,
    max_hz_for_rf_divider,
    output_band_hz,
    solve,
)
from .synthesizer import ADF435xSynthesizer

__all__ = [
    "consts",
    "config",
    "profiles",
    "register_mapper",
    "register_file",
    "ADF435xConfig",
    "ADF435xDeviceProfile",
    "ADF4350",
    "ADF4351",
    "ADF435xRegisterMapper",
    "ADF435xRegisterFile",
    "ADF435xSynthesizer",
    "solve",
    "SolveOptions",
    "SolveResult",
    "DividerOctaveCrossingError",
    "ExactFrequencyError",
    "FrequencyOutOfRangeError",
    "NoSolutionError",
    "output_band_hz",
    "max_hz_for_rf_divider",
]
