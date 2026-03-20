"""Tests for inventory scanner."""
import json
from pathlib import Path
from ai_rules.inventory import scan_inventory, write_inventory_file
from ai_rules.models import InventoryItem


def test_scan_claude_code_mcp_servers(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings = {"mcpServers": {
        "filesystem": {"command": "npx", "args": ["-y", "@anthropic/mcp-filesystem"]},
        "postgres": {"command": "npx", "args": ["-y", "@anthropic/mcp-postgres"]},
    }}
    (claude_dir / "settings.json").write_text(json.dumps(settings))
    items = scan_inventory(claude_settings_path=claude_dir / "settings.json")
    mcp_items = [i for i in items if i.category == "mcp_server"]
    assert len(mcp_items) == 2
    names = {i.name for i in mcp_items}
    assert "filesystem" in names
    assert "postgres" in names


def test_scan_cursor_skills(tmp_path):
    skills_dir = tmp_path / ".cursor" / "skills" / "deploy-scripts"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("Deploy script skill")
    items = scan_inventory(cursor_skills_paths=[tmp_path / ".cursor" / "skills"])
    skill_items = [i for i in items if i.category == "skill"]
    assert len(skill_items) == 1
    assert skill_items[0].name == "deploy-scripts"


def test_write_inventory_file(tmp_path):
    items = [
        InventoryItem(tool="claude-code", category="mcp_server", name="filesystem", path=None),
        InventoryItem(tool="cursor", category="skill", name="deploy-scripts", path="/some/path"),
    ]
    out_path = tmp_path / "inventory.md"
    write_inventory_file(out_path, items)
    content = out_path.read_text()
    assert "filesystem" in content
    assert "deploy-scripts" in content


def test_scan_empty_returns_empty():
    items = scan_inventory()
    assert items == []
