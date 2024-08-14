"""
@Author         : Ailitonia
@Date           : 2024/8/13 下午9:58
@FileName       : gelbooru
@Project        : nonebot2_miya
@Description    : Gelbooru API (Gelbooru Beta 0.2.5) (Read requests only)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import TYPE_CHECKING, Any, Literal, Optional

from src.utils.common_api import BaseCommonAPI
from .models.gelbooru import PostsData, TagsData, UsersData, CommentsData

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes, HeaderTypes, QueryTypes


class BaseGelbooruAPI(BaseCommonAPI, abc.ABC):
    """Gelbooru API 基类, 文档见 https://gelbooru.com/index.php?page=help&topic=dapi"""

    def __init__(self, *, user_id: Optional[str] = None, api_key: Optional[str] = None):
        self.__user_id = user_id
        self.__api_key = api_key

    @property
    def _auth_params(self) -> dict[str, str]:
        if self.__user_id is None or self.__api_key is None:
            return {}

        return {'api_key': self.__api_key, 'user_id': self.__user_id}

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> "HeaderTypes":
        return {}

    @classmethod
    def _get_default_cookies(cls) -> "CookieTypes":
        return None

    async def get_json(
            self,
            url: str,
            params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """使用 GET 方法请求 API, 返回 json 内容"""
        if isinstance(params, dict):
            params.update(self._auth_params)
        else:
            params = self._auth_params

        return await self._get_json(url, params)

    async def get_resource_as_bytes(
            self,
            url: str,
            params: "QueryTypes" = None,
            *,
            timeout: int = 30,
    ) -> bytes:
        return await self._get_resource_as_bytes(url, params, timeout=timeout)

    async def get_resource_as_text(
            self,
            url: str,
            params: "QueryTypes" = None,
            *,
            timeout: int = 10,
    ) -> str:
        return await self._get_resource_as_text(url, params, timeout=timeout)

    """Posts API"""

    async def posts_index(
            self,
            *,
            limit: Optional[int] = None,
            page: Optional[int] = None,
            tags: Optional[str] = None,
            cid: Optional[int] = None,
            id_: Optional[int] = None,
    ) -> PostsData:
        index_url = f'{self._get_root_url()}/index.php'
        params = {'page': 'dapi', 's': 'post', 'q': 'index', 'json': '1'}

        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'pid': str(page)})
        if tags is not None:
            params.update({'tags': tags})
        if cid is not None:
            params.update({'cid': str(cid)})
        if id_ is not None:
            params.update({'id': str(id_)})

        return PostsData.model_validate(await self.get_json(url=index_url, params=params))

    async def post_show(self, id_: int) -> PostsData:
        return await self.posts_index(id_=id_)

    """Tag API"""

    async def tags_index(
            self,
            limit: Optional[int] = None,
            id_: Optional[int] = None,
            after_id: Optional[int] = None,
            name: Optional[str] = None,
            names: Optional[str] = None,
            name_pattern: Optional[str] = None,
            order: Optional[Literal['ASC', 'DESC']] = None,
            orderby: Optional[Literal['date', 'count', 'name']] = None,
    ) -> TagsData:
        index_url = f'{self._get_root_url()}/index.php'
        params = {'page': 'dapi', 's': 'tag', 'q': 'index', 'json': '1'}

        if limit is not None:
            params.update({'limit': str(limit)})
        if id_ is not None:
            params.update({'id': str(id_)})
        if after_id is not None:
            params.update({'after_id': str(after_id)})
        if name is not None:
            params.update({'name': name})
        if names is not None:
            params.update({'names': names})
        if name_pattern is not None:
            params.update({'name_pattern': name_pattern})
        if order is not None:
            params.update({'order': order})
        if orderby is not None:
            params.update({'orderby': orderby})

        return TagsData.model_validate(await self.get_json(url=index_url, params=params))

    """Users API"""

    async def users_index(
            self,
            limit: Optional[int] = None,
            page: Optional[int] = None,
            name: Optional[str] = None,
            name_pattern: Optional[str] = None,
    ) -> UsersData:
        index_url = f'{self._get_root_url()}/index.php'
        params = {'page': 'dapi', 's': 'user', 'q': 'index', 'json': '1'}

        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'pid': str(page)})
        if name is not None:
            params.update({'name': name})
        if name_pattern is not None:
            params.update({'name_pattern': name_pattern})

        return UsersData.model_validate(await self.get_json(url=index_url, params=params))

    """Comments API"""

    async def comments_index(
            self,
            post_id: Optional[int] = None,
    ) -> CommentsData:
        index_url = f'{self._get_root_url()}/index.php'
        params = {'page': 'dapi', 's': 'comment', 'q': 'index', 'json': '1'}

        if post_id is not None:
            params.update({'post_id': str(post_id)})

        return CommentsData.model_validate(await self.get_json(url=index_url, params=params))


class GelbooruAPI(BaseGelbooruAPI):
    """https://gelbooru.com 主站 API"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://gelbooru.com'


__all__ = [
    'GelbooruAPI',
]
