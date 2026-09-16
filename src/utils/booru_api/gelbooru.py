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
from typing import TYPE_CHECKING, Any, Literal

from src.exception import WebSourceException
from src.utils import BaseCommonAPI
from .config import booru_api_config
from .models.gelbooru import CommentsData, Post, PostsData, TagsData, UsersData

if TYPE_CHECKING:
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes, QueryTypes


class BaseGelbooruAPI(BaseCommonAPI, abc.ABC):
    """Gelbooru API 基类, 文档见 https://gelbooru.com/index.php?page=help&topic=dapi"""

    # 类级为 .env 配置默认值, 实例凭据经 __init__ 遮蔽, 避免既往写类属性导致的全局污染
    _user_id: str | None = None
    _api_key: str | None = None

    def __init__(self, *, user_id: str | None = None, api_key: str | None = None):
        if (user_id is not None) and (api_key is not None):
            self._user_id = user_id
            self._api_key = api_key

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'omega-miya/2.0 (user omega-miya)'}

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @property
    def _auth_params(self) -> dict[str, str]:
        if self._user_id is None or self._api_key is None:
            return {}

        return {'api_key': self._api_key, 'user_id': self._user_id}

    async def get_resource_as_json(
            self,
            url: str,
            params: dict[str, Any] | None = None,
    ) -> Any:
        """使用 GET 方法请求 API, 返回 json 内容"""
        # 鉴权参数后置合并, 避免原地修改调用方传入的 params
        merged_params = {**(params if isinstance(params, dict) else {}), **self._auth_params}

        result = await self._get_resource_as_json(url, merged_params)

        # dapi 在搜索失败等场景返回 {"success": false, "message": "..."} 形式的错误响应 (此时上游 HTTP 状态为 200)
        if isinstance(result, dict) and str(result.get('success')).lower() == 'false':
            raise WebSourceException(
                200, f'Gelbooru API request failed (upstream HTTP 200 with success=false), {result.get('message')}'
            )

        return result

    async def get_resource_as_bytes(
            self,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: int = 30,
    ) -> bytes:
        return await self._get_resource_as_bytes(url, params, timeout=timeout)

    async def get_resource_as_text(
            self,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: int = 10,
    ) -> str:
        return await self._get_resource_as_text(url, params, timeout=timeout)

    @staticmethod
    def _convert_page_to_pid(page: int) -> int:
        """将 1 基页码转换为 dapi 的 0 基 pid 参数"""
        return page - 1 if page > 0 else 0

    """Posts API"""

    async def posts_index(
            self,
            *,
            limit: int | None = None,
            page: int | None = None,
            tags: str | None = None,
            cid: int | None = None,
            id_: int | None = None,
    ) -> PostsData:
        """Show posts index

        :param limit: 单页数量上限, 硬上限 100
        :param page: 1 基页码, 内部转换为 dapi 的 0 基 pid
        :param tags: The tags to search for.
        :param cid: Change ID of the post.
        :param id_: The post id.
        """
        index_url = f'{self._get_root_url()}/index.php'
        params = {'page': 'dapi', 's': 'post', 'q': 'index', 'json': '1'}

        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'pid': str(self._convert_page_to_pid(page))})
        if tags is not None:
            params.update({'tags': tags})
        if cid is not None:
            params.update({'cid': str(cid)})
        if id_ is not None:
            params.update({'id': str(id_)})

        return PostsData.model_validate(await self.get_resource_as_json(url=index_url, params=params))

    async def post_show(self, id_: int) -> Post:
        """Show post data, 经 posts_index(id_=) 查询取首条"""
        posts = await self.posts_index(id_=id_)
        if not posts.post:
            raise WebSourceException(404, f'Post(id={id_}) Not Found')
        return posts.post[0]

    async def posts_index_deleted(self, last_id: int | None = None) -> PostsData:
        """[Deactivated]Show deleted posts index

        Note: 端点对 JSON 客户端不可用, 仅返回 XML（上游缺陷, 2026-09 实测）;
        客户端已禁用该端点, 调用直接抛出异常且不发起请求

        :param last_id: 返回该数值之上的全部记录
        """
        # index_url = f'{self._get_root_url()}/index.php'
        # params = {'page': 'dapi', 's': 'post', 'q': 'index', 'json': '1', 'deleted': 'show'}
        #
        # if last_id is not None:
        #     params.update({'last_id': str(last_id)})
        #
        # return PostsData.model_validate(await self.get_resource_as_json(url=index_url, params=params))

        raise WebSourceException(
            501,
            'posts_index_deleted: upstream endpoint deactivated, 端点对 JSON 客户端不可用(仅返回 XML)',
        )

    """Tag API"""

    async def tags_index(
            self,
            *,
            limit: int | None = None,
            id_: int | None = None,
            after_id: int | None = None,
            name: str | None = None,
            names: str | None = None,
            name_pattern: str | None = None,
            order: Literal['ASC', 'DESC'] | None = None,
            orderby: Literal['date', 'count', 'name'] | None = None,
    ) -> TagsData:
        """Show tags index"""
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

        return TagsData.model_validate(await self.get_resource_as_json(url=index_url, params=params))

    """Users API"""

    async def users_index(
            self,
            *,
            limit: int | None = None,
            page: int | None = None,
            name: str | None = None,
            name_pattern: str | None = None,
    ) -> UsersData:
        """Show users index, page 为 1 基页码"""
        index_url = f'{self._get_root_url()}/index.php'
        params = {'page': 'dapi', 's': 'user', 'q': 'index', 'json': '1'}

        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'pid': str(self._convert_page_to_pid(page))})
        if name is not None:
            params.update({'name': name})
        if name_pattern is not None:
            params.update({'name_pattern': name_pattern})

        return UsersData.model_validate(await self.get_resource_as_json(url=index_url, params=params))

    """Comments API"""

    async def comments_index(
            self,
            *,
            post_id: int | None = None,
    ) -> CommentsData:
        """[Deactivated]Show comments index

        Note: 端点已被上游停用, 返回纯文本 Disabled due to abuse.（2026-09 实测）;
        客户端已禁用该端点, 调用直接抛出异常且不发起请求
        """
        # index_url = f'{self._get_root_url()}/index.php'
        # params = {'page': 'dapi', 's': 'comment', 'q': 'index', 'json': '1'}
        #
        # if post_id is not None:
        #     params.update({'post_id': str(post_id)})
        #
        # return CommentsData.model_validate(await self.get_resource_as_json(url=index_url, params=params))

        raise WebSourceException(
            501,
            'comments_index: upstream endpoint deactivated, 端点已被上游停用(返回纯文本 Disabled due to abuse.)',
        )


class GelbooruAPI(BaseGelbooruAPI):
    """https://gelbooru.com 主站 API"""

    _user_id: str | None = booru_api_config.gelbooru_user_id
    _api_key: str | None = booru_api_config.gelbooru_api_key

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://gelbooru.com'


__all__ = [
    'BaseGelbooruAPI',
    'GelbooruAPI',
]
