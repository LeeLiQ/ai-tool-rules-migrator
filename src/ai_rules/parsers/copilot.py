"""Parser for VS Code Copilot instructions files."""
from pathlib import Path
from ai_rules.models import RuleGroup
from ai_rules.parsers.base import BaseParser
from ai_rules.parsers.markdown_utils import read_file_text, split_sections, inject_marked_block


class CopilotParser(BaseParser):
    """Parser for VS Code Copilot .github/copilot-instructions.md files."""

    def parse(self, path: Path) -> list[RuleGroup]:
        """Parse a Copilot instructions file into RuleGroups."""
        text = read_file_text(path)
        rules = split_sections(text)
        return [RuleGroup(name=path.stem, rules=rules, metadata={})]

    def convert(self, rules: list[RuleGroup]) -> dict[str, str]:
        """Convert RuleGroups to Copilot instructions file content."""
        sections = []
        for group in rules:
            for rule in group.rules:
                sections.append(f"## {rule.name}\n\n{rule.content}")
        content = "\n\n".join(sections) + "\n"
        return {"copilot-instructions.md": content}

    def write(self, rules: list[RuleGroup], target_path: Path) -> None:
        """Write rules to a Copilot instructions file, injecting between markers."""
        converted = self.convert(rules)
        generated = next(iter(converted.values()))
        existing = read_file_text(target_path) if target_path.exists() else None
        new_content = inject_marked_block(existing, generated)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(new_content, encoding="utf-8")
