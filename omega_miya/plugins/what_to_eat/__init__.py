"""
@Author         : Ailitonia
@Date           : 2021/10/30 15:22
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 今天吃啥
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from nonebot.log import logger
from nonebot.plugin import on_command, PluginMetadata
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import RawCommand

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD

from .model import get_random_food_message


__plugin_meta__ = PluginMetadata(
    name="今天吃啥",
    description="【今天吃啥插件】\n"
                "给吃饭选择困难症一个解决方案",
    usage="/今天吃啥\n"
          "/早上吃啥\n"
          "/中午吃啥\n"
          "/晚上吃啥\n"
          "/夜宵吃啥",
    extra={"author": "Ailitonia"},
)


what_eat_today = on_command(
    '今天吃啥',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='what_to_eat', level=10),
    aliases={'早上吃啥', '早饭吃啥', '中午吃啥', '午饭吃啥', '晚上吃啥', '晚饭吃啥', '夜宵吃啥', '宵夜吃啥'},
    permission=GROUP | GUILD,
    priority=10,
    block=True
)


@what_eat_today.handle()
async def handle_first_receive(bot: Bot, matcher: Matcher, command: str = RawCommand()):
    command_text = command.lstrip(''.join(bot.config.command_start))
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

    msg = await get_random_food_message(food_type=food_type)
    if isinstance(msg, Exception):
        logger.error(f'WhatToEat | 获取菜单失败, {msg}')
        await matcher.finish('获取菜单失败了QAQ, 请稍后再试')
    else:
        await matcher.finish(msg)
