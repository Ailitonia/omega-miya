# 为 NoneBot2（FastAPI 驱动）+ SQLAlchemy 项目编写单元测试：教程与最佳实践

> 目标读者：已经读过本系列第一篇《pytest 入门：以 FastAPI 为例讲解如何为异步框架编写单元测试》，或者已经掌握 pytest
> 基础（fixture、parametrize、异步测试、ASGITransport、dependency_overrides），现在想给一个真实的 NoneBot2 机器人项目补上测试的开发者。
>
> 本文中所有代码示例、命令输出、报错信息均在本地真实运行验证。凡是实测确认过的行为，文中都会明确标注「实测」。

## 一、前言：本篇要讲什么

上一篇我们解决了「给一个纯 FastAPI 应用写测试」的问题：用 httpx 的 `ASGITransport` 直驱 ASGI 应用、用 `dependency_overrides`
替换数据库依赖、用 pytest-asyncio 跑异步用例。这些技巧在 NoneBot2 项目里依然全部有效——但 NoneBot2 项目多出两类新东西，是通用
pytest 教程覆盖不到的：

1. **matcher（事件响应器）**：机器人的核心业务逻辑挂在 matcher 上，由「事件」驱动，而不是 HTTP 请求。它没有 URL、没有 request
   body，怎么测？答案是 NoneBot 官方配套的 pytest 插件 **nonebug**：它在测试进程内初始化一个完整的 NoneBot，提供假的
   Bot/Adapter 对象，让你把构造好的 OneBot 事件「喂」给 matcher，然后断言机器人调用了哪些 API、回复了什么内容。
2. **异步数据层**：插件通常用 SQLAlchemy 2.x 的异步 API（`create_async_engine` / `async_sessionmaker`）做持久化。数据层本身要测
   CRUD；更麻烦的是，matcher 测试和 HTTP 端点测试也必须跑在 **测试数据库**上，否则测试数据会写进生产库。

因此本篇的目标场景是一个三层齐全的最小项目——「便签机器人」：

- **数据层**：SQLAlchemy 2.x 异步风格，声明式模型 `Note(id, user_id, content, created_at)`，在 `driver.on_startup` 钩子里建表；
- **matcher 插件**：`note 添加 <内容>` / `note 列表` / `note 删除 <id>` 三个子命令；
- **HTTP 端点**：在 FastAPI 驱动上注册 `GET /api/notes`，与 matcher 共享同一数据层。

然后为它配齐三层测试，并解决贯穿全篇的真正难点： **测试隔离**——如何让三条入口（直接调 CRUD、nonebug 事件模拟、HTTP
请求）都作用在同一个测试数据库上，且用例之间互不影响、可乱序执行。

对 pytest 基础本身（fixture 的写法与作用域、`@pytest.mark.parametrize`、`ASGITransport` 的原理、`dependency_overrides`
），本文只做衔接性引用，细节请回看第一篇。

## 二、验证环境与版本表

### 2.1 本文实际使用的版本

以下每一个版本号都来自本文写作时本地环境的 `pip list` 输出，全部 18 个测试用例在这组版本下真实通过：

| 依赖                   | 版本    | 作用                                                 |
|------------------------|---------|------------------------------------------------------|
| Python                 | 3.12.12 | 解释器                                               |
| nonebot2               | 2.5.0   | 机器人框架本体（`[fastapi]` 额外依赖）               |
| nonebot-adapter-onebot | 2.4.6   | OneBot v11 适配器（构造消息事件用）                  |
| nonebug                | 0.4.4   | NoneBot 官方 pytest 测试插件                         |
| pytest                 | 9.1.1   | 测试框架本体                                         |
| pytest-asyncio         | 1.4.0   | 让 pytest 支持异步测试                               |
| pytest-cov             | 7.1.0   | 覆盖率统计                                           |
| SQLAlchemy             | 2.0.52  | 数据层 ORM（`[asyncio]` 额外依赖）                   |
| aiosqlite              | 0.22.1  | SQLite 的异步驱动                                    |
| fastapi                | 0.141.1 | NoneBot 的 FastAPI 驱动（随 nonebot2[fastapi] 安装） |
| httpx                  | 0.28.1  | 异步 HTTP 客户端（含 ASGITransport）                 |
| pydantic               | 2.13.4  | NoneBot/FastAPI 的数据校验依赖                       |

### 2.2 nonebug 的版本兼容性：实测结论

这是整个环境搭建中最容易翻车的地方，我把实测结论直接写在前面。

**nonebug 声明了什么？** 查看 nonebug 0.4.4 在 PyPI 上的依赖元数据，只有四条：

```
asgiref<4.0.0,>=3.8.0
async-asgi-testclient<2.0.0,>=1.4.8
nonebot2<3.0.0,>=2.3.0
pytest<10.0.0,>=7.0.0
```

注意两件事：第一，nonebug 只约束 `pytest >=7, <10`，对 pytest 9.x 是放行的；第二， **nonebug 并不直接依赖 pytest-asyncio**
——官方文档要求你自己安装 pytest-asyncio 或 anyio 之一来跑异步测试。也就是说 pytest-asyncio 的版本不受 pip
的依赖解析保护，装出什么版本全靠你自己控制，冲突不会体现在安装阶段，只会在运行测试时爆炸。

**与最新版是否冲突？实测分三种情况：**

1. **pytest 9.1.1 + pytest-asyncio 1.4.0 + nonebug 0.4.4：可以用，但有两个硬性前提。** 前提一，必须用
   `asyncio_mode = "auto"`。实测改成 strict 模式后，19 个用例全部在 setup 阶段报错（当时还没删调试文件，所以是 19 个）：

   ```
   ERROR at setup of test_list_notes_empty - Failed: '' requested an async
   fixture 'after_nonebot_init' with autouse=True, with no plugin or hook that
   handled it.
   ```

   原因是 nonebug 的核心 fixture（`after_nonebot_init`、`nonebug_init`）是用普通 `@pytest.fixture` 定义的 async
   fixture，strict 模式下 pytest-asyncio 不会接管未被显式声明的异步 fixture，pytest 本体又不认识 async fixture，于是直接报错。auto
   模式下 pytest-asyncio 会接管所有 async fixture 和 async 测试函数，问题解决。 前提二，需要把事件循环作用域提升为 session
   级（原因见 2.3 节），即：

   ```toml
   asyncio_default_fixture_loop_scope = "session"
   asyncio_default_test_loop_scope = "session"
   ```

2. **pytest-asyncio 0.21.x 与 nonebug 0.4.4 直接冲突。** 很多老教程和老项目把 pytest-asyncio 钉在 0.21.x（因为当时 nonebug
   的 CI 用它），实测 0.21.2 + nonebug 0.4.4 会在每个用例 setup 时抛：

   ```
   Failed: ScopeMismatch: You tried to access the function scoped fixture
   event_loop with a session scoped request object.
   Requesting fixture stack:
   tests/conftest.py:15:  def after_nonebot_init(_nonebot_init: None)
   ```

   原因：0.21.x 只有一个 function 级的 `event_loop` fixture，而 nonebug 的异步 fixture 是 session 级的，pytest 不允许
   session 级 fixture 依赖 function 级 fixture。如果你身处被钉死在 0.21.x 的老项目， **实测可用的解法**是在自己的
   conftest.py 里把事件循环提升为 session 级（0.21.x 时代此写法仅触发 DeprecationWarning，不影响运行）：

   ```python
   @pytest.fixture(scope="session")
   def event_loop():
       import asyncio
       loop = asyncio.new_event_loop()
       yield loop
       loop.close()
   ```

   实测加上这个 fixture 后，pytest 9.1.1 + pytest-asyncio 0.21.2 + nonebug 0.4.4 全部 18 个用例通过（伴随 2 条 warning）。

3. **推荐结论**：新项目直接使用本文的版本组合——pytest 9.1.1 + pytest-asyncio 1.4.0 + nonebug 0.4.4，配置 auto 模式 +
   session 级循环作用域，无需任何 workaround。这也是本文全部示例实际运行的组合。

**为什么要钉版本？** 上面三组实测说明：nonebug + pytest-asyncio 的可用性由「pytest 主版本 × pytest-asyncio 主版本 ×
配置写法」三个变量共同决定，且 pip 不会替你挡住冲突。所以在 pyproject.toml / requirements 里把这三者 **钉到次版本**（如
`pytest-asyncio ~= 1.4.0`），并在 CI 里跑完整测试套件，是防止「同事机器上能跑、CI 上爆炸」的唯一可靠办法。

### 2.3 为什么必须配置 session 级事件循环

pytest-asyncio 1.x 的默认行为是：每个测试函数一个全新的事件循环（`asyncio_default_test_loop_scope=function`），async fixture
默认同理。这个默认对普通项目很安全，但对「nonebug + 内存数据库」的组合是灾难，实测不配 session 作用域时 4 个用例失败，典型报错：

```
sqlalchemy.exc.InvalidRequestError: Could not refresh instance '<Note at 0x7f...>'
```

链条是这样的：nonebug 的 `nonebug_init` 是 session 级 async fixture，它在自己的事件循环里执行 driver
启动钩子（我们的建表钩子就在其中），内存数据库的连接在这个循环里被创建；而测试函数在另一个 function 级循环里运行，复用同一个
aiosqlite 连接时，连接内部的 Future 绑定在旧循环上，COMMIT 等操作无法正常完成，表现为「插入看似成功、紧跟着的 SELECT
却查不到行」这类诡异症状。把 fixture 与测试的循环作用域都设为 session 后， **整个测试会话只有一个事件循环**
，启动钩子、fixture、测试函数全部在同一个循环里顺序执行，问题彻底消失，实测 18 个用例全部通过。

顺带说明：这个配置还有一个工程上的好处——整个会话共用一个循环，意味着 SQLAlchemy 连接池、nonebug 的假 Bot
状态都只在会话开始时初始化一次，测试速度更快（本文 18 个用例总耗时约 1 秒）。

## 三、示例项目：便签机器人

### 3.1 目录结构

项目结构遵循 NoneBot2 官方推荐布局（`pyproject.toml` + `.env` + `bot.py` + 插件包），可以用 `nb create`
生成后改造，也可以手动建立——本文采用手动方式，便于看清每个文件的作用：

```
notebot/
├── pyproject.toml            # 项目元数据 + nonebot 插件声明 + pytest 配置
├── .env                      # 公共环境变量（驱动选择）
├── .env.prod                 # 生产环境变量（数据库地址）
├── bot.py                    # 机器人入口
├── notebot/                  # 应用代码包
│   ├── __init__.py
│   ├── datastore/
│   │   ├── __init__.py
│   │   └── notes.py          # 数据层：模型 + 引擎管理 + CRUD
│   └── plugins/
│       ├── __init__.py
│       └── note/
│           └── __init__.py   # 插件：note 命令 + /api/notes 端点
└── tests/                    # 测试代码
    ├── __init__.py
    ├── conftest.py           # 测试基建（本文核心）
    ├── test_datastore.py     # 数据层测试
    ├── test_matcher.py       # matcher 测试（nonebug）
    └── test_api.py           # HTTP 端点测试
```

### 3.2 pyproject.toml

```toml
[project]
name = "notebot"
version = "0.1.0"
description = "便签机器人示例项目"
requires-python = ">=3.10"
dependencies = [
    "nonebot2[fastapi]>=2.4.0",
    "nonebot-adapter-onebot>=2.4.0",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.20",
]

[tool.nonebot]
plugins = ["notebot.plugins.note"]
plugin_dirs = []
builtin_plugins = []

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
pythonpath = ["."]
addopts = "-v"
```

三个 `[tool.pytest.ini_options]` 键都值得解释：

- `asyncio_mode = "auto"`：2.2 节实测结论，nonebug 的 async fixture 要求 auto 模式；同时我们的测试函数也不用再逐个加
  `@pytest.mark.asyncio`。
- 两行 `asyncio_default_*_loop_scope = "session"`：2.3 节实测结论，保证整个会话共用一个事件循环。
- `pythonpath = ["."]`：让测试可以直接 `import notebot.xxx`。这是 pytest 7+ 的内置选项，等价于把项目根目录加入 `sys.path`
  ，比往 conftest 里写 `sys.path.insert` 干净。

### 3.3 环境变量与入口

`.env`（所有环境共享，选择 FastAPI 驱动）：

```dotenv
DRIVER=~fastapi
```

`.env.prod`（生产数据库地址；实测 `nonebot.init()` 默认按 prod 环境加载，日志会打印 `Current Env: prod`）：

```dotenv
NOTE_DATABASE_URL=sqlite+aiosqlite:///notes.db
```

`bot.py`：

```python
"""机器人入口：nb run 或 python bot.py 启动"""

import nonebot
from nonebot.adapters.onebot.v11 import Adapter

# 初始化必须在任何插件/适配器导入使用之前
nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

nonebot.load_plugin("notebot.plugins.note")

if __name__ == "__main__":
    nonebot.run()
```

注意注释里那句话——「init 必须在导入插件之前」不是风格建议，而是硬性约束：`nonebot.load_plugin()`、`nonebot.get_driver()` 在
init 之前调用会直接抛 `ValueError: NoneBot has not been initialized.`。这个约束在测试里会以更隐蔽的方式咬人，第四章详解。

### 3.4 数据层 `notebot/datastore/notes.py`

这是全项目唯一「有状态」的模块，设计目标是 **一句话就能把整套应用切换到测试数据库**：

```python
"""便签数据层：SQLAlchemy 2.x 异步风格。

设计要点：
1. engine / session_factory 是模块级全局变量，通过 init_engine() 初始化。
   测试代码只需在 nonebot 启动钩子执行前调用 init_engine(测试库地址)，
   即可把整个应用（matcher + HTTP 端点）切换至测试数据库。
2. 建表通过 driver.on_startup 钩子完成，应用与测试环境行为一致。
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from nonebot import get_driver
from sqlalchemy import DateTime, String, delete, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

driver = get_driver()  # 本模块只允许在 nonebot.init() 之后导入


class Base(DeclarativeBase):
    """声明式基类"""


class Note(Base):
    """便签表"""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# ---- 引擎与会话工厂（可被测试替换的全局状态） ----

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(url: str, **kwargs) -> AsyncEngine:
    """初始化（或替换）全局 engine 与会话工厂。

    测试通过调用本函数把数据层切换到测试数据库。
    """
    global _engine, _session_factory
    _engine = create_async_engine(url, **kwargs)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def close_engine() -> None:
    """释放引擎资源（测试结束时调用）"""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        # 默认使用配置文件中的数据库地址（生产环境路径）
        url = getattr(driver.config, "note_database_url", None) or (
            "sqlite+aiosqlite:///notes.db"
        )
        return init_engine(url)
    return _engine


@asynccontextmanager
async def new_session() -> AsyncGenerator[AsyncSession, None]:
    """以异步上下文管理器方式获取会话。

    注意：必须用 async with 使用，保证会话在退出时立即关闭。
    （不要用 async for 消费 async generator 后提前 return ——
    那样会话的关闭会被推迟到垃圾回收，配合 StaticPool 单连接
    会导致多个会话共用同一连接、事务错乱。）
    """
    get_engine()  # 确保已初始化
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session


@driver.on_startup
async def _create_tables() -> None:
    """应用启动时建表（幂等）。nonebug 会执行启动钩子，测试环境同样生效。"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---- CRUD 函数 ----


async def add_note(user_id: str, content: str) -> Note:
    """新增便签，返回带 id 的持久化对象"""
    async with new_session() as session:
        note = Note(user_id=user_id, content=content)
        session.add(note)
        await session.commit()
        await session.refresh(note)
        return note


async def list_notes(user_id: str) -> list[Note]:
    """按用户查询全部便签，按 id 升序"""
    async with new_session() as session:
        result = await session.scalars(
            select(Note).where(Note.user_id == user_id).order_by(Note.id)
        )
        return list(result.all())


async def delete_note(user_id: str, note_id: int) -> bool:
    """删除指定 id 的便签（仅限本人），返回是否真的删掉了"""
    async with new_session() as session:
        result = await session.execute(
            delete(Note).where(Note.id == note_id, Note.user_id == user_id)
        )
        await session.commit()
        return result.rowcount > 0
```

几个设计决策背后的原因：

- **`init_engine()` 是唯一的引擎入口**。生产环境由 `get_engine()` 惰性调用它（读 `.env.prod` 里的 `NOTE_DATABASE_URL`
  ），测试环境由 conftest 显式调用它（传入内存库地址）。matcher 和 HTTP 端点都只认模块级全局的 `_session_factory`
  ，所以替换一次全局引擎，两条入口同时被切换——这是后文「测试隔离」的支点。
- **`@driver.on_startup` 建表而不是在引擎创建时建表**。NoneBot 的驱动生命周期由框架管理，启动钩子是建表的官方位置；更重要的是，nonebug
  在测试中会真实执行启动钩子（第四章），因此测试环境的建表路径与生产 **完全一致**，不存在「测试里手工建表、生产里用钩子」两条路径
  diverge 的风险。
- **`new_session()` 用 `@asynccontextmanager` 而不是裸 async generator**。这是本文实测踩出来的坑：最初的写法是
  `async def get_session(): ... yield session` 配合 `async for session in get_session(): ... return`，结果 `return` 会让
  async generator 的收尾（session 关闭、连接归还）推迟到垃圾回收，配合 StaticPool 的单连接复用，后一个会话拿到前一个还没关闭的连接，事务状态错乱，实测报
  `InvalidRequestError: Could not refresh instance`。改成 `async with` 后，session 的关闭是结构化的、确定的。这个坑细节多，FAQ
  里还会再讲。
- **`expire_on_commit=False`**：commit 后对象属性不过期，`note.id`、`note.content` 可以继续在响应里用，避免触发额外的惰性加载（异步会话里惰性加载会抛
  `MissingGreenlet`）。

### 3.5 插件 `notebot/plugins/note/__init__.py`

```python
"""便签插件：note 命令 + /api/notes HTTP 端点。

两者共享同一个数据层（notebot.datastore.notes），
因此测试替换数据层后，两条入口都会作用于测试数据库。
"""

import nonebot
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.drivers import ASGIMixin
from nonebot.params import CommandArg

from ...datastore.notes import add_note, delete_note, list_notes

note_cmd = on_command("note", priority=5, block=True)

USAGE = "用法：note 添加 <内容> / note 列表 / note 删除 <id>"


@note_cmd.handle()
async def handle_note(event: MessageEvent, args: Message = CommandArg()):
    """解析子命令并调用数据层"""
    text = args.extract_plain_text().strip()
    user_id = str(event.get_user_id())

    if text.startswith("添加"):
        content = text.removeprefix("添加").strip()
        if not content:
            await note_cmd.finish("添加失败：内容不能为空\n" + USAGE)
        note = await add_note(user_id, content)
        await note_cmd.finish(f"已添加便签 #{note.id}：{note.content}")

    if text.startswith("列表"):
        notes = await list_notes(user_id)
        if not notes:
            await note_cmd.finish("你还没有任何便签")
        lines = [f"#{n.id} {n.content}" for n in notes]
        await note_cmd.finish("你的便签：\n" + "\n".join(lines))

    if text.startswith("删除"):
        id_text = text.removeprefix("删除").strip()
        if not id_text.isdigit():
            await note_cmd.finish("删除失败：请提供数字 id\n" + USAGE)
        deleted = await delete_note(user_id, int(id_text))
        if deleted:
            await note_cmd.finish(f"已删除便签 #{id_text}")
        else:
            await note_cmd.finish(f"便签 #{id_text} 不存在")

    await note_cmd.finish("未知子命令\n" + USAGE)


# ---- FastAPI 端点：与 matcher 共享数据层 ----

driver = nonebot.get_driver()

if isinstance(driver, ASGIMixin):
    app = nonebot.get_app()  # 拿到驱动内部的 FastAPI 实例

    @app.get("/api/notes")
    async def api_list_notes(user_id: str):
        """查询指定用户的全部便签"""
        notes = await list_notes(user_id)
        return {
            "count": len(notes),
            "notes": [
                {
                    "id": n.id,
                    "user_id": n.user_id,
                    "content": n.content,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notes
            ],
        }
```

两个值得注意的点：

- `matcher.finish()` 会抛出内部异常来终止处理流程，所以每个分支后面不需要 `else`——执行到 `finish`
  就必定结束。这也让「每个分支恰好回复一次」成为可以用 nonebug 精确断言的行为。
- HTTP 端点用 `nonebot.get_app()` 拿到驱动内部的 FastAPI 实例直接 `@app.get` 注册。它和普通 FastAPI 路由没有任何区别——这意味着第一篇里讲的
  `ASGITransport` 测试法原样适用，第七章会用到。`isinstance(driver, ASGIMixin)` 判断保证在非 ASGI 驱动（如纯 aiocqhttp
  正向连接场景）下插件仍可加载。

## 四、测试基建：conftest.py 详解

### 4.1 完整代码

```python
"""测试基建：nonebot 初始化、插件加载、测试数据库切换、事件工厂。

fixture 分层：
- after_nonebot_init（session 级，覆盖 nonebug 同名 fixture）：
  nonebot.init() 已完成 -> 加载插件 -> 切换测试数据库 -> （启动钩子自动建表）
- reset_notes_table（function 级，autouse）：每个用例前清表，保证用例隔离
- make_private_message_event（function 级）：OneBot v11 私聊消息事件工厂
"""

import itertools

import pytest


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(_nonebot_init: None):
    """覆盖 nonebug 提供的同名空 fixture。

    执行时机：nonebot.init() 之后、driver 启动钩子（含建表）之前。
    """
    import nonebot
    from sqlalchemy.pool import StaticPool

    # 1. 此时 nonebot.init() 已执行完毕，加载插件才不会抛 ValueError
    nonebot.load_plugin("notebot.plugins.note")

    # 2. 把数据层切换到测试专用内存数据库（StaticPool 保证跨连接共享同一内存库）
    from notebot.datastore import notes

    notes.init_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    yield
    await notes.close_engine()


@pytest.fixture(autouse=True)
async def reset_notes_table(nonebug_init: None):
    """每个用例执行前重建表，保证用例互不影响、可乱序执行。

    依赖 nonebug_init 是为了保证在启动钩子建表之后再执行清表。
    """
    from notebot.datastore.notes import Base, get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
def make_private_message_event():
    """OneBot v11 私聊消息事件工厂：传入文本即可得到一个合法事件"""
    from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent

    counter = itertools.count(1)

    def _make(text: str, user_id: int = 123456) -> PrivateMessageEvent:
        return PrivateMessageEvent(
            time=1700000000,
            self_id=987654321,  # 机器人自身 QQ 号
            post_type="message",
            message_type="private",
            sub_type="friend",
            user_id=user_id,
            message_id=next(counter),
            message=Message(text),
            raw_message=text,
            font=0,
            sender={"user_id": user_id, "nickname": "测试用户"},
        )

    return _make


@pytest.fixture
def notes_db(nonebug_init: None):
    """延迟导入数据层模块。

    数据层模块在导入时调用 get_driver()，必须等 nonebug 完成 nonebot.init()
    之后才能导入，所以不能写在测试文件顶部，而要通过 fixture 延迟导入。
    """
    from notebot.datastore import notes

    return notes
```

### 4.2 nonebug 的初始化时序：为什么 import 顺序会咬人

要理解这份 conftest，必须先理解 pytest 的两个阶段和 nonebug 在其中的位置：

1. **收集阶段（collection）**：pytest import 所有 `test_*.py` 模块，找出测试函数。此时 **没有任何 fixture 被执行**。
2. **执行阶段（setup/call/teardown）**：按依赖图执行 fixture 和测试。

nonebug 安装后自动注册为 pytest 插件，提供一串 session 级 autouse fixture，简化后的链条是：

```
_nonebot_init      → 调用 nonebot.init(**可配置的 kwargs)
after_nonebot_init → 空 fixture，专门留给用户覆盖
nonebug_init       → 执行 driver 启动/关闭钩子（lifespan）
app                → 返回 nonebug.App 测试入口对象
```

关键点一： **`nonebot.init()` 是在执行阶段、由 `_nonebot_init` fixture 完成的**。因此收集阶段整个进程里 NoneBot
尚未初始化。如果你的测试文件顶部写 `from notebot.datastore import notes`，收集阶段就会触发模块里的 `get_driver()`，实测报错：

```
ERROR tests/test_datastore.py - ValueError: NoneBot has not been initialized.
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

整个测试会话在收集阶段就被打断，一个用例都跑不了。解法就是 NoneBot 官方文档反复强调的写法： **把对 nonebot 相关模块的
import 推迟到 fixture 或测试函数内部**。本文的 conftest 里所有 `import nonebot`、`from notebot... import ...`
全部写在函数体内，测试文件里需要数据层模块时通过 `notes_db` fixture 间接获取。这不是丑，是这个生态的既定惯例，写几次就习惯了。

关键点二： **`after_nonebot_init` 是 nonebug 预留的扩展点**。nonebug 自己定义了一个什么都不做的同名 session fixture，
`nonebug_init` 依赖它。pytest 的 fixture 覆盖规则是「同名 fixture，离测试目录近的覆盖远的（conftest 覆盖插件）」，所以我们在
tests/conftest.py 里重新定义它，就精确地获得了「init 已完成、lifespan 尚未执行」这个时间点——加载插件、切换测试引擎这两件必须在这个窗口做的事都放这里。

关键点三： **`nonebug_init` 会真实执行 driver 的启动钩子**。nonebug 的源码里，如果 driver 是 ASGIMixin（我们就是 FastAPI
驱动），它用 `async-asgi-testclient` 包住 `driver.asgi` 并进入其 lifespan 上下文，于是 `@driver.on_startup`
注册的建表钩子真实执行。这就是为什么测试环境不需要手工建表——启动路径和生产完全一致，差异只有「引擎指向哪个数据库」这一个变量。

### 4.3 内存 SQLite 的两个经典问题与解法

选择 `sqlite+aiosqlite:///:memory:` 做测试库时有两个广为人知的坑，本文都实测踩过：

**问题一：内存库不跨连接共享。** SQLite 的 `:memory:` 数据库生命周期绑定在单个连接上，连接关闭即消失；两个连接各自看到的是两个独立的空库。SQLAlchemy
默认连接池会按需开新连接，于是「建表用连接 A、插入用连接 B」时直接 `no such table`。解法是 `poolclass=StaticPool`：整个引擎只维护
**一条**连接并反复复用，所有会话看到同一个内存库。`connect_args={"check_same_thread": False}` 则是因为 SQLAlchemy
的异步包装在内部跨线程使用连接，需要关掉 sqlite3 的线程检查。

**问题二：连接绑定事件循环。** aiosqlite 的连接对象内部有绑定到创建时事件循环的 Future/锁。2.3 节已经讲过：不配 session
级循环作用域时，session 级 fixture 的循环和测试函数的循环不同，跨循环复用连接会出现「commit 后查不到行」的诡异失败（实测报
`InvalidRequestError: Could not refresh instance`）。解法就是配置里的两行 `asyncio_default_*_loop_scope = "session"`
，让全会话共用一个循环。

如果你不愿意调整循环作用域，替代方案是每个用例用 `tmp_path` 建独立文件库 + `poolclass=NullPool`
（连接用完即关、随用随建，天然规避跨循环复用），代价是慢一些。本文实测走的是 StaticPool + 单循环路线，速度最快（18 用例约 1 秒）。

### 4.4 reset_notes_table：用例级隔离

session 级 fixture 负责「换库」，function 级 autouse fixture 负责「清库」：每个用例前 drop_all +
create_all，用例之间完全隔离。实测验证：把三个测试文件故意打乱顺序执行——

```bash
$ python -m pytest tests/test_matcher.py tests/test_api.py tests/test_datastore.py -q
================== 18 passed in 1.02s ==================
```

依然全部通过。能乱序执行是「用例间无隐式依赖」的最强证据，CI 里可以放心开 `pytest-randomly` 之类的乱序插件。

为什么用 drop/create 而不是 `DELETE FROM notes`？drop/create 同时重置了自增主键计数，用例里才能稳定断言 `note.id == 1`
；DELETE 不会重置 SQLite 的自增序列（除非再清 `sqlite_sequence`），断言会变得脆弱。

## 五、数据层测试

数据层测试是最传统的一层：不经过 matcher、不经过 HTTP，直接调 CRUD 函数断言结果。它的价值在于 **定位精度**——matcher
测试失败时你不知道是事件解析错了、命令路由错了还是 SQL 错了；数据层测试全绿则可以直接排除最后一环。

```python
"""数据层单元测试：直接测 CRUD 函数。

测试引擎由 conftest 的 after_nonebot_init fixture 切换为内存 SQLite，
reset_notes_table fixture 保证每个用例拿到一张空表。
"""

import pytest


async def test_add_and_list_notes(notes_db):
    notes = notes_db
    note = await notes.add_note("user_a", "买牛奶")
    assert note.id == 1  # 自增主键从 1 开始（表是刚重建的）
    assert note.user_id == "user_a"

    await notes.add_note("user_a", "写周报")
    await notes.add_note("user_b", "别人的便签")

    result = await notes.list_notes("user_a")
    assert [n.content for n in result] == ["买牛奶", "写周报"]


async def test_list_notes_empty(notes_db):
    notes = notes_db
    assert await notes.list_notes("nobody") == []


async def test_delete_note(notes_db):
    notes = notes_db
    note = await notes.add_note("user_a", "待删除")
    assert await notes.delete_note("user_a", note.id) is True
    assert await notes.list_notes("user_a") == []
    # 再删一次：不存在，返回 False
    assert await notes.delete_note("user_a", note.id) is False


async def test_delete_note_wrong_user(notes_db):
    notes = notes_db
    note = await notes.add_note("user_a", "私有便签")
    # user_b 无权删除 user_a 的便签
    assert await notes.delete_note("user_b", note.id) is False
    assert len(await notes.list_notes("user_a")) == 1


@pytest.mark.parametrize("bad_id", [0, -1, 9999])
async def test_delete_note_id_not_exist(notes_db, bad_id: int):
    notes = notes_db
    assert await notes.delete_note("user_a", bad_id) is False
```

写作要点：

- **每个用例只依赖 `notes_db` fixture 拿到数据层模块**，底层串起了整条基建链：
  `notes_db → nonebug_init → after_nonebot_init → _nonebot_init`，加上 autouse 的 `reset_notes_table` 保证空表起步。auto
  模式下 async 测试函数无需任何装饰器。
- **断言要落在「可观测语义」上**：`delete_note` 返回 `bool` 表示「是否真的删掉了」，测试就断言 `is True` / `is False` 这个语义，顺便用
  `list_notes` 验证最终状态。「越权删除」和「id 不存在」是两个不同的异常分支，分开测。
- `parametrize` 把 0、-1、9999 三种坏 id 折叠成一个用例模板，这是第一篇讲过的技巧，这里用在异步函数上没有任何区别。

这一层共 7 个用例（含参数化展开），全部实测通过。

## 六、用 nonebug 测试 matcher

### 6.1 App fixture 与测试上下文的模型

nonebug 的核心是 `app` fixture 返回的 `App` 对象。测试 matcher 的固定套路是：

```python
async with app.test_matcher(note_cmd) as ctx:
    ...
```

`test_matcher()` 创建一个 **matcher 测试上下文**，它做了两件大事：

1. **打桩**：通过 monkeypatch 把 Matcher 类的 `send`/`finish`/`reject`/`pause` 等行为替换为「先查断言表再执行」的版本，并把适配器的
   `_call_api` 替换为假实现—— **整个上下文期间没有任何真实网络通信**，机器人「发消息」实际是把调用记录交给 nonebug 校验。
2. **编排**：`async with` 的退出阶段才是真正执行 `nonebot.message.handle_event()` 的时刻。你在 `with` 块内写的代码是「剧本」：先
   `receive_event` 投递事件，再用 `should_*` 系列方法登记期望；退出时 nonebug 按剧本逐条比对，任何一条不符即 `pytest.fail`。

这个「先录剧本、退出时统一回放校验」的模型和直觉相反，是 nonebug 新手最容易困惑的地方，值得专门记住。

### 6.2 创建假 Bot 与构造 OneBot v11 事件

```python
adapter = ctx.create_adapter(base=Adapter)  # base 传 OneBot v11 的 Adapter
bot = ctx.create_bot(base=Bot, adapter=adapter)  # base 传 OneBot v11 的 Bot
```

`create_adapter`/`create_bot` 在你给的适配器/机器人类之上动态生成一个 Fake 子类：Bot 的 `send` 被替换为「和断言表比对」，Adapter
的 `_call_api` 同理。除此之外它们的行为与真实子类一致（事件模型校验、消息对象等都是真的）。

事件则是直接用适配器的事件模型构造的 pydantic 对象。OneBot v11 私聊消息的必填字段较多（`time`、`self_id`、`post_type`、
`message_type`、`sub_type`、`user_id`、`message_id`、`message`、`raw_message`、`font`、`sender`），手写一遍又臭又长，所以 conftest
里提供了 `make_private_message_event` 工厂 fixture，测试里一句 `make_private_message_event("/note 添加 买牛奶")`
即可。注意命令默认前缀是 `/`（NoneBot 内置配置 `command_start` 的默认值），所以消息文本必须写成 `/note ...`。

### 6.3 完整测试代码

```python
"""matcher 测试：用 nonebug 的 App fixture 模拟完整的消息处理流程。

每个用例的模式一致：
1. async with app.test_matcher(note_cmd) as ctx 进入 matcher 测试上下文
2. ctx.create_adapter / ctx.create_bot 创建假的适配器与机器人
3. ctx.receive_event(bot, event) 投递事件
4. ctx.should_call_send(...) 断言机器人回复内容
5. ctx.should_finished(...) 断言 matcher 结束会话
6. 上下文退出后，直接查测试数据库验证持久化结果
"""

from nonebug import App


async def test_add_note(app: App, make_private_message_event):
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.datastore.notes import list_notes
    from notebot.plugins.note import note_cmd

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event("/note 添加 买牛奶")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已添加便签 #1：买牛奶", result=None)
        ctx.should_finished(note_cmd)

    # 关键：回复只是表象，必须验证数据真的写进了测试库
    notes = await list_notes("123456")
    assert len(notes) == 1
    assert notes[0].content == "买牛奶"


async def test_add_note_empty_content(app: App, make_private_message_event):
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.plugins.note import USAGE, note_cmd

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event("/note 添加")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "添加失败：内容不能为空\n" + USAGE, result=None)
        ctx.should_finished(note_cmd)


async def test_list_notes(app: App, make_private_message_event):
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.datastore.notes import add_note
    from notebot.plugins.note import note_cmd

    # 准备数据：两条属于 123456，一条属于别人
    await add_note("123456", "买牛奶")
    await add_note("123456", "写周报")
    await add_note("999999", "别人的便签")

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event("/note 列表")
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "你的便签：\n#1 买牛奶\n#2 写周报", result=None
        )
        ctx.should_finished(note_cmd)


async def test_list_notes_empty(app: App, make_private_message_event):
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.plugins.note import note_cmd

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event("/note 列表")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你还没有任何便签", result=None)
        ctx.should_finished(note_cmd)


async def test_delete_note(app: App, make_private_message_event):
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.datastore.notes import add_note, list_notes
    from notebot.plugins.note import note_cmd

    note = await add_note("123456", "待删除")

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event(f"/note 删除 {note.id}")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, f"已删除便签 #{note.id}", result=None)
        ctx.should_finished(note_cmd)

    assert await list_notes("123456") == []


async def test_delete_note_not_exist(app: App, make_private_message_event):
    """异常分支：删除不存在的 id"""
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.plugins.note import note_cmd

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event("/note 删除 999")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "便签 #999 不存在", result=None)
        ctx.should_finished(note_cmd)


async def test_delete_note_not_a_number(app: App, make_private_message_event):
    """异常分支：id 不是数字"""
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.plugins.note import USAGE, note_cmd

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event("/note 删除 abc")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "删除失败：请提供数字 id\n" + USAGE, result=None)
        ctx.should_finished(note_cmd)


async def test_unknown_subcommand(app: App, make_private_message_event):
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.plugins.note import USAGE, note_cmd

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event("/note 你好")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "未知子命令\n" + USAGE, result=None)
        ctx.should_finished(note_cmd)
```

### 6.4 逐点讲解

**`should_call_send(event, message, result=None)`**：登记「处理这个事件时，matcher 应该调用一次 `bot.send`，消息内容等于
message」。`result` 是假 send 的返回值（matcher 里 `await finish()` 等不到返回值时填 `None`）。注意两点：第一，message
直接写纯字符串即可，nonebug 比对的是 `matcher.finish("文本")` 传进 send 的原始对象，本文实测字符串精确匹配（含 `\n`
）工作正常；第二， **内容是完全相等比对**，差一个字符就失败。实测把期望改成 `"已添加便签 买牛奶"`（漏了 `#1：`）后失败信息为：

```
Failed: Application got send call with message 已添加便签 #1：买牛奶 but expected 已添加便签 买牛奶
```

（外层还会包一层 anyio TaskGroup 的 ExceptionGroup traceback，因为 `handle_event` 在任务组里并发跑 matcher，真正的失败原因要往
traceback 里层找这条 `Failed:` 信息。）

**`should_finished(note_cmd)`**：断言 matcher 对这条事件以 `finish` 结束（即会话终止、不再响应后续消息）。同族还有
`should_rejected`（拒绝，等待下一条输入）、`should_paused`（暂停）。因为插件每个分支都以 `finish` 收尾，所以本文全部用
`should_finished`。如果不登记任何 should_*，matcher 的行为将不被校验，测试失去意义。

**数据落库断言放在 `async with` 之外**：上下文退出后，事件已处理完毕，直接调数据层 `list_notes("123456")`
查测试库。「回复内容正确」和「数据真的写进去了」是两个独立断言，缺一不可——只测回复的话，把 `add_note` 换成 `pass`
测试照样绿。这层断言正是「matcher 测试跑在测试数据库上」的直接体现：如果测试引擎没换掉，这里读到的将是生产库。

**事件里的 user_id 与 self_id**：`make_private_message_event` 默认 `user_id=123456`（发消息的人）、`self_id=987654321`
（机器人自身）。matcher 里 `event.get_user_id()` 取的是前者，所以数据归属断言围绕 `"123456"` 展开；`test_list_notes` 里预先插入一条
`999999` 的数据，顺便验证了「只列本人的便签」这个业务规则。

本章 8 个用例覆盖了三个子命令的正常分支与四个异常分支（空内容、空列表、删除不存在的 id、id 非数字、未知子命令），全部实测通过。

## 七、HTTP 端点测试

### 7.1 思路

第一篇已经讲过核心模式：`httpx.AsyncClient(transport=ASGITransport(app=...))` 直接在进程内驱动 ASGI 应用，不起真实端口。套到
NoneBot 上唯一的区别是 app 从哪来——`nonebot.get_app()` 返回 FastAPI 驱动内部的 FastAPI 实例，插件注册的 `/api/notes`
就在上面。

### 7.2 完整测试代码

```python
"""HTTP 端点测试：httpx.AsyncClient + ASGITransport 直驱 FastAPI app。

nonebot.get_app() 返回驱动内部的 FastAPI 实例，
插件在上面注册的 /api/notes 与 matcher 共享同一数据层。
"""

import httpx
from httpx import ASGITransport


async def _get_client() -> httpx.AsyncClient:
    import nonebot

    return httpx.AsyncClient(
        transport=ASGITransport(app=nonebot.get_app()),
        base_url="http://testserver",
    )


async def test_api_list_notes_empty():
    async with await _get_client() as client:
        resp = await client.get("/api/notes", params={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json() == {"count": 0, "notes": []}


async def test_api_list_notes():
    from notebot.datastore.notes import add_note

    await add_note("u1", "买牛奶")
    await add_note("u1", "写周报")
    await add_note("u2", "别人的便签")

    async with await _get_client() as client:
        resp = await client.get("/api/notes", params={"user_id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert [n["content"] for n in data["notes"]] == ["买牛奶", "写周报"]
    # 每条记录包含完整字段
    assert {"id", "user_id", "content", "created_at"} <= set(data["notes"][0])


async def test_api_shares_data_with_matcher(app, make_private_message_event):
    """端到端：matcher 写入的数据，HTTP 端点能读到（共享同一数据层）"""
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    from notebot.plugins.note import note_cmd

    async with app.test_matcher(note_cmd) as ctx:
        adapter = ctx.create_adapter(base=Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = make_private_message_event("/note 添加 端到端验证")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已添加便签 #1：端到端验证", result=None)
        ctx.should_finished(note_cmd)

    async with await _get_client() as client:
        resp = await client.get("/api/notes", params={"user_id": "123456"})
    assert resp.status_code == 200
    assert resp.json()["notes"][0]["content"] == "端到端验证"
```

### 7.3 要点

- **`_get_client()` 的 import 依然是延迟的**（`nonebot.get_app()` 要求 init 已完成），这与第四章的时序约束一脉相承。
- 这里没有 lifespan 问题：`ASGITransport` 默认不触发 FastAPI 的 startup 事件，但没关系——建表由 nonebug 的 `nonebug_init`
  （driver 级 lifespan）完成，路由函数运行期只依赖全局 `_session_factory`，而该全局量早在 session 级 fixture 里就指向了测试库。
- 第三个用例是本篇最有价值的一条测试： **用 nonebug 从 matcher 入口写入、用 httpx 从 HTTP 入口读出**
  ，端到端证明两条入口共享同一数据层、且都跑在测试库上。它同时充当了「隔离机制没有漏」的哨兵——哪天有人把插件改成自建引擎，这条用例会立刻变红。

## 八、测试隔离与依赖替换的原理总结

回顾整个方案，「隔离」其实由三个正交的机制拼成，理解它们比记住代码更重要：

1. **进程内替换（替代网络）**：nonebug 把 Bot.send / Adapter._call_api 换成假实现；httpx 的 ASGITransport 把 HTTP
   层换成进程内调用。机器人在测试里不连任何真实平台、不开任何真实端口。
2. **全局引擎替换（替代配置文件）**：数据层把引擎收敛到 `init_engine()` 单入口，测试在「init 之后、启动钩子之前」的窗口（nonebug
   预留的 `after_nonebot_init` 扩展点）把全局引擎换成内存库。由于 matcher 和 HTTP 端点都只认这个全局会话工厂，
   **换一处等于换全部**，不需要像第一篇那样逐个路由做 `dependency_overrides`——那是 FastAPI 依赖注入体系里的替换法，而
   NoneBot 插件不经过 FastAPI 的 DI，所以这里用「模块级可替换全局态」这个更朴素的机制。如果你的项目用的是 FastAPI 风格的
   `Depends(get_session)`，第一篇的 override 法依然适用，二者可以共存。
3. **用例级清库（替代用例顺序约定）**：autouse function fixture 每个用例重建表，消灭用例间的隐式依赖，换来乱序执行能力和并行执行的潜力。

再叠加 2.3 节的「单事件循环」配置，就构成了完整的环境模型： **一个进程、一个事件循环、一个内存库、每条用例一张空表**。

## 九、最佳实践清单

1. **目录组织**：应用代码（`notebot/`）与测试代码（`tests/`）分离成两个包；测试内部按层分文件——`test_datastore.py`（数据层）、
   `test_matcher.py`（事件响应）、`test_api.py`（HTTP 端点），基建统一收进 `tests/conftest.py`。
2. **fixture 分层**：session 级负责「一次性且昂贵」的事（init nonebot、加载插件、切换引擎）；function 级 autouse
   负责「每用例必须重置」的事（清表）；普通 function 级负责「按需取用」的事（事件工厂、数据层模块延迟导入）。判断标准：改变它会不会影响别的用例？会，就必须重置或提升作用域。
3. **版本钉死**：nonebug、pytest、pytest-asyncio 三者钉到次版本写进依赖（如 `nonebug ~= 0.4.4`、`pytest-asyncio ~= 1.4.0`
   ），原因见 2.2 节的三组实测。升级任何一个都应在 CI 全量验证后再合并。
4. **善用 markers**：随着项目长大，可以给慢用例打标（`@pytest.mark.slow`）、给适配器相关用例打标（`@pytest.mark.onebot`），在
   pyproject 里注册 markers 后用 `pytest -m "not slow"` 分层跑。本文示例规模尚小，未引入。
5. **CI 建议**：在 CI 里固定 Python 版本、用锁文件或钉版本的 requirements 安装、跑
   `pytest --cov=notebot --cov-report=term-missing`；可以再加 `pytest-randomly` 强制乱序，本文已实测乱序通过。
6. **覆盖率看「缺口」而不是「数字」**。本文最终完整运行结果（真实输出，`pytest --cov=notebot --cov-report=term-missing`）：

   ```
   ============================= test session starts ==============================
   platform linux -- Python 3.12.12, pytest-9.1.1, pluggy-1.6.0
   cachedir: .pytest_cache
   rootdir: /tmp/nonebot_tutorial/notebot
   configfile: pyproject.toml
   plugins: cov-7.1.0, anyio-4.14.2, asyncio-1.4.0, nonebug-0.4.4
   asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=session
   collecting ... collected 18 items

   tests/test_api.py::test_api_list_notes_empty PASSED                      [  5%]
   tests/test_api.py::test_api_list_notes PASSED                            [ 11%]
   tests/test_api.py::test_api_shares_data_with_matcher PASSED              [ 16%]
   tests/test_datastore.py::test_add_and_list_notes PASSED                  [ 22%]
   tests/test_datastore.py::test_list_notes_empty PASSED                    [ 27%]
   tests/test_datastore.py::test_delete_note PASSED                         [ 33%]
   tests/test_datastore.py::test_delete_note_wrong_user PASSED              [ 38%]
   tests/test_datastore.py::test_delete_note_id_not_exist[0] PASSED         [ 44%]
   tests/test_datastore.py::test_delete_note_id_not_exist[-1] PASSED        [ 50%]
   tests/test_datastore.py::test_delete_note_id_not_exist[9999] PASSED      [ 55%]
   tests/test_matcher.py::test_add_note PASSED                              [ 61%]
   tests/test_matcher.py::test_add_note_empty_content PASSED                [ 66%]
   tests/test_matcher.py::test_list_notes PASSED                            [ 72%]
   tests/test_matcher.py::test_list_notes_empty PASSED                      [ 77%]
   tests/test_matcher.py::test_delete_note PASSED                           [ 83%]
   tests/test_matcher.py::test_delete_note_not_exist PASSED                 [ 88%]
   tests/test_matcher.py::test_delete_note_not_a_number PASSED              [ 94%]
   tests/test_matcher.py::test_unknown_subcommand PASSED                    [100%]

   ================================ tests coverage ================================
   _______________ coverage: platform linux, python 3.12.12-final-0 _______________

   Name                               Stmts   Miss  Cover   Missing
   ----------------------------------------------------------------
   notebot/__init__.py                    0      0   100%
   notebot/datastore/__init__.py          0      0   100%
   notebot/datastore/notes.py            58      2    97%   73-76
   notebot/plugins/__init__.py            0      0   100%
   notebot/plugins/note/__init__.py      40      0   100%
   ----------------------------------------------------------------
   TOTAL                                 98      2    98%
   ============================== 18 passed in 2.09s ==============================
   ```

   唯一未覆盖的 73-76 行是 `get_engine()` 里「测试从未走过的生产环境兜底分支」（从配置文件读数据库地址惰性建引擎）——这正是测试引擎被显式替换的直接证据，属于合理缺口。如果你的覆盖率报告里
   matcher 插件出现大片未覆盖，那才说明事件模拟没测全。

## 十、FAQ（均为实测踩过的坑）

**Q1：测试一跑就 `ValueError: NoneBot has not been initialized.`，连收集都过不去？**
你在测试文件（或被它顶层 import 的模块）的顶层写了 `from notebot.xxx import ...`。`nonebot.init()` 是 nonebug 的 fixture
在执行阶段才调用的，收集阶段 NoneBot 尚未初始化，任何顶层 import 应用代码都会炸。解法：测试文件里只顶层 import `pytest`/
`nonebug` 这类纯测试库，应用模块一律在 fixture 或测试函数体内导入（本文的 `notes_db` fixture 就是这个模式）。实测报错见 4.2
节。

**Q2：内存 SQLite 报 `no such table: notes`，但我明明建过表？**
`:memory:` 数据库不跨连接共享：建表用一个连接、业务用另一个连接，就是两个库。给测试引擎加 `poolclass=StaticPool`
（单连接反复复用）即可；如果用文件库则没这个问题，但跨事件循环复用连接仍会踩 Q3 的坑。

**Q3：测试报 `InvalidRequestError: Could not refresh instance`，或者「insert 后 select 查不到」之类的诡异数据错乱？**
两个已实证的诱因，按出现概率排序： （a）事件循环作用域没统一——pytest-asyncio 默认每个测试函数一个新循环，aiosqlite 连接跨循环复用会导致
COMMIT 无法正常完成。解法：配置 `asyncio_default_fixture_loop_scope = "session"` 和
`asyncio_default_test_loop_scope = "session"`（实测从 4 个失败变全绿）。 （b）用
`async for session in get_session(): ... return` 的方式消费 async generator 会话——`return` 导致 generator 收尾被推迟，session
迟迟不关闭，StaticPool 下后续会话复用到同一条未干净的连接。解法：会话一律用 `@asynccontextmanager` + `async with`
，保证关闭是结构化的（本文数据层即此写法）。

**Q4：strict 模式下全部用例 setup 报错 `requested an async fixture ... with no plugin or hook that handled it`？**
nonebug 0.4.4 的 session 级 async fixture 依赖 auto 模式才能被 pytest-asyncio 接管。解法：设 `asyncio_mode = "auto"`
（本文配置），不必再给每个测试加 `@pytest.mark.asyncio`。实测 strict 模式 19 个用例全灭、改回 auto 全绿。

**Q5：老项目被钉在 pytest-asyncio 0.21.x，升级 nonebug 后报
`ScopeMismatch: ... function scoped fixture event_loop with a session scoped request object`？**
0.21.x 的 `event_loop` fixture 只有 function 级，撑不起 nonebug 的 session 级异步 fixture。两种出路：升级 pytest-asyncio 到
1.x 并按本文配置（推荐，实测通过）；或者在 conftest 里自定义 session 级 `event_loop` fixture（2.2 节给了代码，实测 0.21.2 +
nonebug 0.4.4 下 18 用例通过，仅有 DeprecationWarning）。

**Q6：`should_call_send` 断言失败，traceback 是一大坨 ExceptionGroup，怎么看？**
`handle_event` 在 anyio 任务组里并发执行 matcher，pytest.fail 会被包进 `BaseExceptionGroup`。不要被外层吓到，往里层找
`Failed: Application got send call with message ... but expected ...` 这一行，它会原样打印实际与期望的消息文本。实测样例见
6.4 节。

## 十一、总结

给一个 NoneBot2 + FastAPI + SQLAlchemy 项目写测试，真正的新知识只有三块，每一块本文都给出了实测验证过的落地方案：

1. **基建时序**：`nonebot.init()` 由 nonebug 在执行阶段完成 → 应用模块必须延迟导入；`after_nonebot_init` 是「init
   后、启动钩子前」的官方扩展点，加载插件和切换测试引擎都放这里。
2. **三层测法**：数据层直接调 CRUD 断言语义；matcher 用 nonebug 的 `test_matcher` 上下文「录剧本」（`create_bot` →
   `receive_event` → `should_call_send` → `should_finished`），并在上下文外查库验证持久化；HTTP 端点用 `ASGITransport` 直驱
   `nonebot.get_app()`，与第一篇的技巧完全通用。
3. **版本与环境**：pytest 9.1.1 + pytest-asyncio 1.4.0 + nonebug 0.4.4 实测兼容，但必须 auto 模式 + session 级事件循环；内存
   SQLite 必须 StaticPool。这三条配错任何一条，都会得到本文 FAQ 里那些已实证的报错。

最终成果：3 个测试模块 + 1 个 conftest，共 18 个用例全部通过，应用代码覆盖率 98%，全量运行约 2 秒（不含覆盖率统计约 1
秒），可乱序执行。

### 延伸阅读

- NoneBot2 官方文档·单元测试章节（nonebug 用法与事件构造）：https://nonebot.dev/docs/best-practice/testing/
- nonebug 仓库（源码很短，`nonebug/mixin/` 下的实现值得一读）：https://github.com/nonebot/nonebug
- SQLAlchemy 2.x 异步文档：https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- pytest-asyncio 文档（模式与循环作用域配置）：https://pytest-asyncio.readthedocs.io/
- 本系列第一篇《pytest 入门：以 FastAPI 为例讲解如何为异步框架编写单元测试》：fixture、parametrize、ASGITransport、dependency_overrides
  的基础讲解
