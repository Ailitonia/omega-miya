"""
@Author         : Ailitonia
@Date           : 2024/8/8 10:12:16
@FileName       : main.py
@Project        : omega-miya
@Description    : 微博 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.exception import WebSourceException
from .base import BaseWeiboAPI
from .credential_manager import WEIBO_CREDENTIAL_MANAGER
from .misc import parse_weibo_card_from_status_page
from .model import (
    WeiboCard,
    WeiboCardStatus,
    WeiboCards,
    WeiboExtend,
    WeiboFeedData,
    WeiboRealtimeHot,
    WeiboRealtimeHotCard,
    WeiboTopFeed,
    WeiboUserBase,
    WeiboUserInfo,
)


class Weibo(BaseWeiboAPI):
    """微博, 使用手机端网页 api"""

    @classmethod
    async def update_default_cookies(cls) -> dict[str, str]:
        """刷新并确保默认 Cookies 可用 (依次经由内存缓存、数据库、访客风控流程)"""
        from .credential import WeiboCredential

        await WeiboCredential.ensure_cookies()
        return WEIBO_CREDENTIAL_MANAGER.cookies

    @classmethod
    async def query_user_data(cls, uid: int | str) -> WeiboUserBase:
        """获取用户信息"""
        url = f'{cls._get_root_url()}/api/container/getIndex'
        containerid = f'100505{uid}'
        params = {
            'type': 'uid',
            'value': str(uid),
            'containerid': containerid,
        }
        user_response = await cls._get_api_json(url=url, params=params, referer=f'{cls._get_root_url()}/u/{uid}')
        user_info = WeiboUserInfo.model_validate(user_response)

        if user_info.ok != 1:
            raise WebSourceException(400, f'Query user(uid={uid}) data failed, {user_info.data}')

        return user_info.data.userInfo

    @classmethod
    async def query_user_weibo_cards(cls, uid: int | str, since_id: int | str | None = None) -> list[WeiboCard]:
        """获取用户微博

        :param uid: 用户 uid
        :param since_id: 获取的起始 since_id
        :return: WeiboCards
        """
        url = f'{cls._get_root_url()}/api/container/getIndex'
        containerid = f'107603{uid}'
        params = {
            'type': 'uid',
            'value': str(uid),
            'containerid': containerid,
        }
        if since_id is not None:
            params.update({
                'since_id': str(since_id)
            })
        cards_response = await cls._get_api_json(url=url, params=params, referer=f'{cls._get_root_url()}/u/{uid}')
        cards = WeiboCards.model_validate(cards_response)

        if cards.ok != 1:
            raise WebSourceException(400, f'Query user(uid={uid}) weibo cards failed, {cards.data}')

        return cards.data.cards

    @classmethod
    async def query_weibo_card(cls, mid: int | str) -> WeiboCardStatus:
        """获取单条微博"""
        url = f'{cls._get_root_url()}/status/{mid}'
        card_content = await cls._get_resource_as_text(url=url)

        return parse_weibo_card_from_status_page(card_content)

    @classmethod
    async def query_weibo_extend_text(cls, mid: int | str) -> str:
        """获取微博展开全文"""
        url = f'{cls._get_root_url()}/statuses/extend'
        params = {
            'id': str(mid)
        }
        extend_response = await cls._get_api_json(url=url, params=params)
        extend = WeiboExtend.model_validate(extend_response)

        if extend.ok != 1 or extend.data.ok != 1:
            raise WebSourceException(400, f'Query weibo(mid={mid}) extend content failed, {extend}')

        return extend.data.longTextContent

    @classmethod
    async def query_realtime_hot(cls) -> list[WeiboRealtimeHotCard]:
        """获取微博热搜"""
        url = f'{cls._get_root_url()}/api/container/getIndex'
        containerid = '106003type=25&t=3&disable_hot=1&filter_type=realtimehot'
        params = {
            'type': 'uid',
            'containerid': containerid,
        }
        realtime_hot_response = await cls._get_api_json(url=url, params=params)
        realtime_hot = WeiboRealtimeHot.model_validate(realtime_hot_response)

        if realtime_hot.ok != 1:
            raise WebSourceException(400, f'Query realtime hot failed, {realtime_hot.data}')

        return realtime_hot.data.cards

    @classmethod
    async def query_top_feed(cls) -> WeiboFeedData:
        """获取首页 feed 更新 (需要已登录状态)"""
        url = 'https://m.weibo.cn/feed/friends'

        await cls.update_default_cookies()
        feed_response = await cls._get_api_json(url=url)
        feed_data = WeiboTopFeed.model_validate(feed_response)

        if feed_data.ok != 1:
            raise WebSourceException(400, f'Query top feed failed, {feed_data.data}')

        return feed_data.data


__all__ = [
    'Weibo',
]
