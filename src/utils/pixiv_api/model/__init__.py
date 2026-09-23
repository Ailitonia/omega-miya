"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:03
@FileName       : model.py
@Project        : nonebot2_miya
@Description    : Pixiv Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .artwork import (
    PixivIllustData,
    PixivIllustFull,
    PixivIllustPages,
    PixivIllustRecommend,
    PixivIllustUgoiraMeta,
)
from .discovery import PixivDiscovery, PixivTop
from .pixivision import PixivisionArticle, PixivisionIllustrationItem, PixivisionIllustrations
from .ranking import PixivRanking
from .searching import PixivSearchingResult
from .user import (
    PixivBookmark,
    PixivFollowLatestIllust,
    PixivFollowUser,
    PixivUserData,
    PixivUserFull,
    PixivUserProfile,
    PixivUserSearchingResult,
)

__all__ = [
    'PixivIllustData',
    'PixivIllustPages',
    'PixivIllustUgoiraMeta',
    'PixivIllustFull',
    'PixivIllustRecommend',
    'PixivRanking',
    'PixivSearchingResult',
    'PixivDiscovery',
    'PixivTop',
    'PixivUserData',
    'PixivUserProfile',
    'PixivUserFull',
    'PixivUserSearchingResult',
    'PixivFollowLatestIllust',
    'PixivFollowUser',
    'PixivisionArticle',
    'PixivisionIllustrationItem',
    'PixivisionIllustrations',
    'PixivBookmark',
]
