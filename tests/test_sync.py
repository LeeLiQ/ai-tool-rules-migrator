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
        repos=[RepoConfig(path="repo-a", tools=["claude-code"])],
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
    (cursor_dir / "python.mdc").write_text("---\ndescription: Python rules\nalwaysApply: true\n---\n\n# Style\n\nUse snake_case.\n")
    config = Config(
        workspace=workspace, canonical_store=workspace / "universal-rules",
        tools={"cursor": ToolConfig(name="cursor", rule_patterns=[".cursor/rules/*.mdc"])},
        repos=[RepoConfig(path="repo-a", tools=["cursor"])],
    )
    discovered = discover_rules(config)
    assert len(discovered) >= 1
    assert discovered[0].source_tool == "cursor"

def test_discover_rules_skips_missing_repo(tmp_path):
    config = _make_config(tmp_path)
    discovered = discover_rules(config)
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

def test_discover_rules_finds_global_cursor_rules(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    global_cursor = tmp_path / "global_cursor_rules"
    global_cursor.mkdir()
    (global_cursor / "git-worktree.mdc").write_text(
        "---\ndescription: Git worktree conventions\nalwaysApply: true\n---\n\n# Git Worktrees\n\nUse worktrees for feature branches.\n"
    )
    config = Config(
        workspace=workspace,
        canonical_store=workspace / "universal-rules",
        tools={"cursor": ToolConfig(name="cursor", rule_patterns=[".cursor/rules/*.mdc"], global_path=global_cursor)},
        repos=[],
    )
    discovered = discover_rules(config)
    assert len(discovered) == 1
    assert discovered[0].source_tool == "cursor"
    assert "Git Worktrees" in [r.name for r in discovered[0].rule_group.rules]


def test_discover_rules_skips_missing_global_path(tmp_path):
    config = Config(
        workspace=tmp_path,
        canonical_store=tmp_path / "universal-rules",
        tools={"cursor": ToolConfig(name="cursor", rule_patterns=[".cursor/rules/*.mdc"], global_path=tmp_path / "nonexistent")},
        repos=[],
    )
    discovered = discover_rules(config)
    assert discovered == []


def test_push_rules_writes_copilot_file(tmp_path):
    workspace = tmp_path / "workspace"
    repo = workspace / "repo-a"
    repo.mkdir(parents=True)
    store = tmp_path / "universal-rules"
    store.mkdir()
    (store / "python.md").write_text("## snake_case\n\nUse snake_case.\n")
    config = Config(
        workspace=workspace, canonical_store=store,
        tools={"copilot": ToolConfig(name="copilot", rule_patterns=[".github/copilot-instructions.md"])},
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
        workspace=tmp_path, canonical_store=tmp_path / "universal-rules",
        tools={"copilot": ToolConfig(name="copilot", rule_patterns=[".github/copilot-instructions.md"])},
        repos=[RepoConfig(path="nonexistent", tools=["copilot"])],
    )
    state = State()
    assert push_rules(config, "copilot", state) == []
