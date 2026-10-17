"""Driver for the ADF4350 and ADF4351 wideband PLL synthesizers.

Everything here runs on CPython and MicroPython. The SPI/GPIO driver,
``adf435x.device``, is the only module that imports ``machine``, so it is not
imported here and the package also loads on a PC. See docs/api-guide.md.
"""

from . import consts, config, profiles, register_mapper, register_file
from .config import ADF435xConfig
from .profiles import ADF435xDeviceProfile, ADF4350, ADF4351
from .register_mapper import ADF435xRegisterMapper
from .register_file import ADF435xRegisterFile
from .solver import (
    ExactFrequencyError,
    FrequencyOutOfRangeError,
    NoSolutionError,
    SolveOptions,
    SolveResult,
    max_hz_for_rf_divider,
    output_band_hz,
    solve,
)
from .sweep import DividerOctaveCrossingError, FrequencyEntry, FrequencyTable
from .synthesizer import ADF435xSynthesizer, LockTimeoutError

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
    "FrequencyTable",
    "FrequencyEntry",
    "LockTimeoutError",
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
