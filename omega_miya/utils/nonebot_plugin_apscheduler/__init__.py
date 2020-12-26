from nonebot.log import logger
from nonebot import get_driver, export
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Config

driver = get_driver()
global_config = driver.config
plugin_config = Config(**global_config.dict())

scheduler = AsyncIOScheduler()
export().scheduler = scheduler


async def _start_scheduler():
    if not scheduler.running:
        scheduler.configure(plugin_config.apscheduler_config)
        scheduler.start()
        logger.opt(colors=True).info("<y>Scheduler Started</y>")


if plugin_config.apscheduler_autostart:
    driver.on_startup(_start_scheduler)
