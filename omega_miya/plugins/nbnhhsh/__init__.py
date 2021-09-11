from nonebot import on_command, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state
from .utils import get_guess


# Custom plugin usage text
__plugin_custom_name__ = '好好说话'
__plugin_usage__ = r'''【能不能好好说话？】
拼音首字母缩写释义
群组/私聊可用

**Permission**
Friend Private
Command & Lv.30
or AuthNode

**AuthNode**
basic

**Usage**
/好好说话 [缩写]'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
nbnhhsh = on_command(
    '好好说话',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='nbnhhsh',
        command=True,
        level=30),
    aliases={'hhsh', 'nbnhhsh'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True)


# 修改默认参数处理
@nbnhhsh.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await nbnhhsh.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await nbnhhsh.finish('操作已取消')


@nbnhhsh.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['guess'] = args[0]
    else:
        await nbnhhsh.finish('参数错误QAQ')


@nbnhhsh.got('guess', prompt='有啥缩写搞不懂?')
async def handle_nbnhhsh(bot: Bot, event: MessageEvent, state: T_State):
    guess = state['guess']
    res = await get_guess(guess=guess)
    if res.success() and res.result:
        try:
            data = dict(res.result[0])
        except Exception as e:
            logger.error(f'nbnhhsh error: {repr(e)}')
            await nbnhhsh.finish('发生了意外的错误QAQ, 请稍后再试')
            return
        if data.get('trans'):
            trans = str.join('\n', data.get('trans'))
            msg = f"为你找到了{guess}的以下解释:\n\n{trans}"
            await nbnhhsh.finish(msg)
        elif data.get('inputting'):
            trans = str.join('\n', data.get('inputting'))
            msg = f"为你找到了{guess}的以下解释:\n\n{trans}"
            await nbnhhsh.finish(msg)
    await nbnhhsh.finish(f'没有找到{guess}的相关解释QAQ')
