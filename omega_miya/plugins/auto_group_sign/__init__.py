"""
@Author         : Ailitonia
@Date           : 2022/06/27 20:48
@FileName       : auto_group_sign.py
@Project        : nonebot2_miya 
@Description    : 自动群打卡 (go-cqhttp v1.0.0-rc3 以上版本可用)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from nonebot.adapters import Bot
from pydantic import BaseModel

from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.utils.apscheduler import scheduler
from omega_miya.utils.process_utils import semaphore_gather


class AutoGroupSignConfig(BaseModel):
    """自动群打卡插件配置"""
    # 启用自动群打卡
    enable_auto_group_sign: bool = False

    class Config:
        extra = "ignore"


_plugin_config = AutoGroupSignConfig.parse_obj(get_driver().config)


async def _bot_group_sign(bot: Bot):
    gocq_bot = GoCqhttpBot(bot=bot)
    tasks = [gocq_bot.send_group_sign(group_id=group_result.group_id) for group_result in await gocq_bot.get_group_list()]
    await semaphore_gather(tasks=tasks, semaphore_num=16)


async def _sign_main() -> None:
    logger.debug('AutoGroupSign | Starting sign all groups')
    tasks = [_bot_group_sign(bot=bot) for _, bot in get_driver().bots.items()]
    await semaphore_gather(tasks=tasks, semaphore_num=8)
    logger.debug('AutoGroupSign | Sign tasks completed')


if _plugin_config.enable_auto_group_sign:
    scheduler.add_job(
        _sign_main,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        hour='0',
        minute='0',
        second='0',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='auto_group_sign',
        coalesce=True,
        misfire_grace_time=30
    )
    logger.opt(colors=True).success('<lc>AutoGroupSign</lc> | <lg>自动群打卡已启用</lg>')
