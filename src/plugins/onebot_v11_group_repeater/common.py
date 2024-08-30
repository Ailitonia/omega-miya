"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : repeater.py
@Project        : nonebot2_miya
@Description    : 复读姬
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot, GroupMessageEvent as OneBotV11GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from nonebot.plugin import on_message

from src.params.rule import event_has_global_permission
from src.service import enable_processor_state

LAST_MSG: dict[int, str] = {}
"""记录上一条收到的消息"""
LAST_REPEAT_MSG: dict[int, str] = {}
"""记录上一条复读过的消息"""
REPEAT_COUNT: dict[int, int] = {}
"""记录之前相同消息重复的次数"""
REPEAT_THRESHOLD: int = 3
"""复读阈值, 重复的消息达到多少条就复读"""


async def handle_ignore_msg(bot: OneBotV11Bot, event: OneBotV11GroupMessageEvent):
    """忽略特殊类型的消息"""
    msg = event.get_plaintext()
    for command_start in bot.config.command_start:
        if msg.startswith(command_start):
            raise FinishedException
    if msg.startswith('!SU'):
        raise FinishedException


@on_message(
    rule=event_has_global_permission(),
    permission=GROUP,
    handlers=[handle_ignore_msg],
    priority=100,
    block=False,
    state=enable_processor_state('OneBotV11GroupRepeater', enable_processor=False, echo_processor_result=False)
).handle()
async def handle_repeater(event: OneBotV11GroupMessageEvent, matcher: Matcher):
    """处理复读"""
    global LAST_MSG, LAST_REPEAT_MSG, REPEAT_COUNT

    group_id = event.group_id
    try:
        LAST_MSG[group_id]
    except KeyError:
        LAST_MSG[group_id] = ''
    try:
        LAST_REPEAT_MSG[group_id]
    except KeyError:
        LAST_REPEAT_MSG[group_id] = ''

    message = event.get_message()
    raw_msg = event.raw_message

    # 如果当前消息与上一条消息不同, 或者与上一次复读的消息相同, 则重置复读计数, 并更新上一条消息LAST_MSG
    if raw_msg != LAST_MSG[group_id] or raw_msg == LAST_REPEAT_MSG[group_id]:
        LAST_MSG[group_id] = raw_msg
        REPEAT_COUNT[group_id] = 0
        return
    # 否则这条消息和上条消息一致, 开始复读计数
    else:
        REPEAT_COUNT[group_id] += 1
        LAST_REPEAT_MSG[group_id] = ''
        # 当复读计数等于2时说明已经有连续3条同样的消息了, 此时触发复读, 更新上次服务消息LAST_REPEAT_MSG, 并重置复读计数
        if REPEAT_COUNT[group_id] >= REPEAT_THRESHOLD - 1:
            REPEAT_COUNT[group_id] = 0
            LAST_MSG[group_id] = ''
            LAST_REPEAT_MSG[group_id] = raw_msg
            await matcher.send(message)


__all__ = []
