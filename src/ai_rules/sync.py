"""Pull/push/promote orchestration logic."""
import hashlib
from pathlib import Path
from ai_rules.config import Config
from ai_rules.models import DiscoveredRule, RuleGroup
from ai_rules.parsers.claude_code import ClaudeCodeParser
from ai_rules.parsers.copilot import CopilotParser
from ai_rules.parsers.cursor import CursorParser
from ai_rules.parsers.base import BaseParser
from ai_rules.parsers.markdown_utils import read_file_text
from ai_rules.state import State
from ai_rules.store import read_universal_rules

PARSERS: dict[str, BaseParser] = {
    "claude-code": ClaudeCodeParser(),
    "cursor": CursorParser(),
    "copilot": CopilotParser(),
}


def compute_content_hash(content: str) -> str:
    """Compute a SHA-256 hash of the given content string."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _scan_path(path: Path, pattern: str, tool_name: str, parser: BaseParser, workspace: Path) -> list[DiscoveredRule]:
    discovered = []
    for match in sorted(path.glob(pattern)):
        if not match.is_file():
            continue
        raw_content = read_file_text(match)
        groups = parser.parse(match)
        try:
            rel_path = str(match.relative_to(workspace))
        except ValueError:
            rel_path = str(match)
        for group in groups:
            discovered.append(DiscoveredRule(
                rule_group=group, source_tool=tool_name,
                source_path=rel_path, content_hash=compute_content_hash(raw_content),
            ))
    return discovered


def discover_rules(config: Config) -> list[DiscoveredRule]:
    """Scan all configured repos and tools for rules. Also scans workspace-level CLAUDE.md."""
    discovered = []
    # Scan workspace-level CLAUDE.md
    workspace_claude = config.workspace / "CLAUDE.md"
    if workspace_claude.exists():
        parser = PARSERS["claude-code"]
        discovered.extend(_scan_path(config.workspace, "CLAUDE.md", "claude-code", parser, config.workspace))
    # Scan each repo
    for repo_config in config.repos:
        repo_path = config.workspace / repo_config.path
        if not repo_path.exists():
            continue
        for tool_name in repo_config.tools:
            if tool_name not in config.tools:
                continue
            tool_config = config.tools[tool_name]
            parser = PARSERS.get(tool_name)
            if not parser:
                continue
            for pattern in tool_config.rule_patterns:
                discovered.extend(_scan_path(repo_path, pattern, tool_name, parser, config.workspace))
    return discovered


def _get_target_path(tool_name: str, tool_pattern: str, repo_path: Path) -> Path:
    if tool_name == "cursor":
        return repo_path / ".cursor" / "rules"
    return repo_path / tool_pattern


def _load_repo_specific_rules(config: Config, repo_path: Path, target_tool: str) -> list[RuleGroup]:
    repo_rules = []
    for tool_name, tool_config in config.tools.items():
        if tool_name == target_tool:
            continue
        parser = PARSERS.get(tool_name)
        if not parser:
            continue
        for pattern in tool_config.rule_patterns:
            for match in sorted(repo_path.glob(pattern)):
                if not match.is_file():
                    continue
                if match.name.startswith("_universal-"):
                    continue
                groups = parser.parse(match)
                repo_rules.extend(groups)
    return repo_rules


def push_rules(config: Config, tool_name: str, state: State) -> list[str]:
    """Push universal rules (merged with repo-specific rules) to each configured repo for the given tool."""
    parser = PARSERS.get(tool_name)
    if not parser:
        return []
    universal = read_universal_rules(config.canonical_store)
    written = []
    for repo_config in config.repos:
        if tool_name not in repo_config.tools:
            continue
        repo_path = config.workspace / repo_config.path
        if not repo_path.exists():
            continue
        tool_config = config.tools[tool_name]
        target = _get_target_path(tool_name, tool_config.rule_patterns[0], repo_path)
        repo_specific = _load_repo_specific_rules(config, repo_path, tool_name)
        merged = universal + repo_specific
        parser.write(merged, target)
        converted = parser.convert(merged)
        combined = "\n".join(converted.values())
        state.record_push(tool_name, repo_config.path, compute_content_hash(combined))
        written.append(str(target))
    return written
