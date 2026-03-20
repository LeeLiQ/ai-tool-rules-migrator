"""Parser for Claude Code CLAUDE.md files."""
from pathlib import Path
from ai_rules.models import RuleGroup
from ai_rules.parsers.base import BaseParser
from ai_rules.parsers.markdown_utils import read_file_text, split_sections, inject_marked_block


class ClaudeCodeParser(BaseParser):
    def parse(self, path: Path) -> list[RuleGroup]:
        text = read_file_text(path)
        rules = split_sections(text)
        group_name = path.stem.lower()
        return [RuleGroup(name=group_name, rules=rules, metadata={})]

    def convert(self, rules: list[RuleGroup]) -> dict[str, str]:
        sections = []
        for group in rules:
            for rule in group.rules:
                sections.append(f"## {rule.name}\n\n{rule.content}")
        content = "\n\n".join(sections) + "\n"
        return {"CLAUDE.md": content}

    def write(self, rules: list[RuleGroup], target_path: Path) -> None:
        converted = self.convert(rules)
        generated = next(iter(converted.values()))
        existing = read_file_text(target_path) if target_path.exists() else None
        new_content = inject_marked_block(existing, generated)
        target_path.write_text(new_content, encoding="utf-8")
