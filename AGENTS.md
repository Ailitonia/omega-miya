# Omega-Miya AGENTS.md

## Project Overview

Omega-Miya is a multi-platform chatbot built on [NoneBot2](https://github.com/nonebot/nonebot2). It supports OneBot V11,
QQ (Open Platform), Telegram, and Console adapters, and uses an async SQLAlchemy ORM layer with Alembic migrations over
MySQL/PostgreSQL/SQLite backends.

- **Language**: Python >= 3.12
- **Entry Point**: `bot.py` - thin launcher that delegates to `src/cli`. Use `python bot.py --run` to start the bot; the
  `--database-*` commands manage schema migrations (see "Database Migrations (Alembic)").
- **Package Manager**: Poetry (see `pyproject.toml`)
- **Config**: `.env` -> `.env.<ENVIRONMENT>` loaded by NoneBot2/Pydantic

## Main Modules

- `bot.py` - thin launcher; parses CLI arguments via `src/cli` and dispatches to the matching handler.
- `src/cli` - command-line interface.
    - `command.py` - argparse parser definition and the `CliQueryArguments` pydantic model.
    - `hanlder.py` (sic) - command dispatch. `run_bot` sets up logging, calls `nonebot.init()`, registers adapters
      conditionally from config (OneBot V11 / QQ / Telegram / Console), and loads `src/service` then `src/plugins`.
- `src/compat.py` - compatibility helpers, e.g. pydantic v2 URL `TypeAdapter`s and reusable `type` aliases.
- `src/exception.py` - `OmegaException` base class and the project exception hierarchy.
- `src/resource.py` - resource path abstraction. Defines `BaseResource` (plus `AnyResource`, `LogFileResource`,
  `StaticResource`, `TemporaryResource`) and the optional file-hosting `BaseResourceHostProtocol`.
- `src/database` - database layer.
    - `config.py` - reads `DATABASE` env and builds the SQLAlchemy async URL.
    - `connector.py` - creates `AsyncEngine` and `async_sessionmaker` on import.
    - `schema_base.py` - declarative base with constraint naming conventions.
    - `schema.py` - ORM table models.
    - `model.py` - DAL base classes (`BaseDataAccessLayerModel`, `BaseDataQueryResultModel`).
    - `types.py` - cross-dialect column type variants (e.g. `IndexInt`).
    - `migrate.py` - Alembic command wrappers and the `check_migration_state()` safety check (`MigrationStatus`).
    - `internal/` - DALs (data access layers) for bot, entity, plugin, sign-in, subscriptions, etc.
    - `helpers.py` - startup hook runs the migration safety check and auto-upgrade (aborts startup on unsafe states);
      also provides session context utilities and the `DATABASE_SESSION` dependency.
- `src/service` - core services.
    - `omega_base` - entity wrappers, platform middlewares, message/event types, dependency injectors.
    - `omega_processor` - unified permission, cooldown, cost, rate-limit, history, statistic, friendship processing.
    - `omega_api` - FastAPI sub-app mounting and HMAC-signed router utilities.
    - `omega_global_cache` - memory + DB-backed cache.
    - `omega_multibot_support` - multi-protocol bot tracking and response de-duplication.
    - `omega_message_context` - message context manager and custom depends (e.g. artwork extraction).
    - `omega_file_host` / `omega_short_link` - auxiliary HTTP services (file hosting, short links).
    - `apscheduler` - scheduled-job wrapper.
    - `artwork_proxy` / `artwork_collection` - artwork-site proxy and local collection DB.
    - `gocqhttp_addition_event_patch` / `gocqhttp_self_sent_patch` / `qq_guild_audit_patch` - adapter behavior patches.
- `src/params` - NoneBot dependency injectors, handlers, rules, and reusable templates.
- `src/utils` - external API clients and helpers: `bilibili_api`, `pixiv_api`, `weibo_api`, `booru_api`, `openai_api`,
  `nhentai` / `comic18`, `image_searcher`, `image_utils`, `omega_requests` / `omega_common_api`, `crypto`, etc.
- `src/plugins` - business plugins. Naming convention: `omega_*` are core/meta plugins, `onebot_v11_*` are OneBot
  V11-specific, and the rest are platform-agnostic.
- `alembic/` + `alembic.ini` - database migration scripts; the baseline revision is locked (see below).
- `tools/` - standalone utility scripts (artwork downloader, old-version data migration, artwork rating GUI, etc.).
- `tests/` - pytest suite (see "Testing Instructions").

## Database Migrations (Alembic)

- Schema versions are managed by Alembic (`alembic.ini`, `alembic/versions/`). The baseline revision
  (`0bd5556acb4c_init_baseline`) is locked - never edit it; add new revisions instead.
- On startup (`src/database/helpers.py`), the bot runs `check_migration_state()` first: safe states (`FRESH`,
  `UPGRADABLE`, `UP_TO_DATE`) proceed to an automatic upgrade to head followed by a post-migration re-check; unsafe
  states (`UNSTAMPED_DATABASE`, `UNKNOWN_REVISION`, `MULTIPLE_*`) abort startup with remediation guidance.
- Manage migrations through the CLI wrappers instead of calling `alembic` directly:
    - `python bot.py --database-check` - show current/head revisions and check for pending upgrades.
    - `python bot.py --database-upgrade-to-head` / `--database-upgrade <rev>` - upgrade the database.
    - `python bot.py --database-downgrade <rev>` - downgrade the database.
    - `python bot.py --database-revision <message>` - autogenerate a new revision after changing `schema.py`.
    - `python bot.py --database-stamp <rev>` - manually mark the database version (e.g. align an unstamped database).

## Code Style Guidelines

- Python 3.12+ syntax; use type hints throughout.
- Linting / formatting: `ruff` (configured in `pyproject.toml`).
- Line length: 120 characters.
- String quotes: single quotes for inline strings.
- Imports: sorted and grouped; `E402` ignored for NoneBot adapter conditional imports.
- Follow existing patterns:
    - Pydantic v2 models.
    - Async SQLAlchemy 2.0.
    - NoneBot2 matcher/dependency patterns.
    - Place plugin business logic in `command.py`, `data_source.py`, `helpers.py`, etc.

## Testing Instructions

- Test suite lives under `tests/` (pytest + nonebug + pytest-asyncio, `asyncio_mode = "auto"`).
- Test environment config comes from `.env.test` (`tests/conftest.py` sets `ENVIRONMENT=test`); external API calls
  should be mocked.
- Test modules are imported at collection time before NoneBot is initialized (nonebug initializes it in a session
  fixture), so `src.*` imports must stay inside fixtures/test functions.
- `tests/conftest.py` auto-marks every async test with `loop_scope='session'` (shared event loop) and loads all of
  `src/service` and `src/plugins` after nonebug initializes NoneBot.
- `tests/database` tests reuse the real database connection configured by `.env.test` and perform guarded DDL/DML
  (snapshot & restore `alembic_version`, create/drop sentinel tables). Never point the test environment at a production
  database.

## Security Considerations

- **Secrets live in `.env`** and must never be committed.
    - `AES_KEY`, `DB_PASSWORD`, `ONEBOT_ACCESS_TOKEN`, `TENCENT_CLOUD_SECRET_*`, `PIXIV_PHPSESSID`,
      `IMAGE_SEARCHER_SAUCENAO_API_KEY`, etc.
- Database credentials are read via `src/database/config.py` from environment variables.
- `src/service/omega_api/` provides HMAC-signed API routes; verify signatures on any exposed HTTP endpoints.
- Be cautious with adapter-specific patches under `src/service` (`gocqhttp_addition_event_patch`,
  `gocqhttp_self_sent_patch`, `qq_guild_audit_patch`) - they modify event/permission behavior.
- Artwork and image plugins fetch external content; validate paths, avoid SSRF, and do not expose local filesystem
  paths.
- Use parameterized SQLAlchemy queries; do not concatenate raw SQL.
