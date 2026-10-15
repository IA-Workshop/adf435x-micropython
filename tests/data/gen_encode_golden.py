"""Generate ``encode_golden.json``: frozen v0.1.0 encoder output (oracle).

Run from the repository root::

    python tests/data/gen_encode_golden.py

The file is generated once from the current encoder and committed, so the
register-layer rewrite (remediation step A2) can prove it emits identical
words. Configurations are restricted to those that stay valid under the
stricter A2 rules too (on/off fields 0/1, phase < MOD, low-spur MOD >= 50,
no N-divider on MUXOUT, fast band select divider <= 254), so a correct A2
never has to drop a case. Delete this script and the JSON once A2 lands.
"""

import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from adf435x import consts  # noqa: E402
from adf435x.config import (  # noqa: E402
    FIELD_ENUM_VALUES,
    FIELD_NAMES,
    FIELD_WIDTH,
    ADF435xConfig,
)
from adf435x.profiles import ADF4350, ADF4351  # noqa: E402
from adf435x.register_mapper import ADF435xRegisterMapper  # noqa: E402

OUT = pathlib.Path(__file__).with_name("encode_golden.json")
DEFAULTS = {name: getattr(ADF435xConfig(), name) for name in FIELD_NAMES}
BOOL_FIELDS = tuple(n for n in FIELD_NAMES if isinstance(DEFAULTS[n], bool))


def _width_samples(name, rng=None):
    """Representative values for a width-limited field."""
    top = (1 << FIELD_WIDTH[name]) - 1
    values = [0, 1, 2, top // 2, top]
    if rng is not None:
        values.append(rng.randint(0, top))
    return values


def _candidates(name, profile, rng=None):
    """Candidate values for one field (validity is filtered later)."""
    if name in BOOL_FIELDS:
        return [False, True]
    if name in FIELD_ENUM_VALUES:
        return list(FIELD_ENUM_VALUES[name])
    if name == "rf_divider":
        return list(profile.legal_rf_dividers())
    return _width_samples(name, rng)


def _future_valid(cfg):
    """Rules the A2 rewrite adds; keep only cases valid under them too."""
    if cfg.phase >= cfg.mod:
        return False
    if cfg.noise_mode == consts.REG2_LOW_SPUR and cfg.mod < 50:
        return False
    if cfg.muxout == consts.REG2_MUX_NDIVIDER:
        return False
    if cfg.band_clk_mode == consts.REG3_BAND_CLK_HIGH and cfg.band_clk_div > 254:
        return False
    return True


def _encode(mapper, overrides):
    """Return words for *overrides*, or None if invalid now or after A2."""
    cfg = ADF435xConfig(**overrides)
    try:
        mapper.validate_config(cfg)
    except ValueError:
        return None
    if not _future_valid(cfg):
        return None
    return [mapper.encode_register(i, cfg) for i in range(consts.NUM_REGISTERS)]


def _pll_overrides(profile, rng):
    """A random valid INT/FRAC/MOD/prescaler combination."""
    prescaler = rng.choice(consts.REG1_PRESCALER_VALUES)
    if prescaler == consts.REG1_PRESCALER_4_5:
        int_min = profile.int_min_4_5
    else:
        int_min = profile.int_min_8_9
    mod = rng.randint(profile.mod_min, profile.mod_max)
    return {
        "prescaler": prescaler,
        "int_n": rng.randint(int_min, profile.int_max),
        "mod": mod,
        "frac": rng.randint(0, mod - 1),
        "phase": rng.randint(0, mod - 1),
    }


def generate(random_per_profile=150, seed=20261015):
    """Build the case list."""
    rng = random.Random(seed)
    cases = []
    for profile in (ADF4350, ADF4351):
        mapper = ADF435xRegisterMapper(profile)
        seen = set()

        def add(overrides):
            key = tuple(sorted(overrides.items()))
            if key in seen:
                return
            words = _encode(mapper, overrides)
            if words is not None:
                seen.add(key)
                changed = {
                    k: v for k, v in overrides.items() if v != DEFAULTS[k]
                }
                cases.append(
                    {"profile": profile.name, "fields": changed, "words": words}
                )

        add({})
        # One field at a time; PLL fields get a roomy MOD so FRAC/phase fit.
        for name in FIELD_NAMES:
            for value in _candidates(name, profile):
                if name in ("frac", "phase"):
                    add({"mod": 4095, name: value})
                elif name == "int_n":
                    add({name: max(value, profile.int_min_8_9)})
                else:
                    add({name: value})
        # Random combinations of every field.
        attempts = 0
        target = len(cases) + random_per_profile
        while len(cases) < target and attempts < 50 * random_per_profile:
            attempts += 1
            overrides = {
                name: rng.choice(_candidates(name, profile, rng))
                for name in FIELD_NAMES
            }
            overrides.update(_pll_overrides(profile, rng))
            add(overrides)
    return cases


def main():
    """Write the oracle file."""
    payload = {
        "about": "Frozen v0.1.0 encoder output; see gen_encode_golden.py.",
        "defaults": DEFAULTS,
        "cases": generate(),
    }
    # One case per line keeps the file small and its diffs readable.
    lines = ",\n  ".join(json.dumps(c, sort_keys=True) for c in payload["cases"])
    OUT.write_text(
        '{"about": %s,\n "defaults": %s,\n "cases": [\n  %s\n]}\n'
        % (
            json.dumps(payload["about"]),
            json.dumps(payload["defaults"], sort_keys=True),
            lines,
        )
    )
    print("wrote %d cases to %s" % (len(payload["cases"]), OUT))


if __name__ == "__main__":
    main()
