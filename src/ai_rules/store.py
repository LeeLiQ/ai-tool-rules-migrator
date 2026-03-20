"""Read/write universal rules in the canonical store."""
from pathlib import Path
from ai_rules.models import RuleGroup
from ai_rules.parsers.markdown_utils import read_file_text, split_sections


def read_universal_rules(store_path: Path) -> list[RuleGroup]:
    groups = []
    for md_file in sorted(store_path.glob("*.md")):
        text = read_file_text(md_file)
        rules = split_sections(text)
        if rules:
            groups.append(RuleGroup(name=md_file.stem, rules=rules, metadata={}))
    return groups


def write_universal_rules(store_path: Path, groups: list[RuleGroup], *, append: bool = False) -> None:
    store_path.mkdir(parents=True, exist_ok=True)
    for group in groups:
        file_path = store_path / f"{group.normalized_name}.md"
        sections = []
        if append and file_path.exists():
            existing_text = read_file_text(file_path)
            sections.append(existing_text.rstrip("\n"))
        for rule in group.rules:
            sections.append(f"## {rule.name}\n\n{rule.content}")
        content = "\n\n".join(sections) + "\n"
        file_path.write_text(content, encoding="utf-8")
