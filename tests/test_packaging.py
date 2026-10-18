"""Packaging metadata: pyproject.toml and the mip package.json agree."""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE_JSON = json.loads((ROOT / "package.json").read_text())


def _pyproject_version():
    # tomllib is 3.11+; the project supports 3.10.
    text = (ROOT / "pyproject.toml").read_text()
    return re.search(r'^version = "([^"]+)"$', text, re.M).group(1)


class TestVersion:
    def test_pyproject_and_package_json_agree(self):
        assert PACKAGE_JSON["version"] == _pyproject_version()

    def test_is_pep440_release_or_dev(self):
        assert re.fullmatch(r"\d+\.\d+\.\d+(\.dev\d+)?", _pyproject_version())


class TestMipManifest:
    def test_lists_every_library_module(self):
        listed = {dest for dest, _src in PACKAGE_JSON["urls"]}
        modules = {
            p.relative_to(ROOT).as_posix() for p in (ROOT / "adf435x").glob("*.py")
        }
        assert listed == modules

    def test_sources_match_destinations(self):
        assert all(dest == src for dest, src in PACKAGE_JSON["urls"])
