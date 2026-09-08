# nonebug 教程与最佳实践

> 适用版本：nonebug 0.4.x / nonebot2 >= 2.3.0 / pytest 7 ~ 9
>
> 本文基于 nonebug 源码与官方测试用例整理，所有示例均可运行。

**目录**

- [1. 简介与准备](#1-简介与准备)
- [2. 快速上手](#2-快速上手)
- [3. 核心概念](#3-核心概念)
- [4. 测试 Matcher（核心章节）](#4-测试-matcher核心章节)
- [5. 其他测试场景](#5-其他测试场景)
- [6. 最佳实践](#6-最佳实践)
- [附录 A：API 速查表](#附录-aapi-速查表)
- [附录 B：工作原理深入](#附录-b工作原理深入)
- [附录 C：完整可运行示例](#附录-c完整可运行示例)

---

## 1. 简介与准备

### 1.1 nonebug 是什么

nonebug 是 NoneBot2 官方的测试框架，基于 pytest 构建。安装后它会自动注册为 pytest 插件，你的测试中可以直接注入 `app`
fixture，无需手工初始化 NoneBot。

它提供四大测试能力：

| 能力             | 入口                     | 典型场景                                      |
|------------------|--------------------------|-----------------------------------------------|
| 事件处理流程测试 | `app.test_matcher(...)`  | 验证 matcher 的规则、权限、多轮会话、消息发送 |
| API 调用测试     | `app.test_api()`         | 验证 bot 调用了哪些 API、参数与返回值         |
| 依赖注入函数测试 | `app.test_dependent(fn)` | 单独测试 handler / 依赖注入函数               |
| ASGI 服务端测试  | `app.test_server()`      | 测试 driver 上注册的 HTTP 服务                |

### 1.2 安装与配置

```bash
pip install nonebug pytest-asyncio
```

在你的插件项目根目录添加 `pytest.ini`（或 `pyproject.toml` 中的 `[tool.pytest.ini_options]`）：

```ini
[pytest]
asyncio_mode = auto
```

nonebug 通过 `[project.entry-points.pytest11]` 入口点自动注册为 pytest 插件。若某次运行想禁用它，可加参数 `-p no:nonebug`
（nonebug 仓库自己测试时就是这样做的，然后手工导入 fixture）。

### 1.3 核心心智模型

使用 nonebug 前必须理解一句话：

> **`async with` 块内写的是"期望"，块结束时才回放执行。**

nonebug 的每个测试上下文（Context）在进入时给 NoneBot 打补丁（注入 fake adapter/bot、替换 matcher 容器），在 **退出时**
才真正驱动事件回放并逐条校验你的断言：

```python
async with app.test_matcher(matcher) as ctx:  # 进入：打补丁
    ctx.receive_event(bot, event)  # 声明：收到一个事件
    ctx.should_pass_rule(matcher=matcher)  # 声明：期望通过规则
    ctx.should_call_send(event, "你好", "result", bot=bot)  # 声明：期望发送
# ← 退出：真正调用 nonebot 的事件处理，校验以上所有期望
```

所以阅读测试代码时，`with` 块内是"剧本"，退出才是"演出"。

**本章要点**

- nonebug 是 pytest 插件，`app` fixture 即测试入口；
- 四大能力对应四个 `test_*` 方法；
- 期望写在 `with` 块内，执行发生在块退出时。

---

## 2. 快速上手

本节从零搭一个最小可运行的测试项目。假设目录结构如下：

```
my-plugin/
├── pytest.ini
├── conftest.py
├── utils.py          # 自备的 fake 工具（见 3.4）
├── plugins/
│   └── hello.py      # 被测插件
└── tests/
    └── test_hello.py
```

### 2.1 被测插件

```python
# plugins/hello.py
from nonebot import on_command
from nonebot.adapters import Bot, Event

hello = on_command("hello", block=True)


@hello.handle()
async def _(bot: Bot, event: Event):
    await hello.send("world")
    await hello.finish()
```

### 2.2 conftest.py

```python
# conftest.py
from pathlib import Path

import nonebot
import pytest


# 覆盖 nonebug 提供的同名 session fixture，在 NoneBot 初始化后加载你的插件
@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(_nonebot_init: None) -> None:
    nonebot.load_plugins(str(Path(__file__).parent / "plugins"))
```

### 2.3 第一个测试

```python
# tests/test_hello.py
import pytest
from nonebug import App

from utils import make_fake_event, make_fake_message


@pytest.mark.asyncio
async def test_hello(app: App):
    from plugins.hello import hello  # 注意：必须在测试函数内导入！

    Message = make_fake_message()

    async with app.test_matcher(hello) as ctx:
        adapter = ctx.create_adapter()
        bot = ctx.create_bot(adapter=adapter)

        event = make_fake_event(_message=Message("/hello"))()
        ctx.receive_event(bot, event)

        ctx.should_pass_rule(matcher=hello)
        ctx.should_pass_permission(matcher=hello)
        ctx.should_call_send(event, "world", "result", bot=bot)
        ctx.should_finished(matcher=hello)
```

逐行解读：

1. `from plugins.hello import hello` 放在 **函数内部**——nonebot 在 session fixture 中才初始化，顶层导入会直接报错（详见
   6.1）；
2. `app.test_matcher(hello)` 创建 matcher 测试上下文，只有 `hello` 这一个 matcher 参与本次测试；
3. `ctx.create_adapter()` / `ctx.create_bot()` 构造 fake 适配器和 bot，bot 会自动连接到 driver，上下文退出时自动断开；
4. `make_fake_event(...)()` 构造一个假的 message 事件并实例化；
5. `ctx.receive_event(bot, event)` 声明收到该事件；
6. 随后是四条期望：通过规则、通过权限、调用 `send` 并返回 `"result"`、最终 `finish`。

运行：

```bash
pytest tests/test_hello.py -v
```

**本章要点**

- 项目四件套：`pytest.ini`、`conftest.py`（加载插件）、`utils.py`（fake 工具）、测试文件；
- 被测插件在测试函数内导入；
- 标准节奏：`test_matcher` → `create_adapter`/`create_bot` → `receive_event` → 断言链。

---

## 3. 核心概念

### 3.1 初始化链路与配置注入

nonebug 注册了三个 session 级 autouse fixture（定义于 `nonebug/fixture.py`），按依赖顺序执行：

```
_nonebot_init        → nonebot.init(**kwargs)，并把全局 matcher 容器替换为 NoneBugProvider
   ↓
after_nonebot_init   → 空实现，供用户覆盖以加载插件（见 2.2）
   ↓
nonebug_init         → 启动 driver lifespan（ASGI driver 用 TestClient 的 lifespan）
   ↓
app                  → 返回 App() 实例
```

NoneBot 的初始化参数通过 pytest 的 `stash` 机制注入，在 `conftest.py` 的 `pytest_configure` 钩子中设置：

```python
# conftest.py
import pytest
from nonebug import NONEBOT_INIT_KWARGS, NONEBOT_START_LIFESPAN


def pytest_configure(config: pytest.Config) -> None:
    # 等价于 nonebot.init(superusers={"123"}, command_start={"/"})
    config.stash[NONEBOT_INIT_KWARGS] = {"superusers": {"123"}, "command_start": {"/"}}
    # 可选：不启动 lifespan（默认启动）
    # config.stash[NONEBOT_START_LIFESPAN] = False
```

两个 stash key 都定义在 `nonebug/__init__.py`：

- `NONEBOT_INIT_KWARGS`：`nonebot.init()` 的参数字典；
- `NONEBOT_START_LIFESPAN`：是否启动 driver lifespan，默认 `True`。

### 3.2 Context 生命周期

`App` 类本身只是四个 Mixin 的组合，真正的功能在各层 Context 上，继承关系如下：

```
Context                     （基类：异步上下文 + setup/run 生命周期）
 ├── ServerContext          （ASGI 测试）
 ├── ApiContext             （API 调用测试）
 │    ├── MatcherContext    （事件处理测试，最常用）
 │    └── DependentContext  （依赖注入测试）
```

`Context` 的关键行为（`nonebug/base.py`）：

- `__aenter__` 时执行 `setup()`： **打补丁阶段**——fake 化 adapter/bot、替换 matcher 容器；
- `__aexit__` 时执行 `run()`： **回放阶段**——驱动事件处理、校验所有期望；
- 同一个 `App` 同时只能有一个活跃 Context，嵌套使用会抛 `RuntimeError("Another test context is actived")`。

### 3.3 matcher 隔离：NoneBugProvider

NoneBot 全局维护一个按优先级分组的 matcher 容器（`nonebot.matcher.matchers`）。nonebug 在初始化时把它的 provider 替换为
`NoneBugProvider`，后者维护一个栈：

- 进入 Context 时，把当前 matcher 表压栈，替换为 `test_matcher(m)` 传入的 matcher（按 priority 分组）；
- 退出时弹栈恢复。

`app.test_matcher(m)` 的 `m` 支持四种形式：

| 传入形式                      | 含义                                                           |
|-------------------------------|----------------------------------------------------------------|
| `None`                        | 深拷贝当前全局 matcher 表——**所有已加载插件的 matcher 都参与** |
| 单个 matcher 类               | 只测这一个 matcher                                             |
| matcher 列表                  | 按 `matcher.priority` 自动分组                                 |
| `{priority: [matchers]}` 字典 | 手动指定分组                                                   |

大多数情况传单个 matcher 即可；需要验证优先级、阻断（block）等跨 matcher 行为时再传列表或字典。

### 3.4 自备工具：make_fake_event / make_fake_message

**重要：这两个工厂函数不在 nonebug 发布包内**，它们是 nonebug 仓库自己的测试工具（`tests/utils.py`），使用时需复制到你的项目。完整模板：

```python
# utils.py
from collections.abc import Iterable, Mapping
from typing import Optional, Union

from nonebot.adapters import Event, Message, MessageSegment
from pydantic import create_model


def escape_text(s: str, *, escape_comma: bool = True) -> str:
    s = s.replace("&", "&amp;").replace("[", "&#91;").replace("]", "&#93;")
    if escape_comma:
        s = s.replace(",", "&#44;")
    return s


def make_fake_message():
    class FakeMessageSegment(MessageSegment):
        @classmethod
        def get_message_class(cls):
            return FakeMessage

        def __str__(self) -> str:
            return self.data["text"] if self.type == "text" else f"[fake:{self.type}]"

        @classmethod
        def text(cls, text: str):
            return cls("text", {"text": text})

        @staticmethod
        def image(url: str):
            return FakeMessageSegment("image", {"url": url})

        @staticmethod
        def nested(content: "FakeMessage"):
            return FakeMessageSegment("node", {"content": content})

        def is_text(self) -> bool:
            return self.type == "text"

    class FakeMessage(Message):
        @classmethod
        def get_segment_class(cls):
            return FakeMessageSegment

        @staticmethod
        def _construct(msg: Union[str, Iterable[Mapping]]):
            if isinstance(msg, str):
                yield FakeMessageSegment.text(msg)
            else:
                for seg in msg:
                    yield FakeMessageSegment(**seg)
            return

        def __add__(self, other):
            other = escape_text(other) if isinstance(other, str) else other
            return super().__add__(other)

    return FakeMessage


def make_fake_event(
        _base: Optional[type[Event]] = None,
        _type: str = "message",
        _name: str = "test",
        _description: str = "test",
        _user_id: Optional[str] = "test",
        _session_id: Optional[str] = "test",
        _message: Optional[Message] = None,
        _to_me: bool = True,
        **fields,
) -> type[Event]:
    _Fake = create_model("_Fake", __base__=_base or Event, **fields)

    class FakeEvent(_Fake):
        model_config = {"extra": "forbid"}  # noqa: RUF012

        def get_type(self) -> str:
            return _type

        def get_event_name(self) -> str:
            return _name

        def get_event_description(self) -> str:
            return _description

        def get_user_id(self) -> str:
            if _user_id is not None:
                return _user_id
            raise NotImplementedError

        def get_session_id(self) -> str:
            if _session_id is not None:
                return _session_id
            raise NotImplementedError

        def get_message(self) -> "Message":
            if _message is not None:
                return _message
            raise NotImplementedError

        def is_tome(self) -> bool:
            return _to_me

    return FakeEvent
```

用法要点：

- `make_fake_event()` 返回的是 **事件类**，需要再 `()` 实例化；
- 常用参数：`_message`（携带的消息）、`_type`（事件类型，默认 `"message"`）、`_to_me`、`_user_id`、`_session_id`；
- 额外的自定义字段通过 `**fields` 传入 pydantic 字段定义，如 `make_fake_event(post_type=(str, "message"))`；
- `_base=` 可以基于真实适配器的事件类构造（见 5.5）。

**本章要点**

- 初始化链路：`nonebot.init` → 用户加载插件 → lifespan → `app`；
- 配置通过 `config.stash[NONEBOT_INIT_KWARGS]` 注入；
- Context = 进入打补丁 + 退出回放，且互斥；
- `test_matcher(m=None)` 意味着所有已加载 matcher 参与测试，注意隔离；
- `make_fake_event` / `make_fake_message` 需要自备，模板见上文。

---

## 4. 测试 Matcher（核心章节）

### 4.1 事件接收

`MatcherContext` 按 **事件**组织测试。每调用一次 `receive_event(bot, event)`，就开启一个新的事件组：

```python
ctx.receive_event(bot, event)
```

**规则/权限/动作断言挂靠在"最近一次" `receive_event` 上**，所以这些断言必须紧跟对应的 `receive_event` 声明；而
`should_call_api` / `should_call_send` 是整个上下文共享的队列（见 4.4）。多次 `receive_event` 即模拟多轮会话，按声明顺序回放。

### 4.2 规则与权限断言

```python
ctx.should_pass_rule(matcher=test)  # 期望 test 通过规则检查
ctx.should_not_pass_rule(matcher=test)  # 期望 test 未通过规则检查
ctx.should_ignore_rule(matcher=test)  # 期望 test 忽略规则检查
ctx.should_pass_permission(matcher=test)  # 期望通过权限检查
ctx.should_not_pass_permission(matcher=test)
ctx.should_ignore_permission(matcher=test)
```

`matcher` 参数可省略，省略时为 **通配断言**：

- `matcher=test`：专属断言，只会被 `test` 这一个 matcher 消费，消费后即移除；
- `matcher=None`：通配断言，可被任意 matcher 消费，且 **不会因未被消费而报错**（`ignore` 系列通配断言还会强制让检查结果视为通过，常配合
  `permission_updater` 场景使用）。

一次事件触发的多个 matcher 的行为可以一起声明（它们必须写在同一个事件组内）：

```python
event = make_fake_event(_message=Message())()
ctx.receive_event(bot, event)

ctx.should_pass_permission(matcher=test)  # test 通过权限
ctx.should_pass_rule(matcher=test)  # test 通过规则
ctx.should_not_pass_permission(matcher=test_not_pass_perm)  # 另一个 matcher 权限不过
ctx.should_not_pass_rule(matcher=test_not_pass_rule)
ctx.should_ignore_permission()  # 其余 matcher 忽略权限
ctx.should_not_pass_rule()  # 其余 matcher 规则不过
```

### 4.3 动作断言：pause / reject / finish

NoneBot 的会话控制通过三种"控制流异常"实现，nonebug 将其映射为动作断言：

```python
ctx.should_paused(matcher=test)  # handler 中调用了 matcher.pause()，等待下一条消息
ctx.should_rejected(matcher=test)  # 调用了 matcher.reject()，丢弃当前消息重新等待
ctx.should_finished(matcher=test)  # 调用了 matcher.finish()，会话结束
```

约束： **每个 matcher 在同一事件内只能声明一种动作**，重复声明会直接 `pytest.fail`。`matcher` 同样可省略作通配。

典型对应关系（务必记住，多轮测试全靠它）：

| handler 中的写法                         | 期望动作                                        |
|------------------------------------------|-------------------------------------------------|
| `await matcher.got(...)` 且参数未填      | `reject`（等待新输入）                          |
| `await matcher.pause()`                  | `paused`                                        |
| `await matcher.finish()` / `finish(msg)` | `finished`（`finish(msg)` 会先 send 再 finish） |
| handler 正常 return（无 got 等待）       | 无动作断言                                      |

### 4.4 发送与 API 期望：一个顺序敏感的队列

```python
ctx.should_call_send(event, message, result=None, exception=None, bot=None, **kwargs)
ctx.should_call_api(api, data, result=None, exception=None, adapter=None)
```

- `should_call_send`：期望 `bot.send(...)` 或 `matcher.send(...)` 被调用。`message` 与实际调用值用 `==` 比较，`event` 用
  `model_dump` 比较，`kwargs` 匹配额外参数（如 `at_sender=True`）；
- `should_call_api`：期望 `bot.call_api(name, **data)` 被调用。`data` 是关键字参数字典；
- `result`：该调用返回给 handler 的值（handler 里 `await bot.call_api(...)` 拿到的就是它）；
- `exception`：让该调用抛出指定异常，用于测试错误处理路径；
- `bot=` / `adapter=`：限定来源，不限定则任意 bot/adapter 均可消费。

**队列语义（最重要的约定）**：期望按声明顺序排队，实际调用必须按同样顺序发生、逐个消费。全部回放结束后队列若非空，测试失败：

```
Failed: Application has 2 api/send call(s) not called
```

如果 handler 先 send 提示再 finish 消息，就要按同样顺序声明两次 `should_call_send`。

另一个细节：消息比较要求 **类型一致**。handler 用 `send("文本")`（str）就期望 str；若实际传入的是 `Message` 对象，期望值也必须是相等的
`Message`。

### 4.5 多轮会话完整示例

这是 nonebug 官方测试的典型模式（节选自 nonebug 仓库 `tests/test_process.py`），被测插件有两个 handler：第一个发消息后
`pause`，第二个 `reject`：

```python
async def test_process(app: App):
    from tests.plugins.process import test

    Message = make_fake_message()

    async with app.test_matcher() as ctx:  # 不传 matcher：所有已加载 matcher 参与
        adapter = ctx.create_adapter()
        bot = ctx.create_bot(adapter=adapter)

        # ── 第一轮事件 ──
        event = make_fake_event(_message=Message())()
        ctx.receive_event(bot, event)

        ctx.should_pass_permission(matcher=test)
        ctx.should_pass_rule(matcher=test)
        ctx.should_call_send(event, "test_send", "result", bot=bot)
        ctx.should_call_api("test", {"key": "value"}, "result", adapter=adapter)
        ctx.should_paused(matcher=test)

        # ── 第二轮事件 ──
        event = make_fake_event(_message=Message())()
        ctx.receive_event(bot, event)

        ctx.should_pass_permission(matcher=test)
        ctx.should_pass_rule(matcher=test)
        ctx.should_rejected(matcher=test)
```

### 4.6 错误路径测试

- handler 内部抛出真实异常：回放后 nonebug 会以 `Some checks failed when handling event ...` 失败并附上异常列表——即
  handler 抛错本身就是测试失败，无需额外断言；
- API/发送失败路径：用 `should_call_api(..., exception=RuntimeError())` 模拟适配器报错，配合 handler 内的 `try/except`
  验证降级逻辑；
- 期望与实际不符的"故意失败"用例，可用 `@pytest.mark.xfail(strict=True)` 标记（nonebug 仓库自身就用了这种模式验证框架的校验能力）。

**本章要点**

- 断言挂靠最近一次 `receive_event`，多轮会话 = 多次 `receive_event`；
- `matcher=` 专属断言必被消费，通配断言可复用且不检查剩余；
- `got` 未填 → `reject`，`pause` → `paused`，`finish` → `finished`；
- API/send 期望是顺序队列，声明顺序 = 实际调用顺序。

---

## 5. 其他测试场景

### 5.1 单独测试 API 调用

不涉及事件流程、只想验证一段代码对 bot 的调用时，用 `test_api`：

```python
@pytest.mark.asyncio
async def test_got_call_api(app: App):
    async with app.test_api() as ctx:
        adapter = ctx.create_adapter()
        bot = ctx.create_bot(self_id="test", adapter=adapter)

        ctx.should_call_api("test", {"key": "value"}, "result", adapter=adapter)
        result = await bot.call_api("test", key="value")  # 直接调用，立刻消费期望
        assert result == "result"
```

与 `test_matcher` 不同：`test_api` 里代码是 **同步执行**的（`await` 完立刻消费），而 `test_matcher` 中 handler 在退出时才被驱动。

`create_bot` 创建的 bot 会自动注册进 driver（`nonebot.get_bots()` 可查），上下文退出时自动注销——可用来测试依赖 `get_bot()`
的代码。

### 5.2 测试依赖注入函数 / handler

`test_dependent`（别名 `test_handler`）单独驱动一个 handler 或任意可注入依赖的函数：

```python
@pytest.mark.asyncio
async def test_dependent(app: App):
    from nonebot.adapters import Event
    from nonebot.params import EventParam
    from utils import make_fake_event

    FakeEvent = make_fake_event(test_field=(str, "test"))

    def _handle(event: Event): ...

    async with app.test_dependent(_handle, allow_types=[EventParam]) as ctx:
        ctx.pass_params(event=FakeEvent())  # 提供注入参数
        ctx.should_return(...)  # 可选：校验返回值（用 == 比较）
```

- 传入普通函数时框架自动 `Dependent.parse`，`allow_types` 声明允许的注入参数类型；
- `pass_params` 提供依赖值，`should_return` 声明期望返回值；
- 也可用于测试参数 **类型不匹配**场景：注入不匹配类型的事件时，上下文退出会抛出 `TypeMisMatch`，配合
  `pytest.raises((TypeMisMatch, BaseExceptionGroup))` 断言。

### 5.3 测试 ASGI 服务端

`test_server` 提供一个针对 ASGI 应用的测试客户端，适合测试 adapter 在 driver 上注册的 HTTP 回调：

```python
@pytest.mark.asyncio
async def test_driver(app: App):
    # ... 定义 FakeAdapter 并 driver.register_adapter(FakeAdapter)，
    # 在 setup_http_server 注册 POST /test 路由 ...

    async with app.test_server() as ctx:
        client = ctx.get_client()
        res = await client.post("/test", data="test")
        assert res.status_code == 200
```

- 不传参数时默认测 `nonebot.get_asgi()`，并复用 lifespan 启动时创建的全局客户端；
- 传入自定义 `asgi` 应用则使用上下文自建的客户端；
- 服务端 handler 内部对 bot API 的调用同样可以用 `should_call_api` 打桩。

### 5.4 定制 fake：base= 子类化与 patch

需要保留真实适配器行为时，可以基于你自己的 Adapter/Bot 类生成 fake：

```python
class FakeAdapter(Adapter): ...  # 你的适配器实现


class FakeBot(Bot): ...


async with app.test_api() as ctx:
    adapter = ctx.create_adapter(base=FakeAdapter)  # 生成 FakeAdapter 的子类并打桩
    bot = ctx.create_bot(base=FakeBot, self_id="test", adapter=adapter)
```

生成的 fake 类名固定为 `"fake"`（`get_name()` 返回 `"fake"`），但保留基类的全部其他行为。

对于上下文创建之前就已存在的 adapter/bot，nonebug 在进入 `ApiContext` 时 **自动 monkeypatch 所有已注册 adapter 的
`_call_api` 和所有 bot 的 `send`**，因此真实适配器实例上的调用同样会被期望队列拦截，无需手工处理。也可以用
`ctx.patch_adapter(monkeypatch, adapter)` / `ctx.patch_bot(monkeypatch, bot)` 手动 patch 指定对象。

**本章要点**

- `test_api`：同步消费式验证 API 行为，bot 自动注册/注销；
- `test_dependent`：单测 handler，`pass_params` + `should_return`，还能验证 `TypeMisMatch`；
- `test_server`：ASGI 客户端测试，默认复用全局 lifespan 客户端；
- `base=` 让 fake 保留真实适配器行为；已注册的 adapter/bot 会被自动打桩。

---

## 6. 最佳实践

### 6.1 插件导入必须放在测试函数内

NoneBot 在 session fixture 中才初始化，而 pytest 收集阶段就会执行模块顶层代码。顶层导入插件会得到：

```
ValueError: NoneBot has not been initialized.
```

统一写成：

```python
async def test_xxx(app: App):
    from plugins.hello import hello  # ✅ 函数内导入
```

如果插件内 `on_command(...)` 等在 import 时就需要 driver，这一点是硬性要求。

### 6.2 项目组织与 conftest 模板

推荐的 `conftest.py`，一次性完成配置注入与插件加载：

```python
# conftest.py
from pathlib import Path

import nonebot
import pytest
from nonebug import NONEBOT_INIT_KWARGS


def pytest_configure(config: pytest.Config) -> None:
    # nonebot.init 参数：按需注入 superusers、command_start、插件专属配置等
    config.stash[NONEBOT_INIT_KWARGS] = {"command_start": {"/"}}


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(_nonebot_init: None) -> None:
    nonebot.load_plugins(str(Path(__file__).parent / "plugins"))
```

注意：`after_nonebot_init` 是 **整个 session 只执行一次**的加载点；若测试需要不同的 init 参数，只能通过 stash 在
`pytest_configure` 中统一切换（例如用环境变量区分），不能在单个测试里重复 `nonebot.init()`。

### 6.3 断言完整性：让每条期望都有归属

- 规则/权限/动作断言 **必须指定 `matcher=`**
  ，除非你明确想要通配语义。通配断言不检查"是否被消费"，漏写/错写不会报错，容易造成"测试通过但什么都没验证"的假象；
- 每个参与事件处理的 matcher，同一事件内要么声明动作，要么确认它不会执行到 handler（rule/permission 已拦截）；
- API/send 期望按实际调用顺序声明，宁可多写一条让队列消费干净，也不要留隐式未验证的调用—— **退出时队列非空会直接失败**
  ，这是框架帮你兜底的一部分。

### 6.4 多轮会话的组织方式

用注释显式分隔每轮事件；每轮重复"receive_event → checks → actions → api/send 期望"的完整结构。参考 4.5
的示例。轮数多时考虑拆成多个测试函数，每个函数聚焦一个交互片段。

### 6.5 善用 result / exception 做行为驱动

- `result` 是喂给 handler 的返回值：`assert result == "result"` 这类插件内断言也能在测试中覆盖到；
- `exception` 用于错误路径：比真实复现网络错误简单得多；
- 不要在 handler 里 mock，把一切可变性通过期望队列注入，测试会更稳定。

### 6.6 隔离性

- 默认传单个 matcher 给 `test_matcher`，避免其他插件 matcher 串扰；`m=None` 会深拷贝 **全部**已加载 matcher；
- matcher 间的优先级/block 行为，用列表或 `{priority: [...]}` 字典显式声明，不要依赖插件加载顺序；
- `create_bot` 的 bot 在上下文退出后自动断开，但 **同一测试文件内共享 session 状态**（如插件模块级变量）仍需自行重置。

### 6.7 常见报错排查表

| 报错信息                                                | 原因                                                  | 解决                                                                  |
|---------------------------------------------------------|-------------------------------------------------------|-----------------------------------------------------------------------|
| `ValueError: NoneBot has not been initialized.`         | 测试模块顶层导入了插件                                | 导入移入测试函数内（6.1）                                             |
| `RuntimeError: NoneBug is not initialized.`             | fixture 未生效（插件被 `-p no:nonebug` 禁用或未安装） | 确认安装/移除禁用参数；自测时可手工 `from nonebug.fixture import ...` |
| `RuntimeError: Another test context is actived`         | 两个 Context 嵌套或上一个未退出                       | 检查 `async with` 层级，顺序使用                                      |
| `RuntimeError: Please call receive_event first`         | 在 `receive_event` 之前用了 `should_*`                | 先声明事件再写断言                                                    |
| `Failed: Application has N api/send call(s) not called` | 期望未被消费：没调用、顺序不符或参数不符              | 核对队列顺序与参数；检查 handler 是否真的发送                         |
| `Failed: Application got api call X but expected Y`     | API 名/参数/adapter 不匹配                            | 对照 `should_call_api` 的 `data` 字典                                 |
| `Failed: Some checks remain after receive event ...`    | 专属断言（带 `matcher=`）未被对应 matcher 消费        | matcher 没被触发：检查 rule/permission 或传入的 matcher 集合          |
| `Failed: Some actions remain after receive event ...`   | 声明了 pause/reject/finish 但 matcher 未执行该动作    | 核对 handler 控制流与 4.3 的对应表                                    |
| `Failed: Some checks failed when handling event ...`    | handler 执行中抛了异常（列表里有原始异常）            | 修复插件 bug，或确认是否为预期的 xfail 用例                           |
| `Failed: Should not set action twice for same matcher`  | 同一 matcher 同一事件声明了两个动作                   | 一个事件一种动作；多轮用多次 `receive_event`                          |

**本章要点**

- 函数内导入插件、conftest 集中配置，是稳定性的两块基石；
- 断言尽量显式指定 `matcher=`，警惕通配断言的"假通过"；
- 报错排查表覆盖 90% 的日常问题，先查表再调试。

---

## 附录 A：API 速查表

### App 方法

| 方法                                                           | 返回上下文         | 用途                                                               |
|----------------------------------------------------------------|--------------------|--------------------------------------------------------------------|
| `app.test_api()`                                               | `ApiContext`       | API/send 期望测试                                                  |
| `app.test_matcher(m=None)`                                     | `MatcherContext`   | 事件处理测试；`m` 可为 None / matcher / list / `{priority: [...]}` |
| `app.test_dependent(fn, allow_types=None, parameterless=None)` | `DependentContext` | 依赖注入测试（别名 `test_handler`）                                |
| `app.test_server(asgi=None)`                                   | `ServerContext`    | ASGI 服务测试                                                      |

### ApiContext（MatcherContext / DependentContext 均继承）

| 方法                                                                            | 说明                                        |
|---------------------------------------------------------------------------------|---------------------------------------------|
| `create_adapter(base=None, **kw)`                                               | 创建 fake adapter                           |
| `create_bot(base=None, adapter=None, self_id="test", auto_connect=True, **kw)`  | 创建 fake bot 并自动连接                    |
| `should_call_api(api, data, result=None, exception=None, adapter=None)`         | 声明 API 期望                               |
| `should_call_send(event, message, result=None, exception=None, bot=None, **kw)` | 声明发送期望                                |
| `wait_list`                                                                     | 内部期望队列（`queue.Queue`），可断言其状态 |

### MatcherContext 专有

| 方法                                                                                           | 说明                       |
|------------------------------------------------------------------------------------------------|----------------------------|
| `receive_event(bot, event)`                                                                    | 声明收到事件，开启新事件组 |
| `should_pass_rule / should_not_pass_rule / should_ignore_rule(matcher=None)`                   | 规则断言                   |
| `should_pass_permission / should_not_pass_permission / should_ignore_permission(matcher=None)` | 权限断言                   |
| `should_paused / should_rejected / should_finished(matcher=None)`                              | 动作断言                   |

### DependentContext 专有

| 方法                    | 说明             |
|-------------------------|------------------|
| `pass_params(**kwargs)` | 提供依赖注入参数 |
| `should_return(result)` | 声明期望返回值   |

### ServerContext 专有

| 方法           | 说明                                    |
|----------------|-----------------------------------------|
| `get_client()` | 获取 `async_asgi_testclient.TestClient` |

### 模块级导出（`nonebug` 包）

| 名称                     | 说明                             |
|--------------------------|----------------------------------|
| `App`                    | 测试应用类                       |
| `NONEBOT_INIT_KWARGS`    | stash key：`nonebot.init()` 参数 |
| `NONEBOT_START_LIFESPAN` | stash key：是否启动 lifespan     |

---

## 附录 B：工作原理深入

理解机制有助于写出更可靠的测试。以下是 nonebug 0.4.x 的实现要点（文件均相对于包根 `nonebug/`）。

### B.1 初始化与 matcher 隔离

- `fixture.py`：`_nonebot_init` 执行 `nonebot.init(**stash.get(NONEBOT_INIT_KWARGS, {}))` 并调用
  `matchers.set_provider(NoneBugProvider)`；
- `provider.py`：`NoneBugProvider` 实现 `MatcherProvider`（Mapping 协议），核心是 `context(matchers)` 上下文管理器——进入时把当前
  matcher 表压入 `_stack` 并替换（传 `None` 时 `deepcopy` 现表），退出时弹栈。这就是 `test_matcher` 的隔离机制。

### B.2 Context 基类（base.py）

`Context.__init__` 检查 `app.context is not None` 则抛 `RuntimeError`（互斥保证），并把自身登记到 `app.context`。
`__aenter__` → `setup()` 打补丁（补丁统一放入 `AsyncExitStack`），`__aexit__` → `run()` 回放后清理。

### B.3 API 打桩（mixin/call_api/）

- `fake.py`：`make_fake_adapter(ctx, base)` / `make_fake_bot(ctx, base)` **每次调用动态生成新的子类**，把
  `Adapter._call_api` / `Bot.send` 重定向到 `ctx.got_call_api` / `ctx.got_call_send`；
- `got_call_api`：从 `wait_list` 队首取期望，依次比对类型（Api/Send）、名称、data 字典、adapter/bot，不匹配即 `pytest.fail`
  ；匹配则抛出 `exception`（若有）或返回 `result`；
- `ApiContext.setup()`：通过 `MonkeyPatch` 把 **所有已注册 adapter 的 `_call_api` 和所有 bot 的 `send`** 替换为 fake
  版本，并在退出时断开所有 `create_bot` 连接的 bot。

### B.4 matcher 打桩（mixin/process/）

`PATCHES` 表给每个参与测试的 matcher 类打 4 个补丁：

| 补丁                   | 拦截点               | 作用                                                                                                                |
|------------------------|----------------------|---------------------------------------------------------------------------------------------------------------------|
| `make_fake_check_rule` | `Matcher.check_rule` | 调用原方法后把结果交给 `ctx.got_check_rule` 比对断言                                                                |
| `make_fake_check_perm` | `Matcher.check_perm` | 同上，比对权限断言                                                                                                  |
| `make_fake_simple_run` | `Matcher.simple_run` | 捕获 `RejectedException` / `PausedException` / `FinishedException` 交给 `ctx.got_action` 比对动作断言，然后原样重抛 |
| `make_fake_run`        | `Matcher.run`        | 把执行中的**所有**异常（含 pytest 的 fail/skip 信号）收入 `ctx.errors` 后重抛                                       |

两个实现细节值得注意：

1. **`__default_state__` 注入**：每个 matcher 的 `_default_state` 被替换为带 `"__nonebug_matcher__"` 键的副本，fake 方法运行时从
   state 里找回"原始 matcher 类"——因为子类化后的 `cls` 可能已不是你传入的那个类；
2. **异常为什么要收集再抛**：`nonebot.message.handle_event` 会吞掉 handler 的异常（记日志继续跑），如果 `got_*` 里的
   `pytest.fail` 直接抛出会被吞掉。所以 `make_fake_run` 把它们收进 `ctx.errors`，等 `handle_event` 返回后统一检查（
   `Skipped` 转为 `pytest.skip`，其余转为 `pytest.fail`）。

### B.5 回放流程（MatcherContext.run）

```
按声明顺序逐个弹出事件:
  1. 该事件的 checks 按 priority 排序（专属断言优先于通配断言:
     通配的 priority = 基础值 + 100，排序后靠后匹配）
  2. actions 同样排序（通配靠后）
  3. 通过 ContextVar(event_test_context) 把 (事件, 断言组) 传给 fake 层
  4. await nonebot.message.handle_event(bot=..., event=...)   ← 真实的事件总线
  5. 检查 ctx.errors（有则 fail/skip）
  6. 检查剩余专属 checks / actions（有则 fail）
最后执行 ApiContext.run：wait_list 非空则 fail
```

ContextVar 的作用：fake 补丁在构造时只闭包了 `ctx`，具体"当前是哪个事件、哪些断言"必须在调用时从 ContextVar
动态获取，这样多轮事件才能各自匹配各自的断言组。

### B.6 Check 的 priority 设计

`process/model.py` 中：`Ignore*=1`、`NotPass=2`、`Pass=3`，通配（`matcher=None`）再加 100。排升序后，
**专属断言先于通配断言被匹配**；`got_check_*` 取第一个匹配者消费（专属的移除，通配的保留可复用）。这解释了 4.2 的语义。

---

## 附录 C：完整可运行示例

一个经过实际运行验证的多轮对话测试：`/echo` 命令先回显消息，再询问名字并问候。

**项目结构**

```
echo-demo/
├── pytest.ini
├── conftest.py
├── utils.py            # 即 3.4 的模板，原样复制
├── plugins/
│   └── demo.py
└── test_demo.py
```

**plugins/demo.py**

```python
from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.params import ArgStr

echo = on_command("echo", block=True)


@echo.handle()
async def _(bot: Bot, event: Event):
    await echo.send(f"echo: {event.get_message()}")


@echo.got("name", prompt="你的名字?")
async def _(name: str = ArgStr()):
    await echo.finish(f"你好, {name}")
```

**conftest.py**

```python
from pathlib import Path

import nonebot
import pytest


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(_nonebot_init: None) -> None:
    nonebot.load_plugins(str(Path(__file__).parent / "plugins"))
```

**test_demo.py**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest
from nonebug import App

from utils import make_fake_event, make_fake_message


@pytest.mark.asyncio
async def test_echo_multi_turn(app: App):
    from plugins.demo import echo  # 函数内导入！

    Message = make_fake_message()

    async with app.test_matcher(echo) as ctx:
        adapter = ctx.create_adapter()
        bot = ctx.create_bot(adapter=adapter)

        # 第一轮: /echo hi → 回显, got 未填参数 → reject 等待输入
        event1 = make_fake_event(_message=Message("/echo hi"))()
        ctx.receive_event(bot, event1)
        ctx.should_pass_rule(matcher=echo)
        ctx.should_pass_permission(matcher=echo)
        ctx.should_call_send(event1, "echo: /echo hi", "result", bot=bot)
        ctx.should_rejected(matcher=echo)

        # 第二轮: 用户回复名字 → 发送 prompt 与问候 → finish
        event2 = make_fake_event(_message=Message("Alice"))()
        ctx.receive_event(bot, event2)
        ctx.should_pass_rule(matcher=echo)
        ctx.should_pass_permission(matcher=echo)
        ctx.should_call_send(event2, "你的名字?", "result", bot=bot)
        ctx.should_call_send(event2, "你好, Alice", "result", bot=bot)
        ctx.should_finished(matcher=echo)
```

**pytest.ini**

```ini
[pytest]
asyncio_mode = auto
```

运行 `pytest test_demo.py -v` 即可通过。注意两个教学点：

1. `got()` 未填参数时 matcher 走 `reject`（第一轮断言 `should_rejected`），第二轮事件触发 prompt 发送与 handler 执行；
2. 第二轮有 **两次 send**（prompt + finish 消息），期望必须按同样顺序声明两条 `should_call_send`——这正是队列语义的体现。
