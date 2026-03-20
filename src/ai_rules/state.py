"""State file management for change detection."""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class State:
    version: int = 1
    last_pull: str = ""
    rules: dict[str, dict] = field(default_factory=dict)
    pushes: dict[str, dict] = field(default_factory=dict)

    def is_changed(self, key: str, content_hash: str) -> bool:
        if key not in self.rules:
            return True
        return self.rules[key]["content_hash"] != content_hash

    def record_rule(self, key: str, content_hash: str, classification: str, promoted_to: str | None = None) -> None:
        entry: dict = {
            "content_hash": content_hash,
            "classification": classification,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
        if promoted_to:
            entry["promoted_to"] = promoted_to
        self.rules[key] = entry

    def record_push(self, tool: str, repo: str, content_hash: str) -> None:
        if tool not in self.pushes:
            self.pushes[tool] = {}
        self.pushes[tool][repo] = {
            "last_push": datetime.now(timezone.utc).isoformat(),
            "content_hash": content_hash,
        }


def load_state(path: Path) -> State:
    if not path.exists():
        return State()
    data = json.loads(path.read_text(encoding="utf-8"))
    return State(version=data.get("version", 1), last_pull=data.get("last_pull", ""),
                 rules=data.get("rules", {}), pushes=data.get("pushes", {}))


def save_state(path: Path, state: State) -> None:
    data = {"version": state.version, "last_pull": state.last_pull, "rules": state.rules, "pushes": state.pushes}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
