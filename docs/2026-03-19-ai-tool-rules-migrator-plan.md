# AI Tool Rules Migrator — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that syncs AI coding rules between Claude Code, Cursor, and VS Code Copilot via a canonical universal store.

**Architecture:** Parser-per-tool design with a shared data model. Each tool has a parser (read native format) and converter (write native format). A sync layer orchestrates pull/push/promote using a JSON state file for change detection. CLI built with typer.

**Tech Stack:** Python 3.12+, uv, typer, ruamel.yaml, pytest

**Spec:** `docs/2026-03-19-ai-tool-rules-migrator-design.md`

---

## Chunk 0: Repository Setup

### Task 0: Initialize git repo and directory structure

- [ ] **Step 1: Initialize git and create directories**

```bash
cd C:\Users\qli\Workspace\junk-yard\my-AI-workflows\ai-tool-rules-migrator
git init
mkdir -p universal-rules
touch universal-rules/.gitkeep
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
.ai-rules-state.json
universal-rules/inventory.md
```

- [ ] **Step 3: Initial commit**

```bash
git add .
git commit -m "init: empty repo with directory structure"
```

---

## Chunk 1: Project Scaffolding & Data Models

### Task 1: Initialize Python project with uv

**Files:**
- Create: `pyproject.toml`
- Create: `src/ai_rules/__init__.py`

- [ ] **Step 1: Initialize project with uv**

```bash
cd C:\Users\qli\Workspace\junk-yard\my-AI-workflows\ai-tool-rules-migrator
uv init --lib --name ai-rules
```

- [ ] **Step 2: Edit pyproject.toml with dependencies**

```toml
[project]
name = "ai-rules"
version = "0.1.0"
description = "Sync AI coding tool rules across Claude Code, Cursor, and VS Code Copilot"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15",
    "ruamel.yaml>=0.18",
    "rich>=13",
]

[project.scripts]
ai-rules = "ai_rules.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = ["pytest>=8"]
```

- [ ] **Step 3: Install dependencies**

```bash
uv sync
```

- [ ] **Step 4: Verify installation**

```bash
uv run ai-rules --help
```

Expected: typer shows help (will fail until cli.py exists — that's fine, just verify uv resolves deps).

---

### Task 2: Data models

**Files:**
- Create: `src/ai_rules/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write tests for data models**

```python
# tests/test_models.py
from ai_rules.models import Rule, RuleGroup, DiscoveredRule, InventoryItem


def test_rule_creation():
    rule = Rule(name="Use snake_case", content="All Python files use snake_case.")
    assert rule.name == "Use snake_case"
    assert rule.content == "All Python files use snake_case."


def test_rule_group_creation():
    rules = [
        Rule(name="snake_case", content="Use snake_case for files."),
        Rule(name="type hints", content="Include type hints."),
    ]
    group = RuleGroup(name="python", rules=rules, metadata={})
    assert group.name == "python"
    assert len(group.rules) == 2


def test_rule_group_normalized_name():
    group = RuleGroup(name="  Python  ", rules=[], metadata={})
    assert group.normalized_name == "python"


def test_discovered_rule_creation():
    group = RuleGroup(name="python", rules=[], metadata={})
    discovered = DiscoveredRule(
        rule_group=group,
        source_tool="cursor",
        source_path=".cursor/rules/python.mdc",
        content_hash="sha256:abc123",
    )
    assert discovered.source_tool == "cursor"
    assert discovered.content_hash == "sha256:abc123"


def test_inventory_item_creation():
    item = InventoryItem(
        tool="claude-code",
        category="mcp_server",
        name="filesystem",
        path="/some/path",
    )
    assert item.tool == "claude-code"
    assert item.category == "mcp_server"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_rules.models'`

- [ ] **Step 3: Implement data models**

```python
# src/ai_rules/models.py
"""Data models for AI Tool Rules Migrator."""

from dataclasses import dataclass, field


@dataclass
class Rule:
    """A single rule — one ## section within a rule group."""

    name: str
    content: str


@dataclass
class RuleGroup:
    """A group of related rules — one topic file or one .mdc file."""

    name: str
    rules: list[Rule]
    metadata: dict = field(default_factory=dict)

    @property
    def normalized_name(self) -> str:
        """Lowercase, stripped name used for matching across tools."""
        return self.name.strip().lower()


@dataclass
class DiscoveredRule:
    """Transient object used during pull — includes provenance."""

    rule_group: RuleGroup
    source_tool: str
    source_path: str
    content_hash: str


@dataclass
class InventoryItem:
    """A non-universal asset (MCP server, plugin, skill)."""

    tool: str
    category: str
    name: str
    path: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_models.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/test_models.py uv.lock
git commit -m "scaffold project and add data models"
```

---

### Task 3: Configuration loading

**Files:**
- Create: `src/ai_rules/config.py`
- Create: `tests/test_config.py`
- Create: `tests/fixtures/sample_config.yaml`

- [ ] **Step 1: Create sample config fixture**

```yaml
# tests/fixtures/sample_config.yaml
workspace: /tmp/test-workspace
canonical_store: ./universal-rules

tools:
  claude-code:
    rule_patterns: ["CLAUDE.md"]
  cursor:
    rule_patterns: [".cursor/rules/*.mdc"]
  copilot:
    rule_patterns: [".github/copilot-instructions.md"]

repos:
  - path: repo-a
    tools: [claude-code, cursor]
  - path: repo-b
    tools: [claude-code, copilot]
```

- [ ] **Step 2: Write tests for config loading**

```python
# tests/test_config.py
from pathlib import Path

import pytest

from ai_rules.config import Config, load_config


FIXTURES = Path(__file__).parent / "fixtures"


def test_load_config():
    config = load_config(FIXTURES / "sample_config.yaml")
    assert config.workspace == Path("/tmp/test-workspace")
    assert "claude-code" in config.tools
    assert len(config.repos) == 2


def test_load_config_tool_patterns():
    config = load_config(FIXTURES / "sample_config.yaml")
    assert config.tools["cursor"].rule_patterns == [".cursor/rules/*.mdc"]


def test_load_config_repo_tools():
    config = load_config(FIXTURES / "sample_config.yaml")
    repo_a = config.repos[0]
    assert repo_a.path == "repo-a"
    assert "claude-code" in repo_a.tools
    assert "cursor" in repo_a.tools


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))


def test_load_config_canonical_store_resolved():
    config = load_config(FIXTURES / "sample_config.yaml")
    # canonical_store is resolved relative to config file location
    assert config.canonical_store.is_absolute()
    assert config.canonical_store.name == "universal-rules"


def test_load_config_invalid_tool_reference():
    """Repos referencing non-existent tools should raise ValueError."""
    import tempfile
    from ruamel.yaml import YAML
    yaml = YAML()
    bad_config = {
        "workspace": "/tmp",
        "tools": {"claude-code": {"rule_patterns": ["CLAUDE.md"]}},
        "repos": [{"path": "repo", "tools": ["nonexistent"]}],
    }
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        yaml.dump(bad_config, f)
        f.flush()
        with pytest.raises(ValueError, match="unknown tool"):
            load_config(Path(f.name))
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement config loading**

```python
# src/ai_rules/config.py
"""Configuration loading and validation."""

from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML


@dataclass
class ToolConfig:
    """Configuration for a single AI tool."""

    name: str
    rule_patterns: list[str]


@dataclass
class RepoConfig:
    """Configuration for a single repository."""

    path: str
    tools: list[str]


@dataclass
class Config:
    """Top-level configuration."""

    workspace: Path
    canonical_store: Path
    tools: dict[str, ToolConfig] = field(default_factory=dict)
    repos: list[RepoConfig] = field(default_factory=list)


def load_config(path: Path) -> Config:
    """Load and validate config from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    yaml = YAML()
    with open(path) as f:
        data = yaml.load(f)

    config_dir = path.parent

    tools = {}
    for name, tool_data in data.get("tools", {}).items():
        tools[name] = ToolConfig(
            name=name,
            rule_patterns=tool_data.get("rule_patterns", []),
        )

    repos = []
    for repo_data in data.get("repos", []):
        repo_tools = repo_data.get("tools", [])
        # Validate that referenced tools exist
        for t in repo_tools:
            if t not in tools:
                raise ValueError(
                    f"Repo '{repo_data['path']}' references unknown tool '{t}'. "
                    f"Available tools: {', '.join(tools.keys())}"
                )
        repos.append(RepoConfig(path=repo_data["path"], tools=repo_tools))

    # Resolve canonical_store relative to config file location
    raw_store = data.get("canonical_store", "./universal-rules")
    canonical_store = (config_dir / raw_store).resolve()

    return Config(
        workspace=Path(data["workspace"]),
        canonical_store=canonical_store,
        tools=tools,
        repos=repos,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_rules/config.py tests/test_config.py tests/fixtures/
git commit -m "add configuration loading"
```

---

## Chunk 2: Parsers

### Task 4: Base parser interface and shared utilities

**Files:**
- Create: `src/ai_rules/parsers/__init__.py`
- Create: `src/ai_rules/parsers/base.py`
- Create: `src/ai_rules/parsers/markdown_utils.py`
- Create: `tests/test_parsers/__init__.py`
- Create: `tests/test_parsers/test_markdown_utils.py`

- [ ] **Step 1: Write tests for shared markdown utilities**

```python
# tests/test_parsers/test_markdown_utils.py
from ai_rules.parsers.markdown_utils import split_sections, read_file_text, inject_marked_block

MARKER_START = "<!-- ai-rules:start -->"
MARKER_END = "<!-- ai-rules:end -->"


def test_split_sections_basic():
    text = "## Python\n\nUse snake_case.\n\n## Git\n\nCommit often.\n"
    rules = split_sections(text)
    assert len(rules) == 2
    assert rules[0].name == "Python"
    assert "snake_case" in rules[0].content


def test_split_sections_ignores_preamble():
    text = "# Title\n\nSome intro.\n\n## Rule\n\nContent.\n"
    rules = split_sections(text)
    assert len(rules) == 1
    assert rules[0].name == "Rule"


def test_split_sections_empty():
    rules = split_sections("")
    assert rules == []


def test_read_file_text_handles_bom(tmp_path):
    f = tmp_path / "test.md"
    f.write_bytes(b"\xef\xbb\xbf## Rule\n\nContent.\n")
    text = read_file_text(f)
    assert text.startswith("## Rule")


def test_read_file_text_normalizes_crlf(tmp_path):
    f = tmp_path / "test.md"
    f.write_bytes(b"## Rule\r\n\r\nContent.\r\n")
    text = read_file_text(f)
    assert "\r" not in text


def test_inject_marked_block_new_file():
    result = inject_marked_block(None, "generated content")
    assert MARKER_START in result
    assert "generated content" in result
    assert MARKER_END in result


def test_inject_marked_block_append():
    existing = "# My Project\n\nHand-written.\n"
    result = inject_marked_block(existing, "generated")
    assert "Hand-written." in result
    assert MARKER_START in result


def test_inject_marked_block_replace():
    existing = (
        "# My Project\n\n"
        f"{MARKER_START}\nold stuff\n{MARKER_END}\n\n"
        "More content.\n"
    )
    result = inject_marked_block(existing, "new stuff")
    assert "old stuff" not in result
    assert "new stuff" in result
    assert "More content." in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_parsers/test_markdown_utils.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement shared utilities**

```python
# src/ai_rules/parsers/__init__.py
"""Tool-specific rule parsers."""

# src/ai_rules/parsers/markdown_utils.py
"""Shared markdown parsing and file I/O utilities."""

import re
from pathlib import Path

from ai_rules.models import Rule

MARKER_START = "<!-- ai-rules:start -->"
MARKER_END = "<!-- ai-rules:end -->"


def read_file_text(path: Path) -> str:
    """Read a text file, handling BOM and normalizing line endings."""
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_sections(text: str) -> list[Rule]:
    """Split markdown text by ## headings into Rule objects."""
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    rules = []
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        rules.append(Rule(name=name, content=content))
    return rules


def inject_marked_block(existing: str | None, generated: str) -> str:
    """Inject generated content between ai-rules markers.

    If existing is None, creates a new file with just markers.
    If markers exist, replaces content between them.
    If no markers, appends them.
    """
    marked_block = f"{MARKER_START}\n{generated}\n{MARKER_END}\n"

    if existing is None:
        return marked_block

    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END) + r"\n?",
        re.DOTALL,
    )
    if pattern.search(existing):
        return pattern.sub(marked_block, existing)
    else:
        return existing.rstrip("\n") + "\n\n" + marked_block


# src/ai_rules/parsers/base.py
"""Abstract base class for tool parsers."""

from abc import ABC, abstractmethod
from pathlib import Path

from ai_rules.models import RuleGroup


class BaseParser(ABC):
    """Base class all tool parsers implement."""

    @abstractmethod
    def parse(self, path: Path) -> list[RuleGroup]:
        """Read rules from tool-native format."""
        ...

    @abstractmethod
    def convert(self, rules: list[RuleGroup]) -> dict[str, str]:
        """Convert rules to tool-native format.

        Returns a mapping of filename -> content.
        """
        ...

    @abstractmethod
    def write(self, rules: list[RuleGroup], target_path: Path) -> None:
        """Write converted rules to disk."""
        ...
```

Note: `base.py` and `markdown_utils.py` are separate files despite being shown together above.

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_parsers/test_markdown_utils.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_rules/parsers/ tests/test_parsers/
git commit -m "add base parser interface and shared markdown utilities"
```

---

### Task 5: Claude Code parser

**Files:**
- Create: `src/ai_rules/parsers/claude_code.py`
- Create: `tests/test_parsers/__init__.py`
- Create: `tests/test_parsers/test_claude_code.py`
- Create: `tests/fixtures/sample_claude.md`

- [ ] **Step 1: Create Claude Code fixture**

```markdown
# Project Conventions

## Python

- Use snake_case for file names.
- Include type hints.

## Workflow

- Break tasks into smaller pieces.
- Write tests first.

## Database

- Follow naming conventions in database.md.
```

Save as `tests/fixtures/sample_claude.md`.

- [ ] **Step 2: Write tests for Claude Code parser**

```python
# tests/test_parsers/test_claude_code.py
from pathlib import Path

from ai_rules.parsers.claude_code import ClaudeCodeParser
from ai_rules.models import Rule, RuleGroup

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_claude_md():
    parser = ClaudeCodeParser()
    groups = parser.parse(FIXTURES / "sample_claude.md")
    assert len(groups) == 1  # one file = one group
    group = groups[0]
    assert len(group.rules) == 3
    assert group.rules[0].name == "Python"
    assert "snake_case" in group.rules[0].content


def test_parse_claude_md_rule_names():
    parser = ClaudeCodeParser()
    groups = parser.parse(FIXTURES / "sample_claude.md")
    names = [r.name for r in groups[0].rules]
    assert names == ["Python", "Workflow", "Database"]


def test_convert_single_group():
    parser = ClaudeCodeParser()
    rules = [
        Rule(name="Python", content="- Use snake_case.\n- Include type hints."),
        Rule(name="Git", content="- Commit often."),
    ]
    group = RuleGroup(name="conventions", rules=rules, metadata={})
    result = parser.convert([group])
    assert len(result) == 1
    filename, content = next(iter(result.items()))
    assert "## Python" in content
    assert "## Git" in content
    assert "snake_case" in content


def test_write_with_markers(tmp_path):
    parser = ClaudeCodeParser()
    existing = "# My Project\n\nHand-written content.\n"
    target = tmp_path / "CLAUDE.md"
    target.write_text(existing)

    rules = [Rule(name="Python", content="- Use snake_case.")]
    group = RuleGroup(name="universal", rules=rules, metadata={})
    parser.write([group], target)

    result = target.read_text()
    assert "Hand-written content." in result
    assert "<!-- ai-rules:start -->" in result
    assert "## Python" in result
    assert "<!-- ai-rules:end -->" in result


def test_write_creates_new_file(tmp_path):
    parser = ClaudeCodeParser()
    target = tmp_path / "CLAUDE.md"

    rules = [Rule(name="Python", content="- Use snake_case.")]
    group = RuleGroup(name="universal", rules=rules, metadata={})
    parser.write([group], target)

    result = target.read_text()
    assert "<!-- ai-rules:start -->" in result
    assert "## Python" in result


def test_write_replaces_existing_markers(tmp_path):
    parser = ClaudeCodeParser()
    existing = (
        "# My Project\n\n"
        "<!-- ai-rules:start -->\n## Old Rule\n\n- Old content.\n<!-- ai-rules:end -->\n\n"
        "More hand-written content.\n"
    )
    target = tmp_path / "CLAUDE.md"
    target.write_text(existing)

    rules = [Rule(name="New Rule", content="- New content.")]
    group = RuleGroup(name="universal", rules=rules, metadata={})
    parser.write([group], target)

    result = target.read_text()
    assert "Old Rule" not in result
    assert "New Rule" in result
    assert "More hand-written content." in result
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_parsers/test_claude_code.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement Claude Code parser**

```python
# src/ai_rules/parsers/claude_code.py
"""Parser for Claude Code CLAUDE.md files."""

from pathlib import Path

from ai_rules.models import RuleGroup
from ai_rules.parsers.base import BaseParser
from ai_rules.parsers.markdown_utils import read_file_text, split_sections, inject_marked_block


class ClaudeCodeParser(BaseParser):
    """Parse and convert Claude Code CLAUDE.md files."""

    def parse(self, path: Path) -> list[RuleGroup]:
        """Parse CLAUDE.md into a single RuleGroup with rules per ## section."""
        text = read_file_text(path)
        rules = split_sections(text)
        group_name = path.stem.lower()
        return [RuleGroup(name=group_name, rules=rules, metadata={})]

    def convert(self, rules: list[RuleGroup]) -> dict[str, str]:
        """Convert rule groups to CLAUDE.md content."""
        sections = []
        for group in rules:
            for rule in group.rules:
                sections.append(f"## {rule.name}\n\n{rule.content}")
        content = "\n\n".join(sections) + "\n"
        return {"CLAUDE.md": content}

    def write(self, rules: list[RuleGroup], target_path: Path) -> None:
        """Write rules within ai-rules markers."""
        converted = self.convert(rules)
        generated = next(iter(converted.values()))
        existing = read_file_text(target_path) if target_path.exists() else None
        new_content = inject_marked_block(existing, generated)
        target_path.write_text(new_content, encoding="utf-8")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_parsers/test_claude_code.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_rules/parsers/claude_code.py tests/test_parsers/ tests/fixtures/sample_claude.md
git commit -m "add Claude Code parser"
```

---

### Task 6: Cursor parser

**Files:**
- Create: `src/ai_rules/parsers/cursor.py`
- Create: `tests/test_parsers/test_cursor.py`
- Create: `tests/fixtures/cursor_rules/backend-rules.mdc`
- Create: `tests/fixtures/cursor_rules/database-conventions.mdc`

- [ ] **Step 1: Create Cursor fixture files**

```markdown
---
description: Backend coding conventions
globs: "**/*.cs"
alwaysApply: false
---

# Backend Rules

- Use dependency injection.
- Follow repository pattern.
```

Save as `tests/fixtures/cursor_rules/backend-rules.mdc`.

```markdown
---
description: Database naming conventions
alwaysApply: true
---

# Database Conventions

- Use PascalCase for table names.
- Prefix stored procedures with usp_.
```

Save as `tests/fixtures/cursor_rules/database-conventions.mdc`.

- [ ] **Step 2: Write tests for Cursor parser**

```python
# tests/test_parsers/test_cursor.py
from pathlib import Path

from ai_rules.parsers.cursor import CursorParser
from ai_rules.models import Rule, RuleGroup

FIXTURES = Path(__file__).parent.parent / "fixtures" / "cursor_rules"


def test_parse_single_mdc():
    parser = CursorParser()
    groups = parser.parse(FIXTURES / "backend-rules.mdc")
    assert len(groups) == 1
    group = groups[0]
    assert group.name == "backend-rules"
    assert group.metadata["description"] == "Backend coding conventions"
    assert group.metadata["globs"] == "**/*.cs"
    assert group.metadata["alwaysApply"] is False
    assert len(group.rules) >= 1


def test_parse_mdc_always_apply():
    parser = CursorParser()
    groups = parser.parse(FIXTURES / "database-conventions.mdc")
    group = groups[0]
    assert group.metadata["alwaysApply"] is True


def test_convert_to_mdc():
    parser = CursorParser()
    rules = [Rule(name="Conventions", content="- Use PascalCase.")]
    group = RuleGroup(
        name="database",
        rules=rules,
        metadata={"description": "DB rules", "alwaysApply": True},
    )
    result = parser.convert([group])
    assert "database.mdc" in result
    content = result["database.mdc"]
    assert "description: DB rules" in content
    assert "alwaysApply: true" in content
    assert "- Use PascalCase." in content


def test_convert_universal_defaults():
    """Universal rules get alwaysApply: true when no metadata."""
    parser = CursorParser()
    rules = [Rule(name="Style", content="- Be consistent.")]
    group = RuleGroup(name="style", rules=rules, metadata={})
    result = parser.convert([group])
    content = result["style.mdc"]
    assert "alwaysApply: true" in content


def test_write_universal_prefix(tmp_path):
    parser = CursorParser()
    rules = [Rule(name="Python", content="- Use snake_case.")]
    group = RuleGroup(name="python", rules=rules, metadata={})

    rules_dir = tmp_path / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    parser.write([group], rules_dir)

    written = list(rules_dir.glob("_universal-*.mdc"))
    assert len(written) == 1
    assert written[0].name == "_universal-python.mdc"


def test_write_does_not_overwrite_hand_written(tmp_path):
    rules_dir = tmp_path / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    hand_written = rules_dir / "my-custom.mdc"
    hand_written.write_text("my custom rule")

    parser = CursorParser()
    rules = [Rule(name="Python", content="- Use snake_case.")]
    group = RuleGroup(name="python", rules=rules, metadata={})
    parser.write([group], rules_dir)

    assert hand_written.read_text() == "my custom rule"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_parsers/test_cursor.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement Cursor parser**

```python
# src/ai_rules/parsers/cursor.py
"""Parser for Cursor .mdc rule files."""

import re
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from ai_rules.models import Rule, RuleGroup
from ai_rules.parsers.base import BaseParser
from ai_rules.parsers.markdown_utils import read_file_text


class CursorParser(BaseParser):
    """Parse and convert Cursor .mdc files."""

    def parse(self, path: Path) -> list[RuleGroup]:
        """Parse a single .mdc file into a RuleGroup."""
        text = read_file_text(path)
        metadata, body = _split_frontmatter(text)
        name = path.stem
        rules = _body_to_rules(body)
        return [RuleGroup(name=name, rules=rules, metadata=metadata)]

    def convert(self, rules: list[RuleGroup]) -> dict[str, str]:
        """Convert rule groups to .mdc file contents."""
        result = {}
        for group in rules:
            metadata = dict(group.metadata)
            if "alwaysApply" not in metadata:
                metadata["alwaysApply"] = True
            if "description" not in metadata:
                metadata["description"] = group.name

            frontmatter = _dump_yaml(metadata)
            body_parts = []
            for rule in group.rules:
                body_parts.append(f"# {rule.name}\n\n{rule.content}")
            body = "\n\n".join(body_parts) + "\n"

            content = f"---\n{frontmatter}---\n\n{body}"
            result[f"{group.normalized_name}.mdc"] = content
        return result

    def write(self, rules: list[RuleGroup], target_path: Path) -> None:
        """Write _universal-*.mdc files. Removes stale ones."""
        target_path.mkdir(parents=True, exist_ok=True)

        # Remove old _universal- files
        for old in target_path.glob("_universal-*.mdc"):
            old.unlink()

        converted = self.convert(rules)
        for filename, content in converted.items():
            out_path = target_path / f"_universal-{filename}"
            out_path.write_text(content, encoding="utf-8")


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from markdown body."""
    match = re.match(r"^---\n(.*?)\n---\n*(.*)", text, re.DOTALL)
    if not match:
        return {}, text

    yaml = YAML()
    metadata = yaml.load(match.group(1)) or {}
    body = match.group(2)
    return dict(metadata), body


def _body_to_rules(body: str) -> list[Rule]:
    """Split markdown body into rules by # headings."""
    parts = re.split(r"^# (.+)$", body, flags=re.MULTILINE)
    rules = []
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        rules.append(Rule(name=name, content=content))
    if not rules and body.strip():
        rules.append(Rule(name="", content=body.strip()))
    return rules


def _dump_yaml(data: dict) -> str:
    """Dump dict to YAML string."""
    yaml = YAML()
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_parsers/test_cursor.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_rules/parsers/cursor.py tests/test_parsers/test_cursor.py tests/fixtures/cursor_rules/
git commit -m "add Cursor parser"
```

---

### Task 7: VS Code Copilot parser

**Files:**
- Create: `src/ai_rules/parsers/copilot.py`
- Create: `tests/test_parsers/test_copilot.py`
- Create: `tests/fixtures/sample_copilot_instructions.md`

- [ ] **Step 1: Create Copilot fixture**

```markdown
## Python

- Use snake_case for file names.
- Include docstrings.

## Testing

- Write tests first.
- Use pytest.
```

Save as `tests/fixtures/sample_copilot_instructions.md`.

- [ ] **Step 2: Write tests for Copilot parser**

```python
# tests/test_parsers/test_copilot.py
from pathlib import Path

from ai_rules.parsers.copilot import CopilotParser
from ai_rules.models import Rule, RuleGroup

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_copilot_instructions():
    parser = CopilotParser()
    groups = parser.parse(FIXTURES / "sample_copilot_instructions.md")
    assert len(groups) == 1
    group = groups[0]
    assert len(group.rules) == 2
    assert group.rules[0].name == "Python"
    assert group.rules[1].name == "Testing"


def test_convert_to_copilot_format():
    parser = CopilotParser()
    rules = [
        Rule(name="Python", content="- Use snake_case."),
        Rule(name="Git", content="- Commit often."),
    ]
    group = RuleGroup(name="instructions", rules=rules, metadata={})
    result = parser.convert([group])
    assert len(result) == 1
    content = next(iter(result.values()))
    assert "## Python" in content
    assert "## Git" in content


def test_write_with_markers(tmp_path):
    parser = CopilotParser()
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    target = github_dir / "copilot-instructions.md"
    target.write_text("# Custom instructions\n\nDo good work.\n")

    rules = [Rule(name="Python", content="- Use snake_case.")]
    group = RuleGroup(name="universal", rules=rules, metadata={})
    parser.write([group], target)

    result = target.read_text()
    assert "Custom instructions" in result
    assert "<!-- ai-rules:start -->" in result
    assert "## Python" in result
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_parsers/test_copilot.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement Copilot parser**

```python
# src/ai_rules/parsers/copilot.py
"""Parser for VS Code Copilot instructions files."""

from pathlib import Path

from ai_rules.models import RuleGroup
from ai_rules.parsers.base import BaseParser
from ai_rules.parsers.markdown_utils import read_file_text, split_sections, inject_marked_block


class CopilotParser(BaseParser):
    """Parse and convert VS Code Copilot instruction files."""

    def parse(self, path: Path) -> list[RuleGroup]:
        """Parse copilot-instructions.md into a RuleGroup."""
        text = read_file_text(path)
        rules = split_sections(text)
        return [RuleGroup(name=path.stem, rules=rules, metadata={})]

    def convert(self, rules: list[RuleGroup]) -> dict[str, str]:
        """Convert rule groups to copilot-instructions.md content."""
        sections = []
        for group in rules:
            for rule in group.rules:
                sections.append(f"## {rule.name}\n\n{rule.content}")
        content = "\n\n".join(sections) + "\n"
        return {"copilot-instructions.md": content}

    def write(self, rules: list[RuleGroup], target_path: Path) -> None:
        """Write rules within ai-rules markers."""
        converted = self.convert(rules)
        generated = next(iter(converted.values()))
        existing = read_file_text(target_path) if target_path.exists() else None
        new_content = inject_marked_block(existing, generated)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(new_content, encoding="utf-8")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_parsers/test_copilot.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_rules/parsers/copilot.py tests/test_parsers/test_copilot.py tests/fixtures/sample_copilot_instructions.md
git commit -m "add VS Code Copilot parser"
```

---

## Chunk 3: Canonical Store & State Management

### Task 8: Canonical store read/write

**Files:**
- Create: `src/ai_rules/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: Write tests for store**

```python
# tests/test_store.py
from pathlib import Path

from ai_rules.models import Rule, RuleGroup
from ai_rules.store import read_universal_rules, write_universal_rules


def test_read_universal_rules(tmp_path):
    store = tmp_path / "universal-rules"
    store.mkdir()
    (store / "python.md").write_text("## snake_case\n\nUse snake_case.\n\n## Type hints\n\nAlways add type hints.\n")
    (store / "git.md").write_text("## Commits\n\nCommit often.\n")

    groups = read_universal_rules(store)
    assert len(groups) == 2
    names = {g.normalized_name for g in groups}
    assert names == {"python", "git"}


def test_read_universal_rules_empty(tmp_path):
    store = tmp_path / "universal-rules"
    store.mkdir()
    groups = read_universal_rules(store)
    assert groups == []


def test_write_universal_rules(tmp_path):
    store = tmp_path / "universal-rules"
    store.mkdir()

    groups = [
        RuleGroup(
            name="python",
            rules=[
                Rule(name="snake_case", content="Use snake_case."),
                Rule(name="Type hints", content="Always add type hints."),
            ],
            metadata={},
        )
    ]
    write_universal_rules(store, groups)

    assert (store / "python.md").exists()
    content = (store / "python.md").read_text()
    assert "## snake_case" in content
    assert "## Type hints" in content


def test_write_appends_to_existing_group(tmp_path):
    store = tmp_path / "universal-rules"
    store.mkdir()
    (store / "python.md").write_text("## snake_case\n\nUse snake_case.\n")

    new_rule = Rule(name="Docstrings", content="Add docstrings.")
    write_universal_rules(store, [RuleGroup(name="python", rules=[new_rule], metadata={})], append=True)

    content = (store / "python.md").read_text()
    assert "## snake_case" in content
    assert "## Docstrings" in content
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_store.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement store**

```python
# src/ai_rules/store.py
"""Read/write universal rules in the canonical store."""

from pathlib import Path

from ai_rules.models import RuleGroup
from ai_rules.parsers.markdown_utils import read_file_text, split_sections


def read_universal_rules(store_path: Path) -> list[RuleGroup]:
    """Read all universal rule files from the canonical store."""
    groups = []
    for md_file in sorted(store_path.glob("*.md")):
        text = read_file_text(md_file)
        rules = split_sections(text)
        if rules:
            groups.append(RuleGroup(name=md_file.stem, rules=rules, metadata={}))
    return groups


def write_universal_rules(
    store_path: Path,
    groups: list[RuleGroup],
    *,
    append: bool = False,
) -> None:
    """Write rule groups to the canonical store as markdown files."""
    store_path.mkdir(parents=True, exist_ok=True)
    for group in groups:
        file_path = store_path / f"{group.normalized_name}.md"
        sections = []
        if append and file_path.exists():
            existing_text = read_file_text(file_path)
            sections.append(existing_text.rstrip("\n"))
        for rule in group.rules:
            sections.append(f"## {rule.name}\n\n{rule.content}")
        content = "\n\n".join(sections) + "\n"
        file_path.write_text(content, encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_store.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_rules/store.py tests/test_store.py
git commit -m "add canonical store read/write"
```

---

### Task 9: State file management

**Files:**
- Create: `src/ai_rules/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write tests for state management**

```python
# tests/test_state.py
import json
from pathlib import Path

from ai_rules.state import State, load_state, save_state


def test_load_state_empty(tmp_path):
    state = load_state(tmp_path / ".ai-rules-state.json")
    assert state.version == 1
    assert state.rules == {}
    assert state.pushes == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / ".ai-rules-state.json"
    state = State(version=1, last_pull="2026-03-19T17:30:00Z")
    state.rules["CLAUDE.md##Python"] = {
        "content_hash": "sha256:abc123",
        "classification": "universal",
        "promoted_to": "universal-rules/python.md",
        "last_seen": "2026-03-19T17:30:00Z",
    }
    save_state(path, state)

    loaded = load_state(path)
    assert loaded.rules["CLAUDE.md##Python"]["classification"] == "universal"
    assert loaded.last_pull == "2026-03-19T17:30:00Z"


def test_record_push(tmp_path):
    path = tmp_path / ".ai-rules-state.json"
    state = State(version=1)
    state.record_push("copilot", "database-www", "sha256:xyz")
    save_state(path, state)

    loaded = load_state(path)
    assert loaded.pushes["copilot"]["database-www"]["content_hash"] == "sha256:xyz"


def test_is_changed_new_rule():
    state = State(version=1)
    assert state.is_changed("new/path.md", "sha256:new") is True


def test_is_changed_same_hash():
    state = State(version=1)
    state.rules["path.md"] = {"content_hash": "sha256:abc", "classification": "repo-specific", "last_seen": ""}
    assert state.is_changed("path.md", "sha256:abc") is False


def test_is_changed_different_hash():
    state = State(version=1)
    state.rules["path.md"] = {"content_hash": "sha256:old", "classification": "repo-specific", "last_seen": ""}
    assert state.is_changed("path.md", "sha256:new") is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_state.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement state management**

```python
# src/ai_rules/state.py
"""State file management for change detection."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class State:
    """Represents the .ai-rules-state.json file."""

    version: int = 1
    last_pull: str = ""
    rules: dict[str, dict] = field(default_factory=dict)
    pushes: dict[str, dict] = field(default_factory=dict)

    def is_changed(self, key: str, content_hash: str) -> bool:
        """Check if a rule has changed since last pull."""
        if key not in self.rules:
            return True
        return self.rules[key]["content_hash"] != content_hash

    def record_rule(
        self,
        key: str,
        content_hash: str,
        classification: str,
        promoted_to: str | None = None,
    ) -> None:
        """Record a rule in the state file."""
        entry: dict = {
            "content_hash": content_hash,
            "classification": classification,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
        if promoted_to:
            entry["promoted_to"] = promoted_to
        self.rules[key] = entry

    def record_push(self, tool: str, repo: str, content_hash: str) -> None:
        """Record a push to a tool/repo combination."""
        if tool not in self.pushes:
            self.pushes[tool] = {}
        self.pushes[tool][repo] = {
            "last_push": datetime.now(timezone.utc).isoformat(),
            "content_hash": content_hash,
        }


def load_state(path: Path) -> State:
    """Load state from JSON file, or return empty state if not found."""
    if not path.exists():
        return State()
    data = json.loads(path.read_text(encoding="utf-8"))
    return State(
        version=data.get("version", 1),
        last_pull=data.get("last_pull", ""),
        rules=data.get("rules", {}),
        pushes=data.get("pushes", {}),
    )


def save_state(path: Path, state: State) -> None:
    """Save state to JSON file."""
    data = {
        "version": state.version,
        "last_pull": state.last_pull,
        "rules": state.rules,
        "pushes": state.pushes,
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_state.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_rules/state.py tests/test_state.py
git commit -m "add state file management"
```

---

## Chunk 4: Sync Orchestration & Inventory

### Task 10: Pull logic

**Files:**
- Create: `src/ai_rules/sync.py`
- Create: `tests/test_sync.py`

- [ ] **Step 1: Write tests for pull**

```python
# tests/test_sync.py
import hashlib
from pathlib import Path

from ai_rules.config import Config, ToolConfig, RepoConfig
from ai_rules.models import Rule, RuleGroup, DiscoveredRule
from ai_rules.state import State
from ai_rules.store import write_universal_rules
from ai_rules.sync import discover_rules, push_rules, compute_content_hash


def _make_config(workspace: Path) -> Config:
    return Config(
        workspace=workspace,
        canonical_store=workspace / "universal-rules",
        tools={
            "claude-code": ToolConfig(name="claude-code", rule_patterns=["CLAUDE.md"]),
            "cursor": ToolConfig(name="cursor", rule_patterns=[".cursor/rules/*.mdc"]),
        },
        repos=[
            RepoConfig(path="repo-a", tools=["claude-code"]),
        ],
    )


def test_compute_content_hash():
    h = compute_content_hash("hello world")
    assert h.startswith("sha256:")
    assert len(h) > 10


def test_discover_rules_finds_claude_md(tmp_path):
    workspace = tmp_path
    repo = workspace / "repo-a"
    repo.mkdir()
    (repo / "CLAUDE.md").write_text("## Python\n\nUse snake_case.\n")

    config = _make_config(workspace)
    discovered = discover_rules(config)
    assert len(discovered) >= 1
    assert discovered[0].source_tool == "claude-code"
    assert "Python" in [r.name for r in discovered[0].rule_group.rules]


def test_discover_rules_finds_cursor_mdc(tmp_path):
    workspace = tmp_path
    repo = workspace / "repo-a"
    cursor_dir = repo / ".cursor" / "rules"
    cursor_dir.mkdir(parents=True)
    (cursor_dir / "python.mdc").write_text(
        "---\ndescription: Python rules\nalwaysApply: true\n---\n\n# Style\n\nUse snake_case.\n"
    )

    config = Config(
        workspace=workspace,
        canonical_store=workspace / "universal-rules",
        tools={
            "cursor": ToolConfig(name="cursor", rule_patterns=[".cursor/rules/*.mdc"]),
        },
        repos=[RepoConfig(path="repo-a", tools=["cursor"])],
    )
    discovered = discover_rules(config)
    assert len(discovered) >= 1
    assert discovered[0].source_tool == "cursor"


def test_discover_rules_skips_missing_repo(tmp_path):
    config = _make_config(tmp_path)
    # repo-a doesn't exist on disk
    discovered = discover_rules(config)
    # May find workspace-level CLAUDE.md if it exists, but no repo rules
    repo_rules = [d for d in discovered if "repo-a" in d.source_path]
    assert repo_rules == []


def test_discover_rules_includes_workspace_claude_md(tmp_path):
    workspace = tmp_path
    (workspace / "CLAUDE.md").write_text("## Global Rule\n\nApplies everywhere.\n")
    config = _make_config(workspace)
    discovered = discover_rules(config)
    workspace_rules = [d for d in discovered if d.source_path == "CLAUDE.md"]
    assert len(workspace_rules) == 1
    assert "Global Rule" in [r.name for r in workspace_rules[0].rule_group.rules]


def test_push_rules_writes_copilot_file(tmp_path):
    workspace = tmp_path / "workspace"
    repo = workspace / "repo-a"
    repo.mkdir(parents=True)

    store = tmp_path / "universal-rules"
    store.mkdir()
    (store / "python.md").write_text("## snake_case\n\nUse snake_case.\n")

    config = Config(
        workspace=workspace,
        canonical_store=store,
        tools={
            "copilot": ToolConfig(name="copilot", rule_patterns=[".github/copilot-instructions.md"]),
        },
        repos=[RepoConfig(path="repo-a", tools=["copilot"])],
    )
    state = State()
    written = push_rules(config, "copilot", state)

    assert len(written) == 1
    target = workspace / "repo-a" / ".github" / "copilot-instructions.md"
    assert target.exists()
    content = target.read_text()
    assert "snake_case" in content
    assert "copilot" in state.pushes


def test_push_rules_skips_missing_repo(tmp_path):
    config = Config(
        workspace=tmp_path,
        canonical_store=tmp_path / "universal-rules",
        tools={"copilot": ToolConfig(name="copilot", rule_patterns=[".github/copilot-instructions.md"])},
        repos=[RepoConfig(path="nonexistent", tools=["copilot"])],
    )
    state = State()
    written = push_rules(config, "copilot", state)
    assert written == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_sync.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement discover_rules, push_rules, and compute_content_hash**

```python
# src/ai_rules/sync.py
"""Pull/push/promote orchestration logic."""

import hashlib
from pathlib import Path

from ai_rules.config import Config
from ai_rules.models import DiscoveredRule, RuleGroup
from ai_rules.parsers.claude_code import ClaudeCodeParser
from ai_rules.parsers.copilot import CopilotParser
from ai_rules.parsers.cursor import CursorParser
from ai_rules.parsers.base import BaseParser
from ai_rules.parsers.markdown_utils import read_file_text
from ai_rules.state import State
from ai_rules.store import read_universal_rules


PARSERS: dict[str, BaseParser] = {
    "claude-code": ClaudeCodeParser(),
    "cursor": CursorParser(),
    "copilot": CopilotParser(),
}


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _scan_path(
    path: Path,
    pattern: str,
    tool_name: str,
    parser: BaseParser,
    workspace: Path,
) -> list[DiscoveredRule]:
    """Scan a directory for rule files matching a pattern."""
    discovered = []
    for match in sorted(path.glob(pattern)):
        if not match.is_file():
            continue
        raw_content = read_file_text(match)
        groups = parser.parse(match)
        try:
            rel_path = str(match.relative_to(workspace))
        except ValueError:
            rel_path = str(match)
        for group in groups:
            discovered.append(DiscoveredRule(
                rule_group=group,
                source_tool=tool_name,
                source_path=rel_path,
                content_hash=compute_content_hash(raw_content),
            ))
    return discovered


def discover_rules(config: Config) -> list[DiscoveredRule]:
    """Scan all configured repos and tools for rules.

    Also scans workspace-level CLAUDE.md as a special source
    for universal rule candidates.
    """
    discovered = []

    # Scan workspace-level CLAUDE.md (not tied to any repo)
    workspace_claude = config.workspace / "CLAUDE.md"
    if workspace_claude.exists():
        parser = PARSERS["claude-code"]
        discovered.extend(
            _scan_path(config.workspace, "CLAUDE.md", "claude-code", parser, config.workspace)
        )

    # Scan each repo
    for repo_config in config.repos:
        repo_path = config.workspace / repo_config.path
        if not repo_path.exists():
            continue

        for tool_name in repo_config.tools:
            if tool_name not in config.tools:
                continue
            tool_config = config.tools[tool_name]
            parser = PARSERS.get(tool_name)
            if not parser:
                continue

            for pattern in tool_config.rule_patterns:
                discovered.extend(
                    _scan_path(repo_path, pattern, tool_name, parser, config.workspace)
                )

    return discovered


def _get_target_path(tool_name: str, tool_pattern: str, repo_path: Path) -> Path:
    """Determine the write target for a tool in a repo."""
    if tool_name == "cursor":
        return repo_path / ".cursor" / "rules"
    return repo_path / tool_pattern


def _load_repo_specific_rules(
    config: Config,
    repo_path: Path,
    target_tool: str,
) -> list[RuleGroup]:
    """Load repo-specific rules from whatever tool authored them."""
    repo_rules = []
    for tool_name, tool_config in config.tools.items():
        if tool_name == target_tool:
            continue  # skip the tool we're writing to
        parser = PARSERS.get(tool_name)
        if not parser:
            continue
        for pattern in tool_config.rule_patterns:
            for match in sorted(repo_path.glob(pattern)):
                if not match.is_file():
                    continue
                # Skip _universal- files (those are our own output)
                if match.name.startswith("_universal-"):
                    continue
                groups = parser.parse(match)
                repo_rules.extend(groups)
    return repo_rules


def push_rules(
    config: Config,
    tool_name: str,
    state: State,
) -> list[str]:
    """Push universal + repo-specific rules to a tool.

    Returns list of paths written.
    """
    parser = PARSERS.get(tool_name)
    if not parser:
        return []

    universal = read_universal_rules(config.canonical_store)
    written = []

    for repo_config in config.repos:
        if tool_name not in repo_config.tools:
            continue
        repo_path = config.workspace / repo_config.path
        if not repo_path.exists():
            continue

        tool_config = config.tools[tool_name]
        target = _get_target_path(tool_name, tool_config.rule_patterns[0], repo_path)

        # Merge universal + repo-specific rules
        repo_specific = _load_repo_specific_rules(config, repo_path, tool_name)
        merged = universal + repo_specific

        parser.write(merged, target)

        # Compute hash for state tracking
        converted = parser.convert(merged)
        combined = "\n".join(converted.values())
        state.record_push(tool_name, repo_config.path, compute_content_hash(combined))

        written.append(str(target))

    return written
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_sync.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_rules/sync.py tests/test_sync.py
git commit -m "add sync orchestration (discover and push)"
```

---

### Task 11: Inventory scanner

**Files:**
- Create: `src/ai_rules/inventory.py`
- Create: `tests/test_inventory.py`

- [ ] **Step 1: Write tests for inventory**

```python
# tests/test_inventory.py
import json
from pathlib import Path

from ai_rules.config import Config, ToolConfig, RepoConfig
from ai_rules.inventory import scan_inventory, write_inventory_file
from ai_rules.models import InventoryItem


def test_scan_claude_code_mcp_servers(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings = {
        "mcpServers": {
            "filesystem": {"command": "npx", "args": ["-y", "@anthropic/mcp-filesystem"]},
            "postgres": {"command": "npx", "args": ["-y", "@anthropic/mcp-postgres"]},
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings))

    items = scan_inventory(claude_settings_path=claude_dir / "settings.json")
    mcp_items = [i for i in items if i.category == "mcp_server"]
    assert len(mcp_items) == 2
    names = {i.name for i in mcp_items}
    assert "filesystem" in names
    assert "postgres" in names


def test_scan_cursor_skills(tmp_path):
    skills_dir = tmp_path / ".cursor" / "skills" / "deploy-scripts"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("Deploy script skill")

    items = scan_inventory(cursor_skills_paths=[tmp_path / ".cursor" / "skills"])
    skill_items = [i for i in items if i.category == "skill"]
    assert len(skill_items) == 1
    assert skill_items[0].name == "deploy-scripts"


def test_write_inventory_file(tmp_path):
    items = [
        InventoryItem(tool="claude-code", category="mcp_server", name="filesystem", path=None),
        InventoryItem(tool="cursor", category="skill", name="deploy-scripts", path="/some/path"),
    ]
    out_path = tmp_path / "inventory.md"
    write_inventory_file(out_path, items)
    content = out_path.read_text()
    assert "filesystem" in content
    assert "deploy-scripts" in content
    assert "claude-code" in content.lower() or "Claude Code" in content


def test_scan_empty_returns_empty():
    items = scan_inventory()
    assert items == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_inventory.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement inventory scanner**

```python
# src/ai_rules/inventory.py
"""Scan non-universal assets (MCP servers, plugins, skills)."""

import json
from pathlib import Path

from ai_rules.models import InventoryItem


def scan_inventory(
    *,
    claude_settings_path: Path | None = None,
    cursor_skills_paths: list[Path] | None = None,
) -> list[InventoryItem]:
    """Scan for non-universal assets across tools."""
    items: list[InventoryItem] = []

    if claude_settings_path and claude_settings_path.exists():
        items.extend(_scan_claude_code(claude_settings_path))

    for skills_path in (cursor_skills_paths or []):
        if skills_path.exists():
            items.extend(_scan_cursor_skills(skills_path))

    return items


def _scan_claude_code(settings_path: Path) -> list[InventoryItem]:
    """Scan Claude Code settings.json for MCP servers and other assets."""
    items = []
    data = json.loads(settings_path.read_text(encoding="utf-8"))

    for name in data.get("mcpServers", {}):
        items.append(InventoryItem(
            tool="claude-code",
            category="mcp_server",
            name=name,
            path=None,
        ))

    return items


def _scan_cursor_skills(skills_path: Path) -> list[InventoryItem]:
    """Scan Cursor skills directories."""
    items = []
    if not skills_path.is_dir():
        return items

    for skill_dir in sorted(skills_path.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            items.append(InventoryItem(
                tool="cursor",
                category="skill",
                name=skill_dir.name,
                path=str(skill_dir),
            ))

    return items


def write_inventory_file(path: Path, items: list[InventoryItem]) -> None:
    """Write inventory to a markdown file."""
    lines = ["# Non-Universal Assets Inventory\n"]

    by_tool: dict[str, list[InventoryItem]] = {}
    for item in items:
        by_tool.setdefault(item.tool, []).append(item)

    for tool, tool_items in sorted(by_tool.items()):
        lines.append(f"\n## {tool}\n")
        by_category: dict[str, list[InventoryItem]] = {}
        for item in tool_items:
            by_category.setdefault(item.category, []).append(item)

        for category, cat_items in sorted(by_category.items()):
            lines.append(f"\n### {category}\n")
            for item in cat_items:
                path_info = f" ({item.path})" if item.path else ""
                lines.append(f"- {item.name}{path_info}")
            lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_inventory.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_rules/inventory.py tests/test_inventory.py
git commit -m "add inventory scanner"
```

---

## Chunk 5: CLI & Integration

### Task 12: CLI commands

**Files:**
- Create: `src/ai_rules/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write tests for CLI**

```python
# tests/test_cli.py
import json
from pathlib import Path

from typer.testing import CliRunner

from ai_rules.cli import app

runner = CliRunner()


def _setup_workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace for CLI testing."""
    # Config
    config = {
        "workspace": str(tmp_path / "workspace"),
        "canonical_store": str(tmp_path / "universal-rules"),
        "tools": {
            "claude-code": {"rule_patterns": ["CLAUDE.md"]},
            "copilot": {"rule_patterns": [".github/copilot-instructions.md"]},
        },
        "repos": [
            {"path": "repo-a", "tools": ["claude-code", "copilot"]},
        ],
    }
    config_path = tmp_path / "config.yaml"

    from ruamel.yaml import YAML
    yaml = YAML()
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    # Workspace and repo
    workspace = tmp_path / "workspace"
    repo = workspace / "repo-a"
    repo.mkdir(parents=True)
    (repo / "CLAUDE.md").write_text("## Python\n\nUse snake_case.\n")

    # Canonical store
    store = tmp_path / "universal-rules"
    store.mkdir()

    return config_path


def test_status_command(tmp_path):
    config_path = _setup_workspace(tmp_path)
    result = runner.invoke(app, ["status", "--config", str(config_path)])
    assert result.exit_code == 0


def test_pull_command_noninteractive(tmp_path):
    config_path = _setup_workspace(tmp_path)
    result = runner.invoke(app, ["pull", "--config", str(config_path), "--auto-repo-specific"])
    assert result.exit_code == 0
    assert "Found" in result.stdout or "No new" in result.stdout


def test_push_command(tmp_path):
    config_path = _setup_workspace(tmp_path)

    # Put something in the universal store
    store = tmp_path / "universal-rules"
    (store / "python.md").write_text("## snake_case\n\nUse snake_case.\n")

    result = runner.invoke(app, ["push", "copilot", "--config", str(config_path)])
    assert result.exit_code == 0

    # Check file was written
    copilot_file = tmp_path / "workspace" / "repo-a" / ".github" / "copilot-instructions.md"
    assert copilot_file.exists()
    content = copilot_file.read_text()
    assert "snake_case" in content


def test_promote_command(tmp_path):
    config_path = _setup_workspace(tmp_path)
    claude_md = tmp_path / "workspace" / "repo-a" / "CLAUDE.md"
    result = runner.invoke(app, ["promote", str(claude_md), "--config", str(config_path)])
    assert result.exit_code == 0
    assert "Promoted" in result.stdout
    # Check it was written to universal store
    store = tmp_path / "universal-rules"
    assert any(store.glob("*.md"))


def test_inventory_command(tmp_path):
    config_path = _setup_workspace(tmp_path)
    result = runner.invoke(app, ["inventory", "--config", str(config_path)])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI**

```python
# src/ai_rules/cli.py
"""CLI entry point for ai-rules."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ai_rules.config import load_config
from ai_rules.inventory import scan_inventory, write_inventory_file
from ai_rules.state import load_state, save_state
from ai_rules.store import read_universal_rules, write_universal_rules
from ai_rules.sync import discover_rules, push_rules, compute_content_hash

app = typer.Typer(help="Sync AI coding tool rules across Claude Code, Cursor, and VS Code Copilot.")
console = Console()

DEFAULT_CONFIG = Path("config.yaml")


def _resolve_config(config: Path) -> Path:
    if config.exists():
        return config
    raise typer.BadParameter(f"Config file not found: {config}")


@app.command()
def status(
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Show what's out of sync + inventory summary."""
    cfg = load_config(_resolve_config(config))
    state = load_state(config.parent / ".ai-rules-state.json")

    discovered = discover_rules(cfg)
    new_or_changed = [d for d in discovered if state.is_changed(d.source_path, d.content_hash)]

    console.print(f"\n[bold]Unpulled changes:[/bold] {len(new_or_changed)} rule(s)")
    for d in new_or_changed:
        console.print(f"  {d.source_tool}: {d.source_path}")

    universal = read_universal_rules(cfg.canonical_store)
    console.print(f"\n[bold]Universal rules:[/bold] {len(universal)} group(s)")
    for g in universal:
        console.print(f"  {g.name} ({len(g.rules)} rules)")

    # Inventory summary
    items = scan_inventory(
        claude_settings_path=Path.home() / ".claude" / "settings.json",
        cursor_skills_paths=[cfg.workspace / r.path / ".cursor" / "skills" for r in cfg.repos],
    )
    if items:
        console.print(f"\n[bold]Non-universal assets:[/bold] {len(items)}")
        for item in items:
            console.print(f"  [{item.tool}] {item.category}: {item.name}")


@app.command()
def pull(
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    auto_repo_specific: bool = typer.Option(False, "--auto-repo-specific", help="Classify all new rules as repo-specific without prompting"),
) -> None:
    """Scan tools, detect new/changed rules, prompt to classify."""
    cfg = load_config(_resolve_config(config))
    state_path = config.parent / ".ai-rules-state.json"
    state = load_state(state_path)

    discovered = discover_rules(cfg)
    new_or_changed = [d for d in discovered if state.is_changed(d.source_path, d.content_hash)]

    if not new_or_changed:
        console.print("No new or changed rules found.")
        return

    console.print(f"Found {len(new_or_changed)} new/changed rule(s):\n")

    for d in new_or_changed:
        console.print(f"  [bold]{d.source_tool}[/bold]: {d.source_path}")
        for rule in d.rule_group.rules:
            console.print(f"    - {rule.name}")

        if auto_repo_specific:
            classification = "repo-specific"
        else:
            choice = typer.prompt(
                f"  Classify '{d.source_path}' as (u)niversal or (r)epo-specific?",
                default="r",
            )
            classification = "universal" if choice.lower().startswith("u") else "repo-specific"

        if classification == "universal":
            write_universal_rules(cfg.canonical_store, [d.rule_group], append=True)
            promoted_to = f"universal-rules/{d.rule_group.normalized_name}.md"
            state.record_rule(d.source_path, d.content_hash, "universal", promoted_to=promoted_to)
            console.print(f"  → Promoted to {promoted_to}")
        else:
            state.record_rule(d.source_path, d.content_hash, "repo-specific")
            console.print("  → Kept as repo-specific")

    from datetime import datetime, timezone
    state.last_pull = datetime.now(timezone.utc).isoformat()
    save_state(state_path, state)
    console.print("\nState saved.")


@app.command()
def push(
    tool: Optional[str] = typer.Argument(None, help="Tool name (e.g., copilot, claude-code, cursor)"),
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    all_tools: bool = typer.Option(False, "--all", help="Push to all configured tools"),
) -> None:
    """Push universal rules to a tool across configured repos."""
    cfg = load_config(_resolve_config(config))
    state_path = config.parent / ".ai-rules-state.json"
    state = load_state(state_path)

    if all_tools:
        tools_to_push = list(cfg.tools.keys())
    elif tool:
        if tool not in cfg.tools:
            console.print(f"Unknown tool: {tool}. Available: {', '.join(cfg.tools.keys())}")
            raise typer.Exit(1)
        tools_to_push = [tool]
    else:
        console.print("Specify a tool name or use --all.")
        raise typer.Exit(1)

    for t in tools_to_push:
        console.print(f"\nPushing to [bold]{t}[/bold]...")
        written = push_rules(cfg, t, state)
        for path in written:
            console.print(f"  → {path}")

    save_state(state_path, state)
    console.print("\nDone.")


@app.command()
def promote(
    file: Path = typer.Argument(..., help="Path to a tool-native rule file to promote"),
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
) -> None:
    """Promote a repo-specific rule to universal."""
    cfg = load_config(_resolve_config(config))
    state_path = config.parent / ".ai-rules-state.json"
    state = load_state(state_path)

    from ai_rules.sync import PARSERS

    # Detect tool from file path
    tool_name = None
    if file.suffix == ".mdc":
        tool_name = "cursor"
    elif file.name == "CLAUDE.md":
        tool_name = "claude-code"
    elif file.name == "copilot-instructions.md":
        tool_name = "copilot"

    if not tool_name or tool_name not in PARSERS:
        console.print(f"Cannot determine tool for: {file}")
        raise typer.Exit(1)

    parser = PARSERS[tool_name]
    groups = parser.parse(file)

    write_universal_rules(cfg.canonical_store, groups, append=True)

    raw_content = file.read_text(encoding="utf-8")
    content_hash = compute_content_hash(raw_content)
    rel_path = str(file)
    for group in groups:
        promoted_to = f"universal-rules/{group.normalized_name}.md"
        state.record_rule(rel_path, content_hash, "universal", promoted_to=promoted_to)
        console.print(f"Promoted '{group.name}' → {promoted_to}")

    save_state(state_path, state)
    console.print("\nRemember to run 'ai-rules push' to distribute.")


@app.command()
def inventory(
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
) -> None:
    """Scan and display non-universal assets."""
    cfg = load_config(_resolve_config(config))

    items = scan_inventory(
        claude_settings_path=Path.home() / ".claude" / "settings.json",
        cursor_skills_paths=[cfg.workspace / r.path / ".cursor" / "skills" for r in cfg.repos],
    )

    if not items:
        console.print("No non-universal assets found.")
        return

    table = Table(title="Non-Universal Assets")
    table.add_column("Tool")
    table.add_column("Category")
    table.add_column("Name")
    table.add_column("Path")

    for item in items:
        table.add_row(item.tool, item.category, item.name, item.path or "")

    console.print(table)

    # Persist to inventory.md
    inventory_path = cfg.canonical_store / "inventory.md"
    write_inventory_file(inventory_path, items)
    console.print(f"\nSaved to {inventory_path}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Run all tests to verify nothing is broken**

```bash
uv run pytest -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_rules/cli.py tests/test_cli.py
git commit -m "add CLI commands (status, pull, push, promote, inventory)"
```

---

### Task 13: README and config template

**Files:**
- Create: `README.md`
- Create: `config.yaml` (template)

- [ ] **Step 1: Create config.yaml template**

```yaml
# ai-rules configuration
# Adjust workspace path and repos to match your setup.

workspace: C:\Users\qli\Workspace
canonical_store: ./universal-rules

tools:
  claude-code:
    rule_patterns: ["CLAUDE.md"]
  cursor:
    rule_patterns: [".cursor/rules/*.mdc"]
  copilot:
    rule_patterns: [".github/copilot-instructions.md"]

repos:
  - path: database-www
    tools: [claude-code, cursor, copilot]
  - path: productcatalog-api
    tools: [claude-code, cursor, copilot]
```

- [ ] **Step 2: Create README.md**

```markdown
# AI Tool Rules Migrator

Sync AI coding tool rules across Claude Code, Cursor, and VS Code Copilot from a single source of truth.

## Problem

Rules accumulate in whichever tool you're using. When you switch tools, those rules don't follow — so you either recreate them manually or work without them.

## How It Works

- **Universal rules** live in a canonical store (`universal-rules/`) as plain markdown files
- **Repo-specific rules** stay in-place in each repository
- The tool **pulls** new rules from any tool, lets you classify them, and **pushes** universal rules to every configured tool

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd ai-tool-rules-migrator
uv sync
```

## Quick Start

1. Edit `config.yaml` — set your workspace path and repos
2. Pull existing rules:
   ```bash
   uv run ai-rules pull
   ```
3. Classify each detected rule as universal or repo-specific
4. Push universal rules to another tool:
   ```bash
   uv run ai-rules push copilot
   ```

## Commands

| Command | Description |
|---------|-------------|
| `ai-rules status` | Show unpulled changes, universal rules, and asset inventory |
| `ai-rules pull` | Scan tools for new/changed rules, classify them |
| `ai-rules push <tool>` | Push universal rules to a tool (e.g., `copilot`, `cursor`, `claude-code`) |
| `ai-rules push --all` | Push to all configured tools |
| `ai-rules promote <file>` | Move a repo-specific rule to universal |
| `ai-rules inventory` | List non-universal assets (MCP servers, skills, plugins) |

## Configuration

Edit `config.yaml`:

```yaml
workspace: C:\Users\you\Workspace
canonical_store: ./universal-rules

tools:
  claude-code:
    rule_patterns: ["CLAUDE.md"]
  cursor:
    rule_patterns: [".cursor/rules/*.mdc"]
  copilot:
    rule_patterns: [".github/copilot-instructions.md"]

repos:
  - path: my-repo
    tools: [claude-code, cursor, copilot]
```

## Adding a New Tool

Create a new parser in `src/ai_rules/parsers/` implementing `BaseParser`:
- `parse()` — read rules from the tool's native format
- `convert()` — convert rules to the tool's native format
- `write()` — write converted rules to disk

Register it in `src/ai_rules/sync.py` in the `PARSERS` dict.

## How Push Handles Existing Content

- **Claude Code / Copilot:** Rules are written between `<!-- ai-rules:start -->` and `<!-- ai-rules:end -->` markers. Hand-written content outside markers is preserved.
- **Cursor:** Universal rules are written as `_universal-*.mdc` files, so hand-written `.mdc` files are never touched.
```

- [ ] **Step 3: Commit**

```bash
git add README.md config.yaml
git commit -m "add README and config template"
```

---

### Task 14: End-to-end smoke test

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 2: Manual smoke test — pull**

```bash
uv run ai-rules pull --config config.yaml
```

Expected: Discovers rules from configured repos, prompts for classification.

- [ ] **Step 3: Manual smoke test — push**

```bash
uv run ai-rules push copilot --config config.yaml
```

Expected: Writes `copilot-instructions.md` with universal rules in configured repos.

- [ ] **Step 4: Manual smoke test — status**

```bash
uv run ai-rules status --config config.yaml
```

Expected: Shows summary of rules and sync state.
