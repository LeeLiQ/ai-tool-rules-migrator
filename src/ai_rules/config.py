"""Configuration loading and validation."""
from dataclasses import dataclass, field
from pathlib import Path
from ruamel.yaml import YAML

@dataclass
class ToolConfig:
    name: str
    rule_patterns: list[str]
    global_path: Path | None = None

@dataclass
class RepoConfig:
    path: str
    tools: list[str]

@dataclass
class Config:
    workspace: Path
    canonical_store: Path
    tools: dict[str, ToolConfig] = field(default_factory=dict)
    repos: list[RepoConfig] = field(default_factory=list)

def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    yaml = YAML()
    with open(path) as f:
        data = yaml.load(f)
    config_dir = path.parent
    tools = {}
    for name, tool_data in data.get("tools", {}).items():
        raw_global = tool_data.get("global_path")
        global_path = Path(raw_global) if raw_global else None
        tools[name] = ToolConfig(name=name, rule_patterns=tool_data.get("rule_patterns", []), global_path=global_path)
    repos = []
    for repo_data in data.get("repos", []):
        repo_tools = repo_data.get("tools", [])
        for t in repo_tools:
            if t not in tools:
                raise ValueError(f"Repo '{repo_data['path']}' references unknown tool '{t}'. Available tools: {', '.join(tools.keys())}")
        repos.append(RepoConfig(path=repo_data["path"], tools=repo_tools))
    raw_store = data.get("canonical_store", "./universal-rules")
    canonical_store = (config_dir / raw_store).resolve()
    return Config(workspace=Path(data["workspace"]), canonical_store=canonical_store, tools=tools, repos=repos)
