"""Checks on the human documentation (README, CONTRIBUTING, docs/)."""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HUMAN_DOCS = sorted(
    [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "CHANGELOG.md"]
    + list((ROOT / "docs").rglob("*.md"))
)
# Agent docs may link anywhere, but their links must resolve too. The journal
# is append-only history and may cite files that no longer exist.
AGENT_DOCS = sorted(
    [ROOT / "AGENTS.md", ROOT / "CLAUDE.md"]
    + [p for p in (ROOT / ".agents").glob("*.md") if p.name != "journal.md"]
    + list((ROOT / ".claude").rglob("*.md"))
    + list((ROOT / ".cursor").rglob("*.md"))
    + list((ROOT / ".cursor").rglob("*.mdc"))
)
# Generated or nested checkouts, not project docs.
_SKIP_DIRS = {".git", "node_modules", ".pytest_cache", "worktrees", "build-mpy"}
ALL_MARKDOWN = sorted(
    p
    for p in ROOT.rglob("*.md")
    if not _SKIP_DIRS.intersection(p.relative_to(ROOT).parts)
)
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_CODE_FENCE = re.compile(r"```.*?```", re.S)


def _ids(paths):
    return [str(p.relative_to(ROOT)) for p in paths]


def _links(path):
    """Relative link targets in *path*, ignoring code blocks."""
    text = _CODE_FENCE.sub("", path.read_text())
    return [t for t in _LINK.findall(text) if not re.match(r"[a-z]+:", t)]


def _slug(heading):
    """GitHub-style anchor for a heading."""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _anchors(path):
    text = _CODE_FENCE.sub("", path.read_text())
    return {_slug(h) for h in re.findall(r"^#+\s+(.*)$", text, re.M)}


@pytest.mark.parametrize(
    "doc", HUMAN_DOCS + AGENT_DOCS, ids=_ids(HUMAN_DOCS + AGENT_DOCS)
)
def test_relative_links_resolve(doc):
    """Every relative link points at an existing file (and heading)."""
    broken = []
    for target in _links(doc):
        file_part, _, anchor = target.partition("#")
        dest = (doc.parent / file_part).resolve() if file_part else doc
        if not dest.exists():
            broken.append(target)
        elif anchor and dest.suffix == ".md" and anchor not in _anchors(dest):
            broken.append(target)
    assert broken == []


@pytest.mark.parametrize("doc", HUMAN_DOCS, ids=_ids(HUMAN_DOCS))
def test_human_docs_do_not_link_agent_docs(doc):
    """Human docs never point at agent-only material."""
    agent = [
        t
        for t in _links(doc)
        if re.search(r"(^|/)(\.agents/|AGENTS\.md|CLAUDE\.md)", t)
    ]
    assert agent == []


@pytest.mark.parametrize("doc", ALL_MARKDOWN, ids=_ids(ALL_MARKDOWN))
def test_no_register_words_in_markdown(doc):
    """32-bit register words live only in tests/conftest.py (WORKED_WORDS)."""
    assert re.findall(r"0x[0-9A-Fa-f]{8}\b", doc.read_text()) == []


def _python_blocks(path):
    return re.findall(r"```python\n(.*?)```", path.read_text(), re.S)


@pytest.mark.parametrize("doc", ["README.md", "docs/quickstart.md"])
def test_quickstart_code_runs(doc, mock_machine, monkeypatch):
    """The quickstart code runs as written (fake machine, MUXOUT high)."""
    real_pin = mock_machine.Pin

    def pin(number, mode=None, value=0):
        # MUXOUT input reads locked.
        return real_pin(number, mode, 1 if mode == real_pin.IN else value)

    pin.OUT, pin.IN = real_pin.OUT, real_pin.IN
    monkeypatch.setattr(mock_machine, "Pin", pin)
    monkeypatch.setattr("adf435x.synthesizer._sleep_us", lambda us: None)
    namespace = {}
    blocks = [b for b in _python_blocks(ROOT / doc) if "mip" not in b]
    for block in blocks:
        exec(compile(block, doc, "exec"), namespace)
    assert namespace["synth"].achieved_hz in (200_000_000, 433_920_000)
