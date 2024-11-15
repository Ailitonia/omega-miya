"""
@Author         : Ailitonia
@Date           : 2024/10/31 16:54:49
@FileName       : models.py
@Project        : omega-miya
@Description    : bilibili API 数据模型
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .search import (
    AllSearchResultType,
    ArticleSearchResult,
    LiveRoomSearchResult,
    LiveUserSearchResult,
    MediaSearchResult,
    PhotoSearchResult,
    SearchAllResult,
    SearchType,
    SearchTypeResult,
    TopicSearchResult,
    UserSearchResult,
    VideoSearchResult,
)
from .sign import (
    Ticket,
    WebInterfaceNav,
    WebInterfaceSpi,
    WebCookieInfo,
    WebQrcodeGenerateInfo,
    WebQrcodePollInfo,
    WebCookieRefreshInfo,
    WebConfirmRefreshInfo,
)
from .user import (
    Account,
    User,
    UserLiveRoom,
    UserSpaceRenderData,
    VipInfo,
)

__all__ = [
    'Account',
    'AllSearchResultType',
    'ArticleSearchResult',
    'LiveRoomSearchResult',
    'LiveUserSearchResult',
    'MediaSearchResult',
    'PhotoSearchResult',
    'SearchAllResult',
    'SearchType',
    'SearchTypeResult',
    'Ticket',
    'TopicSearchResult',
    'WebCookieInfo',
    'WebCookieRefreshInfo',
    'WebConfirmRefreshInfo',
    'WebInterfaceNav',
    'WebInterfaceSpi',
    'WebQrcodeGenerateInfo',
    'WebQrcodePollInfo',
    'User',
    'UserLiveRoom',
    'UserSearchResult',
    'UserSpaceRenderData',
    'VideoSearchResult',
    'VipInfo',
]
