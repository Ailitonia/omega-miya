# Alembic 版本化迁移详细教程：FastAPI + SQLAlchemy 2.0 异步 + MySQL 实战

> 技术栈：Python 3.11+ / Alembic 1.13+ / SQLAlchemy 2.0 / FastAPI / MySQL 8.0（InnoDB）/ asyncmy
>
> 本教程是《SQLAlchemy 异步入门教程》的姊妹篇，延续其贯穿项目 `fastapi_sqla_demo`，讲解如何为异步项目引入 Alembic 版本化迁移：从
> env.py 异步配置、autogenerate 正确使用，到数据迁移、多人协作分支合并，再到生产环境的 Expand-Contract 发布与 CI 集成。
>
> **版本号约定**：Alembic 默认生成随机十六进制 revision ID（如 `3f8c1a2b9d01`），本教程用「0001、0002……」作为版本顺序的简称指代，正文中
> ID 与简称的对照以注释形式标注。

---

## 第 1 章 为什么需要版本化迁移

在前作里，我们的建表方式很「偷懒」：在 lifespan 中执行 `Base.metadata.create_all`，应用一启动表就自动建好。对学习 Demo
这很舒服，但项目一旦进入真实迭代就走不通了。

### 1.1 回顾：create_all 的四大局限

`create_all` 并没有错，它只是「建表工具」，不是「结构管理工具」：

1. **不会修改已存在的表。** 它的语义是「不存在就创建，已存在就跳过」。给 `User` 模型加了 `phone` 字段，重启后 `users`
   表纹丝不动——它不会帮你 `ALTER TABLE`，直到某个查询报 `Unknown column` 才暴露。
2. **没有版本记录。** 数据库当前结构对应代码的哪个提交？测试库和生产库是否一致？没人答得上。
3. **无法回滚。** 改错了没有「撤销」按钮，只能手工拼 SQL 改回去。
4. **多人协作必然冲突。** 团队库结构靠口口相传，没人说得清最终状态。

### 1.2 迁移 = 数据库结构的 Git

Alembic 的思路和 Git 一致：每次结构变更写成一个 **迁移脚本**，内含升级（`upgrade`）与降级（`downgrade`
）两个方向；每个脚本有唯一版本号并记录上一版本，串成 **版本链**；数据库用 `alembic_version` 表记录当前版本。由此获得三个能力：
**可重放**——任何环境能从空库重放到最新； **可回滚**——出问题一条命令退回； **可审计**——每次变更都躺在仓库里接受 Review。

### 1.3 本教程要解决的三个问题

本教程延续前作项目 `fastapi_sqla_demo`（FastAPI + SQLAlchemy 2.0 异步 + MySQL 8 + asyncmy），围绕三件事展开：

- **异步环境怎么配 Alembic**：`env.py` 的异步桥接、URL 与模型接入（第 2、3 章）；
- **迁移脚本怎么写**：autogenerate 的正确姿势、`op` 操作、数据迁移与回滚、MySQL 的坑（第 4、5 章）；
- **团队和生产怎么用**：分支合并、既有项目接入、部署时机、CI 集成（第 6、7 章）。

## 第 2 章 快速上手：第一条迁移

本章目标很直接：把 Alembic 装进 `fastapi_sqla_demo`，生成第一条迁移，把前作用 `create_all` 建的 `users`、`accounts`
两张表纳入版本管理，并亲手体验一次升级与回滚。

### 2.1 安装与初始化

在前作项目的虚拟环境中安装（要求 Alembic 1.13+，SQLAlchemy 2.0 已自带）：

```bash
pip install alembic
```

然后在 **项目根目录**（与 `app/` 同级）执行初始化：

```bash
alembic init -t async alembic
```

注意 `-t async` 这个参数： **异步项目必须使用 async 模板**。原因是模板生成的 `env.py` 内置了异步引擎的桥接逻辑（`run_sync`
），用默认同步模板则连接数据库时会直接报错。执行后目录下会多出 `alembic.ini` 配置文件和 `alembic/` 迁移目录。

### 2.2 生成的目录结构

```text
fastapi_sqla_demo/
├── alembic.ini            # Alembic 主配置：脚本位置、URL 默认值、日志等
├── alembic/
│   ├── env.py             # 核心：每次执行 alembic 命令都会加载，负责连库、找模型
│   ├── script.py.mako     # 迁移脚本的模板，revision 命令照它生成新脚本
│   └── versions/          # 迁移脚本存放处，一个文件就是一个版本
└── app/ ...
```

三个文件记住一句话即可：`env.py` 是运行时入口，`script.py.mako` 是生成模板，`versions/` 是历史档案，90% 的配置工作都在
`env.py` 里。

### 2.3 最小可用配置

模板生成的 `env.py` 默认不知道我们的模型和数据库地址，先改两处让它「能跑通」（这里只求跑通，逐行原理和第 3 章再细讲）：

```python
# alembic/env.py（改动部分）
import app.models  # noqa: F401  —— 确保所有模型注册进 metadata
from app.db import DATABASE_URL, Base

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)  # URL 以应用配置为准

target_metadata = Base.metadata  # autogenerate 的比对基准
```

两行要点：`target_metadata` 是 autogenerate 的比对基准；URL 直接从 `app.db` 导入，避免在 `alembic.ini` 里重复维护一份连接串。
`import app.models` 看似多余实则关键——不导入模型，metadata 里就是空的。

### 2.4 生成初始迁移 0001

配置就绪，生成第一条迁移：

```bash
alembic revision --autogenerate -m "init"
```

`--autogenerate` 让 Alembic 对比 metadata 与数据库，自动写出建表语句。`versions/` 下会出现类似 `3f8c1a2b9d01_init.py`
的文件（版本号是随机十六进制 ID，本教程统一用 `0001`、`0002` 这样的简称指代版本顺序）。打开它，典型结构如下：

```python
"""init

Revision ID: 3f8c1a2b9d01
Revises:
Create Date: 2024-05-01 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision: str = "3f8c1a2b9d01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        ...
    )
    op.create_table("accounts", ...)

def downgrade() -> None:
    op.drop_table("accounts")
    op.drop_table("users")
```

四个要素必须看懂：

- **`revision`**：本脚本的版本号，唯一标识；
- **`down_revision`**：上一个版本号，第一条迁移为 `None`——正是这两个字段把所有脚本串成版本链；
- **`upgrade()`**：执行升级时运行的函数，这里负责建表；
- **`downgrade()`**：回滚时运行的函数，逻辑应是 `upgrade` 的逆操作（注意建表顺序与删表顺序相反，先删有外键的 `accounts`）。

### 2.5 执行、查看与回滚

执行迁移，把数据库推进到最新版本：

```bash
alembic upgrade head
```

`head` 表示版本链的最新端点。成功后连进 MySQL 看一眼，除了 `users`、`accounts` 两张业务表，还多了一张 Alembic 自己维护的版本表：

```sql
SELECT * FROM alembic_version;
-- +--------------+
-- | version_num  |
-- +--------------+
-- | 3f8c1a2b9d01 |
-- +--------------+
```

几个常用的版本查看命令：

```bash
alembic current            # 当前库停在哪个版本
alembic history --verbose  # 完整版本链，含每条迁移的描述
```

再亲手体验回滚与重做：

```bash
alembic downgrade -1       # 回退一个版本：users、accounts 被删除
alembic upgrade head       # 重新升到最新：两表恢复
```

`-1` 是相对版本写法，意为「后退一步」。至此第一条迁移的完整闭环——生成、执行、查看、回滚、重做——已经跑通。

### 2.6 重要：把建表职责移交给 Alembic

最后一步，也是本章的落脚点： **打开前作 `app/main.py`，删除 lifespan 中 `run_sync(Base.metadata.create_all)` 那段建表逻辑**
。从此数据库结构的唯一权威是 Alembic 迁移，应用启动不再碰 DDL。两种机制并存是大忌：`create_all`
会悄悄掩盖「迁移没执行」的问题，让结构漂移死灰复燃。新环境部署的标准动作变成两步：启动应用前，先 `alembic upgrade head`。

下一章我们逐行拆解 `env.py`，搞懂异步配置背后的原理。

---

## 第 3 章 env.py 异步配置详解

上一章我们用最小改动跑通了第一条迁移。本章把 `alembic/env.py` 彻底讲透：它是 Alembic 与你的项目之间唯一的桥梁，异步项目的绝大多数配置问题都出在这里。

### 3.1 为什么异步项目需要特殊处理

Alembic 诞生于同步时代，它的迁移执行入口——`context.run_migrations()`——是一个 **同步函数**，内部通过普通的 DBAPI 连接执行
DDL。而我们的项目用的是 asyncmy 这类异步驱动，连接对象只能在事件循环里以 `await` 方式使用，两者无法直接对接。

解决办法是 SQLAlchemy 异步体系里已经见过的「桥接」思路（前作讲 greenlet 原理时提过）：异步驱动底层是 await 风格的协程，同步代码无法直接调用；
`AsyncConnection.run_sync()` 会把传入的同步函数送进一个绿色线程（greenlet）里执行，在这个绿色线程内部，SQLAlchemy
用绿色线程切换把异步驱动的 await 伪装成同步阻塞调用，于是同步的 Alembic 代码就能「无感」地跑在异步连接之上。换句话说，
`run_sync` 让「同步的调用方」和「异步的驱动」在 greenlet 的掩护下握手。这就是 async 模板生成的 env.py 与默认模板最大的区别：多了一层
`asyncio.run(...)` + `run_sync(...)` 的包装。

另外，Alembic 在执行迁移时会自己持有独立的连接，与 FastAPI 应用的 engine、连接池完全无关——不要在 env.py 里复用应用的
engine。应用的 engine 绑定在应用的事件循环上，而 `alembic` 命令是在独立的命令行进程里跑的，复用只会引入事件循环冲突和连接泄漏。

### 3.2 env.py 逐行讲解

以下是本教程的 env.py 定稿（`alembic init -t async alembic` 生成后按此修改），后续章节不再改动：

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

import app.models  # noqa: F401  —— 确保所有模型注册进 metadata
from app.db import DATABASE_URL, Base

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)  # URL 以应用配置为准

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

逐段说明：

- **`import app.models  # noqa: F401`**：整份文件里最容易被忽略、却最关键的一行。模型的类只有被导入、类体被执行，才会注册进
  `Base.metadata`。少了它，autogenerate 看到的 metadata 是空的，会生成一份「删除所有表」的灾难性脚本。`noqa: F401` 是告诉
  linter 这个「未使用的导入」是故意的。以后每新增一个模型模块，都要保证它能被这行（或 `app/models.py` 内部的导入链）间接导入。
- **`config.set_main_option("sqlalchemy.url", DATABASE_URL)`**：把 alembic.ini 里的连接串覆盖为应用 `db.py` 中的同一份
  `DATABASE_URL`。数据库地址只维护一处，改环境（开发/测试/生产）时不会出现「应用连 A 库、迁移连 B 库」的事故。
- **`fileConfig(config.config_file_name)`**：加载 alembic.ini 里的日志配置，让迁移过程的 SQL 与版本信息按 ini
  中定义的格式输出；调试迁移时把它调到 DEBUG 能看到每条 DDL。
- **`target_metadata = Base.metadata`**：autogenerate 的对比基准——拿这份 metadata 与真实库结构做 diff。一个项目可以有多个
  Base，但 Alembic 只认这一个入口，所以所有模型必须收敛到同一个 `Base.metadata` 上。
- **`do_run_migrations(connection)`**：同步的迁移执行函数，被 `run_sync` 包进绿色线程。`compare_type=True` 让 autogenerate
  在对比时连「列类型变化」（如 `String(50)` 改成 `String(100)`）也能检测，默认是关闭的。
- **`async_engine_from_config(..., poolclass=pool.NullPool)`**：从 ini 配置构造异步 engine，读取以 `sqlalchemy.`
  为前缀的选项。迁移是「一次连上、跑完就扔」的短命任务，没有并发复用需求，用 `NullPool`
  （每次新建连接、用完即关）即可——既避免常驻连接占用数据库连接数，也杜绝了跨命令复用连接时的事件循环问题。跑完
  `await connectable.dispose()` 干净收尾。
- **入口判断**：`context.is_offline_mode()` 决定走哪条路径，online 路径用 `asyncio.run()` 起事件循环驱动整个迁移。

### 3.3 offline 与 online 两种模式

**online 模式**（默认）：真正连上数据库执行 DDL，同时维护 `alembic_version` 表的版本记录，日常开发用它。

**offline 模式**（加 `--sql`）：不连接数据库，只把迁移 **翻译成 SQL 文本**输出：

```bash
alembic upgrade head --sql > migrate.sql
```

典型场景是生产环境权限分离：开发没有生产库的 DDL 权限，把生成的 `migrate.sql` 交给 DBA 审核、在变更窗口手工执行。注意
offline 模式拿不到数据库连接，凡是需要读库数据的迁移（如第 5 章的数据回填）无法在 offline 下正确工作，生成出来的 SQL
里数据操作部分只会是按字面量渲染的占位语句。offline 配置里的 `literal_binds=True` 表示把参数值直接渲染进 SQL 文本（而不是保留
`:param` 占位符），方便 DBA 阅读；`dialect_opts={"paramstyle": "named"}` 则是占位符风格的兜底约定。

两种模式共用同一份迁移脚本，区别只在 `context.configure()` 拿到的是「URL」还是「连接」——这就是定稿代码里
`run_migrations_offline()` 与 `do_run_migrations()` 分开两个函数、最后按 `context.is_offline_mode()` 分流的原因。

### 3.4 在前作 db.py 基础上补充 naming_convention

这是对前作 `app/db.py` 的 **显式扩展**——前作的 `Base` 是空壳，现在为它挂上一份命名约定：

```python
# app/db.py（在前作基础上补充命名约定）
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)
```

为什么约束必须有稳定的名字？因为迁移脚本里的 `op.drop_constraint("约束名", ...)` 是 **按名字引用**约束的。如果不约定，MySQL
会自动生成形如 `accounts_ibfk_1` 的外键名——同一个模型在两台机器上先后建表，序号可能不同，名字不可预测，写死的迁移脚本换个环境就执行失败。有了
naming_convention，索引、唯一约束、外键的名字由规则唯一确定：`fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`
展开后，accounts 表指向 users 的外键永远叫 `fk_accounts_user_id_users`，谁在哪个环境执行都一样。autogenerate
也能识别「同名同规则」，避免反复生成「删旧约束、建新约束」的噪音变更。

注意这是一份 **从建库之初就该生效**的约定：如果前作的库已经用 `create_all` 建过表，库里已存在的约束还是 MySQL
自动名，需要借助初始迁移（或手工改名）把它们对齐到约定名。新环境由 Alembic 从零建表则天然一致。

### 3.5 常见配置项速查表

`context.configure()` 的常用选项：

| 配置项                      | 作用                                                      | 建议                                          |
|-----------------------------|-----------------------------------------------------------|-----------------------------------------------|
| `compare_type`              | autogenerate 是否检测列类型变化                           | 建议 `True`（本教程已开启）                   |
| `compare_server_default`    | 是否检测列默认值（server_default）变化                    | 项目大量使用数据库默认值时开启                |
| `render_as_batch`           | 用「建影子表-搬数据-改名」的批量模式重写 ALTER            | SQLite 专用，MySQL 原生支持 ALTER，**不需要** |
| `include_object`            | 过滤钩子，返回 `False` 可让指定表/索引不参与 autogenerate | 忽略数据库里非本项目管理的表时使用            |
| `transaction_per_migration` | 每条迁移一个事务                                          | MySQL DDL 隐式提交，意义有限，见 5.6 节       |

`include_object` 的常见写法：

```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name.startswith("legacy_"):
        return False  # legacy_ 开头的表不归 Alembic 管
    return True
```

## 第 4 章 autogenerate：正确使用自动生成的迁移

autogenerate 是 Alembic 最诱人的功能：改动模型，自动生成迁移脚本。但它的本质是一个 diff 工具——拿 `Base.metadata`
的「应有结构」和数据库的「实际结构」做对比，把差异翻译成 `op` 调用。它能看见差异，却不理解语义， **只能生成草稿，不能代替你思考**
。本章讲清它的正确用法与边界。

### 4.1 标准工作流

记住四步： **改模型 → `revision --autogenerate` → 人工审查 → `upgrade`**。以冻结案例 `0002_add_users_phone` 完整走一遍——给
users 表增加手机号列。

开始之前确认前提：当前数据库已执行到 0001（`alembic current` 可见），且模型与库结构一致。autogenerate 是对「当前库」做 diff
的，如果库的版本落后，差异里会混入历史改动，生成的脚本就是错的。

第一步，改 `app/models.py`：

```python
class User(Base):
    __tablename__ = "users"
    # ... 原有的 id / name / email / created_at 列保持不变 ...
    phone: Mapped[str | None] = mapped_column(String(20))  # 新增
```

第二步，生成迁移（确保当前库已处于 0001 版本）：

```bash
alembic revision --autogenerate -m "add_users_phone"
```

第三步，打开 `alembic/versions/xxxx_add_users_phone.py` **逐行审查**。脚本骨架由 `script.py.mako` 模板渲染：头部 docstring
记录版本信息，`revision` 是自身的版本号，`down_revision` 指向上一个版本（即 0001 的 revision id），两者首尾相接构成版本链。自动生成的操作体如下：

```python
"""add_users_phone

Revision ID: b2c3d4e5f6a7   # 教程简称 0002
Revises: 3f8c1a2b9d01
Create Date: 2024-05-02 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "3f8c1a2b9d01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")
```

审查要点：操作是否 **恰好**对应我的模型改动——本例中应该只有一条 `add_column`，多一行少一行都要警觉？有没有多出来的
drop（通常意味着模型没被正确导入，或数据库被人手工改过、与 metadata 漂移了）？downgrade 是否是 upgrade 的逆操作？
`nullable=True` 是否符合预期——`Mapped[str | None]` 声明了可空，脚本里也应如此对应。

第四步，执行并验证：

```bash
alembic upgrade head
alembic current          # 应显示 b2c3d4e5f6a7 (head)
```

到 MySQL 里确认：

```sql
SHOW COLUMNS FROM users;  -- 应能看到 phone varchar(20) 允许 NULL
```

### 4.2 autogenerate 能检测什么

在 `compare_type=True` 的前提下，autogenerate 能可靠检测以下「结构性」差异：

- **表的增删**：新增模型类 → `create_table`（含全部列、约束、索引）；删除模型类 → `drop_table`；
- **列的增删**：模型里多一列 → `add_column`；删掉一列 → `drop_column`；
- **nullable 变化**：`Mapped[str]` 改成 `Mapped[str | None]` → `alter_column(nullable=True)`；
- **列类型变化**：如 `String(50)` → `String(100)`、`Integer` → `BigInteger`，生成带 `existing_type=` 的 `alter_column`
  ——必须开启 `compare_type`，默认关闭时会 **静默忽略**，这是最常见的「明明改了模型却生成空脚本」的原因；
- **索引与唯一约束的增删**：`create_index` / `drop_index` / 唯一约束的增删，配合 naming_convention 时识别稳定。

可以发现规律：它擅长回答「多没多、少没少、属性变没变」这类问题；一旦涉及「这个和那个是不是同一个东西」的语义判断，它就会露馅——下面一节全是这类情况。

### 4.3 检测不到或会误判的

**改名是最大的陷阱。** 把 users 表的 `name` 列改名为 `username`：

```python
username: Mapped[str] = mapped_column(String(50))  # 原名 name
```

autogenerate 无法知道这是「改名」，它只看到「name 消失了、username 出现了」，于是生成：

```python
op.add_column("users", sa.Column("username", sa.String(length=50), nullable=False))
op.drop_column("users", "name")
```

直接执行会怎样？ **旧列连同全部数据被删掉，新列是空的——数据丢失！** 必须手工把这两个操作改写为一条改名：

```python
def upgrade() -> None:
    op.alter_column(
        "users", "name",
        new_column_name="username",
        existing_type=sa.String(length=50),
    )

def downgrade() -> None:
    op.alter_column(
        "users", "username",
        new_column_name="name",
        existing_type=sa.String(length=50),
    )
```

注意 MySQL 下 `alter_column` 必须显式带上 `existing_type=`（它底层要拼完整的 `MODIFY COLUMN` 子句），否则报错，细节见第 5 章。

改表名同理：把 `__tablename__ = "users"` 改成 `"members"` 后，autogenerate 会生成 `create_table("members", ...)` +
`drop_table("users")`，执行即丢全表数据。必须把两个操作删除，替换为一句：

```python
def upgrade() -> None:
    op.rename_table("users", "members")

def downgrade() -> None:
    op.rename_table("members", "users")
```

另外两类常见噪音：

- **约束名变化**：数据库里已存在的约束是 MySQL 自动命名的，而 metadata 里是 naming_convention 的名字，autogenerate
  可能反复生成「删旧约束+建新约束」。这正是 3.4 节要求建表之初就用稳定命名的原因；历史遗留库可结合 `include_object`
  过滤，或在某条迁移里一次性手工改名对齐。
- **server_default 变化**：默认不检测，列的数据库默认值改动不会体现在脚本里。项目依赖数据库默认值时，在
  `context.configure()` 中加 `compare_server_default=True`。
- **数据层面的需求完全检测不到**：给已有数据的表加一个 NOT NULL 且无默认值的列、拆分一张表为两张表、回填历史数据——这些都没有「结构差异」可言，autogenerate
  要么生成执行即报错的脚本，要么什么都不生成，必须手工补写（第 5 章专门讲）。

### 4.4 铁律：autogenerate 只是草稿

把 autogenerate
当作一个「勤勉但不懂业务的助手」：它能忠实地列出结构差异，却不知道改名与删建的分别、不知道你的表里躺着生产数据、不知道加列之后还要回填。它产出的每一份脚本，都必须人工审查、在本地执行验证后，才能提交进版本库。两个落地手段：

1. **审查清单**：有没有意外的 drop（模型没导入或库被手工改过的信号）？改名是否被误拆成删+建？downgrade 是否可逆？生成的类型、长度、nullable
   与模型声明是否一致？
2. **CI 防漂移**：Alembic 1.13+ 提供 `alembic check`——它用 autogenerate 同一套逻辑对比「模型
   metadata」与「迁移链头部对应的库结构」，发现差异（即有人改了模型却没生成迁移）时打印 diff 并以非零状态码退出，正好卡住流水线。标准用法是在
   CI 里建一个干净的临时库：

```bash
alembic upgrade head   # 先在临时库上跑通全部迁移
alembic check          # 再确认模型与迁移无漂移
```

这样，忘记生成迁移、或手工改库造成的漂移，都会在合并前被拦下。从下一章开始，我们离开 autogenerate 的舒适区，学习手工编写迁移脚本。

---

## 第 5 章 迁移操作手册：op 常用操作与数据迁移

autogenerate 能帮我们生成大部分草稿，但真正写好迁移，必须理解脚本里每一个 `op.*` 调用在做什么。本章把常用结构操作、数据迁移写法和
MySQL 特有的坑一次讲透。

### 5.1 结构操作速查

**新增 / 删除列**

```python
def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.drop_column("users", "legacy_field")
```

**修改列：MySQL 必须带 `existing_type=`**

MySQL 的 `ALTER TABLE ... MODIFY COLUMN` 要求给出完整的列定义，Alembic 无法从数据库反推旧类型，所以下面这种写法在 MySQL
上会直接报错：

```python
# ❌ MySQL 报错：alter_column requires existing_type
op.alter_column("users", "name", nullable=False)
```

正确写法是显式声明现有类型：

```python
# ✅ 带上 existing_type，MySQL 才能生成 MODIFY COLUMN
op.alter_column(
    "users",
    "name",
    existing_type=sa.String(50),
    nullable=False,
)
```

**索引**

```python
def upgrade() -> None:
    op.create_index("ix_users_email", "users", ["email"], unique=True)

def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
```

**外键：创建与按名删除**

删除约束必须按名引用（`op.drop_constraint(name, ...)`），这正是第 3 章 `naming_convention` 存在的意义——有了稳定命名，我们才能准确地写出
`fk_accounts_user_id_users` 这样的名字，而不是去猜 MySQL 自动生成的那串字符：

```python
def upgrade() -> None:
    op.create_foreign_key(
        "fk_accounts_user_id_users",   # 命名约定生成的稳定名字
        "accounts",                    # 源表
        "users",                       # 目标表
        ["user_id"],
        ["id"],
    )

def downgrade() -> None:
    op.drop_constraint("fk_accounts_user_id_users", "accounts", type_="foreignkey")
```

**建表 / 删表**

```python
def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
    )

def downgrade() -> None:
    op.drop_table("tags")
```

### 5.2 冻结案例：0004_create_transactions

前作转账案例中，余额变动只有 `accounts` 表里的最终结果，缺少流水记录。现在新增 `transactions` 表补上这一环。执行
`alembic revision -m "create transactions"` 后把脚本补全为：

```python
"""create transactions

Revision ID: d4e5f6a7b8c9   # 教程简称 0004
Revises: c3d4e5f6a7b8      # 即 0003
"""
from alembic import op
import sqlalchemy as sa

# 真实项目中 revision ID 是 Alembic 随机生成的十六进制串，
# 本教程用 0001~0004 这样的简称指代（真实 ID 为示意）
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("from_account_id", sa.Integer, nullable=False),
        sa.Column("to_account_id", sa.Integer, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["from_account_id"],
            ["accounts.id"],
            name="fk_transactions_from_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["to_account_id"],
            ["accounts.id"],
            name="fk_transactions_to_account_id_accounts",
        ),
    )
    # 转账查询几乎都按账户号过滤，两个外键列都要有索引
    op.create_index(
        "ix_transactions_from_account_id",
        "transactions",
        ["from_account_id"],
    )
    op.create_index(
        "ix_transactions_to_account_id",
        "transactions",
        ["to_account_id"],
    )


def downgrade() -> None:
    # drop_table 会连带删除表上的索引和外键，无需逐个 drop
    op.drop_table("transactions")
```

两个细节：`amount` 用 `Numeric(12, 2)` 而不是浮点类型，与前作"金额必须精确"的要求一致；外键名按命名约定手工写死，保证后续
`drop_constraint` 有据可依。

### 5.3 数据迁移：0003_add_users_is_active_backfill

结构变化常常伴随数据变化。这类迁移不是 autogenerate 能完全代劳的，需要用 **空白迁移**手工编写：

```bash
alembic revision -m "add users.is_active and backfill"
```

注意这里没有 `--autogenerate`，生成的是空壳脚本，内容由我们自己填。以冻结案例 0003 为例，演示"**加列（带 server_default）→
回填 → 去掉 server_default**"三步法：

```python
"""add users.is_active and backfill

Revision ID: c3d4e5f6a7b8   # 教程简称 0003
Revises: b2c3d4e5f6a7      # 即 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 第一步：加列，带 server_default="1"（MySQL 的 BOOLEAN 即 TINYINT(1)）。
    # 已有行会被立即填成 1，大表上避免全表 UPDATE 的锁等待。
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
    )
    # 第二步：按需回填真实业务数据（示例：没有邮箱的用户视为未激活）
    op.execute("UPDATE users SET is_active = 0 WHERE email IS NULL OR email = ''")
    # 第三步：回填完成，数据库默认值改由应用层负责，去掉 server_default
    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
```

为什么拆成三步而不是"加列 + 一次性 UPDATE"？因为 MySQL 的 `ADD COLUMN ... DEFAULT 1` 对已有行是即时填充的（MySQL 8 的
instant add column 甚至不动数据文件），而全表 `UPDATE`
在大表上是重型操作。把"让历史数据合法"和"按业务规则回填"分开，脚本更安全，也更容易定位问题。

### 5.4 铁律：迁移脚本里禁止 import 应用的 ORM 模型

这是新手最容易踩的坑。下面这种写法 **绝对禁止**：

```python
# ❌ 危险：import 了应用模型
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User

def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)
    for user in session.scalars(select(User)):
        ...
```

问题在于：迁移脚本必须是 **永远可重放的历史快照**，而 ORM 模型会不断演进。半年后 `User`
加了新列、删了旧列，此时有人从空库重放全部迁移，执行到这条老迁移时，模型定义和当时的数据库结构对不上，脚本直接报错——整条迁移链断掉。

正确姿势是 **在迁移脚本内部用 `sa.table()` 做一个当时的、最小的表定义**，只声明要用到的列：

```python
# ✅ 正确：op.get_bind() + 轻量 sa.table() 定义
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("email", sa.String(255)),
    )
    bind = op.get_bind()
    bind.execute(
        sa.update(users).values(email=sa.func.lower(users.c.email))
    )
```

这里的 `users` 只是一个临时的 `Table` 描述，和应用代码完全解耦。无论 `app/models.py` 将来怎么改，这条迁移在任何时间点重放都成立。简单的单行
SQL 用 `op.execute()` 原生语句（如 5.3）同样合规；涉及条件构造、批量 UPDATE 时，`sa.table()` 写法更不易拼错。

### 5.5 downgrade 怎么写

`downgrade()` 应当是 `upgrade()` 的 **可逆镜像**：upgrade 建表，downgrade 删表；upgrade 加列，downgrade 删列；upgrade
加索引，downgrade 删索引。顺序上还要注意依赖关系，例如先建表再建索引的 upgrade，downgrade 里虽然 `drop_table`
会连带清理索引，但养成"逆序回退"的习惯能让意图更清晰。

对于 **不可逆操作**（典型如 `drop_column`：列删掉后数据已丢失，无法凭空恢复），不要为了形式完整而编造一个会误导人的
downgrade，应当显式声明：

```python
def upgrade() -> None:
    op.drop_column("users", "legacy_field")

def downgrade() -> None:
    # legacy_field 的数据已随列删除而丢失，无法自动恢复
    raise NotImplementedError("drop_column 不可逆，如需回退请从备份恢复数据")
```

显式 `raise NotImplementedError` 比留空或写错好得多——执行 `alembic downgrade` 的人会立刻知道此路不通，而不是得到一个静默错误的库。

### 5.6 MySQL 特别注意：DDL 隐式提交

这是 MySQL 与 PostgreSQL 的关键差异： **MySQL 的 DDL 会隐式提交当前事务**。PostgreSQL 支持事务性
DDL，一条迁移中途失败，整个事务回滚，数据库毫发无损；而 MySQL 下，迁移脚本执行到一半出错时，前面已执行的 `CREATE TABLE`、
`ADD COLUMN` 都已生效且无法回滚——数据库停留在"半成品"状态，`alembic_version` 里的版本号却还是旧的（因为 Alembic
在迁移结束才更新版本号，那一步没走到）。

失败后的标准处理流程：

1. **看报错，定位失败语句**，判断前面的哪些 DDL 已经生效。
2. **手工清理残留**：连上数据库，把迁移执行了一半的对象删掉（如 `DROP TABLE transactions`、
   `ALTER TABLE users DROP COLUMN is_active`），让库回到迁移前的结构。
3. **对齐版本**：确认 `alembic_version` 仍是旧版本则无需处理；如果你是在清理后想跳过某条已部分成功的迁移，可用
   `alembic stamp <revision>` 直接把版本号"盖"到目标版本（只改 `alembic_version` 表，不执行任何脚本）。
4. **修好迁移脚本，重新 `alembic upgrade head`**。

正因为 MySQL 没有事务性 DDL，"一条迁移里只做一件事、先备份再迁移"在 MySQL 环境下不是建议，是纪律。

## 第 6 章 版本管理：分支、合并与多人协作

### 6.1 版本链结构：revision、down_revision 与 head

每个迁移脚本顶部的两个变量构成了一条单向链表：

```python
revision = "d4e5f6a7b8c9"        # 本迁移的唯一标识（教程简称 0004）
down_revision = "c3d4e5f6a7b8"   # 指向父版本（即 0003）
```

Alembic 靠 `down_revision` 指针把所有迁移串成有向无环图。`alembic history` 输出的正是这条链。两个容易混淆的命令：

- `alembic head`：显示当前迁移图中 **唯一的头节点**（链条末端）。前提是图里只有一个头。
- `alembic heads`：显示 **所有头节点**。单人开发时通常只有一个；多人并行时就可能看到多个。

另外 `alembic current` 显示数据库当前所处的版本，拿它和 `heads` 对比，就知道库落后了几个版本。

### 6.2 多人并行：两个 head 的产生与合并

典型场景：你和同事同时基于 0004 开发。你给用户表加字段生成了迁移 `0005_add_users_nickname`（真实 ID `e5f6a7b8c9d0`，
`down_revision = "d4e5f6a7b8c9"`），同事给账户表加字段生成了 `0005_add_accounts_frozen`（真实 ID `f6a7b8c9d0e1`，
`down_revision` 同样是 `"d4e5f6a7b8c9"`）。两人代码合并后执行：

```text
$ alembic heads
e5f6a7b8c9d0 (head)   # 0005_add_users_nickname
f6a7b8c9d0e1 (head)   # 0005_add_accounts_frozen

$ alembic upgrade head
FAILED: Multiple head revisions are present for given argument 'head'
```

迁移图从 `0004` 分成了两个分支，Alembic 不知道先走哪条，拒绝执行。解决办法是生成一个 **合并迁移**，把两个头收拢：

```bash
$ alembic merge heads -m "merge 0005 branches"
```

生成的脚本几乎是空的，核心在于它有两个父版本：

```python
revision = "a7b8c9d0e1f2"   # merge 迁移（教程简称 0006_merge）
down_revision = ("e5f6a7b8c9d0", "f6a7b8c9d0e1")   # 同时继承两条 0005 分支

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
```

`down_revision` 是元组，表示"本版本同时继承两个父节点"。此后 `alembic heads` 重新只剩一个头，`alembic upgrade head`
会按依赖顺序把两个分支都应用上。注意：merge 迁移只负责缝合版本图，
**两个分支如果改了同一张表，仍需人工检查是否存在逻辑冲突**（比如都往 users 表加了同名列）。

### 6.3 相对版本操作与 stamp

版本参数不一定写全 ID，常用相对写法：

```bash
alembic upgrade +1      # 前进一个版本
alembic downgrade -1    # 回退一个版本
alembic upgrade c3d4e5f6a7b8   # 升到指定版本（即 0003，只应用它及之前未执行的）
alembic downgrade base  # 一路回退到空库
```

`alembic stamp` 则是 **只改版本号、不执行任何脚本**：

```bash
alembic stamp head            # 直接把 alembic_version 盖到最新版本
alembic stamp 3f8c1a2b9d01    # 盖到指定版本（即 0001）
```

它的两大用途：一是 5.6 节提到的迁移失败后手工清理完毕、需要跳过该迁移时对齐版本；二是下一节的既有项目接入。

### 6.4 既有老项目接入 Alembic 的完整流程

很多项目不是从第一天就用 Alembic 的：数据库结构已经存在（靠 `create_all` 或手工 SQL 建好），生产库里有真实数据。这时
**绝对不能**直接 `alembic upgrade head`——初始迁移里的 `CREATE TABLE` 会因为表已存在而报错。正确流程分四步：

**第一步：接入配置**。按第 2、3 章初始化 `alembic/`、配好异步 env.py，并让模型与现有库结构保持一致。

**第二步：生成初始迁移**。

```bash
alembic revision --autogenerate -m "init"
```

如果模型定义与库结构一致，autogenerate 生成的 upgrade 应该恰好描述出现有全部表结构。务必人工审查这份脚本，确认没有多余的删表/删列（有则说明模型与库存在漂移，先对齐）。

**第三步：生产库 stamp 到初始版本**。开发库可以删掉重建后正常 `alembic upgrade head` 验证脚本能跑通；但生产库结构已存在，只登记版本号、不执行
DDL：

```bash
# 在生产库上执行：告诉 Alembic"你已经处于 0001"，不执行 CREATE TABLE
alembic stamp 3f8c1a2b9d01   # 即初始迁移 0001
```

**第四步：进入正常迭代**。此后所有结构变更都走标准流程：改模型 → `revision --autogenerate` → 审查 → 开发库验证 → 生产库
`alembic upgrade head`。从这一刻起，老项目和新项目在迁移管理上再无任何区别。

一句话总结本章：版本链是 Alembic 的核心数据结构，`heads` 看分支、`merge` 缝合分支、`stamp`
对齐现实——掌握这三个命令，多人协作和老项目接入的所有场景都能覆盖。

---

## 第 7 章 生产环境与 CI/CD

在本地跑通 `alembic upgrade head` 只是起点。生产环境的约束完全不同：有真实流量、有不能停的服务、有百万行的大表，还有「先改库还是先发版」这个经典的先后问题。本章把前六章的能力串成一套可上线的流程。

### 7.1 迁移与发版的先后问题：Expand-Contract 模式

先问一个直觉问题：给 users 表加 `phone` 列，是先跑迁移再发版，还是先发版再跑迁移？

- 先发版后迁移：新代码读写 `phone`，但列还不存在，请求直接报错；
- 先迁移后发版：迁移执行期间旧版本代码仍在运行——好在「加列」对旧代码无害（旧代码根本不知道这一列），所以
  **新增结构可以先迁移**；
- 真正的麻烦在 **删除/改名**：先删列，旧代码立刻崩；先发版（去掉对旧列的引用）再删列，中间的迁移窗口内新旧代码必须能共存。

这就是 Expand-Contract（扩张-收缩）模式要解决的事： **任何破坏性变更都拆成两次部署**。

1. **Expand（扩张）**：只做增量、向后兼容的迁移——加列、加表、加索引，绝不删不改。对应我们的 `0002_add_users_phone`：`phone` 以
   `nullable=True` 加入，旧代码无感知，新代码可以开始写入。
2. **发版**：部署使用新结构的代码。此时新旧结构并存，旧代码仍可用，随时可回滚。
3. **Contract（收缩）**：确认所有实例都已是新版本、不再需要旧结构后，再单独提一个迁移清理——比如把 `phone` 收紧为 `NOT NULL`
   、回填剩余空值、删除被替代的旧列。这一步往往隔几天甚至隔一个迭代执行。

代价是每次破坏性变更要发两次版、写两个迁移，换来的是全程零停机、随时可回滚。这是生产环境的标准做法。

### 7.2 大表迁移风险：锁表与在线改表

`op.add_column()` 落到 MySQL 就是一条 `ALTER TABLE`。小表毫秒级完成，但对百万行以上的大表，某些操作会触发表重建，期间写入被阻塞，业务直接受损。MySQL
8 的 InnoDB Online DDL 能让很多 `ALTER` 不锁表，但并非所有操作都支持（比如某些改列类型、改主键的操作仍会重建表）。

对大表，业界的成熟方案是用在线改表工具绕过 `ALTER TABLE`：

- **gh-ost**（GitHub 出品，基于 binlog 增量同步，可随时暂停、可无损中止）；
- **pt-online-schema-change**（Percona Toolkit，基于触发器）。

工作流是：在迁移窗口外用 gh-ost 完成物理改表，然后 **不要**让 Alembic 再执行一遍 DDL，而是用 `alembic stamp <revision>`
把版本号直接对齐——告诉 Alembic「这个迁移已经由别的手段执行过了」。对应的迁移文件保留在版本链里，只对新环境（如 CI 临时库）实际生效。

### 7.3 迁移失败应急预案

第 5 章强调过：MySQL 的 DDL 会隐式提交，一条多步迁移中途失败，数据库会停在「半成品」状态，`alembic_version` 却还没更新。生产环境必须有预案：

- **备份铁律**：执行迁移前对生产库做备份（或至少确认有可用的最近备份与 binlog），数据迁移类脚本（如 0003 的回填）尤其需要；
- **失败处理**：失败后不要慌着重跑——先手工检查哪些 DDL 已生效，清理半成品（或直接补做剩余步骤），再用 `alembic stamp`
  把版本号修正到真实状态；
- **回滚演练**：每个破坏性迁移上线前，在预发环境至少演练一次 `downgrade`；对不可逆操作（删列），真正的回滚手段是备份，而不是
  downgrade。

### 7.4 CI 集成：让流水线替你验证迁移

迁移脚本也是代码，应该进 CI。最低成本的两道关卡：

1. **可执行性验证**：流水线里起一个临时 MySQL 8 容器（如 GitHub Actions 的 services 或
   `docker run -e MYSQL_ALLOW_EMPTY_PASSWORD=yes mysql:8`），从空库跑 `alembic upgrade head`
   。这能一次性验证整个版本链（0001 → 0004）可重放、SQL 语法与 MySQL 8 兼容。
2. **漂移检测**：跑 `alembic check`。它对比模型与迁移链推导出的结构，若有人改了 `app/models.py` 却忘了生成迁移，CI
   直接失败——漂移在合并前就被拦住。

再加一条团队铁律： **已合并、尤其是已在任何环境执行过的迁移文件，禁止修改**。Alembic
按版本号追踪执行历史，改老文件不会造成「重新执行」，只会让不同环境的同一版本号对应不同内容。要修正，永远新增一个迁移。

### 7.5 offline 模式：生成 SQL 交给 DBA

很多公司规定应用账号无 DDL 权限，结构变更必须经 DBA 审核执行。这时用 offline 模式把迁移渲染成纯 SQL：

```bash
alembic upgrade d4e5f6a7b8c9:head --sql > migrate.sql   # 0004:head，即生成 0004 之后所有迁移的 SQL；0004 为教程简称，请替换为实际 revision id
```

`migrate.sql` 里是逐条 SQL（含 `alembic_version` 的版本更新语句），可评审、可留档，由 DBA 在生产库执行。前提是 env.py 配置了
offline 支持（`context.is_offline_mode()` 分支与 `literal_binds=True`），我们的定稿 env.py 已内置，详见第 3 章。注意 offline
模式不连库，依赖查询数据库的迁移逻辑（如 `op.get_bind()` 动态回填）无法生效，这类迁移需拆出来单独给 DBA 提供 SQL。

## 第 8 章 常见坑与最佳实践小结

最后一章把全教程的教训浓缩成一份避坑清单和一份 checklist，建议贴在团队 wiki 上。

### 8.1 六个高频坑

**① autogenerate 生成了「删全库」脚本。** 现象：只加了一列，生成的脚本却要把所有表 drop 一遍。原因：env.py 忘了
`import app.models`，`Base.metadata` 是空的，Alembic 认为「模型里什么都没有」→ 库里的表全是多余的。解法：确保 env.py import
所有模型模块；审查脚本时看到大片 `drop_table` 先怀疑 import，而不是执行。

**② 手工改库导致模型与库漂移。** 现象：图省事直接 `ALTER TABLE` 改了生产库，之后 autogenerate
反复生成同一个迁移。原因：结构变更绕过了迁移链，模型、迁移、真实库三者不一致。解法：一切变更走迁移；既成事实的，补一个迁移并用
`stamp` 对齐，用 `alembic check` 定期验证。

**③ 迁移脚本 import 应用 ORM 模型，老迁移失效。** 现象：新同事从空库 `upgrade head`，跑到 0003 报
`MySQL Error 1054: Unknown column 'users.nickname'`——迁移脚本里的 `User` 已是半年后的新模型，查询带上了当时还不存在的列。原因：迁移里
`from app.models import User`，而模型已演进，老脚本读到的是新模型。解法：第 5 章的铁律——迁移脚本只用 `op` 操作、轻量
`table()` 定义或原生 SQL，保证永远可重放。

**④ `alembic_version` 被误删或手工改库后版本对不上。** 现象：`upgrade` 报「表已存在」，或 Alembic
认为当前版本比实际落后。原因：版本表记录与真实结构脱节。解法：核对真实结构后，用 `alembic stamp <revision>` 手工对齐版本号，让
Alembic 从正确的位置继续。

**⑤ 两人同时基于同一版本生成迁移。** 现象：`upgrade head` 报 multiple heads。原因：并行开发产生分支。解法：第 6 章的
`alembic merge heads`；约定合并迁移冲突时再 rebase 各自的迁移文件。

**⑥ 直接修改已发布的迁移文件。** 现象：有人「优化」了已上线的 0002，结果测试库和生产库同一版本号内容不同，行为不可复现。解法：已执行的迁移是历史，只能新增迁移修正（见
7.4）。

### 8.2 十条最佳实践 checklist

1. 结构变更一律走迁移，禁止绕过 Alembic 手工改库；
2. autogenerate 只是草稿，每次执行前逐行人工审查（重点看 drop、rename 误判）；
3. 迁移脚本不 import 应用 ORM 模型，保证任意时刻可从头重放；
4. env.py 必须 import 全部模型模块，URL 以应用配置为准；
5. 约束使用稳定的命名约定（naming_convention），否则无法按名删除；
6. 数据迁移与结构迁移分离，回填用分批 UPDATE，大表控制单批大小；
7. 生产破坏性变更用 Expand-Contract 拆成两次部署，全程可回滚；
8. 百万行以上大表用 gh-ost / pt-osc 在线改表，事后 `stamp` 对齐版本；
9. 迁移前备份，破坏性迁移上线前演练 downgrade；
10. CI 跑 `upgrade head`（临时库）+ `alembic check`，已发布的迁移文件只增不改。

### 8.3 结尾

回到《SQLAlchemy 异步入门教程》的起点：那时 `fastapi_sqla_demo` 用 lifespan 里的 `create_all`
建表，简单但无法长大。现在，这个项目拥有了一套完整的异步数据库方案——`app/db.py` 提供连接与会话管理，事务控制保证业务正确性，而
Alembic 让结构演进像代码一样被版本化、可审查、可回滚、可协作。

从 `alembic init -t async alembic` 的第一个空目录，到 CI 里自动验证的四条迁移链，你掌握的已经不只是几个命令，而是一套能带进任何生产项目的方法论。下一次需求评审说「给
users 加个字段」时，你知道该怎么做了。
