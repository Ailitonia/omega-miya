"""
@Author         : Ailitonia
@Date           : 2023/7/3 3:51
@FileName       : status
@Project        : nonebot2_miya
@Description    : bot 运行状态
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

Source: https://github.com/cscs181/QQ-GitHub-Bot/blob/master/src/plugins/nonebot_plugin_status/data_source.py
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

import psutil
from nonebot import get_driver
from nonebot.log import logger

if TYPE_CHECKING:
    from psutil._ntuples import sdiskusage

_CURRENT_TIMEZONE = datetime.now().astimezone().tzinfo
_NONEBOT_RUN_TIME: datetime


@get_driver().on_startup
async def _():
    global _NONEBOT_RUN_TIME
    _NONEBOT_RUN_TIME = datetime.now(_CURRENT_TIMEZONE)


def get_nonebot_run_time() -> datetime:
    """Get the time when NoneBot started running."""
    try:
        return _NONEBOT_RUN_TIME
    except NameError:
        raise RuntimeError('NoneBot not running!') from None


async def get_cpu_status() -> float:
    """Get the CPU usage status."""
    psutil.cpu_percent()
    await asyncio.sleep(0.5)
    return psutil.cpu_percent()


def get_memory_status():
    """Get the memory usage status."""
    return psutil.virtual_memory()


def get_swap_status():
    """Get the swap usage status."""
    return psutil.swap_memory()


def _get_disk_usage(path: str) -> 'sdiskusage | None':
    try:
        return psutil.disk_usage(path)
    except Exception as e:
        logger.warning(f'Could not get disk usage for {path}: {e!r}')


def get_disk_usage() -> dict[str, 'sdiskusage']:
    """Get the disk usage status."""
    disk_parts = psutil.disk_partitions()
    return {
        d.mountpoint: usage
        for d in disk_parts
        if (usage := _get_disk_usage(d.mountpoint)) is not None
    }


def get_uptime() -> datetime:
    """Get the uptime of the machine."""
    return datetime.fromtimestamp(psutil.boot_time(), tz=_CURRENT_TIMEZONE)


async def get_status() -> str:
    return (
        f'CPU Usage: {await get_cpu_status()}%\n'
        f'Memory Usage: {get_memory_status().percent}%\n'
        f'Swap Usage: {get_swap_status().percent}%\n'
        f'Disk Usage: {" | ".join(f"{k}({v.percent}%)" for k, v in get_disk_usage().items())}\n'
        f'Uptime: {get_uptime().strftime("%Y-%m-%d %H:%M:%S")}\n'
        f'Runtime: {get_nonebot_run_time().strftime("%Y-%m-%d %H:%M:%S")}'
    )


__all__ = [
    'get_status',
]
