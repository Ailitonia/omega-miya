# NoneBot2 启动时自动数据库迁移实战：on_startup + Alembic 最佳实践

> 技术栈：Python 3.11+ / NoneBot 2.3+（fastapi 驱动）/ SQLAlchemy 2.0 / Alembic 1.13+ / MySQL 8.0 / asyncmy
>
> 在 NoneBot2 项目中，我们希望机器人启动时自动完成数据库创建与表结构迁移，而不是手工执行 Alembic 命令。本教程给出一套完整方案：
> `ensure_database`（自动建库）+ `migrate_to_head`（程序化迁移到最新版本）+ `GET_LOCK`
> （多实例并发保护），并讲清其中的关键陷阱——迁移是同步阻塞任务、Alembic
> 异步模板的 `asyncio.run` 与运行中的事件循环冲突，以及各自的正确解法。
>
> 本教程是系列第三篇，前两篇分别讲解 SQLAlchemy 2.0 异步数据库模块（FastAPI + MySQL）与 Alembic 版本化迁移基础。

---

## 第 1 章 场景与总体思路

本系列前两篇分别解决了两个独立的问题：第一篇用 SQLAlchemy 2.0 异步引擎 + asyncmy 搭好了 NoneBot2（fastapi 驱动）+ MySQL
的数据库模块；第二篇引入 Alembic，把表结构变更纳入版本化管理。但还有一个尾巴没收：每次部署到新环境，都得先手工建库、再手工执行
`alembic upgrade head`，然后才能启动机器人。本篇就把这最后一步自动化——让机器人启动时自己把数据库创建和迁移都做完。

### 1.1 NoneBot2 的启动流程

先回顾一下 NoneBot2 应用的启动过程，一个典型的 `bot.py` 长这样：

```python
import nonebot

nonebot.init()                        # 读取 .env，初始化配置与驱动

driver = nonebot.get_driver()         # 拿到全局驱动实例

@driver.on_startup
async def _init_database() -> None:
    ...                               # 启动钩子：驱动器启动后、正式对外服务前执行

nonebot.load_plugins("src/plugins")   # 加载插件

if __name__ == "__main__":
    nonebot.run()                     # 启动驱动器（这里是 fastapi），进入事件循环
```

关键时序是：`nonebot.init()` 解析 `.env`（含 `DRIVER=~fastapi` 和我们自定义的 `DATABASE_URL`）并创建驱动实例；插件在模块级由
`nonebot.load_plugins` 加载完毕；待 `nonebot.run()` 把驱动器（uvicorn）跑起来后，`@driver.on_startup` 注册的协程函数会在
ASGI lifespan 的 startup
阶段被依次执行——此时服务尚未正式对外开放；钩子全部返回后，已加载的插件才开始响应消息。这个"服务就绪前的窗口"正是塞入数据库初始化逻辑的天然位置——它支持
async 函数，又早于任何业务代码触碰数据库。

### 1.2 为什么把迁移放在启动时

把建库和迁移挂在 `on_startup` 上，换来两个直接收益：

- **新环境零手工步骤**：克隆代码、填好 `.env`、`python bot.py`，数据库自动出现并迁移到最新结构。新人上手和换机器部署都不需要记住额外的命令。
- **容器自愈**：Docker 镜像里不需要再塞初始化脚本或 entrypoint 编排，容器启动即完成建库建表；`docker compose up`
  一键拉起整套服务，数据库容器重建后应用重启一次就能自动恢复表结构。

代价是要在应用进程内处理两件 Alembic 命令行时代不需要操心的事，这正是本篇的技术重心。

### 1.3 总体方案三步走

整个方案可以概括为三步，顺序不能乱：

1. **ensure_database ()**：连接 MySQL 服务器（不带库名），`CREATE DATABASE IF NOT EXISTS` 确保目标库存在——Alembic
   只管表结构，不管建库；
2. **migrate_to_head ()**：以程序化方式调用 Alembic，把表结构升级到 head 版本；
3. 前两步完成后启动钩子返回、服务就绪，此前已加载完毕的插件开始响应消息。

但直接在 `on_startup` 里调 `command.upgrade(cfg, "head")` 会踩两个坑，先预告：

- **迁移是同步阻塞任务**：Alembic 的 `command.upgrade` 是普通同步函数，直接在事件循环里调用会卡住整个机器人（详见第 4 章）；
- **async 模板 env.py 的 asyncio.run 冲突**：我们沿用的 async 模板在 env.py 内部用 `asyncio.run` 包了一层，而 `on_startup`
  已经运行在事件循环中，直接调用会抛 `RuntimeError: asyncio.run() cannot be called from a running event loop`（详见第 4、5
  章的解法）。

## 第 2 章 两条路线：nonebot-plugin-orm 还是自己集成

在动手之前需要说明：本篇的 DIY 方案并非唯一选择，NoneBot 官方插件商店里已有现成的 `nonebot-plugin-orm`。先客观地看看两条路线各自的适用场景。

### 2.1 路线一：官方插件 nonebot-plugin-orm

`nonebot-plugin-orm` 是 NoneBot 官方维护的数据库集成插件，底层同样是 SQLAlchemy 2 + Alembic 这套组合，能力和本篇要手工实现的东西高度重合：

- 提供 `nb orm` CLI 子命令，可以在命令行完成迁移的生成、执行、历史查看等操作，相当于把 Alembic 的常用命令接进了 nb-cli；
- 启动时自动迁移：插件内部同样在驱动启动阶段完成数据库结构升级，与本篇思路一致；
- 插件级迁移分发：如果你写了一个带表的 NoneBot 插件想发布给别人用，它提供了一套让迁移文件随插件分发、用户安装后自动建表的机制，这是
  DIY 方案需要额外设计才能做到的（第 7 章会展开讨论这个需求）。

安装只需要：

```bash
pip install nonebot-plugin-orm
```

然后在 `.env` 里配置好数据库连接串，按文档在插件中声明模型，即可使用 `nb orm` 管理迁移；机器人启动时迁移自动执行，开发者基本感知不到
Alembic 的存在。本篇不展开它的具体 API
和配置项——这些细节以官方文档为准，且插件仍在演进，照抄容易过时。需要留意的是，便利的另一面是封装：连接池行为、迁移执行时机等细节由插件决定，遇到非常规需求时定制空间相对有限。

### 2.2 路线二：自己集成（DIY）

DIY 就是本篇的主线：自己写 `app/db.py`（异步引擎、会话工厂、`ensure_database`）和 `app/migrate.py`（程序化调用 Alembic），再手动挂到
`on_startup` 上。整套核心代码不到一百行，完全透明。

### 2.3 怎么选

经验性的建议：

- **常规项目、尤其多插件共享模型或计划分发插件**——优先用官方插件。它解决了插件间模型发现、迁移分发这类 DIY 成本较高的问题，且有社区维护。
- **以下情况选 DIY**：需要完全控制连接池参数（`pool_size`、`pool_recycle` 这类调优）和迁移执行时机；已有自研的 db
  模块不想推翻（比如本系列前两篇搭好的那一套）；或者就是想把 Alembic 与异步事件循环的交互原理搞清楚，知其所以然。

需要强调的是，两条路线并不对立：官方插件的底层机制与本篇 DIY 方案同源——都是 SQLAlchemy 引擎 + Alembic 程序化调用 +
启动钩子。读完本篇，你再看 `nonebot-plugin-orm` 的行为和报错时会心里有数，排查问题也更有方向。接下来第 3 章从项目结构和数据库模块开始，正式搭建
DIY 方案。

---

## 第 3 章 项目结构与数据库模块

从本章开始动手搭建项目。我们先确定目录结构与配置文件，然后实现数据库访问模块 `app/db.py`，最后用签到插件验证它能工作。

### 3.1 目录结构总览

整个 `mybot` 项目的骨架如下：

```text
mybot/
├── bot.py              # 入口：nonebot.init()、注册 on_startup、加载插件
├── .env                # 环境配置（含 DATABASE_URL）
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── db.py           # 异步引擎 / 会话工厂 / Base / ensure_database
│   └── migrate.py      # Alembic 程序化迁移
└── src/plugins/
    └── signin/         # 签到插件（models.py +  matcher）
```

其中 `app/` 是我们自研的基础设施包：`db.py` 集中管理数据库连接，`migrate.py` 负责在启动时程序化执行迁移（第 4 章实现）。
`alembic/` 由 Alembic 初始化命令生成。插件统一放在 `src/plugins/` 下，用 `nonebot.load_plugins("src/plugins")` 加载。

### 3.2 .env 配置

在项目根目录创建 `.env`：

```text
DRIVER=~fastapi
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/mybot?charset=utf8mb4
```

两个键各有讲究：

- `DRIVER=~fastapi`：NoneBot 内置驱动的写法，`~` 前缀表示使用内置的 FastAPI 驱动（依赖安装 `nonebot2[fastapi]` 时一并装好）。
- `DATABASE_URL`：这不是 NoneBot 的内置配置项，而是我们 **自定义**的键。NoneBot 的配置系统基于
  pydantic-settings，允许任意自定义字段——`.env` 里的所有键都会被加载进全局配置对象。约定俗成地，自定义键统一用大写字母加下划线。代码里通过
  `nonebot.get_driver().config.database_url` 就能取到这个值，配置系统会自动把 `DATABASE_URL` 映射为小写属性名
  `database_url`。

URL 里 `mysql+asyncmy` 表示使用 asyncmy 异步驱动，`charset=utf8mb4` 保证完整 Unicode 支持（包括 emoji）。

### 3.3 app/db.py 逐段讲解

这是全项目最重要的基础设施文件，完整代码如下：

```python
# app/db.py
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

import nonebot

DATABASE_URL: str = nonebot.get_driver().config.database_url  # 需在 nonebot.init() 之后导入本模块

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    pass


async def ensure_database() -> None:
    """首次启动时自动创建 MySQL database（Alembic 只管表结构，不管建库）。"""
    url = make_url(DATABASE_URL)
    db_name = url.database
    server_engine = create_async_engine(url.set(database=None))
    async with server_engine.connect() as conn:
        await conn.execute(
            text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                 "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        )
    await server_engine.dispose()
```

**配置加载时机：必须在 `nonebot.init()` 之后导入本模块。** `nonebot.get_driver()` 只能在初始化完成后调用；如果 `app.db` 在
`nonebot.init()` 之前被 import，`get_driver()` 会直接抛异常。退一步说，就算能拿到 driver，配置也尚未从 `.env` 加载，
`config.database_url` 根本不存在。这就是后面反复强调的「导入顺序铁律」的根源——`bot.py` 中必须用延迟导入解决这个问题。

**引擎与连接池。** `create_async_engine` 创建异步引擎，四个池参数简要说明：`pool_size=5` 常驻 5 条连接；`max_overflow=10`
高峰期最多临时再加 10 条；`pool_pre_ping=True` 取连接前先 ping 一下，规避 MySQL 单方面断开后的「僵尸连接」；
`pool_recycle=1800` 每 30 分钟强制回收重建，防止触碰 MySQL 默认 8 小时的 `wait_timeout`。各参数的调优细节请参见本系列第一篇，这里不再展开。
`async_session_factory` 是全局唯一的会话工厂，`expire_on_commit=False` 保证提交后对象属性仍可用（异步场景下避免隐式 IO
报错），`autoflush=False` 让 flush 时机完全可控。

**`Base` 类。** 所有模型都继承它，`Base.metadata` 将汇集全部表结构信息，供 Alembic autogenerate 使用。

**`ensure_database` 建库函数。** 注意一个关键事实： **Alembic 只负责管理表结构，不负责创建 database 本身**。全新环境里连
`mybot` 这个库都不存在，迁移根本无从谈起。这个函数分三步解决：先用 `make_url(DATABASE_URL)` 把 URL 字符串解析成结构化对象并取出库名；再用
`url.set(database=None)` 生成一个不带库名的 URL——这样连接的是 MySQL **服务器**而非具体库，恰好可以执行建库语句；最后执行
`CREATE DATABASE IF NOT EXISTS`，幂等安全，重复启动无副作用。用完调用 `dispose()` 关闭这个临时引擎，避免泄漏连接。

### 3.4 签到插件：模型与会话使用

`src/plugins/signin/models.py`，SQLAlchemy 2.0 的 `Mapped`/`mapped_column` 声明式风格，注意继承的是 `app.db.Base`：

```python
# src/plugins/signin/models.py
from datetime import date

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SigninUser(Base):
    __tablename__ = "signin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), unique=True, comment="QQ 号")
    points: Mapped[int] = mapped_column(Integer, default=0)
    last_sign_date: Mapped[date | None] = mapped_column(nullable=True)
```

matcher 中使用 session 的最简模式——嵌套两个 `async with`，外层建会话、内层开事务：

```python
# src/plugins/signin/__init__.py
from nonebot import on_command
from nonebot.adapters import Event
from sqlalchemy import select

from app.db import async_session_factory
from .models import SigninUser

signin = on_command("签到")


@signin.handle()
async def handle_signin(event: Event) -> None:
    uid = event.get_user_id()
    async with async_session_factory() as session:
        async with session.begin():
            user = await session.scalar(
                select(SigninUser).where(SigninUser.user_id == uid)
            )
            if user is None:
                user = SigninUser(user_id=uid, points=0)
                session.add(user)
            user.points += 10
    await signin.finish(f"签到成功！当前积分：{user.points}")
```

`session.begin()` 退出时自动提交、异常时自动回滚，业务代码无需手写 commit/rollback。

### 3.5 bot.py 骨架与导入顺序铁律

```python
# bot.py
import nonebot

nonebot.init()

driver = nonebot.get_driver()

nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run()
```

**铁律：`nonebot.init()` 必须是第一个实质性调用**，任何直接或间接 import `app.db` 的代码（包括插件）都只能出现在它之后。这是因为
`app/db.py` 模块顶层就读取了 `get_driver().config`。插件通过 `nonebot.load_plugins` 加载天然满足顺序；而 `on_startup`
钩子里用到的 `app.db`/`app.migrate`，我们用「函数体内延迟导入」来保证安全——第 5 章的完整 `bot.py` 会展示这一点。

## 第 4 章 Alembic 环境与程序化调用

数据库模块就绪后，本章搭建 Alembic 环境，并解决全篇的核心技术问题：如何在 NoneBot 的事件循环里安全地执行迁移。

### 4.1 初始化 Alembic

```bash
pip install alembic
alembic init -t async alembic
```

`-t async` 指定使用 **异步模板**，这一步至关重要。我们的应用引擎是 `AsyncEngine`，迁移脚本内部也需要用异步方式连接数据库。async
模板生成的 `env.py` 会把同步的迁移入口包一层 `asyncio.run`，让 Alembic 的同步 API 与异步引擎协作。如果误用了默认的同步模板，env.py
用同步引擎去解析 `mysql+asyncmy://` 的 URL，会直接报驱动加载错误。执行后得到 `alembic.ini` 和 `alembic/` 目录（含 `env.py`
与 `versions/`）。

### 4.2 env.py 要点复述

env.py 沿用本系列前一篇 Alembic 教程的定稿，此处只列四个要点，原理与逐行讲解见前作：

1. `target_metadata = Base.metadata`——autogenerate 比对的目标元数据；
2. **import 所有模型模块**，包括 `src.plugins.signin.models`——模型不 import 就不在 metadata 里，autogenerate
   会把已存在的表误判为「待删除」；
3. `config.set_main_option("sqlalchemy.url", DATABASE_URL)`——URL 从应用配置读取，不在 alembic.ini 里重复维护一份；
4. `context.configure(..., compare_type=True)`——让列类型变化（如 `String(32)` 改 `String(64)`）也能被 autogenerate 感知。

一句话原理：Alembic 的 `command.upgrade` 等迁移函数本身是 **同步**的，async 模板的做法是在 env.py 内部用 `asyncio.run()`
起一个事件循环，在其中用 `connection.run_sync()` 把同步的迁移逻辑桥接到异步连接上。请记住这个 `asyncio.run`，它是下一节问题的关键。

### 4.3 核心问题：为什么不能直接调 command.upgrade

最容易想到的写法是在 `on_startup` 钩子里直接调用：

```python
# ❌ 错误示范，切勿照抄
@driver.on_startup
async def _migrate() -> None:
    command.upgrade(Config("alembic.ini"), "head")
```

这会踩中 **两个叠加的坑**：

**坑一：同步阻塞卡死事件循环。** `command.upgrade` 是普通同步函数，迁移涉及多次 DDL
与网络往返，耗时从几百毫秒到数秒不等。在协程里直接调用，整个事件循环被独占，期间所有消息处理、定时任务全部停摆——机器人表现为「启动时卡死」。

**坑二：`asyncio.run` 冲突直接报错。** 如 4.2 所述，async 模板的 env.py 内部会调用 `asyncio.run()` 执行异步迁移逻辑。而
`asyncio.run` 的硬性约束是： **调用它的线程中不能有正在运行的事件循环**。`on_startup` 协程本身就运行在主事件循环里，于是迁移一开始就会抛出：

```text
RuntimeError: asyncio.run() cannot be called from a running event loop
```

结论：迁移必须 **离开主事件循环所在的线程**去执行。

### 4.4 app/migrate.py 逐行讲解

解决方案是冻结的 `app/migrate.py`，用 `asyncio.to_thread` 一举解决上面两个问题：

```python
# app/migrate.py
import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

ALEMBIC_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = str(ALEMBIC_DIR / "alembic.ini")


def _upgrade_head() -> None:
    """同步函数：在独立线程中运行，env.py 内的 asyncio.run 才能正常工作。"""
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("script_location", str(ALEMBIC_DIR / "alembic"))
    command.upgrade(cfg, "head")


async def migrate_to_head() -> None:
    """异步入口：迁移是同步阻塞任务，丢到线程里执行，避免卡住事件循环。"""
    await asyncio.to_thread(_upgrade_head)
```

逐行看关键点：

- `ALEMBIC_DIR = Path(__file__).resolve().parent.parent`：以本文件的位置为锚点定位项目根目录，`ALEMBIC_INI` 在此基础上拼出
  `alembic.ini` 的 **绝对路径**。这是必要防御——如果只写 `Config("alembic.ini")`，Alembic 会按 **进程当前工作目录**
  解析相对路径，一旦从别的目录启动 bot（如 systemd、Docker 里 WORKDIR 不同），就会报找不到配置文件。
- `cfg.set_main_option("script_location", str(ALEMBIC_DIR / "alembic"))`：显式告诉 Alembic 迁移脚本目录，这里同样必须使用基于
  `__file__` 的 **绝对路径**——Alembic 对相对 `script_location` 同样按进程当前工作目录解析， **并不会相对 ini 文件定位**
  。两处都用绝对路径后，从任何目录启动（systemd/Docker）都能正常工作。
- `command.upgrade(cfg, "head")`：把数据库升级到最新版本，等价于命令行 `alembic upgrade head`。
- `asyncio.to_thread(_upgrade_head)`：把同步函数丢进线程池的 **独立线程**执行并 await
  其完成。这一个调用同时解决两个坑——对坑一，阻塞发生在线程里，主事件循环可以继续调度其他协程；对坑二，新线程中
  **没有正在运行的事件循环**，env.py 内部的 `asyncio.run()` 可以正常创建并运行自己的循环。`asyncio.to_thread` 是 Python
  3.9+ 标准库 API，无需任何第三方依赖。

对外的异步入口 `migrate_to_head()` 保持简洁，第 5 章会在 `on_startup` 钩子里直接 `await` 它。

### 4.5 备选方案：迁移专用同步 URL

如果你不想引入 async 模板，还有一条路线：为迁移单独配置一个 **同步** URL（如 `mysql+pymysql://...`，pymysql 是同步驱动），配合默认同步模板的
env.py。迁移走同步连接、应用运行走异步连接，两者互不干涉。

这种方式下 `command.upgrade` 不会触发 `asyncio.run` 冲突（坑二天然消失），但它 **依然是同步阻塞调用**（坑一仍在），所以
`asyncio.to_thread` 这层包装依然不能省。该方案需额外维护一份同步 URL 配置并安装 pymysql，适合团队已有同步迁移基建、或不想理解
async 模板的场景；本教程主线仍采用 async 模板，与应用引擎保持单一 URL 来源。

---

## 第 5 章 核心实现：on_startup 自动迁移

第 3、4 章已经备齐了所有零件：`app/db.py` 提供 `ensure_database()`（建库），`app/migrate.py` 提供 `migrate_to_head()`（把表结构迁到
head）。本章把它们接到 NoneBot2 的启动流程上，并走完「从零建库 → 首次迁移 → 模型演进 → 重启自动升级」的完整闭环。

### 5.1 启动入口 bot.py

bot.py 全文如下，它是整个项目唯一的启动入口：

```python
# bot.py
import nonebot

nonebot.init()

driver = nonebot.get_driver()


@driver.on_startup
async def _init_database() -> None:
    from app.db import ensure_database          # 延迟导入：必须在 nonebot.init() 之后
    from app.migrate import migrate_to_head

    await ensure_database()                     # 第一步：确保 database 存在
    await migrate_to_head()                     # 第二步：把表结构迁移到最新版本


nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run()
```

其中 `nonebot.init()` 负责读取 `.env` 并把自定义的 `DATABASE_URL` 挂到 `driver.config` 上（细节见第 3
章），它是整条链路的起点。短短二十行，还有三个设计点值得讲透。

**为什么 import 写在函数体里。** `app/db.py` 的模块级代码会立刻执行 `nonebot.get_driver().config.database_url` 读取配置，而
`get_driver()` 在 `nonebot.init()` 之前调用会直接抛异常。把导入收进 `_init_database()` 的函数体，导入时机就被锁死在「钩子被调用」的那一刻——那时
`init()` 早已完成，配置必然就绪。即使将来某个插件或工具模块不小心提前触碰了这条导入链，也不会踩到「init 之前读配置」的坑。

**为什么先 ensure_database 再 migrate_to_head。** Alembic 的职责边界是「库内的表结构」，它不会、也不应该替你创建 database
本身——如果 `mybot` 库不存在，`command.upgrade` 建立连接时就会直接报 `Unknown database 'mybot'`。`ensure_database()` 用的是
`CREATE DATABASE IF NOT EXISTS`，天然幂等，每次启动跑一次几乎零成本，所以固定为第一步。

**@driver.on_startup 的语义。** 这是 NoneBot2 驱动器提供的启动钩子注册器，可直接当装饰器使用、接收 async 函数；可注册多个钩子，按注册顺序逐个
await。执行时机在驱动器（这里是 fastapi + uvicorn）完成服务就绪之前，也就是任何插件 matcher
开始处理消息之前——保证「插件对外提供服务时，数据库一定已就绪」。钩子内抛出异常会导致启动失败，这个特性第 6 章会刻意利用。

### 5.2 生成初始迁移 0001

首次生成前，需要一个空库作为 autogenerate 的对比基线。只有这一次需要手工建库，之后就全部交给 bot 自己了：

```bash
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS mybot DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
```

在项目根目录执行：

```bash
$ alembic revision --autogenerate -m "init"
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.autogenerate.compare] Detected added table 'signin_users'
  Generating .../alembic/versions/3f9c1a2b7d04_init.py ...  done
```

生成的迁移文件（节选）大致如下：

```python
# alembic/versions/3f9c1a2b7d04_init.py
revision: str = "3f9c1a2b7d04"
down_revision: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "signin_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("last_sign_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("signin_users")
```

沿用本系列前作的约定：Alembic 实际生成的是 `3f9c1a2b7d04` 这样的随机十六进制 revision ID，教程为叙述方便，按生成顺序简称它为
**0001**，后文的 **0002** 同理。生成后请人工过目脚本——确认只检测到 `signin_users` 一张表、没有误伤，这是使用 autogenerate
的铁律。

### 5.3 从零验证：删库、启动、查表

模拟一台全新机器的环境，先把库整个删掉：

```bash
mysql -uroot -p -e "DROP DATABASE IF EXISTS mybot;"
```

然后直接启动 bot：

```bash
$ python bot.py
```

观察日志，关键时间线如下（已略去时间戳与无关行）：

```text
[INFO] nonebot | NoneBot is initializing...
[INFO] nonebot | Current Env: prod
[SUCCESS] nonebot | Succeeded to load plugin "signin" from "src.plugins.signin"
[INFO] uvicorn | Started server process [12345]
[INFO] uvicorn | Waiting for application startup.
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Running upgrade  -> 3f9c1a2b7d04, init
[INFO] uvicorn | Application startup complete.
[INFO] uvicorn | Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

可以看到，不存在的 `mybot` 库被静默建好（`ensure_database`，无 SQL 回显），随后 Alembic 一路升级到 0001。注意「Succeeded to
load plugin」出现在迁移日志之前：`nonebot.load_plugins()` 是模块级调用，插件导入在 `nonebot.run()` 之前就完成了；但服务就绪的标志是
`Application startup complete`，我们的启动钩子在它之前执行——即先建库、再迁移，全部完成后插件才开始响应消息。这正是把迁移挂在
on_startup 想要的效果。

进 MySQL 确认结果：

```sql
USE mybot;

SHOW TABLES;
-- alembic_version
-- signin_users

DESC signin_users;
-- id / user_id / points / last_sign_date 四列齐备，user_id 带唯一索引

SELECT * FROM alembic_version;
-- version_num: 3f9c1a2b7d04（即 0001）
```

`alembic_version` 表只有一行一列，记录当前版本号，它是 Alembic 判断「数据库现在处于哪个版本」的唯一依据，之后每次 upgrade
都会更新这一行。

最后验证一下幂等性：不删库，直接再跑一次 `python bot.py`。这次日志里只剩 `Context impl MySQLImpl.`，没有任何
`Running upgrade`——数据库已在 head，`command.upgrade` 是空跑。`CREATE DATABASE IF NOT EXISTS` 加上「已在 head
即跳过」，整个启动钩子天然幂等，可以随每次启动放心执行，这也是它能长期留在 bot.py 里的前提。

### 5.4 模型演进：加一列，重启即生效

签到插件要支持「连续签到天数」。第一步，改模型：

```python
# src/plugins/signin/models.py
class SigninUser(Base):
    # ...原有字段不变...
    consecutive_days: Mapped[int] = mapped_column(default=0, comment="连续签到天数")  # 新增
```

第二步，生成演进迁移：

```bash
$ alembic revision --autogenerate -m "add consecutive_days"
INFO  [alembic.autogenerate.compare] Detected added column 'signin_users.consecutive_days'
  Generating .../alembic/versions/8c2e5b91f0aa_add_consecutive_days.py ...  done
```

```python
# alembic/versions/8c2e5b91f0aa_add_consecutive_days.py（简称 0002）
def upgrade() -> None:
    op.add_column(
        "signin_users",
        sa.Column("consecutive_days", sa.Integer(), nullable=False, comment="连续签到天数"),
    )


def downgrade() -> None:
    op.drop_column("signin_users", "consecutive_days")
```

第三步最能体现本方案的价值： **什么都不要手工执行**——不要 `alembic upgrade head`，不要连进 MySQL 敲 SQL。直接 Ctrl+C 后重新运行
`python bot.py`，启动日志里会出现：

```text
INFO  [alembic.runtime.migration] Running upgrade 3f9c1a2b7d04 -> 8c2e5b91f0aa, add consecutive_days
```

进库验证：

```sql
DESC signin_users;              -- 多出 consecutive_days 列
SELECT * FROM alembic_version;  -- version_num 已变为 8c2e5b91f0aa（0002）
```

「改模型 → autogenerate → 重启 bot」三步走完，数据库的创建与结构变更全部在启动时自动处理完毕——这就是本教程标题所承诺的完整闭环。它的收益在团队协作和部署时会被进一步放大：新同事
clone 仓库、新容器在新机器上拉起，都只需要代码加一份 `.env`，第一次启动就自动得到一套结构最新的数据库，没有任何手工
SQL、没有「记得先跑迁移」的口头约定。剩下的唯一人工环节是迁移脚本生成后的人工审查，例如这次给已有数据的表加 NOT NULL
列，若想让存量行显式落 0，可以在脚本里补一个 `server_default`。

### 5.5 日志美化：让迁移过程可见、失败可查

Alembic 自己的日志走标准 logging，混在 NoneBot 的输出里不够醒目。给启动钩子包一层日志，把 bot.py 中的钩子替换为：

```python
# bot.py
from nonebot.log import logger


@driver.on_startup
async def _init_database() -> None:
    from app.db import ensure_database
    from app.migrate import migrate_to_head

    await ensure_database()

    logger.info("数据库迁移开始")
    try:
        await migrate_to_head()
    except Exception:
        logger.exception("数据库迁移失败：请检查 DATABASE_URL、Alembic 配置与迁移脚本")
        raise
    logger.info("数据库迁移完成")
```

`nonebot.log.logger` 是 NoneBot2 内置的 loguru logger，与框架日志共用同一条输出管道（同样的着色与级别控制），业务日志和框架日志混排后时间线清晰，排障时不用在两套日志之间来回对照；
`logger.exception` 会自动附带完整堆栈，迁移脚本报错时一眼定位。启动效果：

```text
[INFO] nonebot | 数据库迁移开始
INFO  [alembic.runtime.migration] Running upgrade  -> 3f9c1a2b7d04, init
[INFO] nonebot | 数据库迁移完成
```

注意最后那个 `raise` 不能省：记录完异常必须把失败继续抛出去、让启动中断，绝不能让 bot 带着不一致的表结构上线。为什么——这正是下一章的主题之一。

## 第 6 章 进阶：并发安全与失败策略

单实例下，第 5 章的方案已经足够可靠。但生产环境很少只有一个实例：多副本容器、滚动更新、多 worker
并行……本章解决随之而来的两个问题：并发迁移撞车，以及迁移失败时该怎么办。

### 6.1 多实例并发启动：迁移撞车现场

以下场景都会让多个进程几乎同一时刻执行 on_startup 里的迁移：

- 用 uvicorn / gunicorn 起多个 worker 进程跑同一个 FastAPI 应用；
- `docker compose up --scale bot=3`，或 K8s Deployment 多副本同时拉起；
- 滚动更新时新副本已启动、旧副本未退出，下一轮更新又叠加新副本。

Alembic 的 `upgrade` 没有任何跨进程互斥机制，而 MySQL 的 DDL 大多是隐式提交、不受事务保护。两个进程同时执行同一批迁移脚本，典型后果是：后执行
`CREATE TABLE` 的一方收到 `1050 Table 'signin_users' already exists`；加列脚本撞上 `1060 Duplicate column name`；写
`alembic_version` 时版本号主键冲突。更麻烦的是交错执行不同脚本留下的「半迁移」状态：表结构既不在 0001 也不在
0002，事后排查极其痛苦。即使两个进程错开几秒也不安全——第二个进程完全可能读到第一个迁到一半的中间状态。结论：多实例部署必须给迁移加一把跨进程的锁。

### 6.2 MySQL 咨询锁：GET_LOCK 串行化迁移

MySQL 自带与任何表都无关的命名咨询锁（advisory lock），正好适合这个场景：

- `SELECT GET_LOCK('name', timeout)`：全库同一时刻只有一个连接能持有同名锁，拿到返回 1，超时返回 0，出错返回 NULL；
- `SELECT RELEASE_LOCK('name')`：显式释放；
- 兜底机制：锁绑定在连接（会话）上，持锁连接一旦断开——进程崩溃、被 kill、网络闪断——MySQL 服务端自动释放它持有的所有命名锁，不会留下永远解不开的死锁。

有一个硬性要求： **取锁、持锁、放锁必须在同一条连接上**。因此我们不用业务连接池，而是单独建一个 NullPool 引擎持锁。在
`app/migrate.py` 末尾追加：

```python
# app/migrate.py（在第 4 章基础上追加，原有代码不变）
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

MIGRATION_LOCK_NAME = "mybot_alembic_migration"  # 锁名按项目唯一，共库项目互不阻塞


async def migrate_with_lock(timeout: int = 60) -> None:
    """带咨询锁的迁移入口：多实例并发启动时，同一时刻只有一个进程真正执行迁移。"""
    from app.db import DATABASE_URL  # 延迟导入，理由同 bot.py

    lock_engine = create_async_engine(DATABASE_URL, poolclass=NullPool)  # 独立连接持锁
    try:
        async with lock_engine.connect() as conn:
            acquired = await conn.scalar(
                text("SELECT GET_LOCK(:name, :timeout)"),
                {"name": MIGRATION_LOCK_NAME, "timeout": timeout},
            )
            if acquired != 1:
                raise RuntimeError(
                    f"获取迁移锁 {MIGRATION_LOCK_NAME!r} 失败，GET_LOCK 返回 {acquired}"
                )
            try:
                await migrate_to_head()  # 内部仍是 asyncio.to_thread + command.upgrade
            finally:
                await conn.scalar(
                    text("SELECT RELEASE_LOCK(:name)"),
                    {"name": MIGRATION_LOCK_NAME},
                )
    finally:
        await lock_engine.dispose()
```

`async with lock_engine.connect()` 保证 GET_LOCK 与 RELEASE_LOCK 落在同一条物理连接上；迁移本身由 `migrate_to_head()`
在独立线程里用自己的连接完成，持锁连接安静等待即可——MySQL 允许会话持锁时空闲，不影响锁的有效性。

然后把 bot.py 钩子中的调用换掉：

```python
# bot.py（钩子其余部分不变，仅替换迁移调用）
@driver.on_startup
async def _init_database() -> None:
    ...
    await ensure_database()
    await migrate_with_lock()  # 原来是 migrate_to_head()
```

行为变化：第一个实例拿锁、迁移、放锁；其余实例在 GET_LOCK 处排队，拿到锁时数据库已是 head，`command.upgrade` 秒级空跑返回。
`timeout=60` 是等锁的最长秒数，迁移耗时长的大库可适当调大。

### 6.3 失败策略：fail-fast 是唯一正确的默认

推荐的默认策略只有一句话： **迁移失败 = 启动失败**。让异常从 on_startup 里抛出去，NoneBot 启动中断、进程非零退出，剩下的交给进程管理者：systemd
的 `Restart=on-failure`、Docker 的 `restart: unless-stopped`、K8s 的 CrashLoopBackOff
加告警。人（或告警机器人）会在第一时间看到那条带完整堆栈的「数据库迁移失败」日志，而不是三天后才发现签到功能偶发 500。

反面教材是「跳过迁移继续启动」：

```python
@driver.on_startup
async def _init_database() -> None:
    try:
        await migrate_to_head()
    except Exception:
        logger.exception("迁移失败，跳过")  # ← 然后没有 raise，服务照常起来
```

它为什么危险？因为从此刻起， **内存里的代码与磁盘上的表结构分道扬镳**：ORM 模型认为 `signin_users` 有 `consecutive_days`
列，真实库里却没有。bot 会「正常」上线，健康检查全绿，直到某个用户触发签到，`INSERT`/`SELECT` 才抛出
`Unknown column 'consecutive_days'`——报错点远离根因、时机随机、随流量忽隐忽现，远比启动失败难排查。「能启动」成了最危险的假象。除非你明确知道某次失败无害并决定人工介入，否则不要在通用逻辑里吞掉迁移异常。

### 6.4 生产环境建议

**把显式迁移放进部署流水线。** on_startup 迁移的准确定位是：开发环境的零步骤便利 + 生产环境的兜底保险，而不是生产迁移的唯一手段。规范的发布流程是：流水线（CI
job、K8s Job、容器 entrypoint 前置命令）先显式执行一次 `alembic upgrade head`，成功后再滚动替换应用实例。有了 GET_LOCK
兜底，即使流水线步骤被跳过，启动钩子也能安全补齐——两者叠加，双保险。配套约定：迁移脚本保持向后兼容（先加列、后改代码），让滚动期间新旧实例可以共存。

**大表变更另走在线改表工具。** 千万行的表上，`ADD COLUMN` 一类的 DDL 可能耗时数分钟甚至更久，让启动钩子或流水线干等并不可取。这类变更仍应使用
gh-ost 或 pt-online-schema-change 在线改表，改完再用 Alembic 对齐版本状态，完整流程见本系列前作第 7 章，本文不再展开。

---

## 第 7 章 插件作者：随插件分发迁移

### 7.1 场景：插件的表谁来建

前面六章解决的是「自己的机器人项目」的迁移问题。但如果你写的是要发布到 PyPI 的 NoneBot 插件——比如把签到插件做成
`nonebot-plugin-signin`，用户 `pip install` 之后一行 `nonebot.load_plugin("nonebot_plugin_signin")` 就期望它开箱即用——那么
`signin_users` 这张表不能指望用户手工执行 `alembic upgrade` 来建。表结构的创建和演进必须随插件一起分发，并在合适的时机自动执行。这一章介绍两种常见的组织方式。

### 7.2 方式一：插件内嵌独立迁移目录

最直接的做法是插件自带一套完整的 Alembic 环境，与宿主项目的 `alembic/` 目录互不干涉：

```text
nonebot_plugin_signin/
├── __init__.py       # 插件入口：注册 matcher、在 on_startup 里执行迁移
├── models.py         # 插件自己的模型（注意带表名前缀）
├── matcher.py
└── migrations/       # 插件私有的迁移环境，随包分发
    ├── env.py
    └── versions/
        └── 0001_init.py
```

思路与前文完全一致，只是收敛到插件内部：

1. 确认打包配置包含迁移目录（setuptools 的 `package_data`，hatchling 的 `include`/`artifacts`），这是最容易漏的一步；
2. 插件 `__init__.py` 中向 driver 注册 `on_startup` 回调，在回调里用独立的 `Config` 执行迁移——`script_location` 用
   `Path(__file__).parent / "migrations"` 定位到包内目录，数据库 URL 从 `nonebot.get_driver().config` 读取，调用依然是
   `asyncio.to_thread` 包裹的 `command.upgrade`；
3. **必须设置独立的 `version_table`**（例如 `signin_alembic_version`）。多个插件各自带迁移时，如果共用默认的
   `alembic_version` 表，版本记录会互相覆盖，这是内嵌方案最大的坑；
4. 迁移消息（`-m`）和 revision 命名统一带插件名前缀，如 `signin_init`、`signin_add_consecutive_days`
   ，用户排查时一眼能认出归属；同理，表名也统一带插件名前缀（如 `signin_users`），避免与其他插件或宿主项目撞表。

这种方式插件完全自治，版本演进由作者掌控；代价是每个插件都维护一套 env.py，且用户可能同时装着好几个各跑各迁移的插件。

### 7.3 方式二：注册到宿主 Base，由用户统一生成

另一种极端是插件 **不分发任何迁移文件**：约定宿主项目提供公共 `Base`（如本教程的 `app.db.Base`），插件的 `models.py`
基于它声明模型，文档中要求用户在 `env.py` 里 `import` 插件的 models 模块，让 `signin_users` 注册进宿主的 `Base.metadata`
，然后由用户自己执行 `alembic revision --autogenerate` 生成迁移。

优点是零迁移文件、零运行时逻辑，用户侧统一管理所有表；缺点同样明显：插件升级改了表结构，依赖用户重新 autogenerate
并人工核对，作者失去对版本演进的控制，也无法保证用户真的执行了这一步。适合内部插件或表结构极简单的场景。

### 7.4 成熟方案：nonebot-plugin-orm

如第 2 章所述，官方 `nonebot-plugin-orm` 已经系统性地解决了这个问题：插件作者把迁移目录声明给 orm 插件，由它统一接管 CLI
生成、启动时迁移与版本表管理，宿主项目里多个带表插件的迁移被纳入同一套机制。如果你的插件要公开发布，优先评估它；本教程的 DIY
方案更适合理解原理和私有插件。

## 第 8 章 常见坑与最佳实践

### 8.1 六个高频坑

**① 启动卡死：在 `on_startup` 里直接同步调 `command.upgrade`。**
现象：启动日志停在迁移处，bot 不响应任何消息。原因：`command.upgrade` 是同步阻塞调用，直接在事件循环里执行会占住
loop，所有协程排队。解法：用 `asyncio.to_thread` 丢进独立线程，即第 4 章 `app/migrate.py` 的写法。

**② `RuntimeError: asyncio.run() cannot be called from a running event loop`。**
现象：迁移一执行就抛这个异常。原因：`alembic init -t async` 生成的 env.py 内部用 `asyncio.run` 驱动异步迁移，而 `on_startup`
回调所在线程已经有一个运行中的事件循环。解法：同①——`to_thread` 开辟的新线程里没有运行中的 loop，两个问题一并解决。

**③ 换个目录启动就报找不到 `alembic.ini` 或 `script_location`。**
现象：本地 `python bot.py` 正常，systemd / Docker 里启动报路径错误。原因：`Config("alembic.ini")`
用了相对路径，依赖进程工作目录。解法：像冻结代码那样用 `Path(__file__).resolve()` 拼绝对路径，`script_location` 同理。

**④ `app.db` 导入即报错，拿不到 `database_url`。**
现象：启动时抛 `nonebot` 未初始化相关异常或配置属性不存在。原因：`app/db.py` 模块级调用 `nonebot.get_driver().config`，却在
`nonebot.init()` 之前被某个顶层 import 链提前触发。解法：插件顶层 `import app.db` 是允许的，前提是插件只经由
`nonebot.init()` 之后的 `nonebot.load_plugins` 进入 import 链（第 3 章的签到插件正是如此）；真正要避免的是任何在 `init()`
之前就触发 `app.db` 顶层代码的路径，比如在 `bot.py` 里手动提前 import 插件模块。对加载时机不确定的场景，才使用函数内延迟导入（如第
5 章 `bot.py` 在 `on_startup` 回调体内导入）。

**⑤ autogenerate 生成一堆 `drop_table`。**
现象：只想加一列，生成的迁移却要把 `signin_users` 全删掉。原因：`env.py` 忘了 `import` 插件的 models 模块，`Base.metadata`
里没有这些表，Alembic 认为数据库里多出来的表都该删。解法：`env.py` 显式导入所有模型模块，且每次 autogenerate 的结果必须人工
review 再执行。

**⑥ MySQL 迁移失败留下半成品。**
现象：迁移中途报错，重跑时又报「表已存在」，但 `alembic_version` 没更新。原因：MySQL 的 DDL
会隐式提交，无法随事务回滚。解法：按系列前作的处理流程——手工清理残留的表/列，`alembic stamp` 回失败前的版本，修好脚本后重新
upgrade。

### 8.2 最佳实践 checklist

1. 迁移统一放在 `on_startup`，且任何 Alembic 同步调用都用 `asyncio.to_thread` 包裹。
2. `alembic.ini` 与 `script_location` 一律使用基于 `__file__` 的绝对路径。
3. `app/db.py` 坚持在 `nonebot.init()` 之后导入，跨模块引用用函数内延迟导入。
4. `env.py` 显式 import 全部模型模块，autogenerate 结果人工 review 后才入库。
5. 数据库 URL 只从 `driver.config` 读取，任何脚本不写死连接串。
6. 建库（`ensure_database`）与建表（`migrate_to_head`）分两步，永远先库后表。
7. 多实例部署必须用 `GET_LOCK` 咨询锁串行化启动迁移。
8. 迁移失败 fail-fast 让进程退出，交给 systemd / Docker 重启，绝不跳过继续跑。
9. 表名、迁移消息带插件名前缀；多迁移环境并存时使用独立 `version_table`。
10. 生产流水线显式执行 `alembic upgrade head` 再发版，`on_startup` 迁移只作兜底；大表变更走 gh-ost / pt-osc。

### 8.3 结语

回顾全篇，启动时自动迁移的核心不过三件事：`ensure_database` 负责把 database 建出来，`migrate_to_head` 用
`asyncio.to_thread` 把 Alembic 安全地接进异步启动流程，`GET_LOCK` 保证多实例并发时只有一个在做迁移。配合系列前两篇——SQLAlchemy
2.0 异步模块打下的数据访问层、Alembic
教程建立的版本化迁移能力——你现在已经拥有一套从「写模型」到「新环境一键启动自愈」的完整方案：异步数据库模块 → 版本化迁移 →
启动时自动化。剩下的，就是把它用起来。
