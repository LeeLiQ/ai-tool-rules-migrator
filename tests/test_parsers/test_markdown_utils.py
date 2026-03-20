from ai_rules.parsers.markdown_utils import split_sections, read_file_text, inject_marked_block

MARKER_START = "<!-- ai-rules:start -->"
MARKER_END = "<!-- ai-rules:end -->"

def test_split_sections_basic():
    text = "## Python\n\nUse snake_case.\n\n## Git\n\nCommit often.\n"
    rules = split_sections(text)
    assert len(rules) == 2
    assert rules[0].name == "Python"
    assert "snake_case" in rules[0].content

def test_split_sections_ignores_preamble():
    text = "# Title\n\nSome intro.\n\n## Rule\n\nContent.\n"
    rules = split_sections(text)
    assert len(rules) == 1

def test_split_sections_empty():
    assert split_sections("") == []

def test_read_file_text_handles_bom(tmp_path):
    f = tmp_path / "test.md"
    f.write_bytes(b"\xef\xbb\xbf## Rule\n\nContent.\n")
    text = read_file_text(f)
    assert text.startswith("## Rule")

def test_read_file_text_normalizes_crlf(tmp_path):
    f = tmp_path / "test.md"
    f.write_bytes(b"## Rule\r\n\r\nContent.\r\n")
    text = read_file_text(f)
    assert "\r" not in text

def test_inject_marked_block_new_file():
    result = inject_marked_block(None, "generated content")
    assert MARKER_START in result
    assert "generated content" in result

def test_inject_marked_block_append():
    existing = "# My Project\n\nHand-written.\n"
    result = inject_marked_block(existing, "generated")
    assert "Hand-written." in result
    assert MARKER_START in result

def test_inject_marked_block_replace():
    existing = f"# My Project\n\n{MARKER_START}\nold stuff\n{MARKER_END}\n\nMore content.\n"
    result = inject_marked_block(existing, "new stuff")
    assert "old stuff" not in result
    assert "new stuff" in result
    assert "More content." in result
