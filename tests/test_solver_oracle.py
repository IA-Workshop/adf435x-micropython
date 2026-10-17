"""The live solver is never less accurate than the frozen v0.1.0 solver.

Accuracy is the exact |target - output| computed with Fractions from the
returned fields and the *true* (untruncated) PFD frequency, so both solvers
are judged against the hardware, not against their own rounding. It is
compared at the API's resolution, whole hertz (rounded half up): within the
same rounded error both solvers prefer the smaller MOD, so the live solver
may trade a sub-hertz difference for a much smaller MOD, but never a whole
hertz.

Acceptance check for remediation step A4 (solver rewrite). Delete together
with ``reference_solver.py`` once A4's own tests cover accuracy.
"""

import math
import random
from fractions import Fraction

import pytest

import reference_solver as reference
from adf435x import solver
from adf435x.profiles import ADF4350, ADF4351

# (ref_hz, r_counter, doubler, rdiv2): integer and non-integer fPFD paths.
_REF_PATHS = (
    (10_000_000, 1, False, False),
    (25_000_000, 1, False, False),
    (25_000_000, 3, False, False),
    (12_000_000, 1, True, False),
    (122_880_000, 5, False, True),
    (100_000_000, 7, False, False),
)
_PROFILES = (ADF4350, ADF4351)


def _cases(count=120, seed=20261015):
    """Deterministic (profile, target_hz, ref path) samples."""
    rng = random.Random(seed)
    cases = []
    for i in range(count):
        profile = _PROFILES[i % len(_PROFILES)]
        low = 35_000_000 if profile is ADF4351 else 138_000_000
        target = rng.randint(low, 4_400_000_000)
        cases.append((profile, target) + _REF_PATHS[rng.randrange(len(_REF_PATHS))])
    return cases


def _rounded_error(result, target, ref_hz, r_counter, doubler, rdiv2):
    """Exact |target - output| rounded half up to whole hertz."""
    f = result.fields
    f_pfd = Fraction(ref_hz * (2 if doubler else 1), r_counter * (2 if rdiv2 else 1))
    output = (f["int_n"] + Fraction(f["frac"], f["mod"])) * f_pfd / f["rf_divider"]
    return math.floor(abs(target - output) + Fraction(1, 2))


@pytest.mark.parametrize(
    "profile, target, ref_hz, r_counter, doubler, rdiv2",
    _cases(),
    ids=lambda v: getattr(v, "name", None),
)
def test_not_less_accurate_than_reference(
    profile, target, ref_hz, r_counter, doubler, rdiv2
):
    """Live solver rounded error <= frozen v0.1.0 solver rounded error."""
    args = dict(r_counter=r_counter, doubler=doubler, rdiv2=rdiv2)
    try:
        ref = reference.solve(
            target, ref_hz, profile, options=reference.SolveOptions(**args)
        )
    except ValueError:
        pytest.skip("reference solver has no solution")
    live = solver.solve(target, ref_hz, profile, options=solver.SolveOptions(**args))
    path = (ref_hz, r_counter, doubler, rdiv2)
    assert _rounded_error(live, target, *path) <= _rounded_error(ref, target, *path)
