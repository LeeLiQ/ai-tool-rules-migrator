"""Data models for AI Tool Rules Migrator."""

from dataclasses import dataclass, field


@dataclass
class Rule:
    """A single rule — one ## section within a rule group."""
    name: str
    content: str


@dataclass
class RuleGroup:
    """A group of related rules — one topic file or one .mdc file."""
    name: str
    rules: list[Rule]
    metadata: dict = field(default_factory=dict)

    @property
    def normalized_name(self) -> str:
        """Lowercase, stripped name used for matching across tools."""
        return self.name.strip().lower()


@dataclass
class DiscoveredRule:
    """Transient object used during pull — includes provenance."""
    rule_group: RuleGroup
    source_tool: str
    source_path: str
    content_hash: str


@dataclass
class InventoryItem:
    """A non-universal asset (MCP server, plugin, skill)."""
    tool: str
    category: str
    name: str
    path: str | None = None
