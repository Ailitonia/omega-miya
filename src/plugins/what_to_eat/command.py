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

from nonebot import get_driver, logger
from nonebot.params import Depends, RawCommand
from nonebot.plugin import on_command

from src.service import OmegaMatcherInterface as OmMI, enable_processor_state
from .data_source import get_random_food_msg


@on_command(
    '今天吃啥',
    aliases={'早上吃啥', '早饭吃啥', '中午吃啥', '午饭吃啥', '晚上吃啥', '晚饭吃啥', '夜宵吃啥', '宵夜吃啥'},
    priority=10,
    block=True,
    state=enable_processor_state(name='WhatToEat', level=10),
).handle()
async def handle_what_to_eat(
        cmd: Annotated[str, RawCommand()],
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    command_text = cmd.lstrip(''.join(get_driver().config.command_start))

    if '早' in command_text:
        food_type = '早'
    elif '午' in command_text:
        food_type = '午'
    elif '晚' in command_text:
        food_type = '晚'
    elif '夜' in command_text:
        food_type = '夜'
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

    try:
        msg = await get_random_food_msg(food_type=food_type)
        await interface.send_reply(msg)
    except Exception as e:
        logger.error(f'WhatToEat | 获取菜单失败, {e}')
        await interface.send_reply('获取菜单失败了, 请稍后再试')


__all__ = []
