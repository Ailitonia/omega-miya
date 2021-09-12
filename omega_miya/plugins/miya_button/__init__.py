import re
import os
import pathlib
from nonebot import MatcherGroup, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import MessageSegment
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state
from .resources import miya_voices


# Custom plugin usage text
__plugin_custom_name__ = '猫按钮'
__plugin_usage__ = r'''【猫按钮】
发出可爱的猫叫

**Permission**
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
@bot 喵一个'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


button = MatcherGroup(
    type='message',
    rule=to_me(),
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='button',
        command=True,
        level=10),
    permission=GROUP,
    priority=50,
    block=False)


miya_button = button.on_endswith(msg='喵一个')


@miya_button.handle()
async def handle_miya_button(bot: Bot, event: GroupMessageEvent, state: T_State):
    arg = str(event.get_plaintext()).strip().lower()
    keyword = re.sub('喵一个', '', arg)
    voice_file = miya_voices.get_voice(keyword=keyword)
    if not voice_file:
        await miya_button.finish(f'{keyword}是什么不懂喵')
    elif not os.path.exists(voice_file):
        await miya_button.finish('喵？')
    else:
        file_url = pathlib.Path(voice_file).as_uri()
        msg = MessageSegment.record(file=file_url)
        await miya_button.finish(msg)
    logger.info(f'User: {event.user_id} 让 Omega 喵了一下~')
