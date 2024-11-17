"""
@Author         : Ailitonia
@Date           : 2024/8/13 11:17:23
@FileName       : moebooru.py
@Project        : omega-miya
@Description    : Moebooru API (Moebooru 1.13.0-1.13.0+update.3, 兼容 Danbooru 1.13) (Read requests only)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import TYPE_CHECKING, Any, Literal

from src.compat import parse_obj_as
from src.utils import BaseCommonAPI
from .models.moebooru import (
    Artist,
    Comment,
    Forum,
    Note,
    Pool,
    Post,
    SimilarPosts,
    Tag,
    User,
    Wiki,
)

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes, HeaderTypes, QueryTypes


class BaseMoebooruAPI(BaseCommonAPI, abc.ABC):
    """Moebooru API 基类

    文档参考 https://github.com/moebooru/moebooru/blob/master/app/views/help/api.en.html.erb
    端点参考 https://github.com/moebooru/moebooru/blob/master/config/routes.rb
    注意 Moebooru 分级不同, 端点 https://github.com/moebooru/moebooru/blob/master/app/views/help/ratings.en.html.erb
        rating:s - Safe
        rating:q - Questionable
        rating:e - Explicit
    """

    def __init__(
            self,
            *,
            login_name: str | None = None,
            password_hash: str | None = None,
            legacy_endpoint: bool = False,
    ) -> None:
        """初始化鉴权信息

        :param login_name: Your login name.
        :param password_hash: Your SHA1 hashed password.
            Simply hashing your plain password will NOT work since Danbooru salts its passwords.
            The actual string that is hashed is "{site_password_salt}--your-password--".
            The "site_password_salt" can be found in "Help:API" page.
        :param legacy_endpoint: Using legacy endpoint for compatibility, but maybe been removed.
        """
        self.__login = login_name
        self.__password_hash = password_hash
        self.__legacy_endpoint = legacy_endpoint

    @property
    def _auth_params(self) -> dict[str, str]:
        if self.__login is None or self.__password_hash is None:
            return {}

        return {'login': self.__login, 'password_hash': self.__password_hash}

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {}

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    async def get_json(
            self,
            url: str,
            params: dict[str, Any] | None = None,
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

    """Posts API"""

    async def posts_index(
            self,
            *,
            limit: int | None = None,
            page: int | None = None,
            tags: str | None = None,
    ) -> list[Post]:
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/post/index.json'
        else:
            index_url = f'{self._get_root_url()}/post.json'

        params = {}
        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'page': str(page)})
        if tags is not None:
            params.update({'tags': tags})
        params = None if not params else params

        return parse_obj_as(list[Post], await self.get_json(url=index_url, params=params))

    async def posts_show_popular_by_day(self) -> list[Post]:
        index_url = f'{self._get_root_url()}/post/popular_by_day.json'
        return parse_obj_as(list[Post], await self.get_json(url=index_url))

    async def posts_show_popular_by_month(self) -> list[Post]:
        index_url = f'{self._get_root_url()}/post/popular_by_month.json'
        return parse_obj_as(list[Post], await self.get_json(url=index_url))

    async def posts_show_popular_by_week(self) -> list[Post]:
        index_url = f'{self._get_root_url()}/post/popular_by_week.json'
        return parse_obj_as(list[Post], await self.get_json(url=index_url))

    async def posts_show_popular_recent(self) -> list[Post]:
        index_url = f'{self._get_root_url()}/post/popular_recent.json'
        return parse_obj_as(list[Post], await self.get_json(url=index_url))

    async def post_show(self, id_: int) -> Post:
        """获取 post 信息

        moebooru 没有直接提供根据 ID 获取 Post json 数据的 API, 需使用 `/post.json?tags=id:1234` 查询方法
        参考 https://github.com/moebooru/moebooru/issues/144
        """
        post_list = await self.posts_index(tags=f'id:{id_}')
        if not post_list:
            raise IndexError(f'Post(id={id_}) Not Found')
        return post_list[0]

    async def post_show_similar(self, id_: int) -> SimilarPosts:
        index_url = f'{self._get_root_url()}/post/similar/{id_}.json'
        return SimilarPosts.model_validate(await self.get_json(url=index_url))

    """Tags API"""

    async def tags_index(
            self,
            *,
            limit: int | None = None,
            page: int | None = None,
            order: Literal['date', 'count', 'name'] | None = None,
            id_: int | None = None,
            after_id: int | None = None,
            name: str | None = None,
            name_pattern: str | None = None,
    ) -> list[Tag]:
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/tag/index.json'
        else:
            index_url = f'{self._get_root_url()}/tag.json'

        params = {}
        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'page': str(page)})
        if order is not None:
            params.update({'order': order})
        if id_ is not None:
            params.update({'id': str(id_)})
        if after_id is not None:
            params.update({'after_id': str(after_id)})
        if name is not None:
            params.update({'name': name})
        if name_pattern is not None:
            params.update({'name_pattern': name_pattern})
        params = None if not params else params

        return parse_obj_as(list[Tag], await self.get_json(url=index_url, params=params))

    """Artists API"""

    async def artists_index(
            self,
            *,
            name: str | None = None,
            order: Literal['date', 'name'] | None = None,
            page: int | None = None,
    ) -> list[Artist]:
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/artist/index.json'
        else:
            index_url = f'{self._get_root_url()}/artist.json'

        params = {}
        if name is not None:
            params.update({'name': name})
        if order is not None:
            params.update({'order': order})
        if page is not None:
            params.update({'page': str(page)})
        params = None if not params else params

        return parse_obj_as(list[Artist], await self.get_json(url=index_url, params=params))

    """Comments API"""

    async def comment_show(self, id_: int) -> Comment:
        url = f'{self._get_root_url()}/comment/show.json/{id_}'
        # alternative_url = f'{self._get_root_url()}/comment/show/{id_}.json'

        return Comment.model_validate(await self.get_json(url=url))

    """Wiki API"""

    async def wikis_index(
            self,
            *,
            limit: int | None = None,
            page: int | None = None,
            order: Literal['title', 'date'] | None = None,
            query: str | None = None,
    ) -> list[Wiki]:
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/wiki/index.json'
        else:
            index_url = f'{self._get_root_url()}/wiki.json'

        params = {}
        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'page': str(page)})
        if order is not None:
            params.update({'order': order})
        if query is not None:
            params.update({'query': query})
        params = None if not params else params

        return parse_obj_as(list[Wiki], await self.get_json(url=index_url, params=params))

    """Notes API"""

    async def notes_search(self, query: str) -> list[Note]:
        """search notes by query keyword"""
        index_url = f'{self._get_root_url()}/note/search.json'
        params = {'query': query}

        return parse_obj_as(list[Note], await self.get_json(url=index_url, params=params))

    async def note_post_show(self, post_id: int) -> list[Note]:
        """show post's notes"""
        if self.__legacy_endpoint:
            url = f'{self._get_root_url()}/note/index.json'
        else:
            url = f'{self._get_root_url()}/note.json'

        params = {'post_id': post_id}

        return parse_obj_as(list[Note], await self.get_json(url=url, params=params))

    """Users API"""

    async def users_index(
            self,
            *,
            id_: int | None = None,
            name: str | None = None,
    ) -> list[User]:
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/user/index.json'
        else:
            index_url = f'{self._get_root_url()}/user.json'

        params = {}
        if id_ is not None:
            params.update({'id': str(id_)})
        if name is not None:
            params.update({'name': name})
        params = None if not params else params

        return parse_obj_as(list[User], await self.get_json(url=index_url, params=params))

    """Forum API"""

    async def forums_index(
            self,
            *,
            parent_id: int | None = None,
    ) -> list[Forum]:
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/forum/index.json'
        else:
            index_url = f'{self._get_root_url()}/forum.json'

        params = {'parent_id': str(parent_id)} if parent_id is not None else None

        return parse_obj_as(list[Forum], await self.get_json(url=index_url, params=params))

    """Pools API"""

    async def pools_index(
            self,
            *,
            query: str | None = None,
            page: int | None = None,
    ) -> list[Pool]:
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/pool/index.json'
        else:
            index_url = f'{self._get_root_url()}/pool.json'

        params = {}
        if query is not None:
            params.update({'query': query})
        if page is not None:
            params.update({'page': str(page)})
        params = None if not params else params

        return parse_obj_as(list[Pool], await self.get_json(url=index_url, params=params))

    async def pool_posts_show(self, pool_id: int, *, page: int | None = None) -> Pool:
        url = f'{self._get_root_url()}/pool/show.json'
        # alternative_url = f'{self._get_root_url()}/pool/show/{pool_id}.json'

        params = {'id': str(pool_id)}
        if page is not None:
            params.update({'page': str(page)})

        return Pool.model_validate(await self.get_json(url=url, params=params))


class BehoimiAPI(BaseMoebooruAPI):
    """http://behoimi.org 主站 API"""

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {
            'origin': f'{cls._get_root_url()}/',
            'referer': f'{cls._get_root_url()}/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'
        }

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'http://behoimi.org'


class KonachanAPI(BaseMoebooruAPI):
    """https://konachan.com 主站 API, 主站有 Cloudflare 盾, 建议直接使用全年龄站接口"""

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return True

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://konachan.com'


class KonachanSafeAPI(BaseMoebooruAPI):
    """https://konachan.net 全年龄站 API, 与主站 API 数据相同, 只是网站页面不显示 rating:E 的作品"""

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://konachan.net'


class YandereAPI(BaseMoebooruAPI):
    """https://yande.re 主站 API"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://yande.re'


__all__ = [
    'BaseMoebooruAPI',
    'BehoimiAPI',
    'KonachanAPI',
    'KonachanSafeAPI',
    'YandereAPI',
]
