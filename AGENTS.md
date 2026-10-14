# Repository notes

- Small Django schedule app ("Особистий розклад"). Python `3.14` (see `.python-version`); deps in root `pyproject.toml`, locked in `uv.lock`. Always run via `uv run` from the repo root after `uv sync`.
- Layout: project package is `app/config`, apps are `app/accounts` (auth + profile) and `app/planner` (categories + events), shared templates in `app/templates`.
- `app/manage.py` sets `DJANGO_SETTINGS_MODULE=config.settings` (no `app.` prefix). It only resolves when `app/` is on `sys.path`, so run as `uv run python app/manage.py <command>` from the repo root — not as a module path.
- DB is SQLite at `app/db.sqlite3` (git-ignored, local-only). Repo name mentions MySQL but no MySQL config/service exists; do not add one unasked.

## Commands

- `uv sync`
- `uv run python app/manage.py migrate`
- `uv run python app/manage.py runserver`
- `uv run python app/manage.py check`
- `uv run python app/manage.py test accounts planner` (currently zero tests — neither app ships a `tests/` module, so this passes vacuously; add tests alongside the app under test)
- `uv run python app/manage.py createsuperuser` for `/admin/` access

## Conventions that differ from defaults

- UI language is Ukrainian (`LANGUAGE_CODE = 'uk'`); keep user-facing strings in Ukrainian.
- Time handling: `USE_TZ=True`, `TIME_ZONE='UTC'`. Event datetimes are entered/displayed in the user's profile timezone (`accounts.middleware.ProfileTimezoneMiddleware`) and stored in UTC. Ambiguous/nonexistent local times must be rejected, not silently shifted.
- Validation is duplicated at form and DB level — preserve both when touching constraints: profile work hours (`work_end > work_start`, buffer 0–60), category color `#RRGGBB` + per-user name uniqueness, event `end > start`.
- Ownership rule: foreign users' categories/events return 404 (never 403), and category choice fields must be queryset-scoped to `request.user`. Deleting a category sets related events to `NULL` (`on_delete=SET_NULL`); destructive actions only via POST with CSRF.
- No lint/typecheck/CI configured; `manage.py check` + `manage.py test` are the only verification entrypoints.
