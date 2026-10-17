# Repository notes

- Small Django schedule app ("Особистий розклад"). Python `3.14` (see `.python-version`); deps in root `pyproject.toml`, locked in `uv.lock`. Always run via `uv run` from the repo root after `uv sync`.
- Layout: project package `app/config`; apps `app/accounts` (registration, profile) and `app/planner` (categories, events, tasks, calendar, dashboard, notifications); shared templates in `app/templates`.
- `planner` keeps views thin and split per feature in `app/planner/views/*.py`; business logic lives in `app/planner/services/` (`recurrence`, `conflicts`, `autoplan`, `dashboard`, `notifications`, `event_moves`). Put new logic there, not in views.
- `app/manage.py` sets `DJANGO_SETTINGS_MODULE=config.settings` (no `app.` prefix). It only resolves when `app/` is on `sys.path`, so run as `uv run python app/manage.py <command>` from the repo root — not as a module path.
- DB is SQLite at `app/db.sqlite3` (git-ignored, local-only). Repo name mentions MySQL but no MySQL config/service exists; do not add one unasked.
- `README.md` is the stage-by-stage feature spec (Ukrainian) and records rules agreed with the user (e.g. the 365-day conflict-check horizon). Treat it as the requirements source.

## Commands

- `uv sync`
- `uv run python app/manage.py migrate`
- `uv run python app/manage.py runserver`
- `uv run python app/manage.py check`
- `uv run python app/manage.py test accounts planner` — the only test entrypoint; currently 0 tests (prints `NO TESTS RAN`, exits 0). Add tests next to the app under test.
- `uv run python app/manage.py createsuperuser` for `/admin/` access

## Gotchas that bite

- Post-login landing is `/` = dashboard (`LOGIN_REDIRECT_URL = 'planner:dashboard'`), not the profile page.
- Change task status via `Task.save()`; `QuerySet.update()` bypasses the model logic maintaining `completed_at`, and DB checks enforce status/`completed_at` consistency.
- Notifications are generated lazily: `collect_due()` runs inside `GET /api/notifications/pending/`, polled every 30 s by `toasts.js`. There is no cron/management command (a stale `generate_notifications` `.pyc` may exist locally with no source — ignore it).
- Email is not configured: `MAILERS = {...}` in `settings.py` is a nonstandard key Django ignores (it reads `EMAIL_BACKEND`). Reminders are in-app only — don't add email unasked.
- Third-party JS is CDN-pinned with SRI in templates: HTMX 2.0.8, FullCalendar 7.1.2, Luxon 3.7.2 (`app/planner/templates/planner/`). Own JS/CSS lives in `app/planner/static/planner/`.

## Conventions that differ from defaults

- UI language is Ukrainian (`LANGUAGE_CODE = 'uk'`); keep user-facing strings in Ukrainian.
- Time handling: `USE_TZ=True`, `TIME_ZONE='UTC'`. Datetimes are entered/displayed in the user's profile timezone (`accounts.middleware.ProfileTimezoneMiddleware`) and stored in UTC. Ambiguous/nonexistent local (DST) times must be rejected, not silently shifted — recurrence expansion answers 400 with `code=invalid_occurrence_time`.
- Validation is duplicated at form and DB level — preserve both when touching constraints: profile work hours, category `#RRGGBB` + per-user name uniqueness, event `end > start`, task status/`completed_at`/duration/priority.
- Ownership: other users' records return 404 (never 403); choice fields must be queryset-scoped to `request.user`; destructive actions only via POST + CSRF.
- No lint/typecheck/CI configured; `manage.py check` + `manage.py test` are the only verification entrypoints.
- Commit messages use gitmoji + Conventional Commits with scope (`✨ feat(planner): ...`) — follow the `gitmoji-conventional-commits` skill.
