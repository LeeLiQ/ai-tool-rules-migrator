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
