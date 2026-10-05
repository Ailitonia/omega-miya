# Omega-Miya AGENTS.md

## Project Overview

Omega-Miya is a multi-platform chatbot built on [NoneBot2](https://github.com/nonebot/nonebot2). It supports OneBot V11,
Telegram, and Console adapters, and uses an async SQLAlchemy ORM layer with Alembic migrations over
MySQL/PostgreSQL/SQLite backends.

- **Language**: Python >= 3.12
- **Entry Point**: `bot.py` - thin launcher that delegates to `src/cli`. Use `python bot.py --run` to start the bot; the
  `--database-*` commands manage schema migrations (see "Database Migrations (Alembic)"); `--tool-execute
  <module>[:<func>]` runs an entry function of a module under `tools/` (defaults to `main` when `<func>` is omitted).
- **Package Manager**: Poetry (see `pyproject.toml`)
- **Config**: `.env` -> `.env.<ENVIRONMENT>` loaded by NoneBot2/Pydantic

## Main Modules

- `bot.py` - thin launcher; parses CLI arguments via `src/cli` and dispatches to the matching handler.
- `src/cli` - command-line interface.
    - `command.py` - argparse parser definition and the `CliQueryArguments` pydantic model.
    - `hanlder.py` (sic) - command dispatch. `run_bot` sets up logging, calls `nonebot.init()`, registers adapters
      conditionally from config (OneBot V11 / Telegram / Console), and loads `src/service` then `src/plugins`.
- `src/compat.py` - compatibility helpers, e.g. pydantic v2 URL `TypeAdapter`s and reusable `type` aliases.
- `src/exception.py` - `OmegaException` base class and the project exception hierarchy.
- `src/resource.py` - resource path abstraction. Defines `BaseResource` (plus `AnyResource`, `LogFileResource`,
  `StaticResource`, `TemporaryResource`) and the optional file-hosting `BaseResourceHostProtocol`.
- `src/database` - database layer.
    - `config.py` - reads `DATABASE` env and builds the SQLAlchemy async URL.
    - `connector.py` - creates `AsyncEngine` and `async_sessionmaker` on import.
    - `schema_base.py` - declarative base with constraint naming conventions.
    - `schema.py` - ORM table models.
  - `model.py` - DAL base classes (`BaseDataAccessLayer`, `BaseDataOutModel`).
    - `types.py` - cross-dialect column type variants (e.g. `IndexInt`).
    - `migrate.py` - Alembic command wrappers and the `check_migration_state()` safety check (`MigrationStatus`).
    - `internal/` - DALs (data access layers) for bot, entity, plugin, sign-in, subscriptions, etc.
    - `helpers.py` - startup hook runs the migration safety check and auto-upgrade (aborts startup on unsafe states);
      also provides session context utilities and the `DATABASE_SESSION` dependency.
- `src/service` - core services.
    - `omega_base` - core entity and platform abstraction layer, split into three parts:
        - `interface.py` - `OmegaEntityInterface` / `OmegaMatcherInterface`, the unified interfaces for invoking
          platform bot APIs outside Event/Matcher contexts.
        - `internal/` - `OmegaEntity` (DB-backed entity wrapper), the platform adapter registry
          (`ENTITY_TARGET_REGISTER` / `EVENT_DEPEND_REGISTER` over the `BaseEntityTarget` / `BaseEventDepend` base
          classes), online-bot tracking (`get_online_bots`), and custom bot lifecycle events.
        - `middlewares/` - per-platform implementations of those base classes (`console`, `onebot_v11`, `telegram`)
          that adapt nonebot adapters and their events onto the unified interfaces.
    - `omega_processor` - unified event/run pre- and post-processing, organized under `universal/` by concern (plugin
      manager, permission, cooldown, cost, rate limiting, history, statistic, friendship, cancellation).
    - `omega_api` - FastAPI sub-app mounting and HMAC-signed router utilities.
    - `omega_global_cache` - memory + DB-backed cache.
    - `omega_multibot_support` - multi-protocol bot tracking and response de-duplication.
    - `omega_message_context` - message context manager (`manager.py`) plus custom depends for extracting artwork
      data from messages (`custom_depends/`).
    - `omega_file_host` / `omega_short_link` - auxiliary HTTP services (file hosting, short links).
    - `apscheduler` - scheduled-job wrapper.
    - `artwork_proxy` / `artwork_collection` - artwork-site proxy and local collection DB.
    - `onebot_v11_addition_event_patch` / `onebot_v11_self_sent_patch` - adapter behavior patches.
- `src/params` - NoneBot dependency injectors, handlers, rules, and reusable templates.
    - `depends/entity_depends/` - new home (migrating in from the former `src/service/omega_base/depends`) of the
      `EVENT_*` / `USER_*` `Annotated` sub-dependencies for entity params, `OmegaEntity` instances, and the
      entity/matcher interfaces, plus the `get_entity_session*` context helpers. The migration is in progress:
      `depends/__init__.py` still re-exports from the removed `src.service.omega_base.depends` and the moved files
      keep relative imports from their old location, so `src.params.depends` does not import until they are rewired;
      `depends_tmp.py` is a scratchpad of `Annotated` DAL/session type aliases for the same effort, and a few
      `TYPE_CHECKING` imports still reference the removed `omega_base.middlewares.models`.
    - `handler.py` / `permission.py` / `rule.py` - reusable handlers, permission checks, and matcher rules.
    - `template/subscription_manager` - reusable subscription-manager template (manager + handlers).
- `src/utils` - external API clients and helpers: `bilibili_api`, `pixiv_api`, `weibo_api`, `booru_api`, `openai_api`,
  `nhentai` / `comic18`, `image_searcher`, `image_utils`, `omega_requests` / `omega_common_api`, `crypto`, etc.
- `src/plugins` - business plugins. Naming convention: `omega_*` are core/meta plugins, `onebot_v11_*` are OneBot
  V11-specific, and the rest are platform-agnostic.
- `alembic/` + `alembic.ini` - database migration scripts; the baseline revision policy is described below.
- `tools/` - standalone utility scripts (artwork downloader, old-version data migration, artwork rating GUI, etc.).
    - `fix_p0_unique_constraints` - repairs legacy duplicate rows and (re)creates the unique indexes on `sign_in` /
      `auth_setting`; run `python -m tools.fix_p0_unique_constraints` for a dry-run and `--apply` to execute (back
      up the database first).
- `tests/` - pytest suite (see "Testing Instructions"): `test_001_database` (migration state check, database init,
  per-table DAL CRUD, DAL execute), `test_002_core` (compat, resource, apscheduler, event patches, omega services,
  `OmegaEntity`, omega_base internals), `test_003_web` (HTTP client layer, external API clients, artwork proxy -
  against the local uvicorn test server), `test_004_utils` (crypto: key derivation, AES/ChaCha20 modes,
  authenticated envelopes), and `test_009_cli` (CLI `--tool-execute` entry, `extra_args` positional parsing and
  pass-through).
- `docs/` - documentation assets: `img/` holds images referenced by the README; `reference/` holds curated reference
  tutorials (see "Reference Documentation").

## Database Migrations (Alembic)

- Schema versions are managed by Alembic (`alembic.ini`, `alembic/versions/`). Until the 2.0 release (while on the
  `dev-2.0-database-breaking` line) the baseline revision (`69d603c01e0e_init_baseline_20260828`) MAY be edited
  in place for breaking schema changes (see `8ec0c16d`, `db385e29`); editing the baseline does not re-run it on
  databases already stamped at head, so every existing database (including the shared dev/test one) must be rebuilt
  afterwards: `python bot.py --database-downgrade base && python bot.py --database-upgrade-to-head`, or drop and
  re-create the database. After the 2.0 release the baseline is locked - never edit it; add new revisions instead.
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
- Linting (enforced): code must pass `ruff check` (rules configured in `pyproject.toml`) - this is the only
  mandatory style gate.
- Formatting (not enforced): `ruff format` is not used - do not run it over existing code. The codebase follows
  PyCharm's hanging-indent style (double-indent continuation lines), which differs from `ruff format` output;
  match the surrounding code style instead.
- Line length: 120 characters.
- String quotes: single quotes for inline strings.
- Imports: sorted and grouped; `E402` ignored for NoneBot adapter conditional imports.
- Follow existing patterns:
    - Pydantic v2 models.
    - Async SQLAlchemy 2.0.
    - NoneBot2 matcher/dependency patterns.
    - Place plugin business logic in `command.py`, `data_source.py`, `helpers.py`, etc.

## Testing Instructions

### Environment & Setup

- Test suite lives under `tests/` (pytest + nonebug + pytest-asyncio, `asyncio_mode = "auto"`, asyncio only - do
  not add anyio/trio backend parametrization or `@pytest.mark.anyio`; the suite pins one event-loop model).
- Test environment config comes from `.env.test` (`tests/conftest.py` sets `ENVIRONMENT=test`); external API calls
  should be mocked.
- Test modules are imported at collection time before NoneBot is initialized (nonebug initializes it in a session
  fixture), so `src.*` imports must stay inside fixtures/test functions. The same applies to fixture plugins: keep
  them out of collection (`collect_ignore` or no `test_` prefix), load them once per session in an autouse fixture
  after nonebug init (the `after_nonebot_init` pattern), and import their symbols inside test functions.
- `tests/conftest.py` auto-marks every async test with `loop_scope='session'` (shared event loop) and loads all of
  `src/service` after nonebug initializes NoneBot (`src/plugins` loading is commented out in `tests/conftest.py`
  until a test needs it).
- Never resolve async fixtures lazily via `request.getfixturevalue()` inside async tests or async fixtures: with the
  shared session event loop already running, pytest-asyncio would call `Runner.run()` on the running loop and raise
  `RuntimeError`. Declare async fixtures as parameters so they resolve during setup instead.
- `tests/conftest.py` also provides the session-scoped `database_schema_guard` fixture, pulled in by
  `after_nonebot_init` so it runs before nonebug's lifespan startup: it migrates the test database to the Alembic
  head at session start, and skips the whole suite (instead of hard-failing via `sys.exit` in the startup hook) when
  the database is unreachable or the migration state is unsafe.
- `tests/test_001_database` tests reuse the real database connection configured by `.env.test` and perform guarded
  DDL/DML (snapshot & restore `alembic_version`, create/drop sentinel tables). Never point the test environment at
  a production database.

### Writing Tests

- Fabricate events/messages through the shared factories (`tests/utils.py:make_fake_event` / `make_fake_message`;
  platform event builders live in `tests/test_002_core/helpers.py`) with per-test keyword overrides; never hand-roll
  `Event` subclasses per file, and never `unittest.mock` framework objects - fakes plus the real nonebot machinery
  give higher fidelity (`tests/test_002_core/helpers.py:make_mock_bot` is the documented exception for don't-care
  bot carriers).
- Drive matcher/handler flows through nonebug `App` contexts: `app.test_matcher(...)` +
  `ctx.receive_event(bot, event)` + `ctx.should_call_send(...)` / `ctx.should_call_api(...)`; assert *silence* by
  receiving an event with no expectation, and assert teardown after exiting the context.
- Unit-test custom `Annotated` depends (`src/params/depends/entity_depends/`) with `app.test_dependent`:
  `ctx.pass_params(...)` / `ctx.should_return(...)`, including the `TypeMisMatch` negative path fed by a wrong-type
  fabricated event.
- Test custom rules/permissions (and processors such as cooldown/cost) as parametrized truth tables that invoke the
  dependent directly against fabricated events, covering `None` attributes and non-matching event types.
- Prefer sync tests by default; write async tests only when entering a nonebug/matcher/API context.
- Assertion style: identity (`is`) for object passing, structural equality for state dicts, set-of-callables
  comparison for checker wiring, shared sentinels defined once in fixture plugins.
- Exercise real configuration effects via `.env.test` / `NONEBOT_INIT_KWARGS` instead of stubbing config; test
  config parsing against committed dotenv fixtures (defaults, JSON-typed values, aliases, precedence,
  malformed-value error).
- Test HTTP/network code against real local servers scoped to the test directory that needs them (port 0,
  background thread, `shutdown()`+`join()` teardown; `tests/test_003_web`'s uvicorn server is the model), asserting
  against echoed/reflected data - never external hosts, never suite-wide autouse servers.
- Assert error paths as exception + residual state: `pytest.raises(..., match=...)` pinning message fragments, then
  verify registries/state are restored and the session still works; capture swallowed-exception logs with a
  temporary loguru sink + `capsys`, removed in `finally`.
- Parametrize implementation variants through indirect fixtures that resolve a string path (`"pkg.mod:Class"` via
  `request.param`), open the test with an `isinstance` capability guard, and give params explicit readable `id=`.
- Gate version/platform-specific tests with `skipif(..., reason=...)`; express known upstream bugs as `xfail` with
  exact version ranges and issue links; keep version-gated fixture code in separate subtrees.
- Do not re-test framework internals (nonebot/SQLAlchemy/pydantic semantics themselves); test the project's own
  code through public APIs and the nonebug harness. Do not import or monkeypatch nonebot private internals
  (`nonebot.message._check_matcher`, `_event_preprocessors`, `Driver._bots`) - version-fragile; white-box only the
  project's own internals.
- Anchor fixture data files to `Path(__file__).parent`; never use CWD-relative paths.

### Isolation & Patching

- Snapshot and restore every global registry a test mutates (try/finally or a `_recover`-style decorator); prefer
  nonebug `app.provider.context({...})` to scope matcher-registry state, and assert cleanup (registries empty,
  flags reset) after each scenario - under the shared session event loop, leaked state surfaces in unrelated tests.
- Scope monkeypatches lexically with `pytest.MonkeyPatch.context()` inside the test body, patch the narrowest
  target (instance attribute > class attribute), and replace whole registries with fresh containers so
  registrations roll back automatically.
- Never monkeypatch attributes on process-shared modules - stdlib (`asyncio`, `random`, `time`, `os`, `sys`,
  `subprocess`, `zipfile`, ...) or third-party libraries (`py7zr`, `openpyxl`, ...) - whether through dotted paths
  such as `monkeypatch.setattr('src.utils.foo.asyncio.sleep', ...)` or directly on the module object such as
  `monkeypatch.setattr(zipfile, 'ZipFile', ...)`: `src.utils.foo.asyncio` IS the global `asyncio` module object, so
  this replaces `asyncio.sleep` process-wide for the duration of the test. With the shared session event loop,
  long-lived loop residents (e.g. the uvicorn `Server.main_loop` polling `asyncio.sleep(0.1)` from
  `tests/test_003_web`'s session-scoped `test_server`) can then crash mid-session and surface later as misleading
  teardown `ERROR`s attributed to unrelated tests. Instead, rebind the name inside the target module's namespace
  with a copied namespace - the ready-made helpers are `tests/utils.py:rebind_module_namespace` (generic) and
  `tests/test_003_web/helpers.py:patch_module_asyncio_sleep` / `patch_module_time` (specialized).
- Use sentinel-fail patches (replacement body is `pytest.fail(...)`) to prove a code path is *not* taken.
- Bound every concurrency wait (`asyncio.timeout` / `wait_for`) so deadlocks fail fast instead of hanging the
  session loop; never use settling sleeps (`asyncio.sleep` to "let tasks finish") - synchronize on explicit
  `asyncio.Event`s/task groups instead.
- Prefer composition-based fakes; never subclass a third-party client class with a bypassed `__init__`.

## Reference Documentation

Curated reference material lives under `docs/reference/`; consult the relevant document before working on each area:

- Testing: `k.1.1-pytest_fastapi_tutorial.md` (pytest basics with async FastAPI),
  `k.1.2-nonebot2_testing_tutorial.md` (unit-testing a NoneBot2 + SQLAlchemy project, mirrors this repo's setup),
  `g.1.3-nonebug_tutorial.md` (nonebug usage and best practices).
- Database: `k.2.1-sqlalchemy_async_tutorial.md` (async SQLAlchemy 2.0 patterns),
  `k.2.2-alembic_migration_tutorial.md` (Alembic versioned migrations),
  `k.2.3-nonebot2_alembic_startup_tutorial.md` (startup-time auto-migration, the approach implemented in
  `src/database/helpers.py`).
- Command/message handling: `g.3.1-learning_alconna.md` (nonebot-plugin-alconna source-level notes) and
  `g.3.2-alconna_tutorial.md` (developing plugins on alconna/uniseg, as used across `src/service` and
  `src/plugins`).

## Security Considerations

- **Secrets live in `.env`** and must never be committed.
    - `OMEGA_AES_KEY` (required to be non-empty: `src/utils/crypto` now rejects an empty value at startup, and changing
      it makes ciphertext written with the previous key undecryptable), `DB_PASSWORD`, `ONEBOT_ACCESS_TOKEN`,
      `TENCENT_CLOUD_SECRET_*`, `PIXIV_PHPSESSID`, `IMAGE_SEARCHER_SAUCENAO_API_KEY`, etc.
- Database credentials are read via `src/database/config.py` from environment variables.
- `src/service/omega_api/` provides HMAC-signed API routes; verify signatures on any exposed HTTP endpoints.
- Be cautious with adapter-specific patches under `src/service` (`onebot_v11_addition_event_patch`,
  `onebot_v11_self_sent_patch`) - they modify event/permission behavior.
- Artwork and image plugins fetch external content; validate paths, avoid SSRF, and do not expose local filesystem
  paths.
- Use parameterized SQLAlchemy queries; do not concatenate raw SQL.
