from nonebot import on_message
from nonebot.permission import GROUP
from nonebot.typing import Bot, Event
from omega_miya.utils.Omega_plugin_utils import has_notice_permission
import re

last_msg = {}
last_repeat_msg = {}
repeat_count = {}

repeater = on_message(rule=has_notice_permission(), permission=GROUP, priority=100, block=False)


@repeater.handle()
async def handle_repeater(bot: Bot, event: Event, state: dict):
    global last_msg, last_repeat_msg, repeat_count

    group_id = event.group_id

    try:
        last_msg[group_id]
    except KeyError:
        last_msg[group_id] = ''
    try:
        last_repeat_msg[group_id]
    except KeyError:
        last_repeat_msg[group_id] = ''

    msg = str(event.raw_message)
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
            await repeater.send(message=msg)
            repeat_count[group_id] = 0
            last_msg[group_id] = ''
            last_repeat_msg[group_id] = msg
