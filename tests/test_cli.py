import json
from pathlib import Path
from typer.testing import CliRunner
from ai_rules.cli import app

runner = CliRunner()

def _setup_workspace(tmp_path: Path) -> Path:
    config = {
        "workspace": str(tmp_path / "workspace"),
        "canonical_store": str(tmp_path / "universal-rules"),
        "tools": {
            "claude-code": {"rule_patterns": ["CLAUDE.md"]},
            "copilot": {"rule_patterns": [".github/copilot-instructions.md"]},
        },
        "repos": [{"path": "repo-a", "tools": ["claude-code", "copilot"]}],
    }
    config_path = tmp_path / "config.yaml"
    from ruamel.yaml import YAML
    yaml = YAML()
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    workspace = tmp_path / "workspace"
    repo = workspace / "repo-a"
    repo.mkdir(parents=True)
    (repo / "CLAUDE.md").write_text("## Python\n\nUse snake_case.\n")
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
    store = tmp_path / "universal-rules"
    (store / "python.md").write_text("## snake_case\n\nUse snake_case.\n")
    result = runner.invoke(app, ["push", "copilot", "--config", str(config_path)])
    assert result.exit_code == 0
    copilot_file = tmp_path / "workspace" / "repo-a" / ".github" / "copilot-instructions.md"
    assert copilot_file.exists()
    assert "snake_case" in copilot_file.read_text()

def test_promote_command(tmp_path):
    config_path = _setup_workspace(tmp_path)
    claude_md = tmp_path / "workspace" / "repo-a" / "CLAUDE.md"
    result = runner.invoke(app, ["promote", str(claude_md), "--config", str(config_path)])
    assert result.exit_code == 0
    assert "Promoted" in result.stdout
    store = tmp_path / "universal-rules"
    assert any(store.glob("*.md"))

def test_inventory_command(tmp_path):
    config_path = _setup_workspace(tmp_path)
    result = runner.invoke(app, ["inventory", "--config", str(config_path)])
    assert result.exit_code == 0
