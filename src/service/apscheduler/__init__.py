import logging

from nonebot import get_driver
from nonebot.plugin import PluginMetadata
from nonebot.log import LoguruHandler, logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Config
from .utils import reschedule_job


__plugin_meta__ = PluginMetadata(
    name="定时任务",
    description="APScheduler 定时任务插件",
    usage=(
        '声明依赖: `require("nonebot_plugin_apscheduler")\n'
        "导入调度器: `from nonebot_plugin_apscheduler import scheduler`\n"
        "添加任务: `scheduler.add_job(...)`\n"
    ),
    type="library",
    homepage="https://github.com/nonebot/plugin-apscheduler",
    config=Config,
    supported_adapters=None,
)


driver = get_driver()
global_config = driver.config
plugin_config = Config(**global_config.dict())

scheduler = AsyncIOScheduler()
scheduler.configure(plugin_config.apscheduler_config)


async def _start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.opt(colors=True).info("<y>Scheduler Started</y>")


async def _shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.opt(colors=True).info("<y>Scheduler Shutdown</y>")


if plugin_config.apscheduler_autostart:
    driver.on_startup(_start_scheduler)
    driver.on_shutdown(_shutdown_scheduler)

aps_logger = logging.getLogger("apscheduler")
aps_logger.setLevel(plugin_config.apscheduler_log_level)
aps_logger.handlers.clear()
aps_logger.addHandler(LoguruHandler())


__all__ = [
    'scheduler',
    'reschedule_job'
]
