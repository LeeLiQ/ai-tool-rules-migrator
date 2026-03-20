# AI Tool Rules Migrator — Design Spec

**Date:** 2026-03-19
**Status:** Draft

## Problem

AI coding tool rules accumulate organically across Claude Code, Cursor, and VS Code Copilot. When switching tools, rules don't follow — forcing manual recreation or working without them, leading to wasted time fixing avoidable mistakes.

## Solution

A Python CLI tool (`ai-rules`) that:
1. Extracts rules from any supported AI tool's native format
2. Maintains a canonical store of universal rules (plain markdown)
3. Converts and pushes rules into any supported tool's format
4. Inventories non-universal assets (MCP servers, skills, plugins) for reference

## Core Concepts

### Rule Scopes

| Scope | Lives in | Pushed to |
|-------|----------|-----------|
| **Universal** | Canonical store (`universal-rules/`) | Every tool + every repo |
| **Repo-specific** | The repo itself (e.g., `database-www/CLAUDE.md`) | That repo only, in target tool's format |
| **Tool-specific** | Not synced — inventoried only | N/A |

### Canonical Store

A directory (version-controlled) holding universal rules as plain markdown files grouped by topic:

```
universal-rules/
  python.md
  workflow.md
  git.md
  ...
```

Each file is a **rule group** (one topic). Within each file, `##` headings define individual **rules**. No special frontmatter — just markdown.

**Mapping:** one file = one `RuleGroup`, one `##` section = one `Rule`.

### Rule Identity

Rules are matched across tools by **normalized topic name** (lowercase, whitespace-trimmed). For example, a `## Python` section in `CLAUDE.md` and a `python.mdc` file in Cursor are considered the same rule group.

### Repo-Specific Rule Storage

Repo-specific rules stay in-place in the source repo. They are **not** copied to the canonical store. During `pull`, when a rule is classified as repo-specific, this decision is recorded in the state file (see Change Detection). The canonical store only holds universal rules.

### Inventory

Non-universal assets are scanned and reported but not converted:
- Claude Code: MCP servers, plugins, skills
- Cursor: skills (`.cursor/skills/`)

The inventory is printed to the terminal and persisted to `inventory.md` in the canonical store.

## Supported Tools (v1)

### Claude Code
- **Format:** Single `CLAUDE.md` file per repo/workspace
- **Parse:** Split by `##` sections — each `##` section = one `Rule`, the file = one `RuleGroup`
- **Convert:** Assemble rules into a single `CLAUDE.md`
- **Locations:** Workspace root `CLAUDE.md`, repo-level `CLAUDE.md`

### Cursor
- **Format:** One `.mdc` file per rule group in `.cursor/rules/`
- **Parse:** Read YAML frontmatter (`description`, `globs`, `alwaysApply`) + markdown body. Each `.mdc` file = one `RuleGroup`.
- **Convert:** Write one `.mdc` file per `RuleGroup` with appropriate frontmatter
- **Default frontmatter for universal rules:** `alwaysApply: true`, no `globs` (universal rules apply everywhere)
- **Locations:** `<repo>/.cursor/rules/*.mdc`

### VS Code Copilot
- **Format:** Single `.github/copilot-instructions.md` per repo
- **Parse:** Split by `##` sections (similar to Claude Code)
- **Convert:** Assemble into single markdown file
- **Locations:** `<repo>/.github/copilot-instructions.md`

## Push Conflict Strategy

Push uses **marker comments** to manage only the portion of the file it owns:

```markdown
<!-- ai-rules:start -->
(generated universal rules go here)
<!-- ai-rules:end -->
```

Any content outside these markers is left untouched. If the markers don't exist yet, they are appended to the end of the file (or a new file is created with just the markers).

For Cursor (multi-file output), generated `.mdc` files are prefixed with `_universal-` (e.g., `_universal-python.mdc`) to avoid colliding with hand-written rule files.

## CLI Commands

```
ai-rules status          # Show what's out of sync + inventory
ai-rules pull            # Scan tools, detect new/changed rules, prompt to classify
ai-rules push <tool>     # Generate rules for a specific tool across configured repos
ai-rules push --all      # Generate for all configured tools
ai-rules promote <file>  # Move a repo-specific rule to universal
ai-rules inventory       # Refresh and display non-universal assets
```

### `ai-rules status`

Shows:
1. **Unpulled changes** — tool rule files that have changed since last `pull` (detected by comparing content hashes against state file)
2. **Unpushed rules** — universal rules that haven't been written to a configured tool/repo yet
3. **Inventory summary** — count of non-universal assets per tool

### `ai-rules promote <file>`

Argument is a path to a tool-native rule file (e.g., `database-www/.cursor/rules/python.mdc`).

Workflow:
1. Parse the rule from the source file
2. Write it to the canonical store (`universal-rules/<topic>.md`) — appending if the topic file exists, creating if not
3. Update state file to reclassify the rule as universal
4. Print reminder to run `push` to distribute

### Typical Workflow

1. Work in Cursor all day, add a new rule
2. Run `ai-rules pull`
3. Tool detects the new rule: "Found 1 new rule in Cursor (database-www). Repo-specific or promote to universal?"
4. Classify it
5. Run `ai-rules push copilot`
6. Switch to VS Code Copilot — rules are there

## Configuration

`config.yaml` in the project root:

```yaml
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

### Workspace-Level Rules

The workspace root `CLAUDE.md` (e.g., `C:\Users\qli\Workspace\CLAUDE.md`) is treated as a special source during `pull` — its rules are candidates for universal promotion. It is not tied to any single repo.

## Project Structure

```
ai-tool-rules-migrator/
├── pyproject.toml
├── README.md
├── src/
│   └── ai_rules/
│       ├── __init__.py
│       ├── cli.py                 # typer CLI entry point
│       ├── config.py              # load/validate config.yaml
│       ├── models.py              # Rule, RuleGroup, Inventory dataclasses
│       ├── store.py               # read/write universal rules in canonical store
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py            # abstract parser/converter interface
│       │   ├── claude_code.py
│       │   ├── cursor.py
│       │   └── copilot.py
│       ├── sync.py                # pull/push/promote orchestration logic
│       └── inventory.py           # scan non-universal assets
├── tests/
│   ├── test_parsers/
│   ├── test_sync.py
│   └── fixtures/                  # sample CLAUDE.md, .mdc files, etc.
├── config.yaml
└── universal-rules/
    └── ...
```

## Parser Interface

Every tool parser implements:

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, path: Path) -> list[RuleGroup]:
        """Read rules from tool-native format."""
        ...

    @abstractmethod
    def convert(self, rules: list[RuleGroup]) -> dict[str, str]:
        """Convert rules to tool-native format.

        Returns a mapping of filename -> content.
        For single-file tools (Claude Code, Copilot), this returns one entry.
        For multi-file tools (Cursor), this returns one entry per rule group.
        """
        ...

    @abstractmethod
    def write(self, rules: list[RuleGroup], target_path: Path) -> None:
        """Write converted rules to disk.

        For single-file tools: writes within ai-rules markers.
        For Cursor: writes _universal-*.mdc files.
        """
        ...
```

## Data Models

```python
@dataclass
class Rule:
    name: str              # heading text, e.g., "Use snake_case for Python files"
    content: str           # markdown body (under the heading)

@dataclass
class RuleGroup:
    name: str              # topic name, e.g., "python", "workflow"
    rules: list[Rule]
    metadata: dict         # tool-specific metadata (e.g., Cursor globs, alwaysApply)

@dataclass
class DiscoveredRule:
    """Transient object used during pull — includes provenance."""
    rule_group: RuleGroup
    source_tool: str       # "claude-code", "cursor", "copilot"
    source_path: str       # where it was found
    content_hash: str      # SHA-256 of the raw content

@dataclass
class InventoryItem:
    tool: str
    category: str          # "mcp_server", "plugin", "skill"
    name: str
    path: str | None
```

## State File (`.ai-rules-state.json`)

Stored in the project root. Tracks what was seen during the last `pull` to enable change detection.

```json
{
  "version": 1,
  "last_pull": "2026-03-19T17:30:00Z",
  "rules": {
    "database-www/.cursor/rules/python.mdc": {
      "content_hash": "sha256:abc123...",
      "classification": "repo-specific",
      "last_seen": "2026-03-19T17:30:00Z"
    },
    "CLAUDE.md##Python": {
      "content_hash": "sha256:def456...",
      "classification": "universal",
      "promoted_to": "universal-rules/python.md",
      "last_seen": "2026-03-19T17:30:00Z"
    }
  },
  "pushes": {
    "copilot": {
      "database-www": {
        "last_push": "2026-03-19T18:00:00Z",
        "content_hash": "sha256:ghi789..."
      }
    }
  }
}
```

**Fields:**
- `rules` — every rule file seen during pull, keyed by relative path (with `##Section` suffix for multi-section files)
- `content_hash` — SHA-256 of raw file/section content, used to detect changes
- `classification` — `"universal"` or `"repo-specific"`
- `pushes` — tracks what was last pushed to each tool/repo, so `status` can detect unpushed changes

## Change Detection (Pull)

When `ai-rules pull` runs:
1. Scan all configured repos and tools for rule files
2. Parse each file into `DiscoveredRule` objects (with content hash)
3. Compare hashes against `.ai-rules-state.json`
4. Present new/changed rules to the user
5. User classifies: keep as repo-specific, or promote to universal
6. If promoted: write to canonical store
7. Update state file

## Push Merge Logic

When `ai-rules push <tool>` runs for a given repo:
1. Load universal rules from canonical store
2. Load repo-specific rules from that repo (read from the **source tool that authored them** — determined by state file classification records)
3. Merge: universal rules first, then repo-specific
4. Convert merged rules to target tool's format
5. Write to the target location (using markers for single-file tools, `_universal-` prefix for Cursor)
6. Update pushes record in state file

## Technology

- **Language:** Python 3.12+
- **Package manager:** uv
- **CLI framework:** typer
- **YAML parsing:** ruamel.yaml (preserves comments and formatting)
- **Testing:** pytest
- **Platforms:** Windows, macOS

## Future Extensibility

- Adding a new tool = one new file in `parsers/` implementing `BaseParser`
- Potential future tools: Codex (`AGENTS.md`), Windsurf (`.windsurfrules`), Antigravity
- Could add `ai-rules diff` to preview what push would write without writing
- Could add `ai-rules init` to bootstrap config for a new workspace

## Out of Scope (v1)

- Automatic/background syncing (always manual CLI invocation)
- Converting skills or MCP configs between tools
- Team/shared rule management
- GUI
