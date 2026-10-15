"""The encoder reproduces the frozen v0.1.0 output in ``data/encode_golden.json``.

The 501 configurations were generated from the v0.1.0 encoder (generator in
git history, commit ecf5a78) and kept frozen as the acceptance check for the
register-layer rewrite (remediation step A2), which reproduces them exactly.
It stays as an encoder regression net until the remaining remediation steps
land; never regenerate it from the current encoder.
"""

import json
import pathlib

import pytest

from adf435x import consts
from adf435x.config import FIELD_NAMES, ADF435xConfig
from adf435x.profiles import ADF4350, ADF4351
from adf435x.register_mapper import ADF435xRegisterMapper

_GOLDEN = json.loads(
    (pathlib.Path(__file__).parent / "data" / "encode_golden.json").read_text()
)
_PROFILES = {p.name: p for p in (ADF4350, ADF4351)}


def test_defaults_unchanged():
    """Config defaults match those the oracle was generated with."""
    defaults = {name: getattr(ADF435xConfig(), name) for name in FIELD_NAMES}
    assert defaults == _GOLDEN["defaults"]


@pytest.mark.parametrize(
    "case",
    _GOLDEN["cases"],
    ids=["%s-%d" % (c["profile"], i) for i, c in enumerate(_GOLDEN["cases"])],
)
def test_encode_matches_golden(case):
    """Encoding the case's fields yields the frozen R0..R5 words."""
    mapper = ADF435xRegisterMapper(_PROFILES[case["profile"]])
    cfg = ADF435xConfig(**case["fields"])
    words = [mapper.encode_register(i, cfg) for i in range(consts.NUM_REGISTERS)]
    assert words == case["words"]
