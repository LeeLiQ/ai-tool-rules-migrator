"""Parser for Cursor .mdc rule files."""
import re
from io import StringIO
from pathlib import Path
from ruamel.yaml import YAML
from ai_rules.models import Rule, RuleGroup
from ai_rules.parsers.base import BaseParser
from ai_rules.parsers.markdown_utils import read_file_text


class CursorParser(BaseParser):
    def parse(self, path: Path) -> list[RuleGroup]:
        text = read_file_text(path)
        metadata, body = _split_frontmatter(text)
        name = path.stem
        rules = _body_to_rules(body)
        return [RuleGroup(name=name, rules=rules, metadata=metadata)]

    def convert(self, rules: list[RuleGroup]) -> dict[str, str]:
        result = {}
        for group in rules:
            metadata = dict(group.metadata)
            if "alwaysApply" not in metadata:
                metadata["alwaysApply"] = True
            if "description" not in metadata:
                metadata["description"] = group.name
            frontmatter = _dump_yaml(metadata)
            body_parts = []
            for rule in group.rules:
                body_parts.append(f"# {rule.name}\n\n{rule.content}")
            body = "\n\n".join(body_parts) + "\n"
            content = f"---\n{frontmatter}---\n\n{body}"
            result[f"{group.normalized_name}.mdc"] = content
        return result

    def write(self, rules: list[RuleGroup], target_path: Path) -> None:
        target_path.mkdir(parents=True, exist_ok=True)
        for old in target_path.glob("_universal-*.mdc"):
            old.unlink()
        converted = self.convert(rules)
        for filename, content in converted.items():
            out_path = target_path / f"_universal-{filename}"
            out_path.write_text(content, encoding="utf-8")


def _split_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n*(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    yaml = YAML()
    metadata = yaml.load(match.group(1)) or {}
    return dict(metadata), match.group(2)


def _body_to_rules(body: str) -> list[Rule]:
    parts = re.split(r"^# (.+)$", body, flags=re.MULTILINE)
    rules = []
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        rules.append(Rule(name=name, content=content))
    if not rules and body.strip():
        rules.append(Rule(name="", content=body.strip()))
    return rules


def _dump_yaml(data: dict) -> str:
    yaml = YAML()
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()
