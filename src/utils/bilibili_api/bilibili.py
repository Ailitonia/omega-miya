"""
@Author         : Ailitonia
@Date           : 2022/04/11 20:25
@FileName       : bilibili.py
@Project        : nonebot2_miya 
@Description    : Bilibili
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, Optional, Any

from src.resource import TemporaryResource
from src.service.omega_requests import OmegaRequests

from .config import bilibili_config, bilibili_resource_config
from .exception import BilibiliNetworkError
from .model.search import BaseBilibiliSearchingModel, UserSearchingModel
from .model import (BilibiliUserModel, BilibiliUserDynamicModel, BilibiliDynamicModel,
                    BilibiliLiveRoomModel, BilibiliUsersLiveRoomModel)


class Bilibili(object):
    """Bilibili 基类"""
    _root_url: str = 'https://www.bilibili.com'

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

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
                'origin': 'https://www.bilibili.com',
                'referer': 'https://www.bilibili.com/'
            })

        requests = OmegaRequests(timeout=10, headers=headers, cookies=bilibili_config.bili_cookie)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise BilibiliNetworkError(f'{response.request}, status code {response.status_code}')

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
                'origin': 'https://www.bilibili.com',
                'referer': 'https://www.bilibili.com/'
            })

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=bilibili_config.bili_cookie)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise BilibiliNetworkError(f'{response.request}, status code {response.status_code}')

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
                'origin': 'https://www.bilibili.com',
                'referer': 'https://www.bilibili.com/'
            })

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        file = bilibili_resource_config.default_download_folder(original_file_name)
        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=bilibili_config.bili_cookie)

        return await requests.download(url=url, file=file, params=params)

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
        searching_data = await cls.request_json(url=search_url, params=params)
        return BaseBilibiliSearchingModel.parse_obj(searching_data)


class BilibiliUser(Bilibili):
    _data_api_url = 'https://api.bilibili.com/x/space/acc/info'
    _dynamic_api_url = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history'

    def __init__(self, uid: int):
        self.uid = uid
        self.space_url = f'https://space.bilibili.com/{uid}'

        # 实例缓存
        self.user_model: Optional[BilibiliUserModel] = None

    def __repr__(self):
        return f'<{self.__class__.__name__}(uid={self.uid})>'

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
        return UserSearchingModel.parse_obj(searching_result)

    @property
    def mid(self) -> str:
        return str(self.uid)

    async def get_user_model(self) -> BilibiliUserModel:
        """获取并初始化用户对应 BilibiliUserModel"""
        if not isinstance(self.user_model, BilibiliUserModel):
            params = {'mid': self.mid}
            user_data = await self.request_json(url=self._data_api_url, params=params)
            self.user_model = BilibiliUserModel.parse_obj(user_data)

        assert isinstance(self.user_model, BilibiliUserModel), 'Query user model failed'
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
        headers = OmegaRequests.get_default_headers()
        headers.update({
            'origin': 'https://t.bilibili.com',
            'referer': 'https://t.bilibili.com/'
        })
        params = {'host_uid': self.uid, 'offset_dynamic_id': offset_dynamic_id, 'need_top': need_top, 'platform': 'web'}
        if bilibili_config.bili_cookie:
            params.update({'csrf': bilibili_config.bili_csrf, 'visitor_uid': bilibili_config.bili_uid})

        dynamics_data = await self.request_json(url=self._dynamic_api_url, params=params, headers=headers)
        return BilibiliUserDynamicModel.parse_obj(dynamics_data)


class BilibiliDynamic(Bilibili):
    """Bilibili 动态"""
    _dynamic_root_url = 'https://t.bilibili.com/'
    _dynamic_detail_api_url = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail'

    def __init__(self, dynamic_id: int):
        self.dynamic_id = dynamic_id
        self.dynamic_url = f'{self._dynamic_root_url}{dynamic_id}'

        # 实例缓存
        self.dynamic_model: Optional[BilibiliDynamicModel] = None

    @classmethod
    def get_dynamic_root_url(cls) -> str:
        return cls._dynamic_root_url

    @property
    def dy_id(self) -> str:
        return str(self.dynamic_id)

    def __repr__(self):
        return f'<{self.__class__.__name__}(dynamic_id={self.dynamic_id})>'

    async def get_dynamic_model(self) -> BilibiliDynamicModel:
        """获取并初始化动态对应 BilibiliDynamicModel"""
        if not isinstance(self.dynamic_model, BilibiliDynamicModel):
            headers = OmegaRequests.get_default_headers()
            headers.update({
                'origin': 'https://t.bilibili.com',
                'referer': 'https://t.bilibili.com/'
            })
            params = {'dynamic_id': self.dy_id}
            dynamic_data = await self.request_json(url=self._dynamic_detail_api_url, params=params, headers=headers)
            self.dynamic_model = BilibiliDynamicModel.parse_obj(dynamic_data)

        assert isinstance(self.dynamic_model, BilibiliDynamicModel), 'Query dynamic model failed'
        return self.dynamic_model


class BilibiliLiveRoom(Bilibili):
    """Bilibili 直播间"""
    _live_root_url = 'https://live.bilibili.com/'
    _live_api_url = 'https://api.live.bilibili.com/room/v1/Room/get_info'
    _live_by_uids_api_url = 'https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids'

    def __init__(self, room_id: int):
        self.room_id = room_id
        self.live_room_url = f'{self._live_root_url}{room_id}'

        # 实例缓存
        self.live_room_model: Optional[BilibiliLiveRoomModel] = None

    @property
    def rid(self) -> str:
        return str(self.room_id)

    @classmethod
    async def query_live_room_by_uid_list(cls, uid_list: list[int | str]) -> BilibiliUsersLiveRoomModel:
        """根据用户 uid 列表获取这些用户的直播间信息(这个 api 没有认证方法，请不要在标头中添加 cookie)"""
        payload = {'uids': uid_list}
        live_room_response = await OmegaRequests().post(url=cls._live_by_uids_api_url, json=payload)
        if live_room_response.status_code != 200:
            raise BilibiliNetworkError(f'{live_room_response.request}, status code {live_room_response.status_code}')

        return BilibiliUsersLiveRoomModel.parse_obj(OmegaRequests.parse_content_json(live_room_response))

    async def get_live_room_model(self) -> BilibiliLiveRoomModel:
        """获取并初始化直播间对应 Model"""
        if not isinstance(self.live_room_model, BilibiliLiveRoomModel):
            params = {'id': self.rid}
            live_room_data = await self.request_json(url=self._live_api_url, params=params)
            self.live_room_model = BilibiliLiveRoomModel.parse_obj(live_room_data)

        assert isinstance(self.live_room_model, BilibiliLiveRoomModel), 'Query live room model failed'
        return self.live_room_model

    async def get_live_room_user_model(self) -> BilibiliUserModel:
        """获取这个直播间对应的用户信息"""
        live_room_model = await self.get_live_room_model()
        return await BilibiliUser(uid=live_room_model.uid).get_user_model()


__all__ = [
    'BilibiliUser',
    'BilibiliDynamic',
    'BilibiliLiveRoom'
]
