import datetime
from nonebot import CommandGroup, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import init_export
from omega_miya.utils.Omega_plugin_utils import has_command_permission, permission_level
from .utils import maybe, sp,  sp_event


# Custom plugin usage text
__plugin_name__ = '求签'
__plugin_usage__ = r'''【求签】
求签, 求运势, 包括且不限于抽卡、吃饭、睡懒觉、DD
每个人每天求同一个东西的结果是一样的啦!
不要不信邪重新抽啦!

**Permission**
Command & Lv.10

**Usage**
/求签 [所求之事]'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)

# 注册事件响应器
Maybe = CommandGroup('maybe', rule=has_command_permission() & permission_level(level=10),
                     permission=GROUP, priority=10, block=True)

luck = Maybe.command('luck', aliases={'求签'})


# 修改默认参数处理
@luck.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await luck.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await luck.finish('操作已取消')


@luck.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['draw'] = args[0]
    else:
        await luck.finish('参数错误QAQ')


@luck.got('draw', prompt='你想问什么事呢?')
async def handle_luck(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.user_id
    _draw = state['draw']
    # 求签者昵称, 优先使用群昵称
    draw_user = event.sender.card
    if not draw_user:
        draw_user = event.sender.nickname

    # 判断特殊事件
    if _draw in sp.keys():
        draw_result = sp_event(_draw)
    else:
        draw_result = maybe(draw=_draw, user_id=user_id)

    # 向用户发送结果
    today = datetime.date.today().strftime('%Y年%m月%d日')
    msg = f'今天是{today}\n{draw_user}{draw_result}'
    await luck.finish(msg)
