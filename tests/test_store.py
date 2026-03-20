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
    assert read_universal_rules(store) == []

def test_write_universal_rules(tmp_path):
    store = tmp_path / "universal-rules"
    store.mkdir()
    groups = [RuleGroup(name="python", rules=[
        Rule(name="snake_case", content="Use snake_case."),
        Rule(name="Type hints", content="Always add type hints."),
    ], metadata={})]
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
