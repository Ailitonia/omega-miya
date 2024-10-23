"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:53
@FileName       : utils
@Project        : ailitonia-toolkit
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime

from nonebot.log import logger
from sqlalchemy.exc import NoResultFound

from src.database import SystemSettingDAL, begin_db_session
from .consts import DOWNLOADER_SETTING_NAME, LAST_FOLLOWING_SETTING_KEY


async def set_last_follow_illust_pid(pid: int) -> None:
    """保存上次关注用户的最新作品"""
    async with begin_db_session() as session:
        dal = SystemSettingDAL(session=session)
        await SystemSettingDAL(session=session).upsert(
            setting_name=DOWNLOADER_SETTING_NAME,
            setting_key=LAST_FOLLOWING_SETTING_KEY,
            setting_value=str(pid),
            info=f'last scan time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        )


async def get_last_follow_illust_pid() -> int | None:
    """读取上次关注用户的最新作品"""
    async with begin_db_session() as session:
        try:
            setting = await SystemSettingDAL(session=session).query_unique(
                setting_name=DOWNLOADER_SETTING_NAME,
                setting_key=LAST_FOLLOWING_SETTING_KEY,
            )
            last_pid = int(setting.setting_value)
            info = setting.info
        except NoResultFound:
            last_pid = None
            info = 'No result found'
    logger.info(f'Read last scan pid: {last_pid}, {info}')
    return last_pid


__all__ = [
    'set_last_follow_illust_pid',
    'get_last_follow_illust_pid',
]
