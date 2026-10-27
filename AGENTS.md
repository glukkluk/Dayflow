# Repository notes

- Small Django schedule app ("Особистий розклад"). Python `3.14` (see `.python-version`); deps in root `pyproject.toml`, locked in `uv.lock`. Always run via `uv run` from the repo root after `uv sync`.
- Layout: project package `app/config`; apps `app/accounts` (registration, profile) and `app/planner` (categories, events, tasks, calendar, dashboard, notifications); shared templates in `app/templates`.
- `planner` keeps views thin and split per feature in `app/planner/views/*.py`; business logic lives in `app/planner/services/` (`recurrence`, `conflicts`, `autoplan`, `dashboard`, `notifications`, `event_moves`, `free_tasks`). Put new logic there, not in views.
- `app/manage.py` sets `DJANGO_SETTINGS_MODULE=config.settings` (no `app.` prefix). It only resolves when `app/` is on `sys.path`, so run as `uv run python app/manage.py <command>` from the repo root — not as a module path.
- DB is SQLite at `app/db.sqlite3` (git-ignored, local-only). Repo name mentions MySQL but no MySQL config/service exists; do not add one unasked.
- `README.md` is the stage-by-stage feature spec (Ukrainian) and records rules agreed with the user (e.g. the 365-day conflict-check horizon). Treat it as the requirements source.

## Commands

- `uv sync`
- `uv run python app/manage.py migrate`
- `uv run python app/manage.py runserver`
- `uv run python app/manage.py check`
- `uv run python app/manage.py test accounts planner` — the only test entrypoint (plain Django `TestCase`; tests live in `app/<app>/tests.py` or an `app/<app>/tests/` package — `planner` has some, `accounts` has none). Focus with a label, e.g. `... test planner.tests.OnTimeNavigationTests.test_event_periods_and_quick_navigation`; `.Class` / `.Class.method` suffixes work. A label matching nothing prints `NO TESTS RAN` yet exits 0 — exit 0 alone does not prove tests ran.
- `uv run python app/manage.py createsuperuser` for `/admin/` access

## Gotchas that bite

- Post-login landing is `/` (`LOGIN_REDIRECT_URL = 'planner:dashboard'`): guests see the public landing page, authenticated users the private dashboard.
- Change task status via `Task.save()`; `QuerySet.update()` bypasses the model logic maintaining `completed_at`, and DB checks enforce status/`completed_at` consistency.
- Notifications are generated lazily: `collect_due()` runs inside `GET /api/notifications/pending/`, polled every 30 s by `toasts.js`. There is no cron/management command (a stale `generate_notifications` `.pyc` may exist locally with no source — ignore it). Preserve the delivery contract: the page's first poll sends `?silent=true`, marking reminders that came due while signed out as `delivered_at` (badge only, no toast), and showing a toast must never mark a notification read.
- Email is not configured: `MAILERS = {...}` in `settings.py` is a nonstandard key Django ignores (it reads `EMAIL_BACKEND`). Reminders are in-app only — don't add email unasked.
- Third-party JS/CSS is CDN-pinned in `app/planner/templates/planner/`: HTMX 2.0.8 (only it carries SRI `integrity=`), FullCalendar 7.1.2, Luxon 3.7.2. Own JS/CSS: `app/planner/static/planner/` and `app/accounts/static/accounts/`; UI icons are inline SVG branches in `app/templates/partials/icon.html` (`{% include 'partials/icon.html' with name='...' %}`) — extend that partial instead of adding an icon library.
- Avatars need Pillow (declared in `pyproject.toml` — `uv sync` after pulling). Uploads land in git-ignored `app/media/` and are served only when `DEBUG=True` (urls.py wires `static(MEDIA_URL, ...)`); in production set the `SUPABASE_*` env vars (see `.env.example`) so uploads go to a public Supabase Storage bucket via django-storages (Render's disk is ephemeral).

## Conventions that differ from defaults

- UI language is Ukrainian (`LANGUAGE_CODE = 'uk'`); keep user-facing strings in Ukrainian.
- Time handling: `USE_TZ=True`, `TIME_ZONE='UTC'`. Datetimes are entered/displayed in the user's profile timezone (`accounts.middleware.ProfileTimezoneMiddleware`) and stored in UTC. Ambiguous/nonexistent local (DST) times must be rejected, not silently shifted — recurrence expansion answers 400 with `code=invalid_occurrence_time`.
- Date/time rendering is a per-user profile setting: templates must use the `display_formats` context-processor variables (`date_fmt`, `short_date_fmt`, `time_fmt`, `datetime_fmt`, `short_datetime_fmt`) with `|date:`, never hardcoded patterns. All time inputs, dropdowns, work hours and calendar labels follow the profile's 12/24-hour setting; 12-hour input requires AM/PM.
- Validation is duplicated at form and DB level — preserve both when touching constraints: profile work hours, category `#RRGGBB` + per-user name uniqueness, event `end > start`, task status/`completed_at`/duration/priority.
- Ownership: other users' records return 404 (never 403); choice fields must be queryset-scoped to `request.user`; destructive actions only via POST + CSRF.
- No lint/typecheck/CI configured; `manage.py check` + `manage.py test` are the only verification entrypoints.
- Commit messages use gitmoji + Conventional Commits with scope (`✨ feat(planner): ...`) — follow the `gitmoji-conventional-commits` skill.
