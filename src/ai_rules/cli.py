"""CLI entry point for ai-rules."""
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from ai_rules.config import load_config
from ai_rules.inventory import scan_inventory, write_inventory_file
from ai_rules.state import load_state, save_state
from ai_rules.store import read_universal_rules, write_universal_rules
from ai_rules.sync import discover_rules, push_rules, compute_content_hash

app = typer.Typer(help="Sync AI coding tool rules across Claude Code, Cursor, and VS Code Copilot.")
console = Console()
DEFAULT_CONFIG = Path("config.yaml")

def _resolve_config(config: Path) -> Path:
    if config.exists():
        return config
    raise typer.BadParameter(f"Config file not found: {config}")

@app.command()
def status(config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c")) -> None:
    """Show what's out of sync + inventory summary."""
    cfg = load_config(_resolve_config(config))
    state = load_state(config.parent / ".ai-rules-state.json")
    discovered = discover_rules(cfg)
    new_or_changed = [d for d in discovered if state.is_changed(d.source_path, d.content_hash)]
    console.print(f"\n[bold]Unpulled changes:[/bold] {len(new_or_changed)} rule(s)")
    for d in new_or_changed:
        console.print(f"  {d.source_tool}: {d.source_path}")
    universal = read_universal_rules(cfg.canonical_store)
    console.print(f"\n[bold]Universal rules:[/bold] {len(universal)} group(s)")
    for g in universal:
        console.print(f"  {g.name} ({len(g.rules)} rules)")
    items = scan_inventory(
        claude_settings_path=Path.home() / ".claude" / "settings.json",
        cursor_skills_paths=[cfg.workspace / r.path / ".cursor" / "skills" for r in cfg.repos],
    )
    if items:
        console.print(f"\n[bold]Non-universal assets:[/bold] {len(items)}")
        for item in items:
            console.print(f"  [{item.tool}] {item.category}: {item.name}")

@app.command()
def pull(
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    auto_repo_specific: bool = typer.Option(False, "--auto-repo-specific"),
) -> None:
    """Scan tools, detect new/changed rules, prompt to classify."""
    cfg = load_config(_resolve_config(config))
    state_path = config.parent / ".ai-rules-state.json"
    state = load_state(state_path)
    discovered = discover_rules(cfg)
    new_or_changed = [d for d in discovered if state.is_changed(d.source_path, d.content_hash)]
    if not new_or_changed:
        console.print("No new or changed rules found.")
        return
    console.print(f"Found {len(new_or_changed)} new/changed rule(s):\n")
    for d in new_or_changed:
        console.print(f"  [bold]{d.source_tool}[/bold]: {d.source_path}")
        for rule in d.rule_group.rules:
            console.print(f"    - {rule.name}")
        if auto_repo_specific:
            classification = "repo-specific"
        else:
            choice = typer.prompt(f"  Classify '{d.source_path}' as (u)niversal or (r)epo-specific?", default="r")
            classification = "universal" if choice.lower().startswith("u") else "repo-specific"
        if classification == "universal":
            write_universal_rules(cfg.canonical_store, [d.rule_group], append=True)
            promoted_to = f"universal-rules/{d.rule_group.normalized_name}.md"
            state.record_rule(d.source_path, d.content_hash, "universal", promoted_to=promoted_to)
            console.print(f"  → Promoted to {promoted_to}")
        else:
            state.record_rule(d.source_path, d.content_hash, "repo-specific")
            console.print("  → Kept as repo-specific")
    from datetime import datetime, timezone
    state.last_pull = datetime.now(timezone.utc).isoformat()
    save_state(state_path, state)
    console.print("\nState saved.")

@app.command()
def push(
    tool: Optional[str] = typer.Argument(None),
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    all_tools: bool = typer.Option(False, "--all"),
) -> None:
    """Push universal rules to a tool across configured repos."""
    cfg = load_config(_resolve_config(config))
    state_path = config.parent / ".ai-rules-state.json"
    state = load_state(state_path)
    if all_tools:
        tools_to_push = list(cfg.tools.keys())
    elif tool:
        if tool not in cfg.tools:
            console.print(f"Unknown tool: {tool}. Available: {', '.join(cfg.tools.keys())}")
            raise typer.Exit(1)
        tools_to_push = [tool]
    else:
        console.print("Specify a tool name or use --all.")
        raise typer.Exit(1)
    for t in tools_to_push:
        console.print(f"\nPushing to [bold]{t}[/bold]...")
        written = push_rules(cfg, t, state)
        for path in written:
            console.print(f"  → {path}")
    save_state(state_path, state)
    console.print("\nDone.")

@app.command()
def promote(
    file: Path = typer.Argument(...),
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
) -> None:
    """Promote a repo-specific rule to universal."""
    cfg = load_config(_resolve_config(config))
    state_path = config.parent / ".ai-rules-state.json"
    state = load_state(state_path)
    from ai_rules.sync import PARSERS
    tool_name = None
    if file.suffix == ".mdc":
        tool_name = "cursor"
    elif file.name == "CLAUDE.md":
        tool_name = "claude-code"
    elif file.name == "copilot-instructions.md":
        tool_name = "copilot"
    if not tool_name or tool_name not in PARSERS:
        console.print(f"Cannot determine tool for: {file}")
        raise typer.Exit(1)
    parser = PARSERS[tool_name]
    groups = parser.parse(file)
    write_universal_rules(cfg.canonical_store, groups, append=True)
    raw_content = file.read_text(encoding="utf-8")
    content_hash = compute_content_hash(raw_content)
    rel_path = str(file)
    for group in groups:
        promoted_to = f"universal-rules/{group.normalized_name}.md"
        state.record_rule(rel_path, content_hash, "universal", promoted_to=promoted_to)
        console.print(f"Promoted '{group.name}' → {promoted_to}")
    save_state(state_path, state)
    console.print("\nRemember to run 'ai-rules push' to distribute.")

@app.command()
def inventory(config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c")) -> None:
    """Scan and display non-universal assets."""
    cfg = load_config(_resolve_config(config))
    items = scan_inventory(
        claude_settings_path=Path.home() / ".claude" / "settings.json",
        cursor_skills_paths=[cfg.workspace / r.path / ".cursor" / "skills" for r in cfg.repos],
    )
    if not items:
        console.print("No non-universal assets found.")
        return
    table = Table(title="Non-Universal Assets")
    table.add_column("Tool")
    table.add_column("Category")
    table.add_column("Name")
    table.add_column("Path")
    for item in items:
        table.add_row(item.tool, item.category, item.name, item.path or "")
    console.print(table)
    inventory_path = cfg.canonical_store / "inventory.md"
    write_inventory_file(inventory_path, items)
    console.print(f"\nSaved to {inventory_path}")
