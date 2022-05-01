"""
@Author         : Ailitonia
@Date           : 2021/10/30 15:22
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 今天吃啥
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import json
import aiofiles
import pathlib
import random
from typing import Union, Optional
from datetime import datetime
from nonebot import MatcherGroup, logger, get_driver
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp import MessageSegment, Message
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state


__global_config = get_driver().config
RESOURCES_PATH = __global_config.resources_path_
FOOD_RESOURCES_PATH = os.path.abspath(os.path.join(RESOURCES_PATH, 'images', 'what_to_eat'))


# Custom plugin usage text
__plugin_custom_name__ = '今天吃啥'
__plugin_usage__ = r'''【今天吃啥】
给吃饭选择困难症一个解决方案

**Permission**
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
/今天吃啥
/早上吃啥
/中午吃啥
/晚上吃啥
/夜宵吃啥'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
WhatToEat = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='what_to_eat',
        command=True,
        level=10
    ),
    permission=GROUP,
    priority=10,
    block=True)

what_eat_today = WhatToEat.on_command('今天吃啥', aliases={
    '早上吃啥', '早餐吃啥', '中午吃啥', '午餐吃啥', '晚上吃啥', '晚餐吃啥', '夜宵吃啥', '宵夜吃啥'})


@what_eat_today.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    command = state.get('_prefix', {}).get('command')
    if command:
        command_text = command[0]
        if '早' in command_text:
            food_type = 'breakfast'
        elif '午' in command_text:
            food_type = 'lunch'
        elif '晚' in command_text:
            food_type = 'dinner'
        elif '夜' in command_text:
            food_type = 'night'
        elif 4 <= datetime.now().hour < 10:
            food_type = 'breakfast'
        elif 10 <= datetime.now().hour < 16:
            food_type = 'lunch'
        elif 16 <= datetime.now().hour < 20:
            food_type = 'dinner'
        elif 20 <= datetime.now().hour <= 23 or 0 <= datetime.now().hour < 4:
            food_type = 'night'
        else:
            food_type = None
    else:
        food_type = None

    msg = await get_random_food_message(type_=food_type)
    await what_eat_today.finish(msg)


async def get_random_food_message(type_: Optional[str] = None) -> Union[str, Message]:
    try:
        async with aiofiles.open(os.path.join(FOOD_RESOURCES_PATH, 'index.json'), 'r', encoding='utf8') as aio_f:
            index = list(json.loads(await aio_f.read()))

        if type_ == 'breakfast':
            food = random.choice([food for food in index if ('早' in food['type'])])
        elif type_ == 'lunch':
            food = random.choice([food for food in index if ('午' in food['type'])])
        elif type_ == 'dinner':
            food = random.choice([food for food in index if ('晚' in food['type'])])
        elif type_ == 'night':
            food = random.choice([food for food in index if ('夜' in food['type'])])
        else:
            food = random.choice(index)

        food_name = food['name']
        food_img_file = random.choice(food['img'])
        food_img_url = pathlib.Path(os.path.join(FOOD_RESOURCES_PATH, food_img_file)).as_uri()
        img_seg = MessageSegment.image(food_img_url)
        msg = f'不知道吃啥的话，不如尝尝{food_name}如何？\n' + img_seg
    except Exception as e:
        logger.error(f'WhatToEat | Getting food resource failed, error: {repr(e)}')
        msg = '获取菜单失败了QAQ, 请稍后再试'
    return msg
