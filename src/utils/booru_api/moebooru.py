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
from src.exception import WebSourceException
from src.utils import BaseCommonAPI
from .config import booru_api_config
from .models.moebooru import (
    Artist,
    Comment,
    FavoritedUsers,
    Forum,
    Note,
    NoteHistory,
    Pool,
    Post,
    SimilarPosts,
    Tag,
    TagsRelated,
    User,
    Wiki,
)

if TYPE_CHECKING:
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes, QueryTypes


class BaseMoebooruAPI(BaseCommonAPI, abc.ABC):
    """Moebooru API 基类

    文档参考 https://github.com/moebooru/moebooru/blob/master/app/views/help/api.en.html.erb
    端点参考 https://github.com/moebooru/moebooru/blob/master/config/routes.rb
    注意 Moebooru 分级不同, 端点 https://github.com/moebooru/moebooru/blob/master/app/views/help/ratings.en.html.erb
        rating:s - Safe
        rating:q - Questionable
        rating:e - Explicit
    """

    # 类级为 .env 配置默认值, 实例凭据经 __init__ 遮蔽, 避免既往写类属性导致的全局污染
    _login: str | None = None
    _password_hash: str | None = None

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
        self.__legacy_endpoint = legacy_endpoint
        if (login_name is not None) and (password_hash is not None):
            self._login = login_name
            self._password_hash = password_hash

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'omega-miya/2.0 (user omega-miya)'}

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @property
    def _auth_params(self) -> dict[str, str]:
        if self._login is None or self._password_hash is None:
            return {}

        return {'login': self._login, 'password_hash': self._password_hash}

    async def get_resource_as_json(
            self,
            url: str,
            params: dict[str, Any] | None = None,
    ) -> Any:
        """使用 GET 方法请求 API, 返回 json 内容"""
        # 鉴权参数后置合并, 避免原地修改调用方传入的 params
        merged_params = {**(params if isinstance(params, dict) else {}), **self._auth_params}

        return await self._get_resource_as_json(url, merged_params)

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
        """Show posts index

        :param limit: 单页数量上限, 文档记载硬上限 100
        :param page: 页码
        :param tags: 搜索标签, 支持站内全部标签组合与元标签
        """
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/post/index.json'
        else:
            index_url = f'{self._get_root_url()}/post.json'

        params: dict[str, Any] = {}
        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'page': str(page)})
        if tags is not None:
            params.update({'tags': tags})

        return parse_obj_as(list[Post], await self.get_resource_as_json(url=index_url, params=params or None))

    async def posts_show_popular_by_day(
            self,
            *,
            day: int | None = None,
            month: int | None = None,
            year: int | None = None,
    ) -> list[Post]:
        """Show popular posts by day, 可用日期参数指定日期"""
        index_url = f'{self._get_root_url()}/post/popular_by_day.json'

        params: dict[str, Any] = {}
        if day is not None:
            params.update({'day': str(day)})
        if month is not None:
            params.update({'month': str(month)})
        if year is not None:
            params.update({'year': str(year)})

        return parse_obj_as(list[Post], await self.get_resource_as_json(url=index_url, params=params or None))

    async def posts_show_popular_by_month(
            self,
            *,
            month: int | None = None,
            year: int | None = None,
    ) -> list[Post]:
        """Show popular posts by month, 可用日期参数指定月份"""
        index_url = f'{self._get_root_url()}/post/popular_by_month.json'

        params: dict[str, Any] = {}
        if month is not None:
            params.update({'month': str(month)})
        if year is not None:
            params.update({'year': str(year)})

        return parse_obj_as(list[Post], await self.get_resource_as_json(url=index_url, params=params or None))

    async def posts_show_popular_by_week(
            self,
            *,
            month: int | None = None,
            year: int | None = None,
    ) -> list[Post]:
        """Show popular posts by week, 可用日期参数指定周"""
        index_url = f'{self._get_root_url()}/post/popular_by_week.json'

        params: dict[str, Any] = {}
        if month is not None:
            params.update({'month': str(month)})
        if year is not None:
            params.update({'year': str(year)})

        return parse_obj_as(list[Post], await self.get_resource_as_json(url=index_url, params=params or None))

    async def posts_show_popular_recent(self) -> list[Post]:
        index_url = f'{self._get_root_url()}/post/popular_recent.json'
        return parse_obj_as(list[Post], await self.get_resource_as_json(url=index_url))

    async def post_show(self, id_: int) -> Post:
        """获取 post 信息

        moebooru 没有直接提供根据 ID 获取 Post json 数据的 API, 需使用 `/post.json?tags=id:1234` 查询方法
        参考 https://github.com/moebooru/moebooru/issues/144
        """
        post_list = await self.posts_index(tags=f'id:{id_}')
        if not post_list:
            raise WebSourceException(404, f'Post(id={id_}) Not Found')
        return post_list[0]

    async def post_show_similar(self, id_: int) -> SimilarPosts:
        """Show post's similar posts"""
        index_url = f'{self._get_root_url()}/post/similar/{id_}.json'
        return SimilarPosts.model_validate(await self.get_resource_as_json(url=index_url))

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
        """Show tags index"""
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/tag/index.json'
        else:
            index_url = f'{self._get_root_url()}/tag.json'

        params: dict[str, Any] = {}
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

        return parse_obj_as(list[Tag], await self.get_resource_as_json(url=index_url, params=params or None))

    async def tags_related(
            self,
            tags: str,
            *,
            type_: Literal['general', 'artist', 'copyright', 'character'] | None = None,
    ) -> TagsRelated:
        """Show related tags

        :param tags: The tag names to query.
        :param type_: Restrict results to this tag type.
        """
        index_url = f'{self._get_root_url()}/tag/related.json'

        params: dict[str, Any] = {'tags': tags}
        if type_ is not None:
            params.update({'type': type_})

        return TagsRelated.model_validate(await self.get_resource_as_json(url=index_url, params=params or None))

    """Artists API"""

    async def artists_index(
            self,
            *,
            name: str | None = None,
            order: Literal['date', 'name'] | None = None,
            page: int | None = None,
    ) -> list[Artist]:
        """Show artists index"""
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/artist/index.json'
        else:
            index_url = f'{self._get_root_url()}/artist.json'

        params: dict[str, Any] = {}
        if name is not None:
            params.update({'name': name})
        if order is not None:
            params.update({'order': order})
        if page is not None:
            params.update({'page': str(page)})

        return parse_obj_as(list[Artist], await self.get_resource_as_json(url=index_url, params=params or None))

    """Comments API"""

    async def comment_show(self, id_: int) -> Comment:
        """Show comment data"""
        url = f'{self._get_root_url()}/comment/show.json/{id_}'
        # alternative_url = f'{self._get_root_url()}/comment/show/{id_}.json'

        return Comment.model_validate(await self.get_resource_as_json(url=url))

    """Wiki API"""

    async def wikis_index(
            self,
            *,
            limit: int | None = None,
            page: int | None = None,
            order: Literal['title', 'date'] | None = None,
            query: str | None = None,
    ) -> list[Wiki]:
        """Show wikis index"""
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/wiki/index.json'
        else:
            index_url = f'{self._get_root_url()}/wiki.json'

        params: dict[str, Any] = {}
        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'page': str(page)})
        if order is not None:
            params.update({'order': order})
        if query is not None:
            params.update({'query': query})

        return parse_obj_as(list[Wiki], await self.get_resource_as_json(url=index_url, params=params or None))

    async def wiki_show(self, title: str, *, version: int | None = None) -> Wiki:
        """[Deactivated]Show wiki data by title, 标题必须精确匹配 (大小写与空白除外)

        Note: 端点上游不可用, /wiki/show 的 json/xml 格式均返回 406, 普通标题亦同（2026-09 双站点实测）;
        客户端已禁用该端点, 调用直接抛出异常且不发起请求, 可改经 wikis_index 查询

        :param title: The title of the wiki page to retrieve.
        :param version: The version of the page to retrieve.
        """
        # url = f'{self._get_root_url()}/wiki/show.json'
        #
        # params: dict[str, Any] = {'title': title}
        # if version is not None:
        #     params.update({'version': str(version)})
        #
        # return Wiki.model_validate(await self.get_resource_as_json(url=url, params=params))

        raise WebSourceException(
            501,
            'wiki_show: upstream endpoint deactivated, /wiki/show 的 json/xml 格式均返回 406, 端点上游不可用',
        )

    """Notes API"""

    async def notes_search(self, query: str) -> list[Note]:
        """search notes by query keyword"""
        index_url = f'{self._get_root_url()}/note/search.json'
        params = {'query': query}

        return parse_obj_as(list[Note], await self.get_resource_as_json(url=index_url, params=params or None))

    async def note_post_show(self, post_id: int) -> list[Note]:
        """show post's notes"""
        if self.__legacy_endpoint:
            url = f'{self._get_root_url()}/note/index.json'
        else:
            url = f'{self._get_root_url()}/note.json'

        params = {'post_id': post_id}

        return parse_obj_as(list[Note], await self.get_resource_as_json(url=url, params=params or None))

    async def notes_history(
            self,
            *,
            id_: int | None = None,
            post_id: int | None = None,
            limit: int | None = None,
            page: int | None = None,
    ) -> list[NoteHistory]:
        """Show note versions history, 可指定 id 或 post_id 之一, 均不指定时返回全部 note 版本"""
        url = f'{self._get_root_url()}/note/history.json'

        params: dict[str, Any] = {}
        if id_ is not None:
            params.update({'id': str(id_)})
        if post_id is not None:
            params.update({'post_id': str(post_id)})
        if limit is not None:
            params.update({'limit': str(limit)})
        if page is not None:
            params.update({'page': str(page)})

        return parse_obj_as(list[NoteHistory], await self.get_resource_as_json(url=url, params=params or None))

    """Users API"""

    async def users_index(
            self,
            *,
            id_: int | None = None,
            name: str | None = None,
    ) -> list[User]:
        """Show users index"""
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/user/index.json'
        else:
            index_url = f'{self._get_root_url()}/user.json'

        params: dict[str, Any] = {}
        if id_ is not None:
            params.update({'id': str(id_)})
        if name is not None:
            params.update({'name': name})

        return parse_obj_as(list[User], await self.get_resource_as_json(url=index_url, params=params or None))

    """Forum API"""

    async def forums_index(
            self,
            *,
            parent_id: int | None = None,
    ) -> list[Forum]:
        """Show forums index"""
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/forum/index.json'
        else:
            index_url = f'{self._get_root_url()}/forum.json'

        params = {'parent_id': str(parent_id)} if parent_id is not None else None

        return parse_obj_as(list[Forum], await self.get_resource_as_json(url=index_url, params=params or None))

    """Pools API"""

    async def pools_index(
            self,
            *,
            query: str | None = None,
            page: int | None = None,
    ) -> list[Pool]:
        """Show pools index"""
        if self.__legacy_endpoint:
            index_url = f'{self._get_root_url()}/pool/index.json'
        else:
            index_url = f'{self._get_root_url()}/pool.json'

        params: dict[str, Any] = {}
        if query is not None:
            params.update({'query': query})
        if page is not None:
            params.update({'page': str(page)})

        return parse_obj_as(list[Pool], await self.get_resource_as_json(url=index_url, params=params or None))

    async def pool_posts_show(self, pool_id: int, *, page: int | None = None) -> Pool:
        """Show pool data with posts"""
        url = f'{self._get_root_url()}/pool/show.json'
        # alternative_url = f'{self._get_root_url()}/pool/show/{pool_id}.json'

        params = {'id': str(pool_id)}
        if page is not None:
            params.update({'page': str(page)})

        return Pool.model_validate(await self.get_resource_as_json(url=url, params=params or None))

    """Favorites API"""

    async def favorite_list_users(self, id_: int) -> FavoritedUsers:
        """Show post's favorited users, 仅提供 JSON 接口"""
        url = f'{self._get_root_url()}/favorite/list_users.json'

        params = {'id': str(id_)}
        return FavoritedUsers.model_validate(await self.get_resource_as_json(url=url, params=params or None))


class KonachanAPI(BaseMoebooruAPI):
    """https://konachan.com 主站 API, 主站有 Cloudflare 盾, 建议直接使用全年龄站接口"""

    _login: str | None = booru_api_config.konachan_com_login_name
    _password_hash: str | None = booru_api_config.konachan_com_password_hash

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://konachan.com'


class KonachanSafeAPI(BaseMoebooruAPI):
    """https://konachan.net 全年龄站 API, 与主站 API 数据相同, 只是网站页面不显示 rating:E 的作品"""

    _login: str | None = booru_api_config.konachan_net_login_name
    _password_hash: str | None = booru_api_config.konachan_net_password_hash

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://konachan.net'


class YandereAPI(BaseMoebooruAPI):
    """https://yande.re 主站 API"""

    _login: str | None = booru_api_config.yandere_login_name
    _password_hash: str | None = booru_api_config.yandere_password_hash

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://yande.re'


__all__ = [
    'BaseMoebooruAPI',
    'KonachanAPI',
    'KonachanSafeAPI',
    'YandereAPI',
]
