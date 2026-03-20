"""Tests for the Cursor .mdc parser."""
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
    assert groups[0].metadata["alwaysApply"] is True


def test_convert_to_mdc():
    parser = CursorParser()
    rules = [Rule(name="Conventions", content="- Use PascalCase.")]
    group = RuleGroup(name="database", rules=rules, metadata={"description": "DB rules", "alwaysApply": True})
    result = parser.convert([group])
    assert "database.mdc" in result
    content = result["database.mdc"]
    assert "alwaysApply: true" in content
    assert "- Use PascalCase." in content


def test_convert_universal_defaults():
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
