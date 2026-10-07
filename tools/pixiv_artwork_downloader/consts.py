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

DOWNLOAD_SEMAPHORE_NUM: int = 8
"""并行下载数量限制"""
QUERY_BATCH_SIZE: int = 20
"""获取作品信息时分段处理的单批数量"""
FOLLOWING_QUERY_MAX_PAGE: int = 85
"""已关注作品页查询上限 (一页 60 个作品, 最多约 5000 张, 之后的页全是重复内容)"""
FILTER_R18_ALL_PAGES_LIKE_COUNT: int = 1666
"""筛选时 R18 作品下载全部页面所需的最少点赞数, 低于该值仅下载封面"""
FILTER_ALL_PAGES_LIKE_COUNT: int = 666
"""筛选时非 R18 作品下载全部页面所需的最少点赞数, 低于该值仅下载封面"""
LIST_PAGE_QUERY_INTERVAL: float = 3.0
"""分页列表查询(关注新作/收藏/标签用户)的翻页请求间隔秒数, 避免连续翻页触发 pixiv 流控"""
TAG_USER_QUERY_LIMIT: int = 48
"""按标签查询已关注用户时单页数量"""


__all__ = [
    'DOWNLOAD_SEMAPHORE_NUM',
    'DOWNLOADER_SETTING_NAME',
    'FILTER_ALL_PAGES_LIKE_COUNT',
    'FILTER_R18_ALL_PAGES_LIKE_COUNT',
    'FOLLOWING_QUERY_MAX_PAGE',
    'LAST_FOLLOWING_SETTING_KEY',
    'LIST_PAGE_QUERY_INTERVAL',
    'QUERY_BATCH_SIZE',
    'TAG_USER_QUERY_LIMIT',
]
