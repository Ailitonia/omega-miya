import re
import os
from nonebot import MatcherGroup, logger
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import MessageSegment
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import init_permission_state
from .resources import MiyaVoice

"""
miya按钮bot实现版本
测试中
"""


button = MatcherGroup(
    type='message',
    rule=to_me(),
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='button',
        command=True,
        level=10),
    permission=GROUP,
    priority=100,
    block=False)


miya_button = button.on_endswith(msg='喵一个')


@miya_button.handle()
async def miya_button(bot: Bot, event: GroupMessageEvent, state: T_State):
    arg = str(event.get_plaintext()).strip().lower()
    voice = re.sub('喵一个', '', arg)
    voice_file = MiyaVoice().get_voice_filepath(voice=voice)
    if not os.path.exists(voice_file):
        await bot.send(event=event, message='喵？')
    else:
        msg = MessageSegment.record(file=f'file:///{voice_file}')
        await bot.send(event=event, message=msg)
