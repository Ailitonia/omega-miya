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
from typing import Annotated

from nonebot.params import Depends
from nonebot.plugin import MatcherGroup

from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
from .data_source import send_random_food_msg

what_to_eat = MatcherGroup(
    type='message',
    priority=10,
    block=True,
    state=enable_processor_state(name='WhatToEat', level=10, echo_processor_result=False),
)


@what_to_eat.on_command('今天吃啥', aliases={'吃啥'}).handle()
async def handle_what_to_eat(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    if 4 <= datetime.now().hour < 10:
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


@what_to_eat.on_fullmatch(('今早吃啥', '早上吃啥', '早饭吃啥', '早餐吃啥')).handle()
async def handle_what_to_eat_breakfast(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    await send_random_food_msg(interface=interface, food_type='早')


@what_to_eat.on_fullmatch(('今天吃啥', '中午吃啥', '午饭吃啥', '午餐吃啥')).handle()
async def handle_what_to_eat_lunch(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    await send_random_food_msg(interface=interface, food_type='午')


@what_to_eat.on_fullmatch(('今晚吃啥', '晚上吃啥', '晚饭吃啥', '晚餐吃啥')).handle()
async def handle_what_to_eat_dinner(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    await send_random_food_msg(interface=interface, food_type='晚')


@what_to_eat.on_fullmatch(('夜宵吃啥', '宵夜吃啥')).handle()
async def handle_what_to_eat_night(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    await send_random_food_msg(interface=interface, food_type='夜')


__all__ = []
