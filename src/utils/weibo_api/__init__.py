"""
@Author         : Ailitonia
@Date           : 2023/2/3 23:07
@FileName       : weibo_api
@Project        : nonebot2_miya
@Description    : 微博 Api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Optional

from src.resource import TemporaryResource
from src.service import OmegaRequests

from .config import weibo_resource_config
from .exception import WeiboApiError, WeiboNetworkError
from .helper import parse_weibo_card_from_status_page
from .model import (
    WeiboCard,
    WeiboCards,
    WeiboCardStatus,
    WeiboExtend,
    WeiboRealtimeHotCard,
    WeiboRealtimeHot,
    WeiboUserBase,
    WeiboUserInfo
)


class Weibo(object):
    """微博, 使用手机端网页 api"""

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    async def request_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None
    ) -> Any:
        """请求 api 并返回 json 数据"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({
                'origin': 'https://m.weibo.cn/',
                'referer': 'https://m.weibo.cn/'
            })

        requests = OmegaRequests(timeout=10, headers=headers)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise WeiboNetworkError(f'{response.request}, status code {response.status_code}')

        return OmegaRequests.parse_content_json(response)

    @classmethod
    async def request_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 30
    ) -> str | bytes | None:
        """请求原始资源内容"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({
                'origin': 'https://m.weibo.cn/',
                'referer': 'https://m.weibo.cn/'
            })

        requests = OmegaRequests(timeout=timeout, headers=headers)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise WeiboNetworkError(f'{response.request}, status code {response.status_code}')

        return response.content

    @classmethod
    async def download_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 60
    ) -> TemporaryResource:
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({
                'origin': 'https://m.weibo.cn/',
                'referer': 'https://m.weibo.cn/'
            })
        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        file = weibo_resource_config.default_download_folder(original_file_name)
        requests = OmegaRequests(timeout=timeout, headers=headers)

        return await requests.download(url=url, file=file, params=params)

    @classmethod
    async def query_user_data(cls, uid: int | str) -> WeiboUserBase:
        """获取用户信息"""
        url = 'https://m.weibo.cn/api/container/getIndex'
        containerid = f'100505{uid}'
        params = {
            'type': 'uid',
            'value': str(uid),
            'containerid': containerid,
        }
        user_response = await cls.request_json(url=url, params=params)
        user_info = WeiboUserInfo.parse_obj(user_response)

        if user_info.ok != 1:
            raise WeiboApiError(f'Query user(uid={uid}) data failed, {user_info.data}')

        return user_info.data.userInfo

    @classmethod
    async def query_user_weibo_cards(cls, uid: int | str, since_id: int | str | None = None) -> list[WeiboCard]:
        """获取用户微博

        :param uid: 用户 uid
        :param since_id: 获取的起始 since_id
        :return: WeiboCards
        """
        url = 'https://m.weibo.cn/api/container/getIndex'
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
        cards_response = await cls.request_json(url=url, params=params)
        cards = WeiboCards.parse_obj(cards_response)

        if cards.ok != 1:
            raise WeiboApiError(f'Query user(uid={uid}) weibo cards failed, {cards.data}')

        return cards.data.cards

    @classmethod
    async def query_weibo_card(cls, mid: int | str) -> WeiboCardStatus:
        """获取单条微博"""
        url = f'https://m.weibo.cn/status/{mid}'
        card_response = await cls.request_resource(url=url)

        return WeiboCardStatus.parse_obj(parse_weibo_card_from_status_page(card_response))

    @classmethod
    async def query_weibo_extend_text(cls, mid: int | str) -> str:
        """获取微博展开全文"""
        url = f'https://m.weibo.cn/statuses/extend'
        params = {
            'id': str(mid)
        }
        extend_response = await cls.request_json(url=url, params=params)
        extend = WeiboExtend.parse_obj(extend_response)

        if extend.ok != 1 or extend.data.ok != 1:
            raise WeiboApiError(f'Query weibo(mid={mid}) extend content failed, {extend}')

        return extend.data.longTextContent

    @classmethod
    async def query_realtime_hot(cls) -> list[WeiboRealtimeHotCard]:
        """获取微博热搜"""
        url = 'https://m.weibo.cn/api/container/getIndex'
        containerid = '106003type=25&t=3&disable_hot=1&filter_type=realtimehot'
        params = {
            'type': 'uid',
            'containerid': containerid,
        }
        realtime_hot_response = await cls.request_json(url=url, params=params)
        realtime_hot = WeiboRealtimeHot.parse_obj(realtime_hot_response)

        if realtime_hot.ok != 1:
            raise WeiboApiError(f'Query realtime hot failed, {realtime_hot.data}')

        return realtime_hot.data.cards


__all__ = [
    'Weibo'
]
