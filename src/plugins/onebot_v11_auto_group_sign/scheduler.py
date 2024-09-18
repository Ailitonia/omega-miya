"""
@Author         : Ailitonia
@Date           : 2022/06/27 20:48
@FileName       : auto_group_sign.py
@Project        : nonebot2_miya 
@Description    : 自动群打卡定时任务
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.log import logger

from src.service import scheduler
from src.service.omega_multibot_support import get_online_bots
from src.utils import semaphore_gather
from .config import auto_group_sign_config


async def _bot_group_sign(bot: OneBotV11Bot):
    tasks = [
        bot.send_group_sign(group_id=group_data['group_id'])
        for group_data in await bot.get_group_list()
        if group_data.get('group_id')
    ]
    await semaphore_gather(tasks=tasks, semaphore_num=16)


async def _auto_group_sign_main() -> None:
    logger.info('AutoGroupSign | Starting sign all groups')
    tasks = [
        _bot_group_sign(bot=bot)
        for _, bot in get_online_bots().get('OneBot V11', {}).items()
        if isinstance(bot, OneBotV11Bot)
    ]
    await semaphore_gather(tasks=tasks, semaphore_num=2)
    logger.info('AutoGroupSign | Sign tasks completed')


if auto_group_sign_config.enable_auto_group_sign:
    scheduler.add_job(
        _auto_group_sign_main,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        hour=0,
        minute=0,
        second=auto_group_sign_config.auto_group_sign_delay,
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='auto_group_sign',
        coalesce=True,
        misfire_grace_time=30
    )
    logger.opt(colors=True).success('<lc>AutoGroupSign</lc> | <lg>自动群打卡已启用</lg>')


__all__ = []
