"""
@Author         : Ailitonia
@Date           : 2021/12/24 11:09
@FileName       : draw.py
@Project        : nonebot2_miya
@Description    : Roll
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import on_command
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD

from .deck import draw, get_deck

# Custom plugin usage text
__plugin_custom_name__ = '抽卡'
__plugin_usage__ = r'''【抽卡】
模拟各种抽卡
没有保底的啦!
不要上头啊喂!

用法
/抽卡 [卡组]'''


draw_deck = on_command(
    'Draw',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='draw', level=10, cool_down=20),
    aliases={'draw', '抽卡'},
    permission=GROUP | GUILD,
    priority=10,
    block=True
)


@draw_deck.handle()
async def handle_parse_deck(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    deck_name = cmd_arg.extract_plain_text().strip()
    if deck_name:
        state.update({'deck_name': deck_name})
    else:
        msg = '当前可用卡组有:\n\n' + '\n'.join(x for x in get_deck())
        await draw_deck.send(msg)


@draw_deck.got('deck_name', prompt='请输入你想要抽取的卡组:')
async def handle_roll(event: MessageEvent, deck_name: str = ArgStr('deck_name')):
    deck_name = deck_name.strip()
    if deck_name not in get_deck():
        msg = f'没有"{deck_name}"卡组, 请重新在以下可用卡组中选择:\n\n' + '\n'.join(x for x in get_deck())
        await draw_deck.reject(msg)

    draw_msg = draw(deck_name=deck_name, draw_seed=event.user_id)
    await draw_deck.finish(draw_msg, at_sender=True)
