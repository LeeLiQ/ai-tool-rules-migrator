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
