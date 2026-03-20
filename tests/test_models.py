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
        rule_group=group, source_tool="cursor",
        source_path=".cursor/rules/python.mdc", content_hash="sha256:abc123",
    )
    assert discovered.source_tool == "cursor"

def test_inventory_item_creation():
    item = InventoryItem(tool="claude-code", category="mcp_server", name="filesystem", path="/some/path")
    assert item.tool == "claude-code"
    assert item.category == "mcp_server"
