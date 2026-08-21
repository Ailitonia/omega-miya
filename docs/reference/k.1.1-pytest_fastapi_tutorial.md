# pytest 入门：以 FastAPI 为例讲解如何为异步框架编写单元测试

> 目标读者：会 Python 基础、听说过 FastAPI、但还没写过测试的开发者。
> 本文中所有代码示例与命令输出均在本地真实运行验证，绝非「理论上应该能跑」的代码。

## 本文的验证环境

教程中的每一段代码、每一条命令输出都来自下面这个环境，建议你安装相同（或相近）的版本，以保证行为一致：

| 依赖           | 版本    | 作用                                 |
|----------------|---------|--------------------------------------|
| Python         | 3.12.12 | 解释器                               |
| pytest         | 9.1.1   | 测试框架本体                         |
| pytest-asyncio | 1.4.0   | 让 pytest 支持异步测试               |
| pytest-cov     | 7.1.0   | 测试覆盖率统计                       |
| pytest-mock    | 3.15.1  | 对 unittest.mock 的轻量封装          |
| fastapi        | 0.116.1 | 被测的 Web 框架                      |
| httpx          | 0.28.1  | 异步 HTTP 客户端（含 ASGITransport） |
| pydantic       | 2.11.4  | 数据校验（FastAPI 依赖）             |

> **为什么强调版本？** pytest-asyncio 在 0.x 到 1.x 之间行为变化很大（`event_loop` fixture 被移除、`asyncio_mode`
> 默认值、作用域规则都有变化）；httpx 在 0.28 之后移除了 `AsyncClient(app=app)` 的快捷写法，必须显式传 `ASGITransport`
> 。用错版本是初学者踩坑的重灾区，所以本文所有结论都以「本地实际安装版本的行为」为准。

---

## 一、为什么需要测试？为什么是 pytest？

### 1.1 不测的代价

写 FastAPI 项目时，很多人验证接口的方式是：启动 uvicorn，打开浏览器访问 `/docs`
，手动点几下。这在接口只有两三个的时候还行，但当项目长到几十个路由、依赖数据库和外部服务时，每次改动都手工回归一遍是不现实的。自动化测试的价值在于：
**把「验证正确性」变成一条可以反复执行、几秒内跑完的命令**，重构、升级依赖、加新功能时心里有底。

### 1.2 pytest 对比 unittest

Python 标准库自带 unittest，为什么要选 pytest？看同一个断言的两种写法：

```python
# unittest 写法：需要继承 TestCase、记各种 assertXxx 方法
import unittest


class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)


# pytest 写法：一个普通函数 + 原生 assert 就够了
def add(a, b):
    return a + b


def test_add():
    assert add(1, 2) == 3
```

这段代码两种运行方式都验证通过（`python -m unittest` 输出 `OK`，`pytest` 输出 `2 passed`——pytest 甚至能直接收集并运行
unittest 风格的用例，方便老项目迁移）。pytest 的核心优势：

1. **断言简洁**：直接用 Python 原生 `assert`，失败时 pytest 会做「断言重写」，把表达式中每个中间值都打印出来，不需要背
   `assertEqual`、`assertTrue`、`assertIsNone` 这一大家子方法。
2. **fixture 机制**：用依赖注入的方式准备测试环境，比 unittest 的 `setUp/tearDown` 灵活得多，还能声明作用域和组合复用。
3. **插件生态**：pytest-asyncio（异步）、pytest-cov（覆盖率）、pytest-mock（打桩）、pytest-xdist（并行）……本文会用到前三个。

---

## 二、环境准备与安装

### 2.1 安装依赖

建议使用虚拟环境（venv 或 uv），然后：

```bash
pip install fastapi pytest pytest-asyncio httpx pytest-cov pytest-mock
```

安装后可以确认版本：

```bash
$ pip show fastapi httpx pytest pytest-asyncio | grep -E "^(Name|Version)"
Name: fastapi
Version: 0.116.1
Name: httpx
Version: 0.28.1
Name: pytest
Version: 9.1.1
Name: pytest-asyncio
Version: 1.4.0
```

注意 FastAPI 的 `TestClient` 依赖 httpx，所以装 fastapi 时通常 httpx 已经在了；但写异步测试时我们会直接 import
httpx，建议显式列入依赖。

### 2.2 推荐的项目目录结构

从一开始就养成「应用代码」与「测试代码」分离的习惯：

```
todo_app/
├── app/                  # 应用代码
│   ├── __init__.py
│   ├── main.py           # FastAPI 应用与路由
│   ├── schemas.py        # Pydantic 模型
│   ├── database.py       # 数据库（依赖项）
│   └── external.py       # 调用外部 HTTP 服务
├── tests/                # 测试代码
│   ├── __init__.py
│   ├── conftest.py       # 共享 fixture
│   ├── test_sync_client.py
│   ├── test_async_client.py
│   ├── test_dependency_override.py
│   └── test_mock_external.py
└── pytest.ini            # pytest 配置
```

要点：

- **应用和测试分别建包**（都带 `__init__.py`），测试里用 `from app.main import app` 显式导入，避免靠「当前目录恰好能 import
  到」的隐式行为。
- 测试文件以 `test_` 开头，pytest 默认只收集 `test_*.py` 或 `*_test.py`。
- `pytest.ini` 放在项目根目录，它同时决定了 pytest 的 `rootdir`。

---

## 三、第一个测试

### 3.1 最小示例

新建 `test_first.py`：

```python
def add(a, b):
    """一个最简单的待测函数"""
    return a + b


def test_add():
    # pytest 直接使用 Python 原生的 assert 断言
    assert add(1, 2) == 3


def test_add_negative():
    assert add(-1, -1) == -2
```

**命名规则**是 pytest 能找到你的测试的前提：

- 文件名：`test_*.py` 或 `*_test.py`
- 函数名：`test_` 开头
- 类名：`Test` 开头（且不能有 `__init__` 方法）

运行：

```bash
$ pytest test_first.py -v
============================= test session starts ==============================
platform linux -- Python 3.12.12, pytest-9.1.1, pluggy-1.6.0
rootdir: /tmp/pytest_tutorial/01_first_test
plugins: cov-7.1.0, asyncio-1.4.0, mock-3.15.1
collecting ... collected 2 items

test_first.py::test_add PASSED                                           [ 50%]
test_first.py::test_add_negative PASSED                                  [100%]

============================== 2 passed in 0.01s ===============================
```

### 3.2 失败时长什么样

看输出是为了快速定位问题，所以先故意写一个会失败的用例：

```python
def is_even(n):
    return n % 2 == 0


def test_broken():
    # 一个故意写错的断言，用来演示失败输出
    assert is_even(5) is True
```

```bash
$ pytest test_cli_demo.py -v
test_cli_demo.py::test_is_even_true PASSED                               [ 33%]
test_cli_demo.py::test_is_even_false PASSED                              [ 66%]
test_cli_demo.py::test_broken FAILED                                     [100%]

=================================== FAILURES ===================================
_________________________________ test_broken __________________________________

    def test_broken():
        # 一个故意写错的断言，用来演示失败输出
>       assert is_even(5) is True
E       assert False is True
E        +  where False = is_even(5)

test_cli_demo.py:15: AssertionError
=========================== short test summary info ============================
FAILED test_cli_demo.py::test_broken - assert False is True
========================= 1 failed, 2 passed in 0.03s ==========================
```

注意 `E + where False = is_even(5)` 这一行——这就是「断言重写」：pytest 把表达式里函数调用的返回值单独展示出来。如果用
unittest，你只会得到一句 `False is not true`，还得自己猜是哪个环节错了。

### 3.3 常用命令行参数

| 参数            | 作用                          | 真实运行示例                |
|-----------------|-------------------------------|-----------------------------|
| `-v`            | 显示每个用例的名字和结果      | 上文输出即 `-v` 效果        |
| `-k "even"`     | 按名字关键字过滤用例          | `2 passed, 1 deselected`    |
| `-x`            | 遇到第一个失败立刻停止        | `stopping after 1 failures` |
| `--tb=no -q`    | 不显示回溯、简洁模式          | 只剩一行汇总                |
| `-s`            | 显示 print 输出（默认被捕获） | 第四章 fixture 示例用到     |
| `-m "not slow"` | 按 marker 过滤                | 第十二章用到                |

例如 `-k` 的真实输出：

```bash
$ pytest test_cli_demo.py -k "even"
test_cli_demo.py ..                                                      [100%]
======================= 2 passed, 1 deselected in 0.01s ========================
```

`-k` 后面是表达式，支持 `and/or/not`，如 `pytest -k "even and not broken"`。`-x` 适合「修一个错再跑下一个」的调试节奏；平时全量跑则不用它，以便一次看到所有失败。

---

## 四、fixture 机制

### 4.1 为什么需要 fixture

测试通常需要「上下文」：一个用户对象、一个数据库连接、一个临时目录。如果每个测试函数里都手写一遍准备代码，既重复又容易泄漏状态。fixture
就是 pytest 提供的 **依赖注入容器**：你把「准备工作」声明成 fixture，测试函数通过参数名声明「我需要它」，pytest 负责创建、注入和回收。

### 4.2 基本用法

```python
import pytest


@pytest.fixture
def user():
    """fixture 就是一个返回测试数据的函数"""
    return {"name": "小明", "age": 18}


def test_user_name(user):
    # 把 fixture 名字写进参数列表，pytest 会自动注入它的返回值
    assert user["name"] == "小明"


def test_user_age(user):
    assert user["age"] >= 18
```

关键理解： **测试函数的参数不是调用者传的，是 pytest 按参数名去注册表里找同名 fixture 注入的**。写错名字会在收集阶段就报
`fixture 'xxx' not found`，这种快速失败其实是好事。

### 4.3 setup/teardown：yield fixture

很多资源需要「用完清理」，pytest 用 `yield` 把 fixture 分成前后两半：

```python
import pytest


@pytest.fixture
def db(tmp_path):
    """yield 之前的部分是 setup，之后的部分是 teardown"""
    db_file = tmp_path / "test.db"
    db_file.write_text("")  # setup：创建临时数据库文件
    print("\n[setup] 数据库已创建")
    yield str(db_file)  # 把资源交给测试函数
    db_file.unlink()  # teardown：测试结束后清理
    print("[teardown] 数据库已删除")
```

用 `-s` 运行可以亲眼看到执行顺序（真实输出）：

```bash
$ pytest test_yield_fixture.py -s -v
test_yield_fixture.py::test_db_exists 
[setup] 数据库已创建
PASSED[teardown] 数据库已删除

test_yield_fixture.py::test_db_is_writable 
[setup] 数据库已创建
PASSED[teardown] 数据库已删除

============================== 2 passed in 0.02s ===============================
```

**为什么用 yield 而不是 return + 另一个清理函数？** 因为 yield 后的代码在「测试结束后、无论成败」都会执行（类似 try/finally
的语义），而且资源和它的清理逻辑写在同一个函数里，可读性最好。示例里的 `tmp_path` 是 pytest 内置
fixture，提供一个每个测试独立的临时目录——pytest 自带一批这样的内置 fixture（`capsys`、`monkeypatch`、`tmp_path` 等），值得翻一遍文档。

### 4.4 作用域：fixture 创建几次

默认情况下 fixture 是 **function 级**：每个测试函数调用一次。如果某个资源创建很慢（比如起一个数据库容器），可以让它整个模块甚至整个会话只创建一次：

```python
import pytest

call_count = {"n": 0}


@pytest.fixture(scope="function")  # 默认值：每个测试函数调用一次
def function_scoped():
    call_count["n"] += 1
    return call_count["n"]


@pytest.fixture(scope="module")  # 整个测试模块只调用一次
def module_scoped():
    print("\n[module fixture] 我只被创建一次")
    return {"token": "abc123"}
```

`scope` 可选值从小到大：`function`（默认）、`class`、`module`、`package`、`session`。经验法则： **创建昂贵且只读的资源用大作用域；会被测试改动的资源老老实实
function 级**，否则测试之间会互相污染——这是测试「有时过有时挂」的头号原因。

### 4.5 conftest.py：跨文件共享 fixture

fixture 定义在测试文件里只有该文件能用；放进 `conftest.py` 则对 **同目录及所有子目录**的测试生效，不需要 import：

```python
# conftest_demo/conftest.py
import pytest


@pytest.fixture
def api_base_url():
    """放在 conftest.py 里的 fixture，同目录及子目录的测试都能直接用"""
    return "https://api.example.com/v1"


@pytest.fixture
def auth_headers(api_base_url):
    # fixture 之间也可以互相依赖
    return {"Authorization": "Bearer fake-token", "Host": api_base_url}
```

```python
# conftest_demo/test_users.py
def test_url(api_base_url):
    assert api_base_url.startswith("https://")


def test_headers(auth_headers):
    assert auth_headers["Authorization"] == "Bearer fake-token"
```

```python
# conftest_demo/test_orders.py
def test_orders_endpoint(api_base_url):
    assert api_base_url + "/orders" == "https://api.example.com/v1/orders"
```

真实运行结果（连同本章其他示例）：

```bash
$ pytest . -v
conftest_demo/test_orders.py::test_orders_endpoint PASSED                [ 11%]
conftest_demo/test_users.py::test_url PASSED                             [ 22%]
conftest_demo/test_users.py::test_headers PASSED                         [ 33%]
test_basic_fixture.py::test_user_name PASSED                             [ 44%]
test_basic_fixture.py::test_user_age PASSED                              [ 55%]
test_scope.py::test_first PASSED                                         [ 66%]
test_scope.py::test_second PASSED                                        [ 77%]
test_yield_fixture.py::test_db_exists PASSED                             [ 88%]
test_yield_fixture.py::test_db_is_writable PASSED                        [100%]

============================== 9 passed in 0.03s ===============================
```

注意 `auth_headers` 依赖了另一个 fixture `api_base_url`——fixture 可以像搭积木一样层层组合，这正是它强于 unittest `setUp`
的地方。另外 conftest.py 可以 **分层**：项目根目录放一个、tests/ 放一个、tests/api/ 再放一个，内层可以覆盖外层同名
fixture，作用域只影响自己目录下的测试。

---

## 五、参数化测试

### 5.1 为什么不用 for 循环

测试「边界值组合」时，直觉写法是在一个测试函数里 for 循环多组数据。问题是： **循环里第一组失败，后面的组根本没机会跑**
，而且报告里只有一条用例，看不出是哪组数据挂了。`@pytest.mark.parametrize` 把每组数据变成一条独立用例，互不拖累。

### 5.2 基本用法

```python
import pytest


def normalize_title(title: str) -> str:
    """清洗文章标题：去掉首尾空白、截断到 20 个字符"""
    return title.strip()[:20]


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  hello  ", "hello"),  # 去掉首尾空白
        ("pytest 入门教程", "pytest 入门教程"),  # 中文正常保留
        ("a" * 25, "a" * 20),  # 超长被截断到 20 字符
        ("", ""),  # 空字符串边界
    ],
)
def test_normalize_title(raw, expected):
    assert normalize_title(raw) == expected
```

第一个参数是逗号分隔的参数名字符串，第二个参数是「每组值」的列表。运行后每组数据生成一条用例，用例 ID 里直接带数据，失败时一眼定位：

```bash
test_parametrize.py::test_normalize_title[  hello  -hello] PASSED        [ 62%]
test_parametrize.py::test_normalize_title[pytest \u5165\u95e8\u6559\u7a0b-pytest \u5165\u95e8\u6559\u7a0b] PASSED [ 75%]
test_parametrize.py::test_normalize_title[aaaaaaaaaaaaaaaaaaaaaaaaa-aaaaaaaaaaaaaaaaaaaa] PASSED [ 87%]
test_parametrize.py::test_normalize_title[-] PASSED                      [100%]
```

（中文在用例 ID 里会显示成转义形式，不影响运行；介意的话可以用 `ids=` 参数自定义每组的显示名。）

### 5.3 多参数组合：笛卡尔积

叠加多个 parametrize 会产生笛卡尔积，适合验证交换律这类「对所有组合都成立」的性质：

```python
import pytest


@pytest.mark.parametrize("x", [0, 1])
@pytest.mark.parametrize("y", [2, 3])
def test_add_commutative(x, y):
    """多个 parametrize 叠加会产生笛卡尔积：2 x 2 = 4 条用例"""
    assert x + y == y + x
```

```bash
test_multi_param.py::test_add_commutative[2-0] PASSED                    [ 12%]
test_multi_param.py::test_add_commutative[2-1] PASSED                    [ 25%]
test_multi_param.py::test_add_commutative[3-0] PASSED                    [ 37%]
test_multi_param.py::test_add_commutative[3-1] PASSED                    [ 50%]
```

后面第九章会看到，parametrize 还能和异步测试、HTTP 客户端测试自由组合。

---

## 六、异步测试的痛点与 pytest-asyncio

### 6.1 直接测协程会发生什么

FastAPI 的路由都是 `async def`，返回值是协程。新手第一反应是像测普通函数一样测它：

```python
import asyncio


async def fetch_data():
    """模拟一个异步数据获取函数"""
    await asyncio.sleep(0.01)
    return {"id": 1, "title": "pytest 入门"}


def test_fetch_data_naive():
    # 错误示范：直接调用协程函数，拿到的不是返回值，而是协程对象
    result = fetch_data()
    assert result["id"] == 1
```

真实运行结果——失败，而且报的是 TypeError 而不是断言错误：

```bash
$ pytest test_async_naive.py
=================================== FAILURES ===================================
____________________________ test_fetch_data_naive _____________________________

    def test_fetch_data_naive():
        # 错误示范：直接调用协程函数，拿到的不是返回值，而是协程对象
        result = fetch_data()
>       assert result["id"] == 1
               ^^^^^^^^^^^^
E       TypeError: 'coroutine' object is not subscriptable

test_async_naive.py:13: TypeError
============================== 1 failed in 0.02s ===============================
sys:1: RuntimeWarning: coroutine 'fetch_data' was never awaited
```

这里有两个信息都值得记住：

1. **调用 `async def` 函数不会执行它**，只会创建一个协程对象；想拿到结果必须有人（事件循环）去 await 它。
2. 结尾的 `RuntimeWarning: coroutine 'fetch_data' was never awaited` 是协程被垃圾回收时的警告——看到这个警告基本就等于「你忘了
   await」。

那改成 `async def test_...` 行不行？在 pytest 9 里会直接失败并给出明确提示（真实输出）：

```bash
__________________________ test_fetch_data_no_marker ___________________________
async def functions are not natively supported.
You need to install a suitable plugin for your async framework, for example:
  - anyio
  - pytest-asyncio
  - pytest-tornasync
  - pytest-trio
  - pytest-twisted
```

pytest 核心不自带事件循环，需要插件把「运行协程」这件事接管过去。对 asyncio 生态来说，答案就是 pytest-asyncio。

### 6.2 pytest-asyncio 的两种模式

**strict（严格）模式**是默认值：异步测试必须显式加 `@pytest.mark.asyncio` 标记，异步 fixture 必须用
`@pytest_asyncio.fixture` 声明：

```python
import asyncio

import pytest
import pytest_asyncio


async def fetch_data():
    await asyncio.sleep(0.01)
    return {"id": 1, "title": "pytest 入门"}


# strict 模式下，每个异步测试都要显式加这个标记
@pytest.mark.asyncio
async def test_fetch_data():
    result = await fetch_data()
    assert result["id"] == 1
    assert result["title"] == "pytest 入门"


# 异步 fixture：用 pytest_asyncio.fixture 声明
@pytest_asyncio.fixture
async def article():
    await asyncio.sleep(0.01)  # 模拟异步初始化
    data = {"id": 2, "title": "异步 fixture"}
    yield data  # yield 之后可以做异步清理
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_article_fixture(article):
    assert article["title"] == "异步 fixture"
```

```bash
$ pytest test_async_strict.py -v
asyncio: mode=Mode.STRICT, debug=False
collecting ... collected 2 items

test_async_strict.py::test_fetch_data PASSED                             [ 50%]
test_async_strict.py::test_article_fixture PASSED                        [100%]

============================== 2 passed in 0.03s ===============================
```

**auto 模式**：在配置里加一行 `asyncio_mode = auto`，之后所有 `async def` 测试函数和异步 fixture 自动被接管，不用加任何标记。这是
FastAPI 项目的常见选择，因为整个测试套件几乎都是异步的。`pytest.ini` 写法：

```ini
[pytest]
asyncio_mode = auto
```

```python
# auto 模式下：async def 测试函数无需任何标记，自动被 pytest-asyncio 接管
async def test_fetch_data():
    result = await fetch_data()
    assert result["id"] == 1
```

```bash
$ pytest -v
configfile: pytest.ini
asyncio: mode=Mode.AUTO, debug=False
test_async_auto.py::test_fetch_data PASSED                               [100%]

============================== 1 passed in 0.02s ===============================
```

如果项目用 pyproject.toml 管理配置，等效写法（本地同样验证通过，`configfile: pyproject.toml`）：

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "slow: 运行较慢的测试",
]
```

**怎么选？** 纯 FastAPI 项目建议 auto，省去每个函数一行标记；如果测试套件里混了别的异步框架（如 trio、anyio 插件），用 strict
显式标记，避免插件之间抢测试。

> **版本提醒**：pytest-asyncio 0.21 及更早版本里有 `event_loop` fixture 和 `ScopeMismatch` 报错；1.x 已移除 `event_loop`
> fixture，不同作用域的 fixture 会自动使用对应作用域的事件循环。本文基于 1.4.0，网上老教程里重写 `event_loop` fixture
> 的做法在新版本下已失效，不要再抄。

---

## 七、FastAPI 实战：一个待办事项 API

前面学的都是「零件」，现在把它们装进一个真实项目。我们写一个待办事项（Todo）CRUD API，故意包含单元测试里最常见的三类难点：

- **异步路由**：所有路由都是 `async def`；
- **Pydantic 校验**：非法请求要被 422 拦下；
- **依赖注入与外部调用**：数据库通过 `Depends(get_db)` 注入，另有一个路由调用外部格言服务——测试时这两样都要被替换掉。

### 7.1 `app/schemas.py`：Pydantic 模型

```python
"""Pydantic 模型：定义请求/响应的数据结构与校验规则"""
from pydantic import BaseModel, Field


class TodoCreate(BaseModel):
    """创建待办事项的请求体"""

    title: str = Field(min_length=1, max_length=100)  # 标题必填，1~100 字符
    description: str | None = None  # 描述可选
    done: bool = False  # 默认未完成


class Todo(TodoCreate):
    """返回给客户端的完整待办事项（带 id）"""

    id: int


class Motivation(BaseModel):
    """来自外部格言服务的响应"""

    quote: str
```

### 7.2 `app/database.py`：可替换的数据库依赖

```python
"""一个极简的异步内存数据库，用来演示「可替换的依赖」

真实项目中这里会是 SQLAlchemy / Tortoise ORM 之类的异步数据库会话，
测试时通过 dependency_overrides 替换成测试专用实例。
"""
from app.schemas import Todo, TodoCreate


class Database:
    """用字典模拟的异步 KV 存储"""

    def __init__(self) -> None:
        self._items: dict[int, Todo] = {}
        self._next_id: int = 1

    async def create(self, data: TodoCreate) -> Todo:
        todo = Todo(id=self._next_id, **data.model_dump())
        self._items[todo.id] = todo
        self._next_id += 1
        return todo

    async def get(self, todo_id: int) -> Todo | None:
        return self._items.get(todo_id)

    async def list(self) -> list[Todo]:
        return list(self._items.values())

    async def delete(self, todo_id: int) -> bool:
        return self._items.pop(todo_id, None) is not None


# 应用运行时使用的全局数据库实例
_default_db = Database()


async def get_db() -> Database:
    """FastAPI 依赖项：每个请求通过 Depends(get_db) 拿到数据库"""
    return _default_db
```

**设计意图**：把数据库藏在 `get_db` 依赖函数后面，而不是在路由里直接引用全局变量。这个小小的间接层就是测试隔离的支点——第十章会看到，只要替换
`get_db`，就能在不改一行应用代码的情况下换掉整个数据库。

### 7.3 `app/external.py`：外部 HTTP 调用

```python
"""调用外部 HTTP 服务的模块（测试时需要被 mock 掉）"""
import httpx

QUOTE_API_URL = "https://quotes.example.com/api/today"


async def fetch_quote() -> str:
    """从外部格言服务获取每日一句

    注意：单元测试绝不应该真的访问外网，
    测试时我们会用 mock 替换掉这个函数。
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(QUOTE_API_URL, timeout=5)
        resp.raise_for_status()
        return resp.json()["quote"]
```

### 7.4 `app/main.py`：路由

```python
"""FastAPI 应用入口：待办事项 CRUD API"""
from fastapi import Depends, FastAPI, HTTPException, status

from app import external
from app.database import Database, get_db
from app.schemas import Motivation, Todo, TodoCreate

app = FastAPI(title="Todo API")


@app.post("/todos/", response_model=Todo, status_code=status.HTTP_201_CREATED)
async def create_todo(data: TodoCreate, db: Database = Depends(get_db)):
    """创建待办事项"""
    return await db.create(data)


@app.get("/todos/", response_model=list[Todo])
async def list_todos(db: Database = Depends(get_db)):
    """列出全部待办事项"""
    return await db.list()


@app.get("/todos/{todo_id}", response_model=Todo)
async def get_todo(todo_id: int, db: Database = Depends(get_db)):
    """按 id 查询，不存在返回 404"""
    todo = await db.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    return todo


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: int, db: Database = Depends(get_db)):
    """删除待办事项，不存在返回 404"""
    deleted = await db.delete(todo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="待办事项不存在")


@app.get("/motivation", response_model=Motivation)
async def motivation():
    """返回来自外部服务的每日格言（演示需要 mock 的外部依赖）"""
    quote = await external.fetch_quote()
    return Motivation(quote=quote)
```

先手工冒烟一遍，确认应用本身没问题（真实输出）：

```python
>> > from fastapi.testclient import TestClient
>> > from app.main import app
>> > c = TestClient(app)
>> > c.post('/todos/', json={'title': '写教程'}).json()
{'title': '写教程', 'description': None, 'done': False, 'id': 1}
>> > c.get('/todos/999').status_code
404
>> > c.post('/todos/', json={'title': ''}).status_code  # 空标题被 Pydantic 拦截
422
```

---

## 八、同步方式测试 FastAPI：TestClient

`fastapi.testclient.TestClient` 是上手最快的测试工具：它是同步接口，不用装 pytest-asyncio，在普通测试函数里直接调用：

```python
"""同步方式测试 FastAPI：TestClient 快速上手"""
import pytest
from fastapi.testclient import TestClient

from app.database import Database, get_db
from app.main import app


@pytest.fixture
def client():
    """TestClient 可以在普通（同步）测试函数里直接使用"""
    test_db = Database()

    async def _get_test_db():
        return test_db

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as c:  # with 语法会触发应用的启动/关闭事件
        yield c
    app.dependency_overrides.clear()


def test_create_todo_sync(client):
    resp = client.post("/todos/", json={"title": "学习 TestClient"})
    assert resp.status_code == 201
    assert resp.json()["title"] == "学习 TestClient"


def test_list_todos_sync(client):
    client.post("/todos/", json={"title": "第一件事"})
    client.post("/todos/", json={"title": "第二件事"})
    resp = client.get("/todos/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
```

TestClient 底层基于 httpx，内部会自己开一个事件循环门户（portal）去驱动你的异步应用，所以「同步代码测异步应用」成立。两个细节：

- 用 `with TestClient(app)` 包裹，才会执行 FastAPI 的 startup/shutdown 事件（比如建连接池）；裸用 `TestClient(app)` 则不会。
- 测试结束后记得 `app.dependency_overrides.clear()`，否则覆盖会泄漏到其他测试文件。

**TestClient 的局限**：它是纯同步接口——请求发出后阻塞等待响应，你不能在测试里 `await` 别的协程、不能方便地并发发多个请求、测
WebSocket 流式交互时也比较别扭；而且它在自己的线程里跑事件循环，和你测试代码所在的循环不是同一个，混用异步资源（如测试里创建的
asyncio.Queue 传给应用用）时会埋雷。另外本文写作时也实测了「在 async 测试函数里直接用 TestClient」：在 starlette 0.46
下它能跑通，但这种跨循环的用法并不优雅。 **结论：简单的接口冒烟用 TestClient 很快；成体系的异步测试，用下一章的
httpx.AsyncClient。**

---

## 九、异步方式测试 FastAPI：httpx.AsyncClient + ASGITransport

### 9.1 推荐写法

httpx 0.28 之后，`AsyncClient(app=app)` 的快捷写法已被移除，必须显式构造 ASGI 传输层：

```python
from httpx import ASGITransport, AsyncClient

transport = ASGITransport(app=app)
async with AsyncClient(transport=transport, base_url="http://test") as client:
    resp = await client.get("/todos/")
```

**为什么这是推荐写法？** `ASGITransport` 让请求不经过任何真实网络与端口，直接在内存里调用 ASGI 应用——快、稳、不占用端口，且客户端和测试代码跑在
**同一个事件循环**里，可以在测试里自由 await。`base_url="http://test"` 只是给相对路径补一个合法的主机名，写什么无所谓。

### 9.2 项目级 conftest.py

把「全新数据库 + 依赖覆盖 + 异步客户端」做成一组可复用 fixture，这是整个测试体系的核心：

```python
"""测试共享 fixture：每个测试都用一份全新的数据库 + 独立的客户端"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Database, get_db
from app.main import app


@pytest.fixture
def fresh_db() -> Database:
    """每个测试一个全新的内存数据库，保证测试之间互不影响"""
    return Database()


@pytest.fixture
def override_app(fresh_db):
    """用 dependency_overrides 把 get_db 替换成测试数据库"""

    async def _get_test_db() -> Database:
        return fresh_db

    app.dependency_overrides[get_db] = _get_test_db
    yield app
    app.dependency_overrides.clear()  # teardown：恢复原始依赖


@pytest_asyncio.fixture
async def client(override_app):
    """异步 HTTP 客户端：直接驱动 ASGI 应用，不需要真的启动服务器"""
    transport = ASGITransport(app=override_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

三个 fixture 形成一条依赖链：`client` → `override_app` → `fresh_db`。测试函数只要声明 `client`
一个参数，整条链自动建好，用完自动清理——这就是第四章「fixture 层层组合」在实战中的样子。

> 注意：因为项目 `pytest.ini` 里设了 `asyncio_mode = auto`，这里的 `@pytest_asyncio.fixture` 写成 `@pytest.fixture`
> 也能工作；但显式使用 `pytest_asyncio.fixture` 语义更清晰，切回 strict 模式也不用改，推荐保留。

### 9.3 覆盖正常分支与错误分支

```python
"""异步方式测试 FastAPI：httpx.AsyncClient + ASGITransport"""
import pytest

pytestmark = pytest.mark.api  # 给整个文件打上 api 标记


async def test_create_todo(client):
    resp = await client.post("/todos/", json={"title": "写测试", "description": "用 httpx"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["title"] == "写测试"
    assert body["done"] is False


async def test_get_todo(client):
    await client.post("/todos/", json={"title": "买牛奶"})
    resp = await client.get("/todos/1")
    assert resp.status_code == 200
    assert resp.json()["title"] == "买牛奶"


async def test_get_todo_not_found(client):
    """错误分支：查询不存在的 id 返回 404"""
    resp = await client.get("/todos/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "待办事项不存在"


async def test_create_todo_validation_error(client):
    """错误分支：空标题触发 Pydantic 校验，返回 422"""
    resp = await client.post("/todos/", json={"title": ""})
    assert resp.status_code == 422


async def test_delete_todo(client):
    await client.post("/todos/", json={"title": "待删除"})
    resp = await client.delete("/todos/1")
    assert resp.status_code == 204
    # 删除后再查就是 404
    resp = await client.get("/todos/1")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "title",
    ["短标题", "包含 emoji 🎉 的标题", "x" * 100],  # 100 字符是允许的上限
)
async def test_create_todo_parametrized(client, title):
    """参数化 + 异步 + HTTP 测试三者可以组合使用"""
    resp = await client.post("/todos/", json={"title": title})
    assert resp.status_code == 201
    assert resp.json()["title"] == title
```

几条写接口测试的经验：

1. **每个用例都断言状态码**。只断言响应体的话，404 的 `{"detail": ...}` 可能碰巧也有你期望的字段名，状态码是第一道防线。
2. **错误分支和正常分支同样重要**：404、422 这些路径往往藏着真实 bug（比如忘记抛 HTTPException 导致返回 200 + null）。
3. **测业务状态码语义**：创建用 201 而不是 200、删除成功用 204——断言这些约定能保证 API 对客户端的行为稳定。
4. **parametrize 用来扫边界**：1 字符、100 字符上限、含特殊字符，每组独立成例。

---

## 十、依赖覆盖：app.dependency_overrides

上一章的 conftest 已经用了覆盖，这一章把原理讲透，并展示两个进阶用法。FastAPI 处理请求时，遇到 `Depends(get_db)` 会先查
`app.dependency_overrides` 这张「替换表」：表里有 `get_db` 的条目就用替身，没有才调原函数。测试做隔离，本质就是
**每个测试往表里放一份全新的替身，跑完清空**。

### 10.1 验证隔离真的生效

光「用了覆盖」不够，还要写一个测试证明隔离成立——在替身 A 里写入数据，换替身 B 后应该读不到：

```python
"""依赖覆盖：演示 dependency_overrides 如何实现测试隔离"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.database import Database, get_db
from app.main import app


async def test_override_isolation():
    """两个「数据库」各自独立：先在 db1 创建数据，再验证 db2 里查不到"""
    # 第一个「数据库」：创建一条数据
    db1 = Database()

    async def _db1():
        return db1

    app.dependency_overrides[get_db] = _db1
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/todos/", json={"title": "只在 db1 里"})
        assert resp.status_code == 201

    # 换成第二个「数据库」：刚才创建的数据不应该存在
    db2 = Database()

    async def _db2():
        return db2

    app.dependency_overrides[get_db] = _db2
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/todos/")
        assert resp.status_code == 200
        assert resp.json() == []  # 隔离生效：db2 是空的

    app.dependency_overrides.clear()
```

这个测试同时演示了「不经过 conftest、在单个测试里手动覆盖」的写法——覆盖只是一句字典赋值，随时随地可用。

### 10.2 用「坏掉的依赖」测错误处理

正常路径好测，异常路径难造。有了依赖覆盖，可以让数据库「恰好在这个时候挂掉」：

```python
@pytest.mark.slow
async def test_override_with_broken_db():
    """用一个「坏掉的数据库」验证应用的错误处理路径"""

    class BrokenDatabase(Database):
        async def get(self, todo_id: int):
            raise RuntimeError("数据库连接失败")

    async def _broken():
        return BrokenDatabase()

    app.dependency_overrides[get_db] = _broken
    # raise_app_exceptions=False：让应用把异常转成 500 响应，
    # 否则 ASGITransport 默认会把应用里的异常直接抛进测试函数
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/todos/1")
        assert resp.status_code == 500  # 未捕获异常 -> 500

    app.dependency_overrides.clear()
```

**这里有一个本文实测发现的坑**：`ASGITransport` 默认 `raise_app_exceptions=True`，应用里未捕获的异常会被直接抛进你的测试函数（测试变成
RuntimeError 失败），而不是得到 500 响应。想断言 500 就必须显式传 `raise_app_exceptions=False`。这个行为和老版本 TestClient（
`raise_server_exceptions`）类似但参数名不同，迁移代码时注意。

---

## 十一、Mock 外部服务

`/motivation` 路由依赖 `app.external.fetch_quote()`，它会真的发 HTTP 请求。单元测试里绝不能让它碰到外网：一是慢且不稳定，二是
CI 环境常常根本没网。方案是用 mock 把这个函数换成「返回固定值的替身」。

本文用 pytest-mock（对 unittest.mock 的薄封装，自动在测试结束后还原 patch，省去 with 块）：

```python
"""Mock 外部 HTTP 服务：单元测试绝不应该真的访问外网"""
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_motivation_with_mock(mocker):
    """用 pytest-mock 把 fetch_quote 换成返回固定值的 AsyncMock"""
    # patch 的目标是被使用处的名字：app.main.external.fetch_quote
    mock_fetch = mocker.patch(
        "app.external.fetch_quote",
        new=AsyncMock(return_value="种一棵树最好的时间是十年前，其次是现在。"),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/motivation")

    assert resp.status_code == 200
    assert resp.json() == {"quote": "种一棵树最好的时间是十年前，其次是现在。"}
    mock_fetch.assert_awaited_once()  # 验证确实调用了一次外部服务（的替身）


async def test_motivation_external_failure(mocker):
    """外部服务挂了的时候，应用返回 500（异常未被路由捕获）"""
    mocker.patch(
        "app.external.fetch_quote",
        new=AsyncMock(side_effect=RuntimeError("外部服务超时")),
    )

    # raise_app_exceptions=False：让 ASGI 应用把异常转成 500 响应，而不是抛进测试
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/motivation")

    assert resp.status_code == 500
```

三个关键点：

1. **异步函数要用 `AsyncMock`**，不能用普通 `MagicMock`——后者被 await 时会报
   `TypeError: object MagicMock can't be used in 'await' expression`，这是新手用 mock 测异步代码最常犯的错误。
2. **patch 的字符串是「被使用处」而不是「定义处」**。`main.py` 里写的是 `external.fetch_quote()`（通过模块属性访问），所以 patch
   `app.external.fetch_quote` 有效；如果 `main.py` 写的是 `from app.external import fetch_quote`，名字就被绑进了
   `app.main` 命名空间，那就得 patch `app.main.fetch_quote`。记不准就两个都试试，失败信息很直白。
3. **`assert_awaited_once()`** 验证替身被 await 了恰好一次——mock 不只是「挡子弹」，还能做行为断言（调没调、调几次、参数是什么）。

> 另一个思路是 respx 库：不 patch 函数，而是在 httpx 传输层拦截特定 URL 并返回假响应，mock 粒度更细（能测
> URL、header、重试逻辑）。本文选 pytest-mock 是因为它对「替换整个依赖函数」这一需求更直接，且无需新增依赖；需要验证请求细节的场景推荐试试
> respx。

**依赖覆盖 vs mock 怎么选？** 能走 FastAPI 依赖系统的（数据库、配置、当前用户）优先用 `dependency_overrides`
，语义清晰、类型安全；不走依赖系统的模块级函数（如这里的外部 HTTP 调用、发邮件、第三方 SDK）用 mock。当然也可以把 `fetch_quote`
改造成依赖项然后覆盖——两种手段都掌握，按代码结构选顺手的。

---

## 十二、测试组织与最佳实践

### 12.1 自定义 markers

测试多了以后要能「挑着跑」。比如把耗时的用例打上 `slow` 标记，开发时跳过，CI 里全量跑。先在配置里注册
marker（注册后拼错名字会直接报错，而不是静默不匹配）：

```ini
[pytest]
asyncio_mode = auto
markers =
    slow: 运行较慢的测试（可用 -m "not slow" 跳过）
    api: 直接测试应用接口的用例
```

用 `pytestmark = pytest.mark.api` 给整个文件打标记（见第九章示例），或用装饰器给单个用例打标记（见第十章 `@pytest.mark.slow`
）。过滤运行的真实输出：

```bash
$ pytest -m "not slow"
======================= 13 passed, 1 deselected in 0.12s =======================
```

`-m` 支持表达式：`-m "api and not slow"`。

### 12.2 conftest 分层与 fixture 复用

回顾第九章的 conftest：`fresh_db` → `override_app` → `client` 这条链被 8 个测试复用，但定义只写了一份。当项目长大，可以分层：

```
conftest.py            # 全项目通用：事件循环策略、环境变量、日志
tests/conftest.py      # 测试通用：client、fresh_db
tests/api/conftest.py  # 仅接口测试：预置种子数据的 fixture
```

内层 conftest 可以 **覆盖**外层同名 fixture（比如把 `fresh_db` 换成连真实测试库的版本），只影响自己目录——用目录结构表达测试分层，比在一堆
if/else 里切换配置干净得多。

### 12.3 命名与组织清单

- 测试文件 `test_*.py`，与被测模块同名（`main.py` ↔ `test_main.py` 的变体）；
- 一个测试只验证一件事，用例名即文档：`test_get_todo_not_found` 比 `test_get` 强得多；
- 每个用例独立：不依赖其他用例的执行顺序和残留数据（本文所有用例随便打乱顺序跑都能过，靠的就是每例一份 `fresh_db`）；
- 测试也要可读：Arrange（准备数据）→ Act（发请求）→ Assert（断言）三段式，必要时用空行隔开。

---

## 十三、测试覆盖率：pytest-cov

「测试都通过」不代表「代码都被测过」。覆盖率工具告诉你哪些行从未被执行——那些行就是测试盲区。运行：

```bash
$ pytest --cov=app --cov-report=term-missing
```

本地真实输出：

```bash
============================= test session starts ==============================
configfile: pytest.ini
asyncio: mode=Mode.AUTO, debug=False
collected 14 items

tests/test_async_client.py ........                                      [ 57%]
tests/test_dependency_override.py ..                                     [ 71%]
tests/test_mock_external.py ..                                           [ 85%]
tests/test_sync_client.py ..                                             [100%]

================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.12-final-0 _______________

Name              Stmts   Miss  Cover   Missing
-----------------------------------------------
app/__init__.py       0      0   100%
app/database.py      19      1    95%   38
app/external.py       7      4    43%   13-16
app/main.py          26      1    96%   37
app/schemas.py        9      0   100%
-----------------------------------------------
TOTAL                61      6    90%
============================== 14 passed in 0.24s ==============================
```

读这份报告：

- `--cov=app` 限定只统计 app 包；`term-missing` 把未覆盖的行号列在 `Missing` 列。
- `external.py` 只有 43%，缺 13-16 行——正是 `fetch_quote` 里真实发 HTTP 请求的那段，因为我们 mock 掉了它，函数体从未执行。这是
  **预期内的盲区**：它属于集成测试的范畴。这也直观展示了 mock 的代价：被 mock 的代码得不到覆盖，所以核心逻辑不要过度 mock。
- `database.py` 缺的第 38 行是 `return _default_db`——原始 `get_db` 在测试里全被覆盖了，同样符合预期。
- 可以在 CI 里加门槛：`pytest --cov=app --cov-fail-under=85`，低于阈值则构建失败。

**正确心态**：覆盖率是「找盲区」的探照灯，不是 KPI。100% 覆盖不代表没有 bug（断言可能根本没验关键行为），但关键模块 40%
一定说明测试不够。

---

## 十四、常见问题 FAQ

**Q1：测试报 `RuntimeWarning: coroutine 'xxx' was never awaited` 是什么意思？**

你（或你的测试）调用了一个 `async def` 函数但没有 await 它，协程对象被直接丢弃了。在 pytest 场景下三种典型成因：① 测试函数本身是
`async def` 但 pytest-asyncio 没生效（没装、strict 模式忘了加 `@pytest.mark.asyncio`）；② 像 6.1 节那样把协程函数当普通函数调；③
用 `MagicMock` 替代了异步函数（应改用 `AsyncMock`）。pytest 9 对情形①会直接报
`async def functions are not natively supported` 并列出可选插件，按提示装好插件、配对模式即可。

**Q2：异步 fixture 的作用域和事件循环是什么关系？session 级 fixture 还能用吗？**

pytest-asyncio 1.x 中，每个作用域（function/module/session）各自对应一个事件循环，fixture 在自己作用域的循环里运行。默认配置下
**每个测试函数跑在独立的全新事件循环里**——这一点本文实测验证过（两个测试里 `asyncio.get_running_loop()`
返回不同对象）。推论：session 级 fixture 里创建的资源，如果是在创建时就绑定事件循环的对象（如老版本的数据库连接池、自己
`loop=` 参数创建的 asyncio 原语），拿到 function 级测试里 await 就可能报 `attached to a different loop`。解法：① 把 fixture
作用域降到 function；② 或在配置里统一循环作用域，如 `asyncio_default_fixture_loop_scope = "session"` 配合
`asyncio_default_test_loop_scope = "session"`。老教程里常见的
`ScopeMismatch: You tried to access the 'function' scoped fixture 'event_loop'...` 报错来自 pytest-asyncio ≤0.23，1.x 移除了
`event_loop` fixture 后不会再出现，看到这类答案注意甄别时效。

**Q3：异步生成器 fixture（`yield` 写法）的清理代码一定会执行吗？**

会。pytest 保证 fixture 的 teardown（`yield` 之后的部分）在测试结束后执行， **即使测试断言失败或抛异常**。本文实测输出：

```bash
$ pytest test_asyncgen_cleanup.py -s -q
[setup] 建立连接
.[teardown] 关闭连接
1 passed in 0.03s
```

对应写法：

```python
@pytest_asyncio.fixture
async def connection():
    print("\n[setup] 建立连接")
    await asyncio.sleep(0.01)
    yield "conn-obj"
    # 测试结束后（即使断言失败）这里的清理代码依然会执行
    print("[teardown] 关闭连接")
    await asyncio.sleep(0.01)
```

注意清理代码本身是异步的，如果里面再抛异常，pytest 会报 error 而不是简单的 failed——清理逻辑要尽量防御性（比如先判空、catch
掉「连接已关闭」）。

**Q4：`ASGITransport` 把应用里的异常直接抛进了我的测试，没看到 500 响应？**

这是 httpx 的默认行为（`raise_app_exceptions=True`），目的是让 bug 直接暴露在测试里。如果你的测试目标恰恰是「断言服务返回
500」，显式传 `ASGITransport(app=app, raise_app_exceptions=False)` 即可，见第十章示例。

**Q5：多个测试文件都要用同一个 `app`，数据会串吗？**

应用对象 `app` 是全局单例，会串的不是代码而是 **状态**。本文的方案是每个测试通过 `fresh_db` fixture 拿到全新数据库实例 +
结束后 `dependency_overrides.clear()`，因此用例之间互不影响。如果你测的是真实数据库，则常用「每个测试一个事务、结束回滚」的模式达到同样效果。

---

## 十五、总结

回顾一下我们走过的路：

1. **pytest 基础**：`test_` 命名约定 + 原生 `assert` + 断言重写，写测试的心智负担远低于 unittest；
2. **fixture**：依赖注入式的测试环境准备，`yield` 划分 setup/teardown，作用域控制创建次数，conftest.py 实现共享与分层；
3. **parametrize**：边界数据每组独立成例，失败精准定位；
4. **pytest-asyncio**：`asyncio_mode = auto` 一行配置让 pytest 原生般支持 `async def` 测试与异步 fixture，注意 1.x 与老教程的
   `event_loop` 写法已不兼容；
5. **FastAPI 测试三件套**：`httpx.AsyncClient + ASGITransport` 在内存中驱动应用；`dependency_overrides` 换掉数据库实现测试隔离；
   `AsyncMock` 换掉外部 HTTP 调用；
6. **工程化**：markers 挑着跑、conftest 分层、pytest-cov 照出测试盲区。

给新手的最后一句话： **先让测试跑起来，再追求优雅**。一个 201 状态码断言的价值，远大于一个躺在计划里的完美测试框架。

### 延伸阅读

- pytest 官方文档：https://docs.pytest.org/
- pytest-asyncio 文档：https://pytest-asyncio.readthedocs.io/
- FastAPI 测试章节：https://fastapi.tiangolo.com/tutorial/testing/
  与 https://fastapi.tiangolo.com/advanced/testing-dependencies/
- httpx ASGITransport：https://www.python-httpx.org/advanced/transports/#asgi-transport
- pytest-cov：https://pytest-cov.readthedocs.io/
- unittest.mock（含 AsyncMock）：https://docs.python.org/3/library/unittest.mock.html

---

> 附：本文全部示例的运行统计——6 个示例目录共 30 个用例（第一~六章及 FAQ 演示）+ 实战项目 todo_app 14 个用例，合计 44
> 个测试用例全部通过；另有 3 个为展示报错而故意写错的演示用例（3.2 节断言失败、6.1 节两个异步错误示范），其失败输出已如实贴在正文中。todo_app
> 应用代码总行覆盖率 90%。验证环境：Python 3.12.12 / pytest 9.1.1 / pytest-asyncio 1.4.0 / fastapi 0.116.1 / httpx
> 0.28.1 /
> pydantic 2.11.4 / pytest-cov 7.1.0 / pytest-mock 3.15.1。
