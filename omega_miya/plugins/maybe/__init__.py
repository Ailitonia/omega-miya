"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : maybe.py
@Project        : nonebot2_miya
@Description    : 求签
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import datetime
from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD

from .utils import query_maybe


__plugin_meta__ = PluginMetadata(
    name="求签",
    description="【求签插件】\n"
                "求签, 求运势, 包括且不限于抽卡、吃饭、睡懒觉、DD\n"
                "每个人每天求同一个东西的结果是一样的啦!\n"
                "不要不信邪重新抽啦!",
    usage="/求签 [所求之事]",
    extra={"author": "Ailitonia"},
)


maybe = on_command(
    'maybe',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='maybe', level=10),
    aliases={'求签'},
    permission=GROUP | GUILD,
    priority=10,
    block=True
)


@maybe.handle()
async def handle_parse_sign_text(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    sign_text = cmd_arg.extract_plain_text().strip()
    if sign_text:
        state.update({'sign_text': sign_text})


@maybe.got('sign_text', prompt='你想问什么事呢?')
async def handle_sign_text(event: MessageEvent, sign_text: str = ArgStr('sign_text')):
    sign_text = sign_text.strip()
    result_text = query_maybe(sign_text=sign_text, user_id=event.user_id)
    today = datetime.date.today().strftime('%Y年%m月%d日')
    send_message = f'今天是{today}\n{event.sender.card if event.sender.card else event.sender.nickname}{result_text}'
    await maybe.finish(send_message)
