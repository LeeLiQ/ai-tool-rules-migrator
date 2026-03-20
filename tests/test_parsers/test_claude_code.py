from pathlib import Path
from ai_rules.parsers.claude_code import ClaudeCodeParser
from ai_rules.models import Rule, RuleGroup

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_claude_md():
    parser = ClaudeCodeParser()
    groups = parser.parse(FIXTURES / "sample_claude.md")
    assert len(groups) == 1
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
    content = next(iter(result.values()))
    assert "## Python" in content
    assert "## Git" in content


def test_write_with_markers(tmp_path):
    parser = ClaudeCodeParser()
    target = tmp_path / "CLAUDE.md"
    target.write_text("# My Project\n\nHand-written content.\n")
    rules = [Rule(name="Python", content="- Use snake_case.")]
    group = RuleGroup(name="universal", rules=rules, metadata={})
    parser.write([group], target)
    result = target.read_text()
    assert "Hand-written content." in result
    assert "<!-- ai-rules:start -->" in result
    assert "## Python" in result


def test_write_creates_new_file(tmp_path):
    parser = ClaudeCodeParser()
    target = tmp_path / "CLAUDE.md"
    rules = [Rule(name="Python", content="- Use snake_case.")]
    group = RuleGroup(name="universal", rules=rules, metadata={})
    parser.write([group], target)
    result = target.read_text()
    assert "<!-- ai-rules:start -->" in result


def test_write_replaces_existing_markers(tmp_path):
    parser = ClaudeCodeParser()
    existing = "# My Project\n\n<!-- ai-rules:start -->\n## Old Rule\n\n- Old content.\n<!-- ai-rules:end -->\n\nMore hand-written content.\n"
    target = tmp_path / "CLAUDE.md"
    target.write_text(existing)
    rules = [Rule(name="New Rule", content="- New content.")]
    group = RuleGroup(name="universal", rules=rules, metadata={})
    parser.write([group], target)
    result = target.read_text()
    assert "Old Rule" not in result
    assert "New Rule" in result
    assert "More hand-written content." in result
