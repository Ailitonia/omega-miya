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
from .api_base import BaseWeiboAPI
from .credential import WeiboCredential
from .credential_manager import WEIBO_CREDENTIAL_MANAGER
from .model import (
    WeiboCard,
    WeiboCards,
    WeiboExtend,
    WeiboMbLog,
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
        await WeiboCredential.ensure_cookies()
        return WEIBO_CREDENTIAL_MANAGER.cookies

    @classmethod
    async def query_user_data(cls, uid: int | str) -> WeiboUserBase:
        """获取用户信息"""
        await WeiboCredential.ensure_cookies()

        url = f'{cls._get_root_url()}/api/container/getIndex'
        containerid = f'100505{uid}'
        params = {
            'type': 'uid',
            'value': str(uid),
            'containerid': containerid,
        }
        user_response = await cls._get_api_json(url=url, params=params, referer=f'{cls._get_root_url()}/u/{uid}')
        user_info = WeiboUserInfo.model_validate(user_response)

        if user_info.ok != 1 or user_info.data is None:
            raise WebSourceException(400, f'Query user(uid={uid}) data failed, {user_response!r}')

        return user_info.data.userInfo

    @classmethod
    async def query_user_weibo_cards(cls, uid: int | str, since_id: int | str | None = None) -> list[WeiboCard]:
        """获取用户微博

        :param uid: 用户 uid
        :param since_id: 获取的起始 since_id
        :return: WeiboCards
        """
        await WeiboCredential.ensure_cookies()

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

        if cards.ok != 1 or cards.data is None:
            raise WebSourceException(400, f'Query user(uid={uid}) weibo cards failed, {cards_response!r}')

        return cards.data.cards

    @classmethod
    async def query_weibo_card(cls, mid: int | str) -> WeiboMbLog:
        """获取单条微博"""
        await WeiboCredential.ensure_cookies()

        url = f'{cls._get_root_url()}/statuses/show'
        params = {'id': str(mid)}
        card_response = await cls._get_api_json(url, params, referer=f'{cls._get_root_url()}/status/{mid}')

        mblog_data = card_response.get('data') if isinstance(card_response, dict) else None
        if not isinstance(card_response, dict) or card_response.get('ok') != 1 or not isinstance(mblog_data, dict):
            raise WebSourceException(400, f'Query weibo(mid={mid}) failed, {card_response}')

        return WeiboMbLog.model_validate(mblog_data)

    @classmethod
    async def query_weibo_extend_text(cls, mid: int | str) -> str:
        """获取微博展开全文"""
        await WeiboCredential.ensure_cookies()

        url = f'{cls._get_root_url()}/statuses/extend'
        params = {
            'id': str(mid)
        }
        extend_response = await cls._get_api_json(url=url, params=params)
        extend = WeiboExtend.model_validate(extend_response)

        if extend.ok != 1 or extend.data is None or extend.data.ok != 1:
            raise WebSourceException(400, f'Query weibo(mid={mid}) extend content failed, {extend_response!r}')

        return extend.data.longTextContent

    @classmethod
    async def query_realtime_hot(cls) -> list[WeiboRealtimeHotCard]:
        """获取微博热搜"""
        await WeiboCredential.ensure_cookies()

        url = f'{cls._get_root_url()}/api/container/getIndex'
        containerid = '106003type=25&t=3&disable_hot=1&filter_type=realtimehot'
        params = {
            'type': 'uid',
            'containerid': containerid,
        }
        realtime_hot_response = await cls._get_api_json(url=url, params=params)
        realtime_hot = WeiboRealtimeHot.model_validate(realtime_hot_response)

        if realtime_hot.ok != 1 or realtime_hot.data is None:
            raise WebSourceException(400, f'Query realtime hot failed, {realtime_hot_response!r}')

        return realtime_hot.data.cards

    @classmethod
    async def query_top_feed(cls) -> list[WeiboMbLog]:
        """获取首页 feed 更新 (需要已登录状态)"""
        await WeiboCredential.ensure_cookies()

        url = f'{cls._get_root_url()}/feed/friends'
        feed_response = await cls._get_api_json(url=url)
        feed_data = WeiboTopFeed.model_validate(feed_response)

        if feed_data.ok != 1 or feed_data.data is None:
            raise WebSourceException(400, f'Query top feed failed, {feed_response!r}')

        return feed_data.data.statuses


__all__ = [
    'Weibo',
]
