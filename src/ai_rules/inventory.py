"""Scan non-universal assets (MCP servers, plugins, skills)."""
import json
from pathlib import Path
from ai_rules.models import InventoryItem


def scan_inventory(
    *,
    claude_settings_path: Path | None = None,
    cursor_skills_paths: list[Path] | None = None,
) -> list[InventoryItem]:
    """Scan non-universal assets and return a list of inventory items."""
    items: list[InventoryItem] = []
    if claude_settings_path and claude_settings_path.exists():
        items.extend(_scan_claude_code(claude_settings_path))
    for skills_path in (cursor_skills_paths or []):
        if skills_path.exists():
            items.extend(_scan_cursor_skills(skills_path))
    return items


def _scan_claude_code(settings_path: Path) -> list[InventoryItem]:
    """Scan Claude Code settings for MCP servers."""
    items = []
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    for name in data.get("mcpServers", {}):
        items.append(InventoryItem(tool="claude-code", category="mcp_server", name=name, path=None))
    return items


def _scan_cursor_skills(skills_path: Path) -> list[InventoryItem]:
    """Scan Cursor skills directory for installed skills."""
    items = []
    if not skills_path.is_dir():
        return items
    for skill_dir in sorted(skills_path.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            items.append(InventoryItem(tool="cursor", category="skill", name=skill_dir.name, path=str(skill_dir)))
    return items


def write_inventory_file(path: Path, items: list[InventoryItem]) -> None:
    """Write inventory items to a Markdown file grouped by tool and category."""
    lines = ["# Non-Universal Assets Inventory\n"]
    by_tool: dict[str, list[InventoryItem]] = {}
    for item in items:
        by_tool.setdefault(item.tool, []).append(item)
    for tool, tool_items in sorted(by_tool.items()):
        lines.append(f"\n## {tool}\n")
        by_category: dict[str, list[InventoryItem]] = {}
        for item in tool_items:
            by_category.setdefault(item.category, []).append(item)
        for category, cat_items in sorted(by_category.items()):
            lines.append(f"\n### {category}\n")
            for item in cat_items:
                path_info = f" ({item.path})" if item.path else ""
                lines.append(f"- {item.name}{path_info}")
            lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
