# nonebot-plugin-alconna 开发者教程与最佳实践

> **适用版本**：nonebot-plugin-alconna **0.62.1**（要求 nonebot2 ≥ 2.5.0、Python ≥ 3.10）。
> 本文面向 **使用本插件开发机器人/插件的开发者**：假设你了解 NoneBot2 的 matcher、依赖注入与适配器概念，不要求了解 Alconna
> 内部实现。
> 与仓库内其他文档的分工：`docs.md` 偏 API 参考与 Alconna 本体教学（部分内容已过时）；`LEARNING_NOTES.md` 面向源码理解；
> **本文面向"怎样写好一个基于 alconna 的插件"**，所有 API 均以 0.62.1 源码核对过。

## 目录

- [0. 前言：它解决什么问题](#0-前言它解决什么问题)
- [1. 快速开始](#1-快速开始)
- [2. 定义命令](#2-定义命令)
- [3. 消费解析结果：依赖注入与多轮交互](#3-消费解析结果依赖注入与多轮交互)
- [4. 跨平台消息：UniMessage / Target / Receipt](#4-跨平台消息unimessage--target--receipt)
- [5. 扩展（Extension）体系](#5-扩展extension体系)
- [6. 内置资源：插件、扩展、i18n、自定义段](#6-内置资源插件扩展i18n自定义段)
- [7. 工程最佳实践](#7-工程最佳实践)
- [8. 附录：速查表与 FAQ](#8-附录速查表与-faq)

---

## 0. 前言：它解决什么问题

裸写 NoneBot 时你会遇到三类痛点，本插件逐一解决：

| 痛点                                                                       | 本插件的答案                                                                               |
|----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| `on_command`/`on_shell_command` 的参数解析太弱，选项/子命令/类型转换全手写 | **Alconna 命令解析**：类型化 Args、Option/Subcommand、正则头、快捷指令、模糊匹配、补全会话 |
| 换一个适配器（QQ/Telegram/Discord…）就要重写一遍消息构造与发送             | **uniseg 跨平台层**：`UniMessage`/`Target`/`Receipt` 一套代码在 27 个适配器上收发消息      |
| 帮助输出、权限、冷却等横切逻辑每个命令都要复制                             | **Extension 扩展体系**：十类钩子按优先级组成管道，一处实现全局生效                         |

**阅读路线**：

- 速通（10 分钟）：第 1 章 + 第 2.1/2.4 节 + 第 7.10 陷阱清单；
- 完整学习：按章节顺序读，第 7 章是落地关键；
- 查阅：直接翻第 8 章速查表。

---

## 1. 快速开始

### 1.1 安装与启用

```shell
pip install nonebot-plugin-alconna
# 或
nb plugin install nonebot-plugin-alconna
```

它会自动带上命令解析依赖（`arclet-alconna`、`nepattern`）与 `nonebot-plugin-waiter`（补全会话/`prompt` 需要）。

在 `bot.py` 或 `.env` 中加载：

```ini
# .env
DRIVER=~fastapi+~httpx   # 任意驱动皆可；要下载媒体/主动发消息需带 httpx
COMMAND_START=["/"]      # nonebot 原生配置，稍后配合 use_cmd_start 使用
ALCONNA_BUILTIN_PLUGINS=["help"]   # 可选：启用内置 help 插件
```

```python
# bot.py
nonebot.load_plugin("nonebot_plugin_alconna")
```

如果你在 **开发自己的插件**（而不是写 bot 入口），用 `require` 代替 `load_plugin`：

```python
from nonebot import require

require("nonebot_plugin_alconna")   # 确保依赖插件已加载

from nonebot_plugin_alconna import on_alconna, Match   # require 之后再 import
```

### 1.2 第一个命令

```python
from arclet.alconna import Alconna, Args
from nonebot import require

require("nonebot_plugin_alconna")

from nonebot_plugin_alconna import on_alconna, Match

weather = on_alconna(
    Alconna("天气", Args["city#城市名", str]),
    use_cmd_start=True,     # 复用 nonebot 的 COMMAND_START，"/天气 北京" 可触发
    auto_send_output=True,  # 用户输错时自动发送帮助信息（这也是默认值）
    block=True,
)

@weather.handle()
async def _(city: Match[str]):
    # city.available 判断参数是否真的传了
    await weather.finish(f"{city.result}：晴，25℃")
```

用户发送 `/天气 北京` → handler 收到 `city.result == "北京"`；发送 `/天气`（缺参数）→ 自动回复帮助与补全提示。

**要点回顾**：`require` 先于 import；`use_cmd_start` 让命令尊重 bot 全局前缀配置；`Match.available` 必查再取值。

---

## 2. 定义命令

### 2.1 四种定义方式，怎么选

| 方式                | 写法                                          | 适用                                                       |
|---------------------|-----------------------------------------------|------------------------------------------------------------|
| Alconna 对象        | `on_alconna(Alconna(...))`                    | **默认推荐**：能力最全（Option/Subcommand/Meta/namespace） |
| 格式字符串          | `on_alconna("echo <...content>")`             | 简单命令一步到位：`<x:type>` 必填、`[x]` 可选、`...` 变长  |
| Koishi 风格 builder | `Command("book", "测试").option(...).build()` | 想链式声明 + `.action()` 直接绑定返回值                    |
| 函数签名            | `@funcommand()`                               | 把"接收几个参数、返回字符串"的纯函数变成命令               |

```python
# 字符串语法：等价于 Alconna("echo", Args["content", MultiVar(str)])
from nonebot_plugin_alconna import Command, UniMessage, funcommand

echo = on_alconna("echo <...content>", use_cmd_start=True)

book = (
    Command("book", "测试")
    .option("writer", "-w <id:int>")
    .usage("book [-w <id:int>]")
    .action(lambda options: str(options))   # action 返回值自动发送
    .build(use_cmd_start=True)
)

@funcommand()
async def calc(op: Literal["add", "mul"], a: float, b: float):
    """四则运算"""        # docstring 会成为命令描述
    return f"{a} {op} {b} = {a + b if op == 'add' else a * b}"
```

### 2.2 用 Alconna 对象精细构建

```python
from arclet.alconna import Alconna, Args, Option, Subcommand, CommandMeta, Field, MultiVar, count
from nonebot_plugin_alconna import Image   # 通用消息段可直接作类型！

pip_cmd = on_alconna(
    Alconna(
        ["!", "/"],                      # 命令前缀（可省略）；正则只在命令名上生效
        "pip",                           # 命令名；支持 "re:\d+" 与 "{roll:int}" 括号头
        Subcommand(
            "install",
            Args["pak#安装包名", str, Field(completion=lambda: "请输入安装包的名字")],
            Option("--upgrade|-U", help_text="升级"),       # | 分隔别名，最长者为名
            Option("--index-url|-i", Args["url", str]),
        ),
        Subcommand("list", Option("--out-dated")),
        Option("--verbose|-v", action=count, default=0),    # action: store/append/count 系列
        meta=CommandMeta(
            description="模拟 pip",
            usage="pip install <pak> [-U]",
            example="pip install nonebot2",
            fuzzy_match=True,     # "pp install" 也能提示"你是不是想输入 pip"
            compact=True,         # 允许命令名与参数间无空格：/pipinstall nb
        ),
    ),
    use_cmd_start=False,   # 已有显式前缀 ["!", "/"]，不再叠加 COMMAND_START
)
```

**Args 类型标注速查**（值会被 nepattern 转成模式）：

- 内置类型：`str / int / float / bool / "url" / "email" / datetime / …`；
- typing：`Union[str, int]`、`Literal["a", "b"]`、`Optional[X]`（自动默认 None）、`list / dict`；
- **通用消息段**：`At / Image / Reply / Segment …`——直接匹配消息里的段对象，这是跨平台命令的基石；
- 组合：`[str, At]`（任一）、`"foo|bar"`（枚举串）、`"re:\d+"`（正则）、`MultiVar(str)`（变长）、`KeyWordVar(str)`（关键字参数）；
- key 修饰符：`"age?"` 可选、`"id!"` 反匹配、`"note/"` 隐藏注解、`"name#注释"` 携带说明。

### 2.3 `on_alconna` 全参数

```python
def on_alconna(
    command,                 # Alconna | str
    rule=None,               # 解析【前】的额外规则（nonebot Rule/checker）
    after_rule=None,         # 解析【后】的额外规则
    skip_for_unmatch=True,   # 解析失败时是否跳过该响应器
    auto_send_output=None,   # None→跟随配置，配置也未设→True（默认自动发帮助）
    aliases=None,            # 命令别名集合，等价注册为前缀式快捷指令
    comp_config=None,        # 补全会话配置；传 {} 启用默认，传 True 也行
    extensions=None,         # 挂载扩展（类或实例）
    exclude_ext=None,        # 排除扩展（类或 id 字符串；id 以 "!" 开头的不可排除）
    use_origin=False,        # 用未经 to_me 等处理的原始消息解析
    use_cmd_start=False,     # 把 COMMAND_START 并入命令前缀
    use_cmd_sep=False,       # 把 COMMAND_SEP 并入分隔符
    response_self=False,     # 是否响应 bot 自己发出的消息
    permission=None,         # nonebot 权限，如 SUPERUSER
    *, priority=1, block=False, temp=False, expire_time=None,
    handlers=None, default_state=None,   # 标准 nonebot matcher 参数
):
    ...
```

**skip_for_unmatch × auto_send_output 行为矩阵**（决定错误输入时用户看到什么、handler 收到什么）：

| skip \ auto  | True（默认）                          | False                                                          |
|--------------|---------------------------------------|----------------------------------------------------------------|
| True（默认） | 帮助/错误文本自动发送，handler 不执行 | 文本不发送、handler 不执行（静默）                             |
| False        | 帮助与错误信息都自动发送              | 文本不发送，但进入 handler，读 `CommandResult.output` 自行处理 |

### 2.4 命令前缀的三种策略

```python
# ① 命令自带前缀：最直白，适合"魔法命令"风格
cmd1 = on_alconna(Alconna(["!"], "roll"))

# ② use_cmd_start：尊重 bot 的 COMMAND_START 配置，适合通用插件分发
cmd2 = on_alconna("help", use_cmd_start=True)   # "/help"、 "!help" 都行（取决于 .env）

# ③ 命名空间统一前缀：适合一个插件批量注册命令
from arclet.alconna import namespace, config as alc_config
with namespace("myplugin") as ns:
    ns.prefixes = ["/"]
    ns.builtin_option_name["help"] = {"-h", "--帮助"}
    a = on_alconna(Alconna("foo"))   # 此上下文内创建的命令自动带 "/" 前缀
```

❌ 不要同时用 `Alconna(["/"], ...)` 和 `use_cmd_start=True`——前缀会叠加成两份语义（COMMAND_START 被 append 进 prefixes，
`rule.py:117-129`），帮助文本也会变混乱。

### 2.5 别名与快捷指令

```python
setu = on_alconna(Alconna("setu", Args["count", int, 1]), aliases={"色图", "涩图"})

# 静态改写：命令替换 + 附带参数
setu.shortcut("来张图", {"command": "setu 1"})

# 正则 key + 捕获组占位：{0} 第一个分组，{*} 全部后随内容，{%0} 后随第 0 个参数
setu.shortcut(r"(?:要|来|抽)(点|\d*)(?:张|个)?涩图", {"command": "setu {0}", "fuzzy": True})

# wrapper 深度改写槽值（返回 None 丢弃）
def wrap(slot: int | str, content: str | None, ctx):
    if slot == 0 and content == "点":
        return str(random.randint(1, 5))
    return content

setu.shortcut(r"来(点|\d+)张涩图", command="setu {0}", fuzzy=True, wrapper=wrap)
```

运行时用户可用内置选项 `--shortcut` 增删查（`setu --shortcut list`）；给命令挂 `SuperUserShortcutExtension`（见
6.2）可将其限制为超级用户。

### 2.6 多命令冲突

两个插件注册了同名命令时，由 `ALCONNA_CONFLICT_RESOLVER` 决定：`default`（共存，help 分组展示）/ `raise`（抛异常，适合严格项目）/
`ignore`（后注册的丢弃）/ `replace`（新命令替换旧的）。写通用分发插件时保持 `default` 即可。

**要点回顾**：优先 Alconna 对象 + 通用段类型；字符串语法做简单命令；前缀策略三选一别混用；`auto_send_output` 默认就是开的。

---

## 3. 消费解析结果：依赖注入与多轮交互

### 3.1 依赖注入速查

handler 里 **不需要任何 DI 函数**，直接按注解声明即可；DI 函数在需要 middleware/默认值时使用：

```python
from arclet.alconna import Alconna, Arparma, Alconna as Alc, Duplication
from nonebot_plugin_alconna import (
    on_alconna, CommandResult, Match, Query, AlconnaMatches, AlcResult,
)

test = on_alconna(Alconna("test", Option("foo", Args["bar", int]), Option("baz", Args["qux", bool, False])))

@test.handle()
async def handle(
    result: CommandResult,          # 或 result = AlcResult()；.matched/.output/.source/.context
    arp: Arparma,                   # 或 arp = AlconnaMatches()；arp.query[...]、arp.all_matched_args
    bar: Match[int],                # Match[T]：available + result
    all_args: dict,                 # 参数名固定 ctx/context 时注入解析上下文
    qux: Query[bool] = Query("baz.qux", False),   # Query 必须 default 传 path（也可以 "~xxx" 相对路径）
):
    ...
```

| 注入目标                                      | 说明                                                                                    |
|-----------------------------------------------|-----------------------------------------------------------------------------------------|
| `CommandResult`                               | `{result: Arparma, output: str \| None}`，最常用入口                                    |
| `Arparma`                                     | 原始结果：`query[path]` / `find(path)` / `all_matched_args` / `options` / `subcommands` |
| `Match[T]`                                    | `all_matched_args[name]`；`available` 判断是否存在                                      |
| `Query[T]`（默认值传 `Query(path, default)`） | 任意路径查询，含选项值 `"opt.value"`                                                    |
| `Duplication` 子类                            | 类型化结果视图（见 3.7）                                                                |
| `Alconna`                                     | 源命令对象                                                                              |
| `dict`（形参名 ctx/context）                  | parse 时注入的上下文（含 `event`、`bot.self_id`、`adapter.name`）                       |
| `dict`（`AlconnaExecResult()`）               | `.action()`/`bind()` 回调的返回值字典，键为函数名                                       |
| 扩展类型注解（如 `ext: MyExt`）               | 从本次事件选中的扩展里取实例                                                            |

### 3.2 裸参数名：最省事也最易踩坑的能力

不写任何注解依赖时，形参名会按以下顺序解析（`params.py` 的 `AlconnaParam._solve`）：

1. `got_path` 存过的键（全等或以 `.名字` 结尾）；
2. `Arparma.all_matched_args` 里的同名参数；
3. 选项值：`query("{名字}.value")`—— **选项参数也能直接裸取**；
4. 都没有 → 用默认值；无默认值则跳过该 handler。

```python
@pip_cmd.assign("install")
async def install(pak: str, upgrade: bool):   # pak 来自主参数，upgrade 来自 -U 选项值
    ...
```

❌ 裸参数名与命令参数 **对不上时 handler 会被静默跳过**（而不是报错）。调试"handler 不执行"时先检查这里；建议关键参数仍用
`Match` 显式声明。

### 3.3 条件分派：assign / dispatch

```python
# 方式一：同一 matcher 内分派（推荐命令结构简单时用）
@pip_cmd.assign("install")                  # 仅 pip install xxx
async def install(pak: str):
    await pip_cmd.finish(f"installing {pak}")

@pip_cmd.assign("install.pak", "nb")        # 仅 pak == "nb"
async def install_nb():
    await pip_cmd.finish("正在安装 nb")

@pip_cmd.assign("list", or_not=True)        # list，或没有任何子命令/选项时（$main）
async def list_all():
    await pip_cmd.finish("all packages")

# 方式二：dispatch 生成独立子 matcher（priority = 父+1，共享命令与扩展）
install_cmd = pip_cmd.dispatch("install")

@install_cmd.assign("~upgrade")             # "~xxx" 展开为父 basepath + ".xxx"
async def upgrade(pak: Query[str] = Query("~pak")):
    await install_cmd.finish(f"pip upgrading {pak.result}...")
```

`assign(path, value, or_not, additional)` 的 `additional` 是额外的异步检查函数 `(event, bot, state, arp) -> bool`
，可用于二级权限/风控。等价的底层写法是 `@handle([Check(assign(...))])`，`Check` 不通过时 `matcher.skip()`。

### 3.4 多轮交互：got / got_path / prompt

```python
from nonebot_plugin_alconna import AlconnaMatcher, AlconnaArg, At, UniMessage

test_cmd = on_alconna(Alconna("test", Args["target?", [str, At]]))

@test_cmd.handle()
async def h(matcher: AlconnaMatcher, target: Match[str | At]):
    if target.available:
        matcher.set_path_arg("target", target.result)   # 存入 state，供 got_path 消费

@test_cmd.got_path("target", prompt="请输入目标")
async def g(target: str | At):
    await test_cmd.send(UniMessage(["收到：", target]))
```

- `got_path(path, prompt, middleware, fallback)`：参数缺失时发 `prompt` 并等待下一条消息；新消息的 **首个有效段**会用该路径
  Arg 的类型校验（文档说"最后一段"已过时，源码取 `msg[0]`，`matcher.py:610`），失败自动重问；
- `matcher.got(key, prompt)`：NoneBot 原版语义，整条消息存为 arg；
- `matcher.reject_path(path, prompt)`：handler 内判定"这个答案不行"时打断重问；
- `matcher.prompt(message, timeout=120)`：不经过 Arg 的临时追问，返回 `UniMessage | None`（内部走 nonebot_plugin_waiter）；
- 读取已存参数：`matcher.get_path_arg(path, default)` / DI `AlconnaArg(path)`。

### 3.5 middleware：拿到"处理过"的参数值

`AlconnaMatch` / `AlconnaQuery` / `got_path` 都支持 middleware——`(event, bot, state, value) -> 新值`，常用来把 `Image`
段变成 bytes：

```python
from nonebot_plugin_alconna import image_fetch, Image

mask = on_alconna(Alconna("设置词云形状", Args["img?", Image]))

@mask.handle()
async def h(matcher: AlconnaMatcher, img: Match[bytes] = AlconnaMatch("img", image_fetch)):
    if img.available:
        matcher.set_path_arg("img", img.result)   # 存的是 bytes 而非 Image

@mask.got_path("img", prompt="请输入图片", middleware=image_fetch)
async def g(img: bytes):
    ...
```

### 3.6 补全会话（比 got-reject 更强的引导）

```python
cmd = on_alconna(
    Alconna("添加教师", Args["name", str], Args["phone", int]),
    comp_config={"tab": "切换", "enter": "确认", "exit": "退出", "timeout": 60},
    skip_for_unmatch=False,
)
```

首次解析失败后进入会话：Alconna 给出建议项，用户用 `切换`/`切换 2` 换建议、`确认` 提交、`退出` 放弃。`lite: True` 隐藏控制指令说明；
`hides`/`disables` 精细控制。全局默认配置用 `ALCONNA_GLOBAL_COMPLETION`（命令传 `comp_config=True` 时套用）。

### 3.7 Duplication：一次性把结果摊平成对象

```python
from arclet.alconna import Duplication, SubcommandStub
from typing import Optional

class PipResult(Duplication):
    pak: str
    upgrade: bool
    url: Optional[str] = None
    list: SubcommandStub

@pip_cmd.handle()
async def h(res: PipResult): ...
```

**要点回顾**：能用注解就别写 DI 函数；裸参数名方便但失配会静默跳过；多轮交互优先 `got_path`（有类型校验）；需要引导式补全用
`comp_config`。

---

## 4. 跨平台消息：UniMessage / Target / Receipt

### 4.1 心智模型

```
你的代码 ──UniMessage(通用段)──> exporter 按当前适配器转换 ──> 适配器 MessageSegment ──> 平台
平台 ──> 适配器 MessageSegment ──> builder 转换 ──> UniMessage ──> 你的代码
```

- **入站自动发生**：`rule` 阶段事件消息已转为 `UniMessage` 并放进 state（有 LRU 缓存，消息 id 重复利用不重复转换）；
- **出站显式构造**：永远构造 `UniMessage`，`send/export` 时按 bot 所在适配器落地；
- 转换不了的段有 **回退策略**兜底（见 4.8），不会让消息发不出去。

### 4.2 构造与容器操作

```python
from nonebot_plugin_alconna import UniMessage, At, Image, Text, Reply

msg = UniMessage.text("看图：").at("123456").image(path="data/cat.png")
msg += "\n完"                       # 文本自动合并进相邻 Text 段
msg2 = UniMessage(["前缀", At("user", "1")]) + msg

msg[Image]            # 所有图片段 → UniMessage
msg[Image, 0]         # 第一张图片 → Image
msg.has(At) / At in msg
msg.get(At, 2)        # 前 2 个 At 段
msg.exclude(Reply) / msg.include(Text, At)     # 类型过滤
msg.extract_plain_text()
msg.select(Image)     # 递归收集（含段内 children，如 Keyboard 里的 Button）
msg.split(" ") / msg.replace("旧", "新") / msg.startswith("/") / msg.strip()
msg.copy()            # 深拷贝
```

### 4.3 模板：`{:Type(...)}` 与 `$` 取值

```python
tpl = UniMessage.template("{:At(user, $event.get_user_id())} 已确认目标为 {target}")
await test_cmd.send(tpl)     # AlconnaMatcher.send 会自动补全 $event/$target/$message_id
                            # 并用解析结果(all_matched_args)+state 填充 {target}
```

- `{:At(user, 123)}` / `{:At(type=user, target=id)}`：构造任意段；参数可引用 kwargs（`$xxx.yyy` 沿属性/下标路由）；
- 在 matcher 之外用 `.format(target="x")` 手动填充；模板对象也可以是一个 `UniMessage`（只格式化其中的文本段）。

### 4.4 发送与 Receipt

```python
receipt = await UniMessage.image(path="a.png").send(
    at_sender=True,    # 非私聊时在开头 @发送者
    reply_to=True,     # 开头加回复段（引用当前消息）；也可传 str 消息 id
    fallback=True,     # True=自动回退；也可传 FallbackStrategy（见 4.8）
)
if receipt.recallable:                 # 能力探测：exporter 是否实现了 recall
    await receipt.reply("10 秒后撤回")
    await receipt.recall(delay=10, index=0)
if receipt.editable:
    await receipt.edit(UniMessage.text("改文案"))
await receipt.reaction("👍")            # reactionable 才有效，否则静默跳过

await UniMessage.text("结束").finish()  # send + FinishedException，等价 matcher.finish
```

在 handler 里直接 `matcher.send(UniMessage...)` 即可（自动过扩展的 send_wrapper）； **matcher 之外**（定时任务、webhook）必须显式传
`target`/`bot`，见 4.5。

### 4.5 主动消息：Target 与 Bot 选择

```python
from nonebot_plugin_alconna import Target, SupportScope, UniMessage

# Target.(group|user|channel_)(id, scope)：scope 指平台而非适配器
await Target.group("123456", SupportScope.qq_client).send(UniMessage.text("群里好"))
await Target.user("10001", SupportScope.telegram).send(UniMessage.image(url="https://.../x.png"))

# 同一平台多个 bot 时：self_id 直选，或 selector 谓词
await Target.group("123", SupportScope.qq_client, self_id="10086").send(...)

# 持久化（如存数据库做"订阅推送"）：dump/load 往返，only_scope=True 时跨适配器仍可用
data = target.dump()              # dict，可 JSON 化
target2 = Target.load(data)
```

`SupportScope` 是 **平台维度**（qq_client / telegram / discord / …），一个平台可能由多个适配器承载（QQ 客户端可走
OneBotV11/V12、Mirai、Satori…），`Target.select()` 会按 scope+平台挑一个在线 bot。`ALCONNA_APPLY_FETCH_TARGETS=true` 可在启动时预拉各
bot 的会话列表，让"该 bot 是否在这个群里"的判断更准（satori 等适配器还支持运行时校验）。

### 4.6 handler 里的跨平台 DI 与规则

```python
from nonebot_plugin_alconna import UniMsg, MsgTarget, MsgId, at_me, Reply, UniversalSegment

sign = on_alconna("签到", rule=at_me())    # 也可 at_in("10001", "10002") 限定特定人 @

@sign.handle()
async def h(
    msg: UniMsg,                 # 当前消息（解析阶段已转换并缓存）
    target: MsgTarget,          # 发送对象 Target
    msg_id: MsgId,              # 消息 id（str）
    reply: Reply = UniversalSegment(Reply),   # 取消息中第 0 个 Reply 段
):
    if msg.has(Image):
        ...
```

### 4.7 媒体与回复的获取

```python
from nonebot_plugin_alconna import image_fetch, get_message_id, message_recall
from nonebot_plugin_alconna.uniseg import reply_fetch   # 注意：此函数仅在 uniseg 子包导出

reply = await reply_fetch()                  # 当前事件引用的原消息（OB11 读 event.reply 等）
await message_recall()                       # 撤回当前会话中 bot 的上一条消息
# image_fetch 作为 middleware 用法见 3.5；它按适配器自动选择下载路径
await UniMessage.image(url="...").download() # 把消息里的媒体拉回 raw（走 driver httpx）
```

需要把本地大文件变成 URL（某些平台发 raw 失败时）可启用文件托管：`ALCONNA_APPLY_FILEHOST=true`（需另装
`nonebot-plugin-filehost` 与 `nonebot-plugin-localstore`）。

### 4.8 回退策略与支持矩阵

当某通用段在目标适配器上不可发送时（如 Button 在 OneBotV11）：

| 策略                                     | 行为                                                                           |
|------------------------------------------|--------------------------------------------------------------------------------|
| `FallbackStrategy.ignore`                | 丢弃该段                                                                       |
| `FallbackStrategy.to_text`               | 转 `[button]xxx` 文本                                                          |
| `FallbackStrategy.rollback`              | 从段的 children 里提取可发送内容                                               |
| `FallbackStrategy.forbid`                | 抛 `SerializeFailed`                                                           |
| `FallbackStrategy.auto` / `True`（默认） | 智能降级：Image→`[image]url`、At→`@名字`、Keyboard→按钮文字…；全失败兜底纯文本 |

**最佳实践**：写多适配器插件时 **只构造 UniMessage**、不 import 任何 `nonebot.adapters.*`；发送一律 `fallback=True`
；对"撤回/编辑/表情回应"等操作先探测 `receipt.recallable` 等能力再决定交互文案。各平台元素/操作支持差异见 README 支持矩阵。

**要点回顾**：入站白嫖、出站构造；`at_sender/reply_to` 一步到位；主动消息 = `Target + scope`，可 dump
持久化；能力探测后降级；永远别在多适配器插件里硬编码适配器段。

---

## 5. 扩展（Extension）体系

### 5.1 什么时候写扩展

| 需求                                 | 用什么                                        |
|--------------------------------------|-----------------------------------------------|
| 只影响**本命令**的收发/权限/输出     | `Extension`（本章）                           |
| 跨命令的通用能力（冷却、风控、翻译） | `Extension` + `add_global_extension` 全局注册 |
| 单纯读取数据                         | 普通 DI / `rule`                              |
| 与命令解析无关的响应逻辑             | 普通 matcher                                  |

### 5.2 钩子速查与组合语义

扩展只需声明 `priority`、`id` 并 **覆盖你关心的钩子**（基类自动记录 `_overrides`，未覆盖的钩子零开销）：

| 钩子                                                     | 时机               | 多扩展组合语义                         |
|----------------------------------------------------------|--------------------|----------------------------------------|
| `validate(bot, event)`                                   | 选择扩展时         | 过滤（默认只收 message 事件）          |
| `message_provider(event, state, bot, use_origin)`        | 取消息             | **首个非 None 生效**，其余跳过         |
| `receive_wrapper(bot, event, cmd, receive)`              | 解析前             | 按 priority **链式**加工               |
| `context_provider(ctx, event, bot, state)`               | 构造解析上下文     | 链式，最后统一补 event/self_id/adapter |
| `permission_check(bot, event, medium)`                   | 头部匹配后、执行前 | 任一 False 即拒绝                      |
| `parse_wrapper(bot, state, event, res)`                  | 解析成功后         | `asyncio.gather` **并发**执行          |
| `output_converter(output_type, content)`                 | 发送帮助/错误时    | 首个成功者生效                         |
| `send_wrapper(bot, event, send)`                         | 每次发送前         | 链式加工                               |
| `before_catch(name, anno, default)` + `catch(interface)` | handler 参数解析   | 自定义依赖注入                         |
| `post_init(alc)`                                         | 响应器创建后       | 对命令对象的后处理                     |

`priority` 数值 **越小越先**执行（默认扩展 `!default` 为 16）。`id` 建议用 `"插件名:扩展名"` 防撞；以 `!` 开头的 id 不可被
`exclude_ext` 排除。`namespace` 非空时只作用于同命名空间命令。

### 5.3 实战范例一：全局冷却

```python
import time
from nonebot_plugin_alconna import Extension

class CoolDownExtension(Extension):
    def __init__(self, cool_down: float = 60):
        self.cd = cool_down
        self._last: dict[str, float] = {}

    @property
    def priority(self) -> int:
        return 15

    @property
    def id(self) -> str:
        return "myplugin:cooldown"

    async def permission_check(self, bot, event, medium) -> bool:
        key = event.get_session_id()
        now = time.time()
        if (last := self._last.get(key)) and (rest := self.cd - (now - last)) > 0:
            await bot.send(event, f"冷却中，还剩 {rest:.0f} 秒")
            return False
        self._last[key] = now
        return True
```

> 提醒：示例用内存字典，重启即失忆、多进程不共享；生产环境请换数据库（这也正是 `with` 内置插件存 per-target 前缀时面临的同类问题）。

### 5.4 实战范例二：自然语言翻译成命令（LLM）

```python
class LLMExtension(Extension):
    def __init__(self, llm):
        self.llm = llm

    @property
    def priority(self) -> int:
        return 10

    @property
    def id(self) -> str:
        return "myplugin:llm"

    async def receive_wrapper(self, bot, event, command, receive):
        # 命令头都匹配不上时才交给 LLM 翻译，避免无谓调用
        text = receive.extract_plain_text()
        if command.parse(text).matched:
            return receive
        return UniMessage(await self.llm.to_command(text))

matcher = on_alconna(alc, extensions=[LLMExtension(my_llm)])
```

### 5.5 实战范例三：把帮助输出渲染成图片

```python
async def text_to_image(text: str) -> Image:
    return Image(raw=await my_renderer(text))

cmd = on_alconna(
    alc,
    extensions=[MarkdownOutputExtension(text_to_image=text_to_image)],   # 内置扩展，见 6.2
)
```

### 5.6 注册、排除与依赖注入

```python
# ① 命令级
cmd = on_alconna(alc, extensions=[CoolDownExtension(30)], exclude_ext=["other:ext_id"])

# ② 全局（Python 代码）——之后创建与已存在的命令全部生效（延迟回填）
from nonebot_plugin_alconna import add_global_extension
add_global_extension(CoolDownExtension())

# ③ 全局（配置文件）：支持 ~ 前缀(=nonebot_plugin_alconna.) 与 @ 前缀(=内置扩展目录)
ALCONNA_GLOBAL_EXTENSIONS=["@markdown", "my_pkg.ext:MyExtension"]
```

扩展还能给 handler 注入自定义参数：`before_catch(name, annotation, default)` 认领参数名，`catch(interface)` 返回值——
`interface.name/annotation/default` 可用于分支；扩展内部要复用 nonebot DI 时用 `await self.inject(dependent)`。

---

## 6. 内置资源：插件、扩展、i18n、自定义段

### 6.1 内置插件（builtins/plugins/）

```python
from nonebot_plugin_alconna import load_builtin_plugins
load_builtin_plugins("echo", "help", "lang", "switch", "with")
# 或在 .env：ALCONNA_BUILTIN_PLUGINS=["help", "switch"]
```

| 插件       | 命令                                                     | 说明                                                                                                                                                        |
|------------|----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **help**   | `help [query...] [--page] [--plugin-info] [--namespace]` | 汇总 `command_manager` 里全部命令；查询具体命令时**委托该命令自己的扩展**渲染帮助（Markdown 扩展也生效）；`nbp_alc_page_size` 配置分页，分页用 `a`/`d` 翻页 |
| **switch** | `enable / disable`（超级用户）                           | 调 `command_manager.set_enabled` 真正启停命令（rule 阶段即拦截）                                                                                            |
| **lang**   | `lang list / lang switch <locale>`                       | 切换 tarina 全局语言，所有 i18n 消息即时变化                                                                                                                |
| **with**   | `with <前缀> [--expire <时间>]`                          | 给**当前会话**设置本地短前缀：设 `with tp` 后 `tp -U` 等价完整命令（靠全局 `PrefixAppendExtension`）                                                        |
| **echo**   | `echo <...content>`                                      | 复读；演示 `Command`+`action`+`ReplyMergeExtension` 的标准写法                                                                                              |

### 6.2 内置扩展（builtins/extensions/）

```python
# 输出转 Markdown（text_to_image 可选：帮助文本渲染为图片）
from nonebot_plugin_alconna.builtins.extensions import MarkdownOutputExtension, ReplyRecordExtension
# from ...builtins.extensions.reply import ReplyMergeExtension
# from ...builtins.extensions.permission import SubcommandPermExtension
# from ...builtins.extensions.shortcut import SuperUserShortcutExtension

cmd = on_alconna(alc, extensions=[
    MarkdownOutputExtension(escape_dot=True, text_to_image=my_text_to_image),
])

# 回复记录：handler 里按消息 id 取"这条消息引用了谁"
rec = on_alconna(alc2, extensions=[ReplyRecordExtension()])
@rec.handle()
async def _(msg_id: MsgId, ext: ReplyRecordExtension):
    if reply := ext.get_reply(msg_id):
        ...

# 回复合并：把被引用的原消息拼进当前消息参与解析（复读被引用命令）
merge_cmd = on_alconna(alc3, extensions=[ReplyMergeExtension(add_left=False, sep=" ")])

# 子命令权限：按 "command.<名>.<子命令>[.$options.<选项>]" 字符串调用你的 checker
async def my_checker(bot, event, permission: str) -> bool:
    return permission in await load_user_perms(event.get_user_id())
perm_cmd = on_alconna(alc4, extensions=[SubcommandPermExtension(my_checker, include_options=True)])

# 限定 --shortcut 内置选项仅超管可用
sct = on_alconna(alc5, extensions=[SuperUserShortcutExtension()])
```

平台专属扩展（按需单独 import）：

- `builtins.extensions.onebot11.MessageSentExtension`：让 `response_self=True` 的命令能解析 OB11 的 `message_sent`（bot
  自己发的消息）；
- `builtins.extensions.telegram.TelegramSlashExtension`：`/` 开头命令自动注册为 Telegram BotCommand（bot 上线时
  `set_my_commands`）；
- `builtins.extensions.discord.DiscordSlashExtension`： **把 Alconna 命令自动翻译成 Discord 斜杠命令**注册，交互事件反向拍平成文本再走
  Alconna 解析——handler 代码完全不用改。

### 6.3 i18n

```python
# ① 消息段级：export 时才解析，自动注入 $event/$target/$message_id
await matcher.send(UniMessage.i18n("my-plugin", "welcome", name=event.get_user_id()))

# ② matcher 级：解析结果(all_matched_args)与 state 也能作为占位符
await matcher.send(matcher.i18n("my-plugin", "result", city="{city}"))

# ③ 自己的插件注册语言包（tarina lang）
from tarina import lang
lang.load(Path(__file__).parent / "lang")   # 目录含 zh-CN.json / en-US.json
# JSON 结构：{"my-plugin": {"welcome": "欢迎 {name}"}}
```

语言切换：`lang switch zh-CN`（内置插件）或 `tarina.lang.select("zh-CN")`。

### 6.4 自定义通用段（custom_register / custom_handler）

第三方可以定义 **新的通用段类型**而不必改 27 个适配器：

```python
from nonebot_plugin_alconna import Segment, custom_register, custom_handler, SupportAdapter

class Dice(Segment):
    count: int

# 入站：仅当 onebot v11 的 "dice" 段出现时转换
@custom_register(Dice, "dice")
def build_dice(builder, seg):          # seg 是适配器 MessageSegment
    return Dice(count=seg.data.get("count", 1))

# 出站：告诉各适配器怎么发
@custom_handler(Dice)
async def export_dice(exporter, seg: Dice, bot, fallback):
    if bot.adapter.get_name() == "OneBot V11":
        from nonebot.adapters.onebot.v11.message import MessageSegment
        return MessageSegment.dice()
    return None                        # 返回 None 走回退策略
```

内置示范可参考 `builtins/uniseg/markdown.py`（QQ 官方 Markdown）、`market_face.py`、`music_share.py`——它们都是 opt-in：
`import` 即注册。

### 6.5 兼容补丁

- `ALCONNA_ENABLE_SAA_PATCH=true`：让旧项目里的 `nonebot-plugin-send-anything-anywhere` `MessageFactory.send` 在不支持的平台自动转由
  uniseg 发送；
- `ALCONNA_APPLY_FILEHOST=true`：本地媒体自动上传换 URL（配合 auto 回退，解决部分平台 raw 发送限制）；
- `patch_matcher_send()`：给 **所有** matcher 的 `send` 增加 UniMessage 支持（on_alconna 的 matcher 天生支持，普通
  on_command 需要此补丁）。

**要点回顾**：横切逻辑进扩展；全局扩展三选一（代码/配置/命令级）；帮助、权限、回复类需求先看内置扩展有没有现成的；新消息类型走
custom_register。

---

## 7. 工程最佳实践

### 7.1 项目结构

一个功能完整的 alconna 插件建议这样组织（以 `nonebot-plugin-mytool` 为例）：

```
nonebot_plugin_mytool/
├── __init__.py        # require + 插件元数据 + 少量粘合代码
├── config.py          # 本插件自己的 Config（pydantic）
├── commands/          # 每个命令（或命令组）一个模块
│   ├── __init__.py    #   定义 Alconna 与 matcher
│   ├── query.py
│   └── admin.py
├── handlers/          # handler 拆分（可选，与 commands 合并亦可）
├── extensions.py      # 自定义扩展
├── service/           # 业务逻辑（网络请求、数据库），与 nonebot 解耦
└── lang/              # i18n 资源（zh-CN.json / en-US.json）
```

```python
# __init__.py
from nonebot import require, get_driver
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")      # 按需声明其他依赖

from nonebot_plugin_alconna import SupportAdapterModule
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="mytool",
    description="...",
    usage="/mytool query <key>",
    type="application",
    config=Config,
    # 显式声明支持的适配器（读者可据此判断能否用于自己的 bot）
    supported_adapters={SupportAdapterModule.onebot11.value, SupportAdapterModule.qq.value},
)

from . import commands   # 最后 import，保证命令注册
```

❌ 把命令定义写在 `__init__.py` 顶部、元数据放最后——元数据后的 import 顺序错误是插件加载失败的常见原因。
✅ 先 `require` → 再定义元数据 → 最后 import 子模块注册命令。

### 7.2 命令设计

```python
alc = Alconna(
    "mytool",
    Subcommand("query", Args["key", str], help_text="查询条目"),
    Subcommand("bind", Option("--force", help_text="覆盖已有绑定")),
    meta=CommandMeta(
        description="我的工具箱",
        usage="/mytool query <key>",
        example="/mytool query 点歌",
        fuzzy_match=True,
    ),
)
```

- **命名统一前缀**：所有子命令挂同一个主命令下（`mytool query`、`mytool bind`），help 输出自然成组；避免几十个顶层命令刷屏；
- **写好 description/usage/example**：`help` 插件、补全会话、fuzzy 提示都会用它们；不想暴露的调试命令设
  `CommandMeta(hide=True)`；
- **参数带注释**：`Args["key#条目名", str]`、`Field(completion=...)` 让补全会话的提示真正有用；
- **冲突策略**：通用分发插件保持 `ALCONNA_CONFLICT_RESOLVER=default`；私有 bot 可用 `replace` 强制覆盖；
- ❌ 一个命令塞 8 个 Option 且互斥语义靠 handler 里 if——改用 `Subcommand` 分组 + `assign` 分派，帮助与补全都更清晰。

### 7.3 权限分层

按"范围从小到大"选择：

1. **整命令级**：`on_alconna(alc, permission=SUPERUSER)`（switch 这类管理命令）；
2. **子命令/选项级**：`SubcommandPermExtension(checker)`——权限字符串 `command.mytool.bind` 精确到子命令与选项，checker
   里查你的权限表；
3. **handler 级**：`@cmd.assign("bind", additional=my_check)` 或 `@handle([Check(...)])`；
4. **自实现**：自定义扩展覆盖 `permission_check`（见 5.3 冷却范例），注意它发生在 **头部已匹配**
   之后——错误输入不会触发权限拒绝文案，只有真的走到该命令才检查。

### 7.4 输出与错误处理

- 默认 `auto_send_output=True` 适合绝大多数命令：用户敲错立刻看到帮助；
- 想自定义错误体验：`auto_send_output=False, skip_for_unmatch=False`，在 handler 读 `CommandResult.output` 自己排版（配合
  `MarkdownOutputExtension` 或 `output_converter` 扩展）；
- 长输出（列表、排行榜）：用 `matcher.prompt` 做翻页（内置 help 插件 `a`/`d` 翻页即此实现），或 `--page` 选项；
- ❌ 在 handler 里 `try/except` 包住整个逻辑再 `finish(str(e))`——敏感信息（API key、内部路径）会直接发给用户；✅ 记日志，给用户发
  i18n 化的友好文案。

### 7.5 多适配器兼容（本插件的最大卖点，也最易翻车）

1. **只构造 UniMessage**：源码里不出现 `from nonebot.adapters...`，测试时你的插件才能同时跑 OB11/QQ/Telegram；
2. **能力探测再交互**：`receipt.recallable/editable/reactionable` 决定你敢不敢在按钮文案里写"点击撤回"；
3. **回退策略显式化**：发富内容时 `matcher.send(msg, fallback=True)`；对必须完整到达的内容（如二维码图片）用
   `fallback=FallbackStrategy.forbid` 并 try `SerializeFailed` 给出"当前平台不支持"的降级提示；
4. **平台特例集中管理**：确实需要特判时用 `target.scope`/`SupportScope` 判断平台而不是适配器（`qq_client` 平台无论哪个适配器接入都命中）；
5. **发布前核对支持矩阵**：README 中"支持的消息元素/操作"两张表是能力契约。

### 7.6 主动消息

```python
# 订阅场景：把 Target 存下来（数据库/JSON），推送时 load
data = target.dump()                    # 只存 scope 亦可: target.dump(only_scope=True)
...
await Target.load(data).send(UniMessage.text("日报来了"), fallback=True)
```

- 多 bot 场景给 `Target` 传 `self_id` 或 `selector` 谓词固定投递账号，避免"随机 bot 在不在群里"的不确定性；
- `ALCONNA_APPLY_FETCH_TARGETS=true` 让 `Target.select()` 前先校验 bot 是否真在该会话（satori 等支持运行时校验）；
- ❌ 把 `Target.dump()` 里 `self_id` 存死还换机器人账号——✅ `dump(save_self_id=False)` 或推送失败时降级重选。

### 7.7 性能与缓存要点

- 入站消息 → UniMessage 有 **LRU (16)** 缓存（按消息 id），同一条消息被多个 matcher/多次 DI 消费只转换一次；
  `ALCONNA_CACHE_MESSAGE=false` 可关（一般别关）；
- `UniMessage.of(event.get_message())` 手动转换时 **传 bot**（利用缓存与适配器定位），别只传 adapter 字符串反复查表；
- 补全会话期间，同一 session 的后续消息会 **排队**等待前一条解析完成（`rule.py` 的 per-session task 表），设计高频命令时避免长会话；
- 媒体 bytes 处理完即释放；需要落盘用 `media.save()`（localstore 托管、md5 分片，重复文件自动去名）。

### 7.8 测试

**① 声明式自检**（零成本，启动即验）：

```python
cmd = (
    on_alconna(alc)
    .test("mytool query 点歌", {"key": "点歌"})
    .test("mt 点歌", {"key": "点歌"})          # 顺便测快捷指令
)
```

`driver.on_startup` 时逐条解析并校验 `query(path) == expected`，失败打 ERROR 日志——命令语法回归的第一道防线。

**② nonebug 集成测试**（本仓库 `tests/` 即范本）：

```python
# conftest.py 关键项
os.environ["PLUGIN_ALCONNA_TESTENV"] = "1"   # uniseg 全量装载适配器映射
# 注册被测适配器 → require("nonebot_plugin_alconna")

@pytest.mark.asyncio
async def test_query(app: App):
    from nonebot.adapters.onebot.v11.event import MessageEvent  # 或用 fake 工厂
    async with app.test_matcher(query_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/mytool query 点歌"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已查询：点歌", True)
        ctx.should_finished(query_cmd)
```

- 测 got_path 流程：第一次 `should_call_send(event, "请输入目标", result=None)` + `should_rejected`，再 `receive_event`
  第二条消息；
- 测 rule 拦截：`ctx.should_not_pass_rule(matcher)`；
- 纯消息转换可脱bot 测试：`msg.export_sync(adapter="OneBot V11")` 与期望的 `MessageSegment` 直接断言相等。

### 7.9 发布

```toml
# pyproject.toml
[project]
name = "nonebot-plugin-mytool"
dependencies = [
    "nonebot2>=2.5.0",
    "nonebot-plugin-alconna>=0.62.0",
]

[tool.pdm.dev-dependencies]
test = ["nonebug", "pytest-asyncio", "nonebot-adapter-onebot", ...]
```

- `__plugin_meta__.supported_adapters` 如实填写（全适配器可写 `None` 或
  `set(SupportAdapterModule.__members__.values())`）；
- 用了可选功能（filehost/SAA 补丁）对应依赖放进 `[project.optional-dependencies]` 并在 README 说明；
- 发布前跑 `pytest`（矩阵参考本仓库 CI：Python 3.10–3.14）。

### 7.10 陷阱清单（每条都来自源码核对）

1. ❌ `from nonebot_plugin_alconna.adapters.onebot11 import Image` ——0.62.x 已删除该路径；✅
   `from nonebot_plugin_alconna import Image`（通用段）。
2. ❌ 依赖 `got_path` "取最后一个消息段"的旧文档说法；✅ 实际取 **首个**非空白段（`matcher.py:610`）。
3. ❌ `auto_send_output` 以为默认关；✅ 默认开（None→配置→仍未设→True，`rule.py:105`）。
4. ❌ 同时给命令显式前缀又开 `use_cmd_start`；✅ 二选一（前缀会叠加）。
5. ❌ handler 裸参数名拼错后期望报错；✅ 失配是 **静默跳过**，用 `Match`/`CommandResult` 显式化。
6. ❌ 在 OB11 等"不响应自己"平台想让 bot 解析自发消息却不开 `response_self`；✅ `response_self=True` + 全局
   `MessageSentExtension`（OB11）。
7. ❌ QQ 官方 API 群聊里用"是否 @ 我"判断命令触发失败就删掉 at_me；✅ 该平台 **吞 At**，`at_me()` 已特判补插（
   `uniseg/rule.py:53`），继续用即可。
8. ❌ 补全会话里设计"立刻发下一条"的连招；✅ 同 session 解析任务串行，下一条会排队。
9. ❌ 依赖 `ctx["bot.platform"]`；✅ 该键因实现瑕疵恒不写入（`extension.py:238`），平台信息走 `Target.scope`。
10. ❌ 对 `Other` 段（未知适配器段）做序列化持久化并期望跨适配器还原；✅ `Other.dump` 记录的是模块路径，跨环境未必可 import。
11. ❌ 在 matcher 外调用 `UniMessage.send()` 不传 bot/target 然后疑惑 `LookupError`；✅ 主动消息必须给 `Target`（或同时给
    `Event+Bot`）。
12. ❌ 忘了 `matcher.send()` 的消息会先过 **所有扩展的 send_wrapper**（含全局扩展）再发出，导致"消息被改了"的灵异现象排查方向错误；✅
    排查时先停用全局扩展。
13. ❌ 快捷指令正则 key 未加 `^...$` 锚定导致误触发范围过大；✅ 用完整匹配语义写正则，必要时 `fuzzy=False`。
14. ❌ 在多进程部署（如多个 bot 进程）下用扩展的内存 dict 做冷却/状态；✅ 外部存储。

**要点回顾**：结构上 require→meta→commands；命令成组、元数据齐全；权限按范围选层；多适配器只碰 UniMessage+能力探测；测试先
`matcher.test` 再 nonebug；发布前过一遍陷阱清单。

---

## 8. 附录：速查表与 FAQ

### 8.1 配置速查（`.env`，均带 `ALCONNA_` 前缀）

| 配置项                | 默认        | 一句话                                                       |
|-----------------------|-------------|--------------------------------------------------------------|
| `AUTO_SEND_OUTPUT`    | None(≡True) | 全局自动发送帮助/错误输出                                    |
| `USE_COMMAND_START`   | False       | COMMAND_START 并入全局命令前缀                               |
| `GLOBAL_COMPLETION`   | None        | 补全会话全局默认配置（命令传 `comp_config=True` 时套用）     |
| `USE_ORIGIN`          | False       | 全局用原始消息解析                                           |
| `USE_CMD_SEP`         | False       | COMMAND_SEP 并入分隔符                                       |
| `GLOBAL_EXTENSIONS`   | []          | 全局扩展路径；`~x`=`nonebot_plugin_alconna.x`，`@x`=内置扩展 |
| `CONTEXT_STYLE`       | None        | 上下文插值风格 bracket `{...}` / parentheses `$(...)`        |
| `ENABLE_SAA_PATCH`    | False       | SAA 兼容补丁                                                 |
| `APPLY_FILEHOST`      | False       | 媒体上传换 URL（需 filehost 插件）                           |
| `APPLY_FETCH_TARGETS` | False       | 启动拉取会话列表，精确化 Bot 选择                            |
| `BUILTIN_PLUGINS`     | []          | 内置插件集合：help/echo/switch/lang/with                     |
| `CONFLICT_RESOLVER`   | default     | 同名命令策略：raise/default/ignore/replace                   |
| `RESPONSE_SELF`       | False       | 响应 bot 自己的消息                                          |
| `CACHE_MESSAGE`       | True        | 入站消息 LRU 缓存                                            |

### 8.2 依赖注入速查

| 写法                                  | 得到                                                                                            |
|---------------------------------------|-------------------------------------------------------------------------------------------------|
| `res: CommandResult` / `AlcResult`    | 结果+输出                                                                                       |
| `arp: Arparma` / `AlcMatches`         | 原始解析结果                                                                                    |
| `x: Match[T]` / `AlconnaMatch("x")`   | 参数匹配项                                                                                      |
| `x: Query[T] = Query("path", 默认)`   | 路径查询项（`~` 相对 basepath）                                                                 |
| `dup: MyDup(Duplication)`             | 类型化视图                                                                                      |
| `ctx: dict`（或 `AlconnaContext()`）  | 解析上下文                                                                                      |
| `AlconnaExecResult()`                 | action 返回值字典                                                                               |
| `ext: MyExtension`                    | 当前事件的扩展实例（注解即注入；DI 函数 `AlconnaExtension` 在 `nonebot_plugin_alconna.params`） |
| `msg: UniMsg` / `OriginalUniMsg`      | 当前消息（原始版含 to_me 处理前内容）                                                           |
| `target: MsgTarget` / `msg_id: MsgId` | 发送对象 / 消息 id                                                                              |
| `seg: At = UniversalSegment(At)`      | 消息中第 N 个指定类型段                                                                         |

### 8.3 扩展钩子速查（按执行顺序）

```
validate → message_provider → receive_wrapper → context_provider
→ [Alconna parse] → permission_check → parse_wrapper
→ handlers(含 before_catch/catch 注入)
→ output_converter → send_wrapper → [实际发送]
（post_init 在命令创建时执行一次）
```

### 8.4 Segment 速查

| 段                                      | 字段要点                                    |
|-----------------------------------------|---------------------------------------------|
| `Text(text, styles)`                    | `.mark/bold/link(...)` 富文本               |
| `At(flag, target, display)`             | flag: user/role/channel                     |
| `AtAll(here)` / `Emoji(id, name)`       |                                             |
| `Image/Audio/Voice/Video/File`          | 继承 Media：`id/url/path/raw/mimetype/name` |
| `Reply(id, msg, origin)`                | 发送时 `UniMessage.reply(id)` 即可          |
| `Reference(id, nodes)`                  | 转发消息；`RefNode`/`CustomNode`            |
| `Hyper("json"\|"xml", content)`         | 卡片                                        |
| `Button(flag, label, ...)` / `Keyboard` | flag: action/link/input/enter               |
| `Other(origin)`                         | 未知段透传                                  |
| `I18n(scope, type)`                     | 发送时解析                                  |

### 8.5 FAQ

**Q：命令敲了对但 handler 没进？**
按序检查：① 前缀（`use_cmd_start` vs 显式前缀）；② rule/`at_me`；③ `assign` 条件；④ 裸参数名失配（静默跳过，见 7.10-5）；⑤ 被
`switch` 插件 disable 了。TRACE 日志（`Plugin-Alconna` 前缀）会打出每条消息对每个命令的解析结果。

**Q：怎么让命令只在某个平台生效？**
`rule=to_me()` 之外，可用 `on_alconna(..., rule=平台判断)`，或扩展的 `validate(bot, event)` 里按 `bot.adapter.get_name()`/
`bot.platform` 过滤。

**Q：`send` 时图片发不出去？**
按序：① `fallback` 是否为 False/forbid；② raw 太大（部分平台限制，用 filehost 或 url）；③ 该适配器对该媒体类型的支持看 README
矩阵（⬆️ 发送/⬇️ 接收）。

**Q：补全会话和 got_path 用哪个？**
`got_path`：参数缺一两个、类型明确；补全会话：想让用户"被引导着填完整个命令"。二者可共存。

**Q：`AlconnaFormat` 字符串语法支持哪些？**
`<name:type>` 必填、`[name:type]` 可选、`...` 变长（`<...content>`），类型段同 Args；复杂结构（Subcommand/action）仍需 Alconna
对象或 `Command` builder。

**Q：哪里看官方示例？**
`example/plugins/demo.py`（全特性演示）与 `tests/`（每个特性的最小验证）；内置插件源码（`builtins/plugins/help`
）是"命令+扩展+i18n+分页"的标准工程范本。

---

*本文基于 nonebot-plugin-alconna 0.62.1 源码撰写；行为存疑处均已标注源码位置，深入阅读可配合仓库内 `LEARNING_NOTES.md`
（源码级学习笔记）。*




