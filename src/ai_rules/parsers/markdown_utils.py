"""Shared markdown parsing and file I/O utilities."""
import re
from pathlib import Path
from ai_rules.models import Rule

MARKER_START = "<!-- ai-rules:start -->"
MARKER_END = "<!-- ai-rules:end -->"

def read_file_text(path: Path) -> str:
    """Read a text file, handling BOM and normalizing line endings."""
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")

def split_sections(text: str) -> list[Rule]:
    """Split markdown text by ## headings into Rule objects."""
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    rules = []
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        rules.append(Rule(name=name, content=content))
    return rules

def inject_marked_block(existing: str | None, generated: str) -> str:
    """Inject generated content between ai-rules markers."""
    marked_block = f"{MARKER_START}\n{generated}\n{MARKER_END}\n"
    if existing is None:
        return marked_block
    pattern = re.compile(re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END) + r"\n?", re.DOTALL)
    if pattern.search(existing):
        return pattern.sub(lambda _: marked_block, existing)
    else:
        return existing.rstrip("\n") + "\n\n" + marked_block
