import json
from pathlib import Path
from ai_rules.state import State, load_state, save_state


def test_load_state_empty(tmp_path):
    state = load_state(tmp_path / ".ai-rules-state.json")
    assert state.version == 1
    assert state.rules == {}
    assert state.pushes == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / ".ai-rules-state.json"
    state = State(version=1, last_pull="2026-03-19T17:30:00Z")
    state.rules["CLAUDE.md##Python"] = {
        "content_hash": "sha256:abc123", "classification": "universal",
        "promoted_to": "universal-rules/python.md", "last_seen": "2026-03-19T17:30:00Z",
    }
    save_state(path, state)
    loaded = load_state(path)
    assert loaded.rules["CLAUDE.md##Python"]["classification"] == "universal"
    assert loaded.last_pull == "2026-03-19T17:30:00Z"


def test_record_push(tmp_path):
    path = tmp_path / ".ai-rules-state.json"
    state = State(version=1)
    state.record_push("copilot", "my-repo", "sha256:xyz")
    save_state(path, state)
    loaded = load_state(path)
    assert loaded.pushes["copilot"]["my-repo"]["content_hash"] == "sha256:xyz"


def test_is_changed_new_rule():
    state = State(version=1)
    assert state.is_changed("new/path.md", "sha256:new") is True


def test_is_changed_same_hash():
    state = State(version=1)
    state.rules["path.md"] = {"content_hash": "sha256:abc", "classification": "repo-specific", "last_seen": ""}
    assert state.is_changed("path.md", "sha256:abc") is False


def test_is_changed_different_hash():
    state = State(version=1)
    state.rules["path.md"] = {"content_hash": "sha256:old", "classification": "repo-specific", "last_seen": ""}
    assert state.is_changed("path.md", "sha256:new") is True
