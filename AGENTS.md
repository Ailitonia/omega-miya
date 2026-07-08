# Omega-Miya AGENTS.md

## Project Overview

Omega-Miya is a multi-platform chatbot built on [NoneBot2](https://github.com/nonebot/nonebot2). It supports OneBot V11,
QQ (Open Platform), Telegram, and Console adapters, and uses an async SQLAlchemy ORM layer with MySQL/PostgreSQL/SQLite
backends.

- **Language**: Python >= 3.12
- **Entry Point**: `bot.py`
- **Package Manager**: Poetry (see `pyproject.toml`)
- **Config**: `.env` -> `.env.<ENVIRONMENT>` loaded by NoneBot2/Pydantic

## Main Modules

- `bot.py` - startup entry. Sets up logging, calls `nonebot.init()`, registers adapters conditionally, and loads
  `src/service` then `src/plugins`.
- `src/resource.py` - resource path abstraction. Defines `BaseResource`, `LogFileResource`, `StaticResource`,
  `TemporaryResource`, and optional file-hosting protocol.
- `src/database` - database layer.
    - `config.py` - reads `DATABASE` env and builds SQLAlchemy async URL.
    - `connector.py` - creates `AsyncEngine` and `async_sessionmaker` on import.
    - `schema*.py` / `model.py` - ORM base and models.
    - `internal/` - DALs (data access layers) for bot, entity, plugin, sign-in, subscriptions, etc.
    - `helpers.py` - startup/shutdown hooks and session context utilities.
- `src/service` - core services.
    - `omega_base` - entity wrappers, platform middleware, message/event types, dependency injectors.
    - `omega_processor` - unified permission, cooldown, cost, rate-limit, history, statistic, friendship processing.
    - `omega_api` - FastAPI sub-app mounting and HMAC-signed router utilities.
    - `omega_global_cache` - memory + DB-backed cache.
    - `omega_multibot_support` - multi-protocol bot tracking and response de-duplication.
    - `apscheduler` - scheduled-job wrapper.
    - `artwork_proxy` / `artwork_collection` - artwork-site proxy and local collection DB.
- `src/params` - NoneBot dependency injectors, handlers, rules, and reusable templates.
- `src/utils` - external API clients, image processing, HTTP request utilities, etc.
- `src/plugins` - business plugins (sign-in, monitors, image search, games, group management, etc.).

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

- **No test suite currently exists** in this repository.
- For automated testing, add tests under a `tests/` directory using `pytest` and mock external API calls / database
  sessions.

## Security Considerations

- **Secrets live in `.env`** and must never be committed.
    - `AES_KEY`, `DB_PASSWORD`, `ONEBOT_ACCESS_TOKEN`, `TENCENT_CLOUD_SECRET_*`, `PIXIV_PHPSESSID`,
      `IMAGE_SEARCHER_SAUCENAO_API_KEY`, etc.
- Database credentials are read via `src/database/config.py` from environment variables.
- `src/service/omega_api.py` provides HMAC-signed API routes; verify signatures on any exposed HTTP endpoints.
- Be cautious with adapter-specific patches under `src/service/*_patch*` - they modify event/permission behavior.
- Artwork and image plugins fetch external content; validate paths, avoid SSRF, and do not expose local filesystem
  paths.
- Use parameterized SQLAlchemy queries; do not concatenate raw SQL.
