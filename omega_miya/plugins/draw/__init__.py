from nonebot import CommandGroup, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state, PluginCoolDown
from .data_source import deck_list, draw_deck

# Custom plugin usage text
__plugin_name__ = '抽卡'
__plugin_usage__ = r'''【抽卡】
模拟各种抽卡
没有保底的啦!
不要上头啊喂!
仅限群聊使用

**Permission**
Command & Lv.10
or AuthNode

**AuthNode**
basic

**CoolDown**
用户冷却时间
1 Minutes

**Usage**
/抽卡 [卡组]'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    PluginCoolDown.skip_auth_node,
    'basic'
]

# 声明本插件的冷却时间配置
__plugin_cool_down__ = [
    PluginCoolDown(PluginCoolDown.user_type, 1)
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__, __plugin_cool_down__)

# 注册事件响应器
Draw = CommandGroup(
    'draw',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='draw',
        command=True,
        level=10,
        auth_node='basic'),
    permission=GROUP,
    priority=10,
    block=True)

deck = Draw.command('deck', aliases={'抽卡'})


# 修改默认参数处理
@deck.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await deck.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await deck.finish('操作已取消')


@deck.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 载入牌堆
    state['deck'] = deck_list.keys()

    args = str(event.get_plaintext()).strip().lower().split()

    if not args:
        msg = '当前可用卡组有:'
        for item in state['deck']:
            msg += f'\n【{item}】'
        await deck.send(msg)
    elif args and len(args) == 1:
        state['draw'] = args[0]
    else:
        await deck.finish('参数错误QAQ')


@deck.got('draw', prompt='请输入你想要抽取的卡组:')
async def handle_deck(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.user_id
    _draw = state['draw']
    _deck = state['deck']
    if _draw not in _deck:
        await deck.finish('没有这个卡组QAQ')

    # 抽卡者昵称, 优先使用群昵称
    draw_user = event.sender.card
    if not draw_user:
        draw_user = event.sender.nickname

    draw_result = draw_deck(_draw)(user_id)

    # 向用户发送结果
    msg = f"{draw_user}抽卡【{_draw}】!!\n{'='*12}\n{draw_result}"
    await deck.finish(msg)
