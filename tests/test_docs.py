"""Checks on the Markdown docs and the agent tool files."""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HUMAN_DOCS = sorted(
    [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "CHANGELOG.md"]
    + list((ROOT / "docs").rglob("*.md"))
)
# Generated or nested checkouts, not project docs. .claude/ holds only
# symlinks into .agents/, so scanning it would count those files twice.
_SKIP_DIRS = {".git", "node_modules", ".pytest_cache", "build-mpy", ".claude"}


def _project(paths):
    return sorted(
        p for p in paths if not _SKIP_DIRS.intersection(p.relative_to(ROOT).parts)
    )


# Agent docs may link anywhere, but their links must resolve too. The journal
# is append-only history and may cite files that no longer exist.
AGENT_DOCS = _project(
    [ROOT / "AGENTS.md", ROOT / "CLAUDE.md"]
    + [p for p in (ROOT / ".agents").rglob("*.md") if p.name != "journal.md"]
    + list((ROOT / ".cursor").rglob("*.mdc"))
)
ALL_MARKDOWN = _project(ROOT.rglob("*.md"))
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


# Agent tool files. Content lives in .agents/; .claude/ holds symlinks to it
# and .cursor/ holds pointer files with the same globs.

AGENTS = ROOT / ".agents"
AREA_RULES = sorted((AGENTS / "rules").glob("*.md"))
SKILLS = sorted((AGENTS / "skills").glob("*/SKILL.md"))


def _frontmatter(path):
    """Return the lines between the leading ``---`` markers."""
    lines = path.read_text().splitlines()
    assert lines[0] == "---", path
    return lines[1 : lines.index("---", 1)]


def _rule_paths(path):
    return {
        line.strip()[2:].strip('"')
        for line in _frontmatter(path)
        if line.strip().startswith("- ")
    }


def _cursor_globs(path):
    for line in _frontmatter(path):
        if line.startswith("globs:"):
            return {g.strip() for g in line[len("globs:") :].split(",")}
    return set()


class TestToolFiles:
    @pytest.mark.parametrize("rule", AREA_RULES, ids=_ids(AREA_RULES))
    def test_rule_has_paths(self, rule):
        assert _rule_paths(rule)

    def test_claude_rules_link_to_agents(self):
        link = ROOT / ".claude" / "rules"
        assert link.is_symlink() and link.resolve() == AGENTS / "rules"

    @pytest.mark.parametrize("rule", AREA_RULES, ids=_ids(AREA_RULES))
    def test_cursor_pointer_matches_rule(self, rule):
        cursor = ROOT / ".cursor" / "rules" / (rule.stem + ".mdc")
        assert _cursor_globs(cursor) == _rule_paths(rule)

    def test_no_orphan_cursor_rules(self):
        cursor = {p.stem for p in (ROOT / ".cursor" / "rules").glob("*.mdc")}
        assert cursor == {p.stem for p in AREA_RULES}

    @pytest.mark.parametrize("skill", SKILLS, ids=_ids(SKILLS))
    def test_skill_name_matches_directory(self, skill):
        assert "name: " + skill.parent.name in _frontmatter(skill)

    @pytest.mark.parametrize("skill", SKILLS, ids=_ids(SKILLS))
    def test_skill_uses_portable_keys(self, skill):
        allowed = {"name", "description", "disable-model-invocation"}
        keys = {
            line.split(":")[0]
            for line in _frontmatter(skill)
            if line and not line.startswith(" ")
        }
        assert keys <= allowed

    def test_claude_skills_link_to_agents(self):
        links = {p.name: p.resolve() for p in (ROOT / ".claude" / "skills").iterdir()}
        assert links == {s.parent.name: s.parent for s in SKILLS}

    def test_claude_dir_holds_only_links(self):
        # Local files (settings.local.json, worktrees/) are gitignored.
        allowed = {"rules", "skills", "settings.json", "settings.local.json"}
        extra = {
            p.name
            for p in (ROOT / ".claude").iterdir()
            if p.name not in allowed and p.name != "worktrees"
        }
        assert extra == set()

    @pytest.mark.parametrize("doc", AREA_RULES + SKILLS, ids=_ids(AREA_RULES + SKILLS))
    def test_no_relative_links_in_linked_files(self, doc):
        """These files are read through symlinks too, so relative links break."""
        assert _links(doc) == []
