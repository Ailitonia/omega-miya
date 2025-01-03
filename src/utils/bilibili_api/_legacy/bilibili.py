"""
@Author         : Ailitonia
@Date           : 2022/04/11 20:25
@FileName       : bilibili.py
@Project        : nonebot2_miya 
@Description    : Bilibili
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import warnings
from collections.abc import Sequence
from typing import Literal
from urllib.parse import unquote

from lxml import etree
from nonebot.utils import run_sync

from src.compat import parse_json_as
from .api_base import BilibiliCommon
from .model import (
    BilibiliDynamicModel,
    BilibiliLiveRoomModel,
    BilibiliUserDynamicModel,
    BilibiliUserModel,
    BilibiliUsersLiveRoomModel,
)
from .model.search import BaseBilibiliSearchingModel, UserSearchingModel


class Bilibili(BilibiliCommon):
    """Bilibili 主站方法"""

    @classmethod
    async def _global_search(
            cls,
            keyword: str,
            search_type: str,
            page_size: int,
            *,
            page: int = 1,
            order: str = '',
            duration: str = '',
            order_sort: int | str = '',
            user_type: int | str = '',
            category_id: int | str = '',
            dynamic_offset: int | str = '',
            context: str = '',
            from_source: str = '',
            from_spmid: str = '333.337',
            platform: str = 'pc',
            highlight: int = 1,
            single_column: int = 0,
            preload: str = 'true',
            com2co: str = 'true',
            refresh_: str = 'true',
            extra_: str = ''
    ) -> BaseBilibiliSearchingModel:
        """Bilibili 通用搜索接口

        :param keyword: 搜索关键词
        :param search_type: 搜索类型
        :param page_size: 搜索页结果数量
        :param page: 搜索页码
        :param order: 排序类型, 不同 search_type 有不同值
        :param duration: 看参数名是搜索范围, 基本都是空值
        :param order_sort: 排序时是否倒序, 只有在搜索结果支持排序时才有用
        :param user_type: 用户类型, 只有在 search_type 是 bili_user 时有用
        :param category_id: 专栏分区, 只有在 search_type 是 article 时有用,
        :param dynamic_offset: 看参数名是动态位移, 不知道啥用, 但基本都是空值
        :param context: 固定参数, 不要动
        :param from_source: 固定参数, 不要动
        :param from_spmid: 固定参数, 不要动
        :param platform: 固定参数, 不要动
        :param highlight: 固定参数, 不要动
        :param single_column: 固定参数, 不要动
        :param preload: 固定参数, 不要动
        :param com2co: 固定参数, 不要动
        :param refresh_: 固定参数, 不要动
        :param extra_: 固定参数, 不要动
        """
        params = {
            '__refresh__': refresh_,
            '_extra': extra_,
            'context': context,
            'page': page,
            'page_size': page_size,
            'order': order,
            'duration': duration,
            'from_source': from_source,
            'from_spmid': from_spmid,
            'platform': platform,
            'highlight': highlight,
            'single_column': single_column,
            'keyword': keyword,
            'category_id': category_id,
            'search_type': search_type,
            'order_sort': order_sort,
            'user_type': user_type,
            'dynamic_offset': dynamic_offset,
            'preload': preload,
            'com2co': com2co,
        }
        search_url: str = 'https://api.bilibili.com/x/web-interface/search/type'
        searching_data = await cls._get_json(url=search_url, params=params)
        return BaseBilibiliSearchingModel.model_validate(searching_data)


class BilibiliUser(Bilibili):
    warnings.warn(
        'The bilibili user dynamic old API seems to be deprecated and will be removed in the near future, '
        'future version should change to new API instead.',
        PendingDeprecationWarning,
        stacklevel=2,
    )

    def __init__(self, uid: int):
        self.uid = uid
        self.space_url = f'https://space.bilibili.com/{uid}'

        # 实例缓存
        self.user_model: BilibiliUserModel | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(uid={self.uid})'

    @classmethod
    async def search(
            cls,
            user_name: str,
            *,
            order: Literal['fans', 'level', ''] = '',
            order_sort: int = 0
    ) -> UserSearchingModel:
        """搜索用户

        :param user_name: 搜索用户名
        :param order: 排序模式, fans: 粉丝数, level: 等级, null: 默认排序
        :param order_sort: 排序方式, 0: 由高到低, 1: 由低到高
        """
        searching_result = await cls._global_search(
            search_type='bili_user', page_size=36, keyword=user_name, order=order, order_sort=order_sort
        )
        return UserSearchingModel.model_validate(searching_result.model_dump())

    @property
    def mid(self) -> str:
        return str(self.uid)

    @staticmethod
    @run_sync
    def _parse_user_space_w_webid(content: str) -> dict[str, str]:
        """解析用户页面 __RENDER_DATA__ 内容"""
        html = etree.HTML(content)
        render_data = html.xpath('/html/head/script[@id="__RENDER_DATA__"]').pop(0).text
        return parse_json_as(dict[str, str], unquote(render_data))

    @classmethod
    async def _query_user_space_w_webid(cls, mid: int | str) -> dict[str, str]:
        """获取并解析用户页面 __RENDER_DATA__ 内容"""
        user_space_url = f'https://space.bilibili.com/{mid}'
        user_space_page = await cls._get_resource_as_text(url=user_space_url)
        return await cls._parse_user_space_w_webid(content=user_space_page)

    async def query_user_data(self) -> BilibiliUserModel:
        """获取并初始化用户对应 BilibiliUserModel"""
        api_url = 'https://api.bilibili.com/x/space/wbi/acc/info'

        if not isinstance(self.user_model, BilibiliUserModel):
            render_data = await self._query_user_space_w_webid(mid=self.mid)
            params = await self.update_wbi_params({'mid': self.mid, 'w_webid': render_data['access_id']})
            user_data = await self._get_json(url=api_url, params=params)
            self.user_model = BilibiliUserModel.model_validate(user_data)

        if not isinstance(self.user_model, BilibiliUserModel):
            raise TypeError('Query user model failed')
        return self.user_model

    async def query_dynamics(
            self,
            *,
            offset_dynamic_id: int = 0,
            need_top: int = 0
    ) -> BilibiliUserDynamicModel:
        """获取用户最近发布的动态

        :param offset_dynamic_id: 获取动态起始位置
        :param need_top: 是否获取置顶动态
        """
        api_url = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history'  # TODO: Update to New API
        headers = self._get_default_headers()
        headers.update({
            'origin': 'https://t.bilibili.com',
            'referer': 'https://t.bilibili.com/'
        })
        params = {'host_uid': self.uid, 'offset_dynamic_id': offset_dynamic_id, 'need_top': need_top, 'platform': 'web'}

        # 这里是风控玄学, 虽然加不加这个好像也没啥影响, 但请求数量多了好像是有点用, 就是不知道有多大用
        params = await self.update_wbi_params(params)

        data = await self._get_json(url=api_url, params=params, headers=headers)
        return BilibiliUserDynamicModel.model_validate(data)


class BilibiliDynamic(BilibiliCommon):
    """Bilibili 动态"""

    warnings.warn(
        'The bilibili user dynamic old API seems to be deprecated and will be removed in the near future, '
        'future version should change to new API instead.',
        PendingDeprecationWarning,
        stacklevel=2,
    )

    def __init__(self, dynamic_id: int):
        self.dynamic_id = dynamic_id
        self.dynamic_url = f'{self.get_dynamic_root_url()}/{dynamic_id}'

        # 实例缓存
        self.dynamic_model: BilibiliDynamicModel | None = None

    @classmethod
    def get_dynamic_root_url(cls) -> str:
        return 'https://t.bilibili.com'

    @property
    def dy_id(self) -> str:
        return str(self.dynamic_id)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(dynamic_id={self.dynamic_id})'

    async def query_dynamic_data(self) -> BilibiliDynamicModel:
        """获取并初始化动态对应 BilibiliDynamicModel"""
        api_url = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail'  # TODO: Update to New API

        if not isinstance(self.dynamic_model, BilibiliDynamicModel):
            headers = self._get_default_headers()
            headers.update({
                'origin': 'https://t.bilibili.com',
                'referer': 'https://t.bilibili.com/'
            })
            params = {'dynamic_id': self.dy_id}
            dynamic_data = await self._get_json(url=api_url, params=params, headers=headers)
            self.dynamic_model = BilibiliDynamicModel.model_validate(dynamic_data)

        if not isinstance(self.dynamic_model, BilibiliDynamicModel):
            raise TypeError('Query dynamic model failed')
        return self.dynamic_model


class BilibiliLiveRoom(BilibiliCommon):
    """Bilibili 直播间"""

    def __init__(self, room_id: int):
        self.room_id = room_id
        self.live_room_url = f'{self.get_live_root_url()}/{room_id}'

        # 实例缓存
        self.live_room_model: BilibiliLiveRoomModel | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(room_id={self.room_id})'

    @property
    def rid(self) -> str:
        return str(self.room_id)

    @classmethod
    def get_live_root_url(cls) -> str:
        return 'https://live.bilibili.com'

    @classmethod
    async def query_live_room_by_uid_list(cls, uid_list: Sequence[int | str]) -> BilibiliUsersLiveRoomModel:
        """根据用户 uid 列表获取这些用户的直播间信息(这个 api 没有认证方法，请不要在标头中添加 cookie)"""
        api_url = 'https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids'
        payload = {'uids': uid_list}

        # 该接口无需鉴权
        live_room_data = await cls._post_json(url=api_url, json=payload, no_headers=True, no_cookies=True)
        return BilibiliUsersLiveRoomModel.model_validate(live_room_data)

    async def query_live_room_data(self) -> BilibiliLiveRoomModel:
        """获取并初始化直播间对应 Model"""
        api_url = 'https://api.live.bilibili.com/room/v1/Room/get_info'

        if not isinstance(self.live_room_model, BilibiliLiveRoomModel):
            params = {'id': self.rid}
            live_room_data = await self._get_json(url=api_url, params=params)
            self.live_room_model = BilibiliLiveRoomModel.model_validate(live_room_data)

        if not isinstance(self.live_room_model, BilibiliLiveRoomModel):
            raise TypeError('Query live room model failed')
        return self.live_room_model

    async def query_live_room_user_data(self) -> BilibiliUserModel:
        """获取这个直播间对应的用户信息"""
        live_room_model = await self.query_live_room_data()
        return await BilibiliUser(uid=live_room_model.uid).query_user_data()


__all__ = [
    'BilibiliUser',
    'BilibiliDynamic',
    'BilibiliLiveRoom',
]
