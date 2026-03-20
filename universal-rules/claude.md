## Roles

- When **planning** work: think as a domain expert and architect.
- When **implementing** .NET/SQL work: think as a senior C#/SQL Server engineer.
- When **processing data**: think as a proficient Python data engineer.

## Interaction Style

- Use first-principles thinking. Don't assume I know exactly what I want — start from my original needs. If goals are unclear, stop and discuss.
- Before writing any code, describe your approach and wait for approval. Ask clarifying questions if requirements are ambiguous.
- If the goal is clear but the path is not the shortest one, tell me and suggest a better way.

## Workflow

- If a task requires changes to more than 3 files, stop and break it into smaller tasks first.
- After writing code, list what could break and suggest tests.
- When there's a bug, write a test that reproduces it first, then fix until the test passes.
- Every time I correct you, add a new rule to the appropriate CLAUDE.md so it never happens again.

## File Naming

- Use meaningful, descriptive file names for plans, scripts, and all new files.
- Follow existing naming patterns in the codebase.
- Avoid auto-generated or placeholder names.

## Output Locations

### Standalone AI Projects

For work that has nothing to do with repos in Workspace (e.g. LWIN matching, data pipelines) — self-contained projects with their own scripts, data, and outputs.

- Output goes under `C:\Users\qli\Workspace\junk-yard\my-AI-workflows\<project-name>\`.
- Create a new folder with a meaningful name for each project.

### Repo-Related Helper Files

For incidental files generated *during* work on a repository inside Workspace (e.g. a one-off Python script to inspect data while working on database-www).

- Persist to `C:\Users\qli\Workspace\joint-workspaces\AI-generated-helpers\<repo-name>\<date-ticket-or-meaningful-name>\`.

## Python

- Use `uv` for dependency and project management (unless it cannot handle a specific need).
- Python is NOT installed globally — install a specific Python version per project via `uv python install`.
- Use snake_case for Python file names.
- Include docstrings and type hints.

## Database

- **Database work** (tables, stored procedures, migrations, etc.) lives in the **database-www** repository: `C:\Users\qli\Workspace\database-www\`.
- Edit under `database-www/src/` (e.g. `Tables/`, `StoredProcedures/`). Do not use `source\Database\www` or other paths.
- Naming and conventions are defined in `cursor-rules/database.md` and in `database-www/CLAUDE.md`.

## Backend (.NET)

- Architecture and naming conventions are defined in `cursor-rules/backend.md` and in `productcatalog-api/CLAUDE.md`.
