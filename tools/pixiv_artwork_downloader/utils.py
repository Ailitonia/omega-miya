"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:53
@FileName       : utils
@Project        : ailitonia-toolkit
@Description    : 辅助工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime

from nonebot.log import logger
from sqlalchemy.exc import NoResultFound

from src.database import SystemSettingDAL
from .consts import DOWNLOADER_SETTING_NAME, LAST_FOLLOWING_SETTING_KEY


async def set_last_follow_illust_pid(pid: int) -> None:
    """保存上次关注用户的最新作品"""
    async with SystemSettingDAL.create() as dal:
        await dal.add_update_exist(
            setting_name=DOWNLOADER_SETTING_NAME,
            setting_key=LAST_FOLLOWING_SETTING_KEY,
            setting_value=str(pid),
            info=f'last scan time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        )


async def get_last_follow_illust_pid() -> int | None:
    """读取上次关注用户的最新作品"""
    async with SystemSettingDAL.create() as dal:
        try:
            setting = await dal.query_unique(
                setting_name=DOWNLOADER_SETTING_NAME,
                setting_key=LAST_FOLLOWING_SETTING_KEY,
            )
            try:
                last_pid = int(setting.setting_value)
                info = setting.info
            except (TypeError, ValueError):
                # 数据库中残留脏数据时视为无历史分界, 本次全量扫描
                logger.warning(f'Invalid last follow illust pid in database: {setting.setting_value!r}, ignored')
                last_pid = None
                info = f'Invalid setting value: {setting.setting_value!r}'
        except NoResultFound:
            last_pid = None
            info = 'No result found'
    logger.info(f'Read last scan pid: {last_pid}, {info}')
    return last_pid


__all__ = [
    'set_last_follow_illust_pid',
    'get_last_follow_illust_pid',
]
