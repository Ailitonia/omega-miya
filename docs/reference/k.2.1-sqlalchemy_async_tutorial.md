# SQLAlchemy 异步入门教程：FastAPI + MySQL 数据库模块实战

> 技术栈：Python 3.11+ / SQLAlchemy 2.0 / FastAPI / MySQL 8.0（InnoDB）/ asyncmy
>
> 本教程以一个可运行的「用户 + 转账」项目为主线，讲解如何为异步框架编写数据库模块，并重点解决两个核心问题：事务的 **原子性**
> （一组操作同生共死）与 **隔离性**（并发下的数据正确性）。

---

## 第 1 章 为什么异步框架需要异步数据库模块

FastAPI 之所以快，核心在于 asyncio 事件循环：一个线程里同时挂着成千上万个协程，谁在等待
IO，谁就主动让出执行权，让别的请求继续跑。但这一切有个前提——所有协程都必须遵守「不堵路」的规矩。一旦有人在事件循环里执行同步阻塞调用，整个循环就被卡死，所有并发请求一起排队。

### 1.1 同步驱动会阻塞事件循环

最常见的「堵路」方式就是直接在 FastAPI 里用 pymysql、psycopg2 这类同步驱动。看个对比：

```python
# 错误示范：同步驱动会卡住整个事件循环
import pymysql

@app.get("/users/{user_id}")
def get_user(user_id: int):
    conn = pymysql.connect(host="localhost", user="root",
                           password="password", database="demo")
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()
```

如果这个查询因为锁等待或慢索引花了 2 秒，那么这 2 秒内事件循环什么也干不了——服务器上正在处理的其他几百个请求全部原地等待。你花了异步框架的成本，得到的却是比同步框架更差的体验。

```python
# 正确姿势：异步驱动在等待 IO 时让出事件循环
@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()  # 需配合 response_model 使用（第 4 章详述）
```

`await` 的那一刻，协程挂起，事件循环立刻去服务其他请求；MySQL 返回数据后再被唤醒。同样 2 秒的慢查询，其他请求完全无感。

### 1.2 SQLAlchemy 的 asyncio 支持

SQLAlchemy 从 1.4 开始、在 2.0 中正式稳定了 asyncio 支持。它的原理一句话概括： **SQLAlchemy 内部仍是同步代码，通过 greenlet
在协程与同步上下文之间搭了一座桥，把底层的同步调用无缝切换到真正的异步驱动（如 asyncmy）上执行**，因此你写出的代码是
`await session.execute(...)` 这样的原生异步风格，而不是裹着 `run_in_executor` 的伪异步。

### 1.3 本教程要解决的三个问题

光会 `await` 还不够，写出一个生产可用的异步数据库模块，至少要回答三个问题：

1. **模块怎么写**：引擎、连接池、会话工厂怎么配，模型怎么声明，一次请求一个 session 怎么落地（第 3、4 章）。
2. **原子性怎么保证**：转账这类「多步操作同生共死」的场景，事务怎么开、怎么回滚（第 5 章）。
3. **隔离怎么处理**：并发请求同时改同一行数据时，悲观锁、乐观锁、原子 UPDATE 怎么选（第 6 章）。

我们从环境搭建开始，一步步把这个模块写出来。

## 第 2 章 环境准备与项目搭建

本章目标：装好依赖、建好数据库、搭出项目骨架，并让服务启动时自动建表。

### 2.1 依赖安装

建议使用 Python 3.11+，创建虚拟环境后执行：

```bash
pip install "fastapi[all]" "sqlalchemy[asyncio]>=2.0" asyncmy
```

三个包的分工：

- `fastapi[all]`：Web 框架全家桶，含 uvicorn、Pydantic v2 等。
- `sqlalchemy[asyncio]>=2.0`：SQLAlchemy 2.0 本体，`[asyncio]` extra 会顺带装上 greenlet——它是异步桥接的必需品，漏装会在首次
  `await` 时报错。
- `asyncmy`：MySQL 的异步驱动（基于 Cython，性能优于纯 Python 的 aiomysql）。如果你环境装不上 asyncmy，可用 aiomysql 替代，只需把数据库
  URL 的 `mysql+asyncmy://` 前缀改成 `mysql+aiomysql://`。

### 2.2 MySQL 8 准备

登录 MySQL 8 后创建数据库：

```sql
CREATE DATABASE demo
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

如果没有现成的 MySQL 8，用 Docker 起一个最省事：

```bash
docker run -d --name mysql8 -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=password mysql:8.0
```

两点说明：

- **为什么用 utf8mb4**：MySQL 旧的 `utf8` 编码最多只存 3 字节，存不下 emoji 和部分生僻字；`utf8mb4` 才是真正的
  UTF-8。我们后续的数据库 URL 里也会带上 `charset=utf8mb4`，客户端与服务端保持一致。
- **为什么是 InnoDB**：它是 MySQL 8 的默认引擎，也是唯一同时支持 **事务、行级锁、外键**的主流引擎。本教程第 5 章的原子性、第 6
  章的悲观锁/乐观锁全都建立在这些能力之上；如果你用的是 MyISAM 之类不支持事务的引擎，回滚会静默失效，数据正确性无从谈起。

### 2.3 项目目录结构总览

项目名为 `fastapi_sqla_demo`，结构如下：

```text
fastapi_sqla_demo/
├── app/
│   ├── __init__.py
│   ├── main.py              # 应用入口，lifespan 初始化
│   ├── db.py                # 数据库模块：引擎、会话工厂、get_db 依赖
│   ├── models.py            # 声明式模型：User、Account
│   ├── schemas.py           # Pydantic v2 请求/响应模型
│   └── routers/
│       ├── __init__.py
│       ├── users.py         # 用户 CRUD 接口
│       └── transfer.py      # 转账接口
└── requirements.txt
```

注意 `app/` 和 `app/routers/` 下的 `__init__.py` 不能省——我们的 import 全部使用 `from app.db import ...`
这样的绝对路径，缺少它们会导致包无法被识别。另外 `requirements.txt` 建议锁定版本，便于团队协作和部署复现：

```text
fastapi[all]>=0.110
sqlalchemy[asyncio]>=2.0
asyncmy>=0.2.9
```

贯穿全书的示例是「用户 + 转账」：两张表 `users(id, name, email, created_at)` 和 `accounts(id, user_id, balance, version)`
，其中 `version` 字段留给第 6 章做乐观锁演示。数据库连接串统一为：

```text
mysql+asyncmy://root:password@localhost:3306/demo?charset=utf8mb4
```

### 2.4 服务启动时建表

学习阶段我们不引入迁移工具，直接在 FastAPI 的 lifespan 里用 metadata 建表。`app/main.py` 的骨架：

```python
# app/main.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import engine, Base
import app.models  #  noqa: F401  确保模型被注册到 Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 启动时建表（幂等：已存在的表会跳过）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时释放连接池
    await engine.dispose()


app = FastAPI(title="fastapi_sqla_demo", lifespan=lifespan)
```

这段代码有两个关键点：

1. **`engine.begin()` 拿到的是 `AsyncConnection`，而 `create_all` 是同步方法**，所以要用 `conn.run_sync()` 把它送回同步上下文执行——这是
   SQLAlchemy 异步用法中处理「只有同步版本的工具方法」的标准套路。
2. **必须 import `app.models`**。`Base.metadata` 是靠模型类被定义时自动注册的，如果没人 import models 模块，`create_all`
   会一张表都不建，而且不报错。这类「静默建空库」是新手最常见的坑之一。

启动服务验证：

```bash
uvicorn app.main:app --reload
```

然后在 MySQL 里执行 `SHOW TABLES;`，应能看到 `users` 和 `accounts` 两张表。

**生产环境提示**：`create_all` 只会「建不存在的表」，不会修改已有表的结构——给模型加字段、改类型，它一概不管。因此它只适合学习和原型阶段；正式项目请使用
Alembic 做版本化迁移（`alembic revision --autogenerate`），让表结构的每一次变更都有据可查、可以回滚。本书为聚焦主题，后续章节仍沿用
lifespan 建表方式。

下一章我们正式编写 `app/db.py` 和 `app/models.py`，讲透引擎、连接池、会话工厂和声明式模型的每一个参数。

---

## 第 3 章 核心概念与数据库模块编写

上一章搭好了环境和目录，本章进入正题：编写整个项目的心脏——`app/db.py` 数据库模块。这个模块在第 3 章定稿后会被后续所有章节直接
import，所以值得逐行吃透。先认识四个核心对象，再看代码。

### 3.1 四个核心对象

SQLAlchemy 2.0 的异步用法里，你 99% 的时间只和这四个对象打交道：

- **AsyncEngine（异步引擎）**：由 `create_async_engine()` 创建，全局只建一次。它本身不是数据库连接，而是「连接池 +
  方言」的封装：对内维护一个连接池，对外负责把 Python 调用翻译成 MySQL 协议。可以把它理解为数据库的「总开关」。
- **async_sessionmaker（会话工厂）**：一个绑定了 engine、固化了一组配置（比如 `expire_on_commit`）的工厂类。每次调用
  `async_session_factory()` 就产出一个新的 AsyncSession。工厂全局一个，session 随用随造。
- **AsyncSession（异步会话）**：真正干活的「工作单元」（Unit of Work）。它内部维护身份映射（identity map）和变更追踪：你 `add()`
  进去的对象、查询出来的对象、改过的属性，都由它记账，最后由 `commit()` 一次性落库。 **它是并发不安全的**，必须做到「一次请求一个
  session」。
- **DeclarativeBase（声明式基类）**：所有 ORM 模型的基类。继承它的同时，SQLAlchemy 会把每个模型类的表结构登记到
  `Base.metadata` 中，建表、迁移都以此为依据。

四者的关系一句话概括： **一个 engine 配一个工厂，工厂为每个请求造一个 session，session 操作继承自 Base 的模型。**

### 3.2 逐行讲解 app/db.py

以下是定稿的数据库模块，后续章节直接 `from app.db import ...` 使用：

```python
# app/db.py
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "mysql+asyncmy://root:password@localhost:3306/demo?charset=utf8mb4"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**连接 URL**：`mysql+asyncmy://` 表示「MySQL 方言 + asyncmy 异步驱动」，这是异步的关键——驱动本身基于
asyncio，查询时事件循环可以切去服务其他请求。`charset=utf8mb4` 保证 emoji 等多字节字符不乱码。

**engine 参数逐个看**：

- `echo=False`：是否把每条 SQL 打到日志。开发时改成 `True` 非常有助于理解 SQLAlchemy 的行为，生产关掉。
- `pool_size=5`：连接池中 **常驻**的连接数，池子启动后会保持 5 条连接反复复用，避免每次请求都经历 TCP + MySQL 握手的开销。
- `max_overflow=10`：高并发时允许在 `pool_size` 之上临时多开 10 条连接，用完后释放。因此本配置最多同时支撑 5 + 10 = 15
  条连接；第 16 个并发请求会在池外排队，超过 `pool_timeout`（默认 30 秒）拿不到连接就报错。估算并发量时要以这个总和为准。
- `pool_pre_ping=True`：每次从池里 **取出**连接时，先执行一次轻量的 `SELECT 1`
  探测。如果连接已被服务端断开，就丢弃并换一条，对应用完全透明。代价是每次取连接多一个往返，换来的是杜绝「拿到死连接」这类玄学报错，非常值得。
- `pool_recycle=1800`：连接在池中存活超过 1800 秒就回收重建。它专门对付 MySQL 的 `wait_timeout`——MySQL 默认会断开空闲超过
  8 小时（`wait_timeout=28800`）的连接，但服务端断开时 **不会通知**连接池，池里那条连接就成了「僵尸」，下次使用直接报
  `Lost connection to MySQL server during query`。防御手段就是让 `pool_recycle` 明显小于 `wait_timeout`（1800 秒远小于 8
  小时，即使 DBA 把 `wait_timeout` 调小到 1 小时也安全），连接在被服务端杀死前先由客户端主动换新。`pool_pre_ping` 是兜底，
  `pool_recycle` 是主动预防，两者配合才稳妥。

**async_sessionmaker 参数**：

- `class_=AsyncSession`：明确工厂产出的是异步会话。
- `expire_on_commit=False`： **对异步用法至关重要**。默认值为 `True`，含义是 commit 之后把 session
  里所有对象的属性标记为「过期」，下次访问任何属性都会触发一次「刷新」查询。问题在于：同步代码里这次刷新是隐式发生的，你毫无感知；而异步代码里所有数据库
  IO 都必须 `await`，这种「访问属性 → 偷偷发起 IO」的隐式行为会直接抛出 `MissingGreenlet`（若 session 已关闭则是
  `DetachedInstanceError`），是新手最常踩的坑（第 7 章还会专门讲）。设为 `False` 后，commit
  只是提交事务，对象属性保留原值，可以安全地继续读取（比如序列化成响应）。代价是对象可能短时间内与库中最新值不一致，但我们的
  session 生命周期只有一个请求，影响为零。
- `autoflush=False`：关闭「查询前自动 flush」的隐式行为，何时把变更刷入数据库完全由代码显式控制（第 4 章会看到
  `await db.flush()`），行为更可预测。

**Base 与 get_db**：`Base` 目前空空如也，但它的 `metadata` 会收集所有模型定义。`get_db` 是 FastAPI 依赖，下一节详讲。

### 3.3 模型定义：Mapped + mapped_column

```python
# app/models.py
from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    version: Mapped[int] = mapped_column(default=0)
```

2.0 的风格是「类型注解驱动」：`Mapped[int]` 声明该列在 Python 侧是 `int`，同时让 mypy / IDE 能正确推断类型；`Mapped[str]` 不带
`Optional` 即隐含 `NOT NULL`。几个细节：

- `email` 上的 `unique=True` 是第 4 章处理「重复注册返回 409」的数据库依据。
- `created_at` 用 `server_default=func.now()`，即由 **MySQL 服务端**填默认值，INSERT 语句里根本不出现这一列。注意区分：
  `default=` 是 Python 侧在 INSERT 时填值，`server_default=` 是 DDL 里的 `DEFAULT NOW()`。
- 金额用 `Numeric(12, 2)` 映射到 Python 的 `Decimal`， **绝不用 float 存钱**，否则 0.1 + 0.2 的浮点误差迟早让你对不上账。
- `version` 字段现在先放着，第 6 章讲乐观锁时它是主角。
- `ForeignKey("users.id")` 建立外键，`index=True` 为按用户查账户的高频场景建索引。

### 3.4 get_db：一次请求一个 session

再回看 `get_db`，它是一个异步生成器，正好契合 FastAPI「yield 依赖」的语义：

1. 请求进来，`async_session_factory()` 造出全新 session，`async with` 保证用完关闭、连接归还连接池；
2. `yield session` 把它交给接口函数使用；
3. 接口正常返回 → `await session.commit()`，把本次请求的全部变更作为一个事务提交；
4. 接口抛任何异常（包括业务校验的 `HTTPException`）→ `await session.rollback()` 回滚后原样抛出，由 FastAPI 转成错误响应。

这就是「依赖注入托管事务」模式： **业务代码只管读写，commit / rollback 收口在依赖里**，天然保证一个请求要么全成功、要么全不生效。

最后强调一条铁律： **绝不能把 session 做成全局变量或单例跨请求共享**。原因有三：其一，AsyncSession 并发不安全，两个请求同时操作同一个
session 会产生不可预期的交错状态；其二，某个请求触发的异常会让 session 进入「待回滚」的半死状态，后续所有共享它的请求跟着陪葬；其三，session
的身份映射会随查询不断膨胀，长期存活的 session 就是内存泄漏。「工厂全局唯一，session 即用即弃」——记住这句话，第 7
章的坑清单里一半问题都源于违反它。

## 第 4 章 CRUD 实战：users 接口

概念备齐，本章用 users 资源把增删改查全部跑通。所有数据库操作都通过第 3 章的 `get_db` 注入 session，业务代码里不出现任何
commit / rollback。

### 4.1 Pydantic v2 schemas

先定义「进」和「出」两个模型，把接口契约和 ORM 模型解耦：

```python
# app/schemas.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: EmailStr

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime
```

要点是 `UserOut` 上的 `from_attributes=True`（Pydantic v2 写法，对应 v1 的 `orm_mode`）：它允许 Pydantic 直接从 ORM
对象的属性取值，于是接口里可以 `return user`（一个 `User` 实例），由 FastAPI 自动序列化。`EmailStr` 自带邮箱格式校验（
`fastapi[all]` 已包含依赖）。注意 `UserCreate` 故意不含 `id` 和 `created_at`——这两样由数据库生成，客户端无权指定。

为什么要单独定义 schemas，而不是直接把 `User` 模型当请求/响应体用？因为三者的生命周期和职责完全不同：请求体描述「客户端允许传什么」，响应体描述「服务端愿意暴露什么」，ORM
模型描述「表里存什么」。混在一起，要么把内部字段泄露给客户端，要么让客户端能篡改本不该由它决定的字段。 schemas
这一层薄薄的转换，换来的是清晰的接口契约。

### 4.2 创建用户：add + flush 与唯一冲突

```python
@router.post("", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(name=payload.name, email=payload.email)
    db.add(user)
    try:
        await db.flush()  # 立即发送 INSERT，但不提交事务
    except IntegrityError:
        raise HTTPException(status_code=409, detail="邮箱已被注册")
    await db.refresh(user)  # MySQL 无 RETURNING，显式取回 server_default 列
    return user
```

四个关键动作：

1. `db.add(user)` 只是把新对象挂进 session，此时尚未产生任何 SQL；
2. `await db.flush()` 把挂起的 INSERT 真正发给 MySQL——在 **当前事务内**执行，事务并未提交。这里要注意两类「数据库生成的值」行为不同：自增的
   `user.id` 会由驱动通过 `lastrowid` 直接回填到对象上；而 `created_at` 这类 `server_default` 列，因为 MySQL 不支持
   `INSERT ... RETURNING`，flush 后处于 **过期（expired）状态**——异步代码里直接访问它就会触发一次隐式的 SELECT 刷新，抛出第
   3 章讲过的 `MissingGreenlet`；
3. `await db.refresh(user)` 显式发一条 SELECT，把 `created_at` 等列的最新值取回对象。这一步不可省略，否则接口 `return user`
   后 FastAPI 用 `UserOut` 序列化时读取 `created_at`，正好踩中上面的雷（第 7 章还会系统梳理这类隐式 IO 陷阱）；
4. 如果邮箱撞上 `unique` 约束，MySQL 报错，驱动抛出 `IntegrityError`。我们捕获它转成语义化的 HTTP 409。异常抛到 `get_db`
   后事务被整体回滚，session 不会残留半截数据。

这正是第 3 章 `autoflush=False` 价值的体现：flush、refresh 的时机完全由代码显式控制，行为可预测。

### 4.3 查询：select、where 与分页

2.0 的查询从 `select()` 开始，执行用 `await db.execute(stmt)`，取结果用 `.scalars()` 系列方法（直接得到模型对象，而不是包一层的
Row 元组）：

```python
filters = []
if keyword:
    filters.append(User.name.like(f"%{keyword}%"))

total = await db.scalar(select(func.count()).select_from(User).where(*filters))
stmt = select(User).where(*filters).order_by(User.id).offset(offset).limit(limit)
result = await db.execute(stmt)
items = result.scalars().all()
```

分页的正确姿势是 **两条 SQL**：

- 一条 `select(func.count()).select_from(User).where(...)` 算总数，与列表查询共用同一套过滤条件；
- 一条加 `offset()` / `limit()` 取当前页。务必配合 `order_by()`，否则 MySQL 不保证翻页间顺序稳定，会出现「同一行在第二页又冒出来」。

`limit` 用 `Query(ge=1, le=100)` 封顶，防止客户端一次要十万行把服务拖垮。

取结果的几个方法容易混淆，这里一次说清：`result.scalars().all()` 返回模型对象的列表；`result.scalars().first()` 取第一个或
`None`；确定只有一行时用 `result.scalar_one_or_none()`；而 `await db.scalar(stmt)` 是「执行 + 取单个标量」的合体，上面用它直接拿到了
count 数字。共同点是都带 `scalar`——只要列里含模型实体，先 `scalars()` 剥掉 Row 外壳，代码会干净很多。

### 4.4 更新与删除：先查再改，查无此人 404

更新和删除遵循同一模式： **先按主键把对象查出来（`db.get()` 按主键查询，会命中身份映射，性能最好），不存在就返回
404；存在就改属性 / 标记删除，交给 get_db 统一提交。**

```python
@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.name = payload.name
    user.email = payload.email
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="邮箱已被注册")
    return user

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    await db.delete(user)   # 标记删除，commit 时生成 DELETE
```

改属性不需要任何额外调用——session 的变更追踪（dirty tracking）会自动发现 `user.name` 变了，flush / commit 时生成
UPDATE。更新邮箱同样可能撞唯一约束，所以更新路径也要兜 `IntegrityError`。

为什么强调「先查再改」而不是直接发 `update()` / `delete()` 语句？对单表按主键的操作，先 `db.get()`
有两个直接收益：一是能准确区分「资源不存在」（404）和「数据库错误」（500）；二是 `db.get()` 优先命中 session
的身份映射，同一请求内重复查同一行甚至不产生 SQL。批量更新、批量删除才轮到 `update()` / `delete()` 语句出场，那种场景我们会在第
6 章的原子 UPDATE 方案里见到。另外注意删除返回 204 时不带响应体，这是 REST 惯例，`status_code=204` 下 FastAPI 会忽略返回值。

### 4.5 完整代码与 curl 验证

完整的 `app/routers/users.py`：

```python
# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserPage

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(name=payload.name, email=payload.email)
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="邮箱已被注册")
    await db.refresh(user)  # MySQL 无 RETURNING，显式取回 server_default 列
    return user


@router.get("", response_model=UserPage)
async def list_users(
    keyword: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if keyword:
        filters.append(User.name.like(f"%{keyword}%"))

    total = await db.scalar(select(func.count()).select_from(User).where(*filters))
    stmt = select(User).where(*filters).order_by(User.id).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return UserPage(total=total or 0, items=result.scalars().all())


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.name = payload.name
    user.email = payload.email
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="邮箱已被注册")
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    await db.delete(user)
```

schemas.py 里补一个分页响应模型：

```python
class UserPage(BaseModel):
    total: int
    items: list[UserOut]
```

最后在 `app/main.py` 挂载路由。下面是与第 2 章 lifespan 建表逻辑合并后的完整版本，可直接整段复制：

```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, engine
import app.models  # noqa: F401  # 导入模型，把表结构登记到 Base.metadata
from app.routers import users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表（仅演示用，生产环境请改用 Alembic 迁移）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="fastapi_sqla_demo", lifespan=lifespan)
app.include_router(users.router)
```

注意 `import app.models` 这行看似「没用」，实则必须：不导入模型模块，`Base.metadata` 里就没有任何表定义，`create_all` 会建出一个空库。

启动 `uvicorn app.main:app --reload` 后逐条验证。建议把 `app/db.py` 里的 `echo` 临时改成 `True`，对照终端里打印的 SQL
观察每个接口实际执行了什么——创建接口能看到 flush 时先 INSERT、请求结束时 COMMIT；列表接口能看到先 COUNT 再 SELECT
LIMIT/OFFSET，这是理解 flush 与 commit 分工最直观的方式。

```bash
# 创建：返回 201，id 与 created_at 由数据库生成
curl -X POST http://127.0.0.1:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"name": "张三", "email": "zhangsan@example.com"}'
# {"id":1,"name":"张三","email":"zhangsan@example.com","created_at":"..."}

# 再发一次同样的请求：唯一约束生效，返回 409
# {"detail":"邮箱已被注册"}

# 分页查询
curl 'http://127.0.0.1:8000/users?offset=0&limit=10'
# {"total":1,"items":[...]}

# 更新
curl -X PUT http://127.0.0.1:8000/users/1 \
  -H 'Content-Type: application/json' \
  -d '{"name": "张三丰", "email": "zhangsan@example.com"}'

# 删除：返回 204 无响应体；再次查询该 id 返回 404
curl -i -X DELETE http://127.0.0.1:8000/users/1
curl http://127.0.0.1:8000/users/1
# {"detail":"用户不存在"}
```

这套验证还顺带覆盖了错误路径：重复邮箱 409、查无此人 404、非法分页参数被 `Query` 校验拦下返回 422。建议每条都亲手跑一遍，并留意一点：即使是
404 / 409 这类「失败」响应，`get_db` 里的 `except` 分支也执行了 rollback——事务边界始终干净，这正是收口设计的好处。

至此一套生产可用的异步 CRUD 就完成了。回顾一下本章最重要的认知：接口函数里 **没有** commit——业务代码只描述「要改什么」，事务的成败由
`get_db` 统一裁决。下一章的转账场景会进一步说明，为什么这个收口设计是原子性的基石。

---

## 第 5 章 事务原子性：让一组操作同生共死

### 5.1 什么是原子性：转账是最经典的例子

原子性（Atomicity）是事务的第一要义：一组数据库操作要么全部成功，要么全部失败，绝不允许只执行一半。转账是最经典的例子——从账户
A 扣 100 元，给账户 B 加 100 元，这两条 UPDATE 必须「同生共死」：

- 两条都成功：A 少 100，B 多 100，账目平衡；
- 任意一条失败：两条都回滚，账目回到原样。

最怕的是中间状态：A 的钱扣了，服务进程却在给 B 加钱之前崩溃了——此时数据库里凭空蒸发了 100 元。崩溃只是最显眼的触发方式，真实项目里更常见的元凶是：第二条
SQL 本身报错（约束冲突、类型错误）、网络闪断、连接被回收、甚至开发者自己中途 return
漏掉了第二步。没有事务保护时，这些「小概率事件」乘以请求的总量，就是必然会在生产环境踩中的坑。

数据库事务机制正是为此而生：把多条语句包进一个事务，commit 之前所有修改都只是「暂存」，由 InnoDB 的 undo log
记下旧值，一旦事务失败或连接中断，数据库自动把已做的修改整体撤销。事务的四大特性（ACID）里，原子性排第一是有道理的——它是其余特性的地基，也是应用代码唯一能「免费」获得强保证的地方：你不需要写任何补偿逻辑，只需要正确地划定事务边界。对应用层来说，我们要做的一件事是：
**不要把一次业务操作拆到多个事务里，也不要在事务成功之前就对外宣告成功**。

### 5.2 SQLAlchemy 的两种事务写法

**写法一：依赖注入托管（第 3 章已定稿）。** 回顾第 3 章的 `get_db` 依赖：`yield` 出 session 后，请求正常结束就 `commit()`，抛异常就
`rollback()` 并重新抛出。也就是说， **一次 HTTP 请求天然就是一个事务边界**，路由函数里只管 `add`、改字段、`execute`
，提交与回滚由依赖统一兜底。这种写法适合绝大多数「单请求单事务」的接口，第 4 章的 users CRUD 走的就是这条路。本章不再重复贴代码，直接
`from app.db import get_db` 使用。

**写法二：显式 `session.begin()`。** 当你需要在请求内部精确控制事务边界（比如事务只占请求的一小段，或者需要手动划分多个事务），可以显式使用：

```python
async with session.begin():
    # 这里面的所有操作属于同一个事务
    ...
# 正常退出 -> commit；抛出异常 -> rollback 并把异常继续抛出
```

`session.begin()` 是一个异步上下文管理器：正常退出时自动提交，块内抛出任何异常都会先回滚再原样抛出， **绝不吞异常**
。注意两点：其一，必须在 session 尚未开启事务（即还没有执行过任何 SQL）时调用，否则会报 `A transaction is already begun`；其二，它与
`get_db` 不冲突——块内已提交，`get_db` 末尾的 `commit()` 是空操作。

如果需要在事务内部设置「部分撤销点」，可以用 savepoint：

```python
async with session.begin():          # 外层事务
    ...
    try:
        async with session.begin_nested():  # SAVEPOINT sp1
            ...
    except SomeExpectedError:
        pass  # 只回滚到 sp1，外层事务不受影响，可继续提交
```

`begin_nested()` 对应数据库的 `SAVEPOINT`，适合「批量导入中容忍个别行失败」这类场景。注意 savepoint
只能在已有事务内使用，并且它回滚的是「部分操作」，业务语义是否允许部分成功要自己想清楚——转账场景就绝不能用它容忍单步失败。

**两种写法如何取舍？** 原则是：默认用写法一（`get_db`
托管），只有当事务边界与请求边界不一致时才用写法二。典型场景有三种：请求里要先做一段只读查询、再把核心写入压缩进一个短事务；一个请求需要先后提交两个独立事务（如先落日志再处理业务）；或者需要
savepoint。混用两者也完全合法，唯一要记住的是 `session.begin()` 必须在第一条 SQL 之前调用。

### 5.3 完整的转账接口

下面给出本章的完整代码 `app/routers/transfer.py`。要点：显式 `session.begin()` 包住「扣款 + 加款」，先查账户并校验余额，余额不足抛
`HTTPException` 触发回滚；为了演示回滚效果，请求体里留了一个 `simulate_crash` 开关，在扣款之后、加款之前人为制造异常。

```python
# app/routers/transfer.py
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Account

router = APIRouter(prefix="/transfer", tags=["transfer"])


class TransferIn(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(gt=0, le=Decimal("1000000"))
    simulate_crash: bool = False  # 仅用于演示回滚，生产环境删除


@router.post("")
async def transfer(payload: TransferIn, session: AsyncSession = Depends(get_db)):
    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(400, "转出与转入账户不能相同")

    async with session.begin():
        result = await session.execute(
            select(Account).where(
                Account.id.in_([payload.from_account_id, payload.to_account_id])
            )
        )
        accounts = {a.id: a for a in result.scalars()}
        from_acc = accounts.get(payload.from_account_id)
        to_acc = accounts.get(payload.to_account_id)
        if from_acc is None or to_acc is None:
            raise HTTPException(404, "账户不存在")
        if from_acc.balance < payload.amount:
            raise HTTPException(400, "余额不足")

        # 第一步：A 扣款
        from_acc.balance -= payload.amount

        if payload.simulate_crash:
            # 人为制造崩溃：此刻 A 的钱已经"扣了"，B 还没收到
            raise RuntimeError("模拟扣款后服务崩溃")

        # 第二步：B 加款
        to_acc.balance += payload.amount
    # session.begin() 正常退出即提交；上面任何异常都会整体回滚

    return {
        "from": {"id": from_acc.id, "balance": str(from_acc.balance)},
        "to": {"id": to_acc.id, "balance": str(to_acc.balance)},
    }
```

在 `app/main.py` 里挂载路由：`app.include_router(transfer.router)`。接下来准备两个账户。注意 `accounts.user_id` 有外键约束，请
**先通过第 4 章的创建用户接口新建两个用户（确保其 id 分别为 1、2），再插入以下账户数据**，否则会触发外键报错（ERROR 1452）：

```bash
mysql> INSERT INTO accounts (user_id, balance, version)
       VALUES (1, 1000.00, 0), (2, 500.00, 0);
```

正常转账 100 元：

```bash
$ curl -s -X POST http://127.0.0.1:8000/transfer \
    -H "Content-Type: application/json" \
    -d '{"from_account_id": 1, "to_account_id": 2, "amount": "100"}'
{"from":{"id":1,"balance":"900.00"},"to":{"id":2,"balance":"600.00"}}
```

现在制造一次崩溃——扣款之后、加款之前抛异常：

```bash
$ curl -s -X POST http://127.0.0.1:8000/transfer \
    -H "Content-Type: application/json" \
    -d '{"from_account_id": 1, "to_account_id": 2,
         "amount": "100", "simulate_crash": true}'
{"detail":"Internal Server Error"}   # HTTP 500

$ curl -s -X POST http://127.0.0.1:8000/transfer \
    -H "Content-Type: application/json" \
    -d '{"from_account_id": 1, "to_account_id": 2, "amount": "10000"}'
{"detail":"余额不足"}              # HTTP 400：业务校验失败同样整体回滚
```

再查数据库，余额仍是 `900.00` 和 `600.00`：

```sql
mysql> SELECT id, balance, version FROM accounts;
+----+---------+---------+
| id | balance | version |
+----+---------+---------+
|  1 |  900.00 |       0 |
|  2 |  600.00 |       0 |
+----+---------+---------+
```

扣款语句虽然执行过，但异常让 `session.begin()` 回滚了整个事务，A 的钱分文未少。余额不足时同理：抛出的 `HTTPException` 一路穿透
`begin` 块和 `get_db`，回滚后原样返回 400。这就是原子性： **失败的操作就像从未发生过**。

### 5.4 两个反例，都是血的教训

**反例一：边操作边 commit。** 有人觉得「早点提交能减少锁占用」，于是写成：

```python
from_acc.balance -= amount
await session.commit()      # 第一次提交：A 的钱已扣，落库了
# ……此时进程崩溃 / 机器断电……
to_acc.balance += amount
await session.commit()      # 永远执行不到
```

两次 commit 之间不是原子的。第一次提交后扣款已经永久生效，第二次提交前的任何崩溃都会让 B 永远收不到钱——100
元凭空消失。更要命的是这种错误在测试环境极难暴露：功能测试一切正常，只有真实崩溃（或第二条语句偶发报错）才触发，等你发现账目对不上时往往已经积累了一串脏数据，只能靠人工对账逐笔追回来。记住铁律：
**一个业务动作只允许有一个 commit 点，且在动作的最后**。

**反例二：在 `begin` 块外吞掉异常。** `session.begin()` 遇到异常会先回滚再重新抛出，如果你在外面把它接住吃掉：

```python
try:
    async with session.begin():
        ...
        raise ValueError("余额不足")
except ValueError:
    pass  # 事务已回滚，但调用方浑然不知，接口照样返回 200
```

结果是「静默回滚」：用户收到成功响应，数据库里却什么都没改，排查时对着日志和数据库两边对不上，极其折磨。要么不捕获，要么捕获后转成一个明确的失败响应（如
400/409），绝不能让回滚与对外结果不一致。

### 5.5 长事务危害：事务里绝不调用外部 HTTP API

事务持有的不只是几条 SQL，还有行锁、连接池里的一个连接，以及不断增长的 undo
log。事务每多存活一秒，锁就多占一秒，其他事务就多等一秒，连接池里的可用连接也少一个；undo log 膨胀还会拖慢整个实例的 MVCC
快照链。如果事务里夹杂了调用第三方支付、发短信之类的 HTTP 请求，一次网络抖动就能把事务拖上数秒甚至超时：行锁堆积引发大量锁等待（最终满屏
`Lock wait timeout exceeded`），连接池被占满（`pool_timeout` 报错，见第 7 章），整个服务雪崩。慢查询同理——事务里混入一条全表扫描，效果等同调了一次慢接口。

正确姿势是把「准备数据」和「落库」分开：

```python
# 错误：HTTP 调用夹在事务里，锁和时间都被网络延迟绑架
async with session.begin():
    from_acc.balance -= amount
    await notify_bank_api(...)     # 千万别这么做
    to_acc.balance += amount

# 正确：先在事务外完成外部调用与数据准备，事务内只做数据库操作
pay_result = await notify_bank_api(...)
async with session.begin():
    ...  # 只含 SQL，毫秒级结束
```

事务的黄金标准是： **只装 SQL，快进快出**。

## 第 6 章 事务隔离：并发下的数据正确性

### 6.1 隔离级别速览

第 5 章解决了「单个事务内的同生共死」，本章解决另一个问题： **多个事务并发执行时，彼此能看到对方多少未提交的中间状态**。SQL
标准定义了四种隔离级别，以及它们分别能挡住哪些并发异常：

| 隔离级别                       | 脏读   | 不可重复读 | 幻读       |
|--------------------------------|--------|------------|------------|
| READ UNCOMMITTED               | 可能   | 可能       | 可能       |
| READ COMMITTED                 | 不可能 | 可能       | 可能       |
| REPEATABLE READ（InnoDB 默认） | 不可能 | 不可能     | 通常可避免 |
| SERIALIZABLE                   | 不可能 | 不可能     | 不可能     |

三个异常各一句话：

- **脏读**：读到了别的事务尚未提交、随后可能被回滚的数据，相当于信了「草稿」；
- **不可重复读**：同一事务内两次读同一行，结果不一样——期间被别的事务改了并提交；
- **幻读**：同一事务内两次执行同一个范围查询，第二次冒出了新行——别的事务插入并提交了符合条件的记录。

MySQL InnoDB 默认 REPEATABLE READ，并且借助一致性快照（MVCC）和 next-key lock，在绝大多数场景下连幻读也一并挡住了，比标准定义更强。PostgreSQL
的默认则是 READ COMMITTED，迁移数据库时要留意差异。

### 6.2 并发转账的竞态：读-改-写丢失更新

隔离级别再高，也管不住应用层自己制造的「读-改-写」竞态。看第 5 章转账代码里这段逻辑：`SELECT` 读出余额 → Python 里做减法 →
`UPDATE` 写回。假设 A 余额 1000 元，两个请求同时给 A 扣款——请求一扣 100，请求二扣 50：

| 时刻 | 请求一（扣 100）    | 请求二（扣 50）     |
|------|---------------------|---------------------|
| t1   | 读到 balance = 1000 | 读到 balance = 1000 |
| t2   | 算出 900，写回 900  | 算出 950，写回 950  |
| t3   | 提交                | 提交                |

两个事务都合法提交，没有脏读、没有回滚，但最终余额是 950——请求一写入的 900 被请求二覆盖，A 白白少扣了 100 元。这就是
**丢失更新（Lost Update）**：后提交者覆盖了先提交者的结果，而双方对此都毫无察觉。MVCC
只保证「读不阻塞写、写不阻塞读」，并不阻止两个事务基于同一份旧快照各自改写。要堵住这个洞，需要在应用层三选一：悲观锁、乐观锁、原子
UPDATE。

### 6.3 方案一：悲观锁 `with_for_update()`

悲观锁的思路是「先下手为强」：读取时就给行加排他锁（`SELECT ... FOR UPDATE`），其他事务想改同一行必须排队等锁，读-改-写被强制串行化：

```python
@router.post("/pessimistic")
async def transfer_pessimistic(
    payload: TransferIn, session: AsyncSession = Depends(get_db)
):
    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(400, "转出与转入账户不能相同")

    async with session.begin():
        # 关键：with_for_update() 对选中的行加排他锁，直到事务结束
        result = await session.execute(
            select(Account)
            .where(Account.id.in_([payload.from_account_id, payload.to_account_id]))
            .order_by(Account.id)          # 固定加锁顺序，降低死锁概率
            .with_for_update()
        )
        accounts = {a.id: a for a in result.scalars()}
        from_acc = accounts.get(payload.from_account_id)
        to_acc = accounts.get(payload.to_account_id)
        if from_acc is None or to_acc is None:
            raise HTTPException(404, "账户不存在")
        if from_acc.balance < payload.amount:
            raise HTTPException(400, "余额不足")

        from_acc.balance -= payload.amount   # 持锁期间安全地读-改-写
        to_acc.balance += payload.amount

    return {"from": str(from_acc.balance), "to": str(to_acc.balance)}
```

并发请求二执行到同一条 `SELECT ... FOR UPDATE` 时会被阻塞，直到请求一提交释放锁；它再读到的就是 900 而不是
1000，丢失更新不复存在。注意三个细节：锁必须在事务内获取（`FOR UPDATE` 脱离事务立即释放，这正是上面必须用 `session.begin()`
的原因）；涉及多行时按固定顺序（如 id 升序）加锁，避免两个事务交叉持锁造成死锁；行锁依赖索引命中，若 `where` 条件走了全表扫描，InnoDB
会升级为锁大量行甚至全表。

### 6.4 方案二：乐观锁 version 字段

乐观锁的思路相反：「先干活，提交前检查有没有人动过」。`accounts` 表里的 `version` 字段就是为此准备的——每次更新把 version
加一，并把「读到的旧 version」作为更新条件；条件不成立说明数据已被别人改过，本次更新作废：

```python
from sqlalchemy import update

@router.post("/optimistic")
async def transfer_optimistic(
    payload: TransferIn, session: AsyncSession = Depends(get_db)
):
    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(400, "转出与转入账户不能相同")

    async with session.begin():
        from_acc = await session.get(Account, payload.from_account_id)
        to_acc = await session.get(Account, payload.to_account_id)
        if from_acc is None or to_acc is None:
            raise HTTPException(404, "账户不存在")
        if from_acc.balance < payload.amount:
            raise HTTPException(400, "余额不足")

        # 条件更新：只有 version 仍等于读到的旧值才生效
        stmt = (
            update(Account)
            .where(Account.id == from_acc.id, Account.version == from_acc.version)
            .values(
                balance=from_acc.balance - payload.amount,
                version=from_acc.version + 1,
            )
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            # version 对不上：数据已被并发事务修改，让客户端重试
            raise HTTPException(409, "数据已被并发修改，请重试")

        stmt = (
            update(Account)
            .where(Account.id == to_acc.id, Account.version == to_acc.version)
            .values(
                balance=to_acc.balance + payload.amount,
                version=to_acc.version + 1,
            )
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(409, "数据已被并发修改，请重试")

    return {"detail": "ok"}
```

并发冲突时，失败方的 `rowcount` 为 0，事务回滚并返回 409，客户端（或网关）收到 409 后重新读取最新余额和 version
再试一次。冲突概率低时重试成本几乎为零，这就是「乐观」的含义。优点是完全不加锁、无死锁风险；缺点是热点行冲突激烈时重试会退化成空转，且每一笔更新都要多读一次
version。

### 6.5 方案三：原子 UPDATE

其实针对「扣款」这个具体场景，还有一个更彻底的办法： **根本不要在 Python 里做减法，把校验和计算全部压进一条 SQL**：

```python
@router.post("/atomic")
async def transfer_atomic(
    payload: TransferIn, session: AsyncSession = Depends(get_db)
):
    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(400, "转出与转入账户不能相同")

    async with session.begin():
        # 一条语句同时完成"余额校验 + 扣款"，单语句天然原子
        stmt = (
            update(Account)
            .where(
                Account.id == payload.from_account_id,
                Account.balance >= payload.amount,   # 余额不足则匹配不到行
            )
            .values(balance=Account.balance - payload.amount)
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(400, "余额不足或账户不存在")

        stmt = (
            update(Account)
            .where(Account.id == payload.to_account_id)
            .values(balance=Account.balance + payload.amount)
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(404, "收款账户不存在")

    return {"detail": "ok"}
```

`UPDATE accounts SET balance = balance - 100 WHERE id = 1 AND balance >= 100` 是一条独立语句，InnoDB 对单条语句的执行为其隐式加锁，
**不存在「读到旧值再写回」的时间窗**，天然免疫丢失更新；`balance >= amount` 条件把余额校验也下沉到数据库，余额不足时匹配不到任何行，
`rowcount` 为 0，直接报 400。代码最短、无锁等待、无重试，是「金额增减」这类场景的首选。它的局限也很明显：只适合能在单条 SQL
里表达的运算；如果更新前需要根据旧值做复杂业务判断（比如发积分、记流水依赖扣款前余额），还是得回到方案一或二。

### 6.6 调整隔离级别

少数场景需要改默认隔离级别。最直接的方式是在创建引擎时指定：

```python
engine = create_async_engine(
    DATABASE_URL,
    isolation_level="READ COMMITTED",   # 对 pool 内所有连接生效
    # 其余参数同第 3 章……
)
```

READ COMMITTED 的好处是快照读能看到最新已提交数据、锁冲突更少，适合以查询为主、且能接受「同一事务内两次读结果不同」的报表类服务；许多从
PostgreSQL 迁来的团队也会统一调成它以减少心智差异。也可以只对个别会话临时调整：

```python
async with async_session_factory() as session:
    await session.connection(
        execution_options={"isolation_level": "SERIALIZABLE"}
    )
    ...
```

什么时候需要 SERIALIZABLE？当「不存在某条记录」本身也是业务判断依据时——典型如库存扣减前先查「还有没有库存」、对账时断言「某时间段内没有重复流水」。REPEATABLE
READ 的快照读可能让你看不到并发事务刚插入的行，SERIALIZABLE 则把快照读退化为加锁读，用锁彻底封死幻读。代价是并发度骤降、死锁概率上升，因此只应小范围、短事务地使用，能用唯一约束或原子
UPDATE 解决的场景就不要动用它。

### 6.7 三个方案对比

| 维度     | 悲观锁 `with_for_update()`       | 乐观锁 version 字段                | 原子 UPDATE                  |
|----------|----------------------------------|------------------------------------|------------------------------|
| 核心思路 | 先加锁再读写，强制串行           | 先更新再校验 version，冲突重试     | 校验与计算压进单条 SQL       |
| 适用场景 | 冲突频繁、逻辑复杂、需读旧值判断 | 冲突少、读多写少                   | 余额/库存等纯数值增减        |
| 优点     | 行为确定，无重试，语义直观       | 不加锁，无死锁，吞吐高             | 代码最短，天然原子，无锁等待 |
| 缺点     | 锁等待降低并发，有误用死锁风险   | 冲突高时重试空转；需客户端配合重试 | 表达力有限，无法承载复杂判断 |
| 失败表现 | 等待或死锁超时                   | 409，客户端重试                    | rowcount=0，立即失败         |

经验法则： **能用原子 UPDATE 就不用锁**；需要读旧值做判断时，冲突少用乐观锁、冲突多用悲观锁。三种手段都要求第 5
章的原子性打底——无论选哪条路，扣款和加款永远待在同一个事务里。

---

## 第 7 章 常见坑与排错

异步 SQLAlchemy 的报错往往出现在「看起来没问题」的代码上。本章按出现频率梳理五个坑，每个都给出报错现象、根因和正确写法。

### 7.1 MissingGreenlet：异步下没有「自动」懒加载

报错信息：

```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
can't call await_only() here. Was IO attempted in an unexpected place?
```

原因：同步版 SQLAlchemy 里，访问未加载的关联或过期属性会自动补发一条 SQL（隐式 IO）；异步版的 IO 必须在 greenlet
桥接内发生，而你在普通协程上下文里直接访问属性，桥接没启动，于是抛出 `MissingGreenlet`。两个高发场景：`commit`
之后访问被过期的属性（这正是第 3 章 `expire_on_commit=False` 存在的原因），以及访问 `relationship` 触发懒加载。

正确写法：查询时就用 `selectinload` 一次性预加载，绝不在序列化阶段碰未加载的属性：

注意：以下代码块中给 `User` 补充的 `accounts` 关系 **仅为本节的临时扩展（演示后可移除）**，不属于第 3 章定稿的
models.py；若要在自己项目里使用，需额外补一行 `from sqlalchemy.orm import relationship`：

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import User

# 临时扩展（演示后可移除），models.py 中需补 from sqlalchemy.orm import relationship：
#   accounts: Mapped[list["Account"]] = relationship()
stmt = (
    select(User)
    .options(selectinload(User.accounts))  # 预加载，避免懒加载触发隐式 IO
    .where(User.name == "Alice")
)
result = await db.execute(stmt)
user = result.scalar_one()

for account in user.accounts:  # 已加载完毕，纯内存访问，不会再发 SQL
    print(account.balance)
```

`selectinload` 用第二条 `SELECT ... WHERE user_id IN (...)` 批量取回关联数据，既避免 N+1
又完全适配异步。记住一句话：异步世界里「用到才查」的懒加载不存在，要么预加载，要么显式 join。

### 7.2 跨请求共享 session

错误写法——把 session 挂到模块级变量：

```python
# 千万别这么干
session = async_session_factory()
```

现象：低并发时一切正常，压测一上来就灵异不断——`sqlalchemy.exc.InvalidRequestError: This session is in 'prepared' state`
、一个请求读到另一个请求尚未提交的数据、响应内容互相串。原因：`AsyncSession` 是「工作单元」，内部持有单一连接和一套事务状态机，本身不是并发安全的；多个协程同时驱动同一个
session，状态机必然错乱。

正确写法：一个请求一个 session，用第 3 章定稿的 `get_db` 依赖注入，请求结束 session 自动关闭、连接归还连接池：

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User

@router.get("/users/{user_id}")
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    ...
```

同理，也不要把 session 存进 `app.state` 或全局字典里复用。

### 7.3 连接池打满：QueuePool timeout

报错信息：

```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached,
connection timed out, timeout 30.00
(Background on this error at: https://sqlalche.me/e/20/3o7r)
```

含义：`app/db.py` 里 `pool_size=5`、`max_overflow=10`，即最多同时借出 15 条连接；第 16 个并发请求开始排队，等满
`pool_timeout`（默认 30 秒）仍拿不到连接就抛这个错。

处理顺序建议：

1. 先查「谁占着连接不放」。最常见的是长事务——第 5 章反复强调的「事务里调用外部 HTTP API」，以及手工创建却忘记关闭的
   session。修代码比加连接有效得多。
2. 确认没有泄漏后，再按并发量调参：池上限应略大于单实例并发峰值，且所有应用实例的池子上限之和不能超过 MySQL 的
   `max_connections`。
3. 调小 `pool_timeout` 让请求快速失败（返回 503），好过所有请求挂 30 秒：

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,        # 常驻连接
    max_overflow=20,     # 峰值临时连接：最多并发 30 条
    pool_timeout=5,      # 等 5 秒拿不到就抛错，快速失败
    pool_pre_ping=True,
    pool_recycle=1800,
)
```

### 7.4 MySQL 把空闲连接掐了

报错信息（常在服务跑了一夜、早高峰第一波请求时集中出现）：

```
sqlalchemy.exc.OperationalError: (asyncmy.errors.OperationalError)
(2013, 'Lost connection to MySQL server during query')
```

原因：MySQL 的 `wait_timeout`（默认 28800 秒，即 8 小时）会主动断开长时间空闲的 TCP 连接，但应用侧连接池对此毫不知情，把这条「尸体连接」借给你，一执行查询就炸。

`app/db.py` 里的两个参数正是为此而设：

- `pool_pre_ping=True`：每次从池中借出连接前先发一个轻量的 `SELECT 1` 探测，发现连接已断就自动换一条。开销极小，生产环境强烈建议常开。
- `pool_recycle=1800`：连接存活超过 1800 秒就主动回收重建。注意它必须小于服务端的 `wait_timeout`——如果设成 7200 而服务端
  3600 就断连，回收永远跑在断连之后，形同虚设。

### 7.5 混用同步驱动：事件循环被静默阻塞

现象：没有任何报错，但压测时吞吐量断崖式下跌——一个慢查询执行期间，所有请求（哪怕不查库）一起卡住，事件循环「假死」。

错误写法：

```python
# 错误一：连接串用了同步驱动
DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/demo"

# 错误二：在 async 路由里直接用同步库
import pymysql
conn = pymysql.connect(host="localhost", user="root", password="password")
conn.cursor().execute("SELECT SLEEP(5)")  # 整个事件循环陪它睡 5 秒
```

原因：pymysql 的每次网络读写都是阻塞调用，会直接把事件循环线程占住，事件循环上挂着的几百个协程只能一起干等。这也是第 1
章强调「异步框架必须配异步驱动」的根本原因。

正确做法：全链路使用异步驱动 asyncmy（连接串 `mysql+asyncmy://`）；实在绕不开某段同步阻塞代码（老 SDK、CPU
密集的计算），把它丢到线程池执行，别碰事件循环：

```python
import asyncio

result = await asyncio.to_thread(blocking_legacy_call, arg1, arg2)
```

## 第 8 章 测试与最佳实践小结

### 8.1 接口测试：pytest-asyncio + httpx

测试的两条铁律：用独立的测试库（`demo_test`），绝不碰开发库；每个用例在一条连接的事务里运行、结束时整体回滚，用例之间零残留、与执行顺序无关。

先安装依赖并建测试库：

```bash
pip install pytest pytest-asyncio httpx
mysql -uroot -p -e "CREATE DATABASE demo_test CHARACTER SET utf8mb4"
```

开启 pytest-asyncio 自动模式，省去每个用例手写 `@pytest.mark.asyncio`：

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
```

核心 fixture（`tests/conftest.py`）——事务回滚隔离模式：

```python
# tests/conftest.py
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import Base, get_db
from app.main import app

TEST_DATABASE_URL = (
    "mysql+asyncmy://root:password@localhost:3306/demo_test?charset=utf8mb4"
)
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db():
    # 测试库建表（httpx 的 ASGITransport 不会触发应用 lifespan，需自己建）
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session():
    # 连接内开启外层事务，用例结束整体 rollback：数据不落地
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        yield session
        await session.close()
        await trans.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session  # 注意：不 commit

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

这个模式的要点：`connect()` 之后先 `begin()` 一条外层事务，session 以 `create_savepoint` 模式加入，因此用例里业务代码的所有
`commit()` 实际上只是释放保存点，真正的写入随 `trans.rollback()` 一起消失；`override_get_db` 把应用的 `get_db` 替换成测试
session 且故意不提交，业务代码零改动、无感知。

为什么选回滚隔离而不是「每个用例重建表」？一是快：建表、删表是
DDL，几百个用例跑下来差距是分钟级对毫秒级；二是行为一致：回滚模式下业务代码走的仍是正常的事务提交路径，不需要为测试写任何分支。代价是它无法覆盖「跨事务」场景——比如第
6 章隔离级别、悲观锁并发效果这类必须真实提交才能观察的行为，需要单独开一组测试，用真实提交加用例后显式清理数据的方式来写。

测试用例（`tests/test_users.py`）：

```python
# tests/test_users.py
async def test_create_user(client):
    resp = await client.post(
        "/users", json={"name": "Alice", "email": "alice@example.com"}
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "alice@example.com"


async def test_duplicate_email_returns_409(client):
    payload = {"name": "Bob", "email": "bob@example.com"}
    assert (await client.post("/users", json=payload)).status_code == 201
    # 唯一约束冲突，第二次创建返回 409
    assert (await client.post("/users", json=payload)).status_code == 409
```

`pytest -v` 跑起来后可以发现：无论跑多少遍，`demo_test` 里始终查不到 Alice 和 Bob——这正是回滚隔离想要的效果。日常开发建议配合
`-x`（首个失败即停）快速定位问题；CI 流水线上则可以加一个临时 MySQL 容器，整套测试无需任何手工准备即可运行。

### 8.2 最佳实践清单（10 条）

最后，用 10 条 checklist 收束全文，上线前逐条对照：

1. 异步框架必须配异步驱动：连接串用 `mysql+asyncmy://`，事件循环里绝不出现 pymysql 等同步调用。
2. 一个请求一个 session，用 `get_db` 依赖管理生命周期，绝不把 session 挂到模块级变量或 `app.state` 上共享。
3. `async_sessionmaker` 固定设置 `expire_on_commit=False`，避免 commit 后访问属性触发隐式 IO 报 `MissingGreenlet`。
4. 关联数据一律用 `selectinload`/`joinedload` 预加载，异步下没有懒加载这回事。
5. 多步写操作必须包在同一个事务里（`async with session.begin():`），要么全部成功，要么整体回滚，绝不边操作边 commit。
6. 事务内不做慢操作：不调外部 HTTP API、不 sleep，尽量缩短持锁和占用连接的时间。
7. 并发写同一行数据时，按场景三选一：悲观锁 `with_for_update()`、乐观锁 version 字段加 rowcount 校验、或原子
   `UPDATE ... WHERE balance >= amt`。
8. 引擎固定配置 `pool_pre_ping=True`，且 `pool_recycle` 必须小于 MySQL 的 `wait_timeout`。
9. 按并发量规划 `pool_size + max_overflow`，出现 QueuePool timeout 先查连接泄漏和长事务，再考虑调参。
10. 生产环境用 Alembic 管理表结构迁移；测试用独立测试库 + 事务回滚 fixture 隔离用例，保证测试可重复、无副作用。
