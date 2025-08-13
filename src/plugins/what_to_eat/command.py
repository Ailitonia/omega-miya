"""
@Author         : Ailitonia
@Date           : 2021/10/30 15:22
@FileName       : command.py
@Project        : nonebot2_miya
@Description    : 今天吃啥
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime

from nonebot.plugin import MatcherGroup

from src.params.depends import EVENT_MATCHER_INTERFACE
from src.service import enable_processor_state
from .data_source import send_random_food_msg

what_to_eat = MatcherGroup(
    type='message',
    priority=10,
    block=True,
    state=enable_processor_state(name='WhatToEat', level=10, echo_processor_result=False),
)


async def handle_what_to_eat(interface: EVENT_MATCHER_INTERFACE) -> None:
    if '早' in (plain_message := interface.get_event_message().extract_plain_text()):
        food_type = '早'
    elif '午' in plain_message:
        food_type = '午'
    elif '晚' in plain_message:
        food_type = '晚'
    elif '夜' in plain_message:
        food_type = '夜'
    elif '今天' in plain_message:
        food_type = None
    elif 4 <= datetime.now().hour < 10:
        food_type = '早'
    elif 10 <= datetime.now().hour < 16:
        food_type = '午'
    elif 16 <= datetime.now().hour < 20:
        food_type = '晚'
    elif 20 <= datetime.now().hour <= 23 or 0 <= datetime.now().hour < 4:
        food_type = '夜'
    else:
        food_type = None

    await send_random_food_msg(interface=interface, food_type=food_type)


what_to_eat.on_command('今天吃啥', aliases={'吃啥'}, handlers=[handle_what_to_eat])
"""注册命令型事件响应器"""
what_to_eat.on_regex(r'^.{0,2}吃(啥|什么).?$', handlers=[handle_what_to_eat])
"""注册正则型事件响应器"""


__all__ = []
