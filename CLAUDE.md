# Threads Development Guide

## Build & Development Commands
- Install: `uv install --tool -e .` or `pip install -e .` 
- Add dependency: `uv add <package>` (or `uv add --dev <package>` for dev dependencies)
- Run: `thread <command>` (installed script)
- Lint: `ruff check .`
- Format: `ruff format .`
- Test: `pytest tests/`
- Test single: `pytest tests/test_file.py::test_function -v`

## Code Style & Conventions

### Python
- Python ≥3.12 required
- Use type hints everywhere; see `py.typed` marker
- Function annotations with return types: `def func() -> str:`
- Use docstrings for functions ("""Description""")
- **Fail early**: Check conditions at function start and return/raise immediately

### Error Handling
- CLI errors: Use `console.print("[red]Error:[/red] Message")` + `sys.exit(1)`
- DB errors: Handle SQLite errors with try/except (see `add_tag`)
- Validate inputs at function start before processing

### Naming & Organization
- snake_case for functions/variables
- Functions prefixed with purpose: `cmd_*`, `get_*`, etc.
- Use type hints for function parameters and return values
- CLI commands organized in module `cli.py`
- Database operations in `db.py`

### Imports
- Standard library first, then third-party, then local
- Group imports by source (stdlib, external, internal)
- Import specific functions from modules when appropriate

### Testing
- Use pytest for testing: `python -m pytest`
- Install test dependencies with `uv add --dev pytest`
- Tests in `tests/` directory mirroring src structure
- Use `tmp_path` fixture for temporary test databases: `test_db = tmp_path / "test_threads.db"`
- Test functions prefixed with `test_`: `def test_something():` 
- Use mocks for external dependencies: `@patch("threads.cli.console")`