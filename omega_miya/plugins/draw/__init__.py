import datetime
from nonebot import on_command, export, logger
from nonebot.permission import GROUP
from nonebot.typing import Bot, Event
from omega_miya.utils.Omega_plugin_utils import init_export
from omega_miya.utils.Omega_plugin_utils import has_command_permission, permission_level
from .data_source import deck_list, maybe, sp,  sp_event, draw_deck

# Custom plugin usage text
__plugin_name__ = '求签'
__plugin_usage__ = r'''【求签 & Draw】
求签, 求运势, 包括且不限于抽卡、吃饭、睡懒觉、DD
每个人每天求同一个东西的结果是一样的啦!
不要不信邪重新抽啦!

**Permission**
Command & Lv.10

**Usage**
/求签|draw [所求之事|卡组]'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)

# 注册事件响应器
draw = on_command('求签', rule=has_command_permission() & permission_level(level=10), aliases={'Draw', 'draw'},
                  permission=GROUP, priority=20, block=True)


# 修改默认参数处理
@draw.args_parser
async def parse(bot: Bot, event: Event, state: dict):
    args = str(event.plain_text).strip().lower().split()
    if not args:
        await draw.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await draw.finish('操作已取消')


@draw.handle()
async def handle_first_receive(bot: Bot, event: Event, state: dict):
    args = str(event.plain_text).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['draw'] = args[0]
    else:
        await draw.finish('参数错误QAQ')


@draw.got('draw', prompt='你想问什么事呢?')
async def handle_draw(bot: Bot, event: Event, state: dict):
    user_id = event.user_id
    _draw = state['draw']
    # 求签者昵称, 优先使用群昵称
    draw_user = event.sender['card']
    if not draw_user:
        draw_user = event.sender['nickname']

    # 载入牌堆
    deck = deck_list.keys()

    # 判断特殊事件
    if _draw == '卡组':
        msg = '当前可用卡组有:'
        for item in deck:
            msg += f'\n【{item}】'
        await draw.finish(msg)
    if _draw in sp.keys():
        draw_result = sp_event(_draw)
    elif _draw in deck:
        draw_result = draw_deck(_draw)(user_id=user_id)
    else:
        draw_result = maybe(draw=_draw, user_id=user_id)

    # 向用户发送结果
    today = datetime.date.today().strftime('%Y年%m月%d日')
    msg = f'今天是{today}\n{draw_user}{draw_result}'
    await draw.finish(msg)
