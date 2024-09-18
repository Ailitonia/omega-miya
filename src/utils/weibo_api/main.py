"""
@Author         : Ailitonia
@Date           : 2024/8/8 10:12:16
@FileName       : main.py
@Project        : omega-miya
@Description    : 微博 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Any

from src.exception import WebSourceException
from src.utils import BaseCommonAPI
from .config import weibo_resource_config
from .helper import parse_weibo_card_from_status_page
from .model import (
    WeiboCard,
    WeiboCards,
    WeiboCardStatus,
    WeiboExtend,
    WeiboRealtimeHotCard,
    WeiboRealtimeHot,
    WeiboUserBase,
    WeiboUserInfo,
)

if TYPE_CHECKING:
    from src.resource import TemporaryResource


class Weibo(BaseCommonAPI):
    """微博, 使用手机端网页 api"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://m.weibo.cn'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> dict[str, Any]:
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'origin': 'https://m.weibo.cn',
            'referer': 'https://m.weibo.cn/'
        })
        return headers

    @classmethod
    def _get_default_cookies(cls) -> dict[str, str]:
        return {}

    @classmethod
    async def download_resource(
            cls,
            url: str,
            *,
            subdir: str | None = None,
            ignore_exist_file: bool = False
    ) -> "TemporaryResource":
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=weibo_resource_config.default_download_folder,
            url=url,
            subdir=subdir,
            ignore_exist_file=ignore_exist_file
        )

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
        user_response = await cls._get_json(url=url, params=params)
        user_info = WeiboUserInfo.model_validate(user_response)

        if user_info.ok != 1:
            raise WebSourceException(404, f'Query user(uid={uid}) data failed, {user_info.data}')

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
        cards_response = await cls._get_json(url=url, params=params)
        cards = WeiboCards.model_validate(cards_response)

        if cards.ok != 1:
            raise WebSourceException(404, f'Query user(uid={uid}) weibo cards failed, {cards.data}')

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
        extend_response = await cls._get_json(url=url, params=params)
        extend = WeiboExtend.model_validate(extend_response)

        if extend.ok != 1 or extend.data.ok != 1:
            raise WebSourceException(404, f'Query weibo(mid={mid}) extend content failed, {extend}')

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
        realtime_hot_response = await cls._get_json(url=url, params=params)
        realtime_hot = WeiboRealtimeHot.model_validate(realtime_hot_response)

        if realtime_hot.ok != 1:
            raise WebSourceException(404, f'Query realtime hot failed, {realtime_hot.data}')

        return realtime_hot.data.cards


__all__ = [
    'Weibo',
]
