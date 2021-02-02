import re
from nonebot import on_message
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import has_notice_permission
from .utils import sp_event_check

last_msg = {}
last_repeat_msg = {}
repeat_count = {}

repeater = on_message(rule=has_notice_permission(), permission=GROUP, priority=100, block=False)


@repeater.handle()
async def handle_repeater(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_id = event.group_id

    global last_msg, last_repeat_msg, repeat_count

    try:
        last_msg[group_id]
    except KeyError:
        last_msg[group_id] = ''
    try:
        last_repeat_msg[group_id]
    except KeyError:
        last_repeat_msg[group_id] = ''

    # 特殊消息
    sp_res, sp_msg = await sp_event_check(event=event)
    if sp_res:
        repeat_count[group_id] = 0
        await repeater.finish(message=sp_msg)

    t_msg = event.message
    msg = event.raw_message

    if re.match(r'^/', msg):
        return

    if msg != last_msg[group_id] or msg == last_repeat_msg[group_id]:
        last_msg[group_id] = msg
        repeat_count[group_id] = 0
        return
    else:
        repeat_count[group_id] += 1
        last_repeat_msg[group_id] = ''
        if repeat_count[group_id] >= 2:
            await repeater.send(t_msg)
            repeat_count[group_id] = 0
            last_msg[group_id] = ''
            last_repeat_msg[group_id] = msg
