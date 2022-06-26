import logging

from nonebot import get_driver
from nonebot.log import logger, LoguruHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Config
from .utils import reschedule_job

driver = get_driver()
plugin_config = Config.parse_obj(driver.config)

scheduler: AsyncIOScheduler = AsyncIOScheduler()


async def _start_scheduler():
    if not scheduler.running:
        scheduler.configure(plugin_config.apscheduler_config)
        scheduler.start()
        logger.opt(colors=True).info("<y>Scheduler Started</y>")


if plugin_config.apscheduler_autostart:
    driver.on_startup(_start_scheduler)

aps_logger = logging.getLogger("apscheduler")
aps_logger.setLevel(plugin_config.apscheduler_log_level)
aps_logger.handlers.clear()
aps_logger.addHandler(LoguruHandler())


__all__ = [
    'scheduler',
    'reschedule_job'
]
