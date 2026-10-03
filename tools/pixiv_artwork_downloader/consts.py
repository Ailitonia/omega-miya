"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:57
@FileName       : consts
@Project        : ailitonia-toolkit
@Description    : pixiv_artwork_downloader 工具常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

DOWNLOADER_SETTING_NAME: Literal['omega_tool_pixiv_artwork_downloader'] = 'omega_tool_pixiv_artwork_downloader'
"""下载工具数据库设置表中的字段名"""
LAST_FOLLOWING_SETTING_KEY: Literal['last_latest_following_artwork'] = 'last_latest_following_artwork'
"""下载工具数据库设置表中上次下载时关注作品中最新的作品的配置名"""


__all__ = [
    'DOWNLOADER_SETTING_NAME',
    'LAST_FOLLOWING_SETTING_KEY',
]
