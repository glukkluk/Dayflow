# Repository notes

- This is a small Django project. Dependencies and Python requirement (`>=3.14`) are declared in the root `pyproject.toml` and locked in `uv.lock`; use `uv run` to run project commands.
- Django's project package is `app/config`; `app/manage.py` sets `config.settings`. From the repository root, run management commands as `uv run python app/manage.py <command>` (for example, `check`, `test`, or `migrate`).
- The checked-in settings currently use SQLite at `app/db.sqlite3`. Do not assume a MySQL service or configuration is present despite the repository name.
- There is no configured lint/typecheck/test runner in the root manifest; Django's built-in test runner is the available test entrypoint.
