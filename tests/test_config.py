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

def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))

def test_load_config_canonical_store_resolved():
    config = load_config(FIXTURES / "sample_config.yaml")
    assert config.canonical_store.is_absolute()
    assert config.canonical_store.name == "universal-rules"

def test_load_config_invalid_tool_reference():
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
