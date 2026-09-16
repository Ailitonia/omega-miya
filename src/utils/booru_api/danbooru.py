"""
@Author         : Ailitonia
@Date           : 2024/8/2 14:30:31
@FileName       : danbooru.py
@Project        : omega-miya
@Description    : Danbooru API (bd0c6a37a81f851bd3e7862b97f7cf2fae7d5381) (Read requests only)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import base64
from typing import TYPE_CHECKING, Any

from src.compat import parse_obj_as
from src.utils import BaseCommonAPI
from .config import booru_api_config
from .models.danbooru import (
    Artist,
    ArtistCommentary,
    ArtistCommentaryVersion,
    ArtistVersion,
    Comment,
    Dmail,
    ForumPost,
    ForumTopic,
    Note,
    NoteVersion,
    Pool,
    PoolVersion,
    Post,
    PostAppeal,
    PostFlag,
    PostVersion,
    Tag,
    TagAlias,
    TagImplication,
    Upload,
    User,
    Wiki,
    WikiPageVersion,
)

if TYPE_CHECKING:
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes, QueryTypes


class BaseDanbooruAPI(BaseCommonAPI, abc.ABC):
    """Danbooru API 基类, 文档见 https://danbooru.donmai.us/wiki_pages/help:api"""

    # 类级为 .env 配置默认值, 实例凭据经 __init__ 遮蔽, 避免既往写类属性导致的全局污染
    _username: str | None = None
    _api_key: str | None = None

    def __init__(self, *, username: str | None = None, api_key: str | None = None):
        if (username is not None) and (api_key is not None):
            self._username = username
            self._api_key = api_key

    @staticmethod
    def _build_user_agent(username: str | None) -> str:
        # 文档要求使用唯一 User-Agent 标识客户端, 不伪装浏览器、不使用库默认 UA
        # 文档建议 UA 包含用户标识(如 YourBotName/1.0 (user #id)), 已配置凭据时拼接 login 名
        if username is not None:
            return f'omega-miya/2.0 (user {username})'
        return 'omega-miya/2.0 (user omega-miya)'

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': cls._build_user_agent(cls._username)}

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @property
    def _auth_headers(self) -> 'HeaderTypes':
        """HTTP Basic Auth 鉴权头

        文档同时支持 login/api_key URL 参数与 HTTP Basic Auth 两种鉴权方式;
        采用 Basic Auth 以避免 api_key 随 URL 出现在异常消息与日志中
        """
        if self._username is None or self._api_key is None:
            return None

        credentials = base64.b64encode(f'{self._username}:{self._api_key}'.encode()).decode()
        return {'Authorization': f'Basic {credentials}'}

    async def get_resource_as_json(
            self,
            url: str,
            params: dict[str, Any] | None = None,
    ) -> Any:
        """使用 GET 方法请求 API, 返回 json 内容"""
        # 基类中传入 headers 会整体替换默认头; UA 与鉴权头按实例状态生成
        headers = {'User-Agent': self._build_user_agent(self._username)}
        if (auth_headers := self._auth_headers) is not None:
            headers.update(auth_headers)

        return await self._get_resource_as_json(url, params, headers=headers)

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
    def generate_common_search_params(
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> dict[str, Any]:
        """全站通用搜索参数

        :param page: 页码, 或 b<id>/a<id> 形式的游标分页 (如 page=b999999)
        :param limit: 单页数量上限 (/posts.json 最大 200, 其余端点最大 1000)
        """
        params = {}
        if page is not None:
            params.update({'page': page})
        if limit is not None:
            params.update({'limit': limit})
        if search_kwargs:
            for k, v in search_kwargs.items():
                if v is None:
                    continue
                # 驱动 (aiohttp/yarl) 查询编码不接受 bool, 序列化为文档记载的布尔语法(true/false)
                if isinstance(v, bool):
                    v = 'true' if v else 'false'
                if k.startswith('search_'):
                    params.update({f'search[{k.removeprefix("search_")}]': v})
                else:
                    params.update({k: v})
        return params

    """Versioned Type: Artist"""

    async def artists_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Artist]:
        """Show artists index"""
        index_url = f'{self._get_root_url()}/artists.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Artist], await self.get_resource_as_json(url=index_url, params=params))

    async def artists_index_banned(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Artist]:
        """Show banned artists index"""
        # 上游主站已移除该端点(2026-09 实测 404, wiki 路由表记载未更新), 保留仅为兼容其他 Danbooru 实例;
        # 主站等效能力: artists_index(search_is_banned=True)
        index_url = f'{self._get_root_url()}/artists/banned.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Artist], await self.get_resource_as_json(url=index_url, params=params))

    async def artist_show(self, id_: int) -> Artist:
        """Show artist data"""
        url = f'{self._get_root_url()}/artists/{id_}.json'

        return Artist.model_validate(await self.get_resource_as_json(url=url))

    """Versioned Type: Artist Commentary"""

    async def artist_commentaries_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[ArtistCommentary]:
        """Show artist commentaries index"""
        index_url = f'{self._get_root_url()}/artist_commentaries.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ArtistCommentary], await self.get_resource_as_json(url=index_url, params=params))

    async def artist_commentary_show(self, id_: int) -> ArtistCommentary:
        """Show artist commentary data"""
        url = f'{self._get_root_url()}/artist_commentaries/{id_}.json'

        return ArtistCommentary.model_validate(await self.get_resource_as_json(url=url))

    """Versioned Type: Note"""

    async def notes_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Note]:
        """Show notes index"""
        index_url = f'{self._get_root_url()}/notes.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Note], await self.get_resource_as_json(url=index_url, params=params))

    async def note_show(self, id_: int) -> Note:
        """Show note data"""
        url = f'{self._get_root_url()}/notes/{id_}.json'

        return Note.model_validate(await self.get_resource_as_json(url=url))

    """Versioned Type: Pool"""

    async def pools_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Pool]:
        """Show pools index"""
        index_url = f'{self._get_root_url()}/pools.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Pool], await self.get_resource_as_json(url=index_url, params=params))

    async def pool_show(self, id_: int) -> Pool:
        """Show pool data"""
        url = f'{self._get_root_url()}/pools/{id_}.json'

        return Pool.model_validate(await self.get_resource_as_json(url=url))

    """Versioned Type: Post"""

    async def posts_index(
            self,
            *,
            tags: str | None = None,
            md5: str | None = None,
            random: bool | None = None,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Post]:
        """Show posts index

        注: ApiPosts 文档称 posts 端点的 search 参数需用链式格式 search[post][FIELD], 平铺 search[FIELD] 仅适用
        全站通用字段; 链式键可经 search_kwargs 原样透传, 如 posts_index(**{'search[post][rating]': 's'})

        :param tags: The post query to search for using tags and metatags
        :param md5: Search for an MD5 match. Takes priority over all other parameters.
        :param random: Selects a random sampling under the post query.
        :param page: Returns the given page.
        :param limit: The number of results to return per page.
        """
        index_url = f'{self._get_root_url()}/posts.json'

        params = self.generate_common_search_params(
            page=page, limit=limit, tags=tags, md5=md5, random=random, **search_kwargs
        )
        result = await self.get_resource_as_json(url=index_url, params=params)
        # md5 精确匹配时上游返回单个 post 对象而非数组, 统一包装为列表
        if isinstance(result, dict):
            result = [result]
        return parse_obj_as(list[Post], result)

    async def explore_popular_posts(self) -> list[Post]:
        """Show popular posts"""
        index_url = f'{self._get_root_url()}/explore/posts/popular.json'

        return parse_obj_as(list[Post], await self.get_resource_as_json(url=index_url))

    async def explore_curated_posts(self) -> list[Post]:
        """Show curated posts, 上游主站已移除该端点"""
        # 上游主站已移除该端点(2026-09 实测 404, wiki 路由表记载未更新), 保留仅为兼容其他 Danbooru 实例
        index_url = f'{self._get_root_url()}/explore/posts/curated.json'

        return parse_obj_as(list[Post], await self.get_resource_as_json(url=index_url))

    async def explore_viewed_posts(self) -> list[Post]:
        """Show most viewed posts"""
        index_url = f'{self._get_root_url()}/explore/posts/viewed.json'

        return parse_obj_as(list[Post], await self.get_resource_as_json(url=index_url))

    async def explore_searches_posts(self) -> list[tuple[str, float]]:
        """Show most searched keywords, 响应为 [搜索词, 计数] 二元组数组"""
        # 响应格式未记载于 wiki 文档, 2026-09 实测为上游 reportbooru 的 [搜索词, 计数] 二元组数组
        index_url = f'{self._get_root_url()}/explore/posts/searches.json'

        return parse_obj_as(list[tuple[str, float]], await self.get_resource_as_json(url=index_url))

    async def explore_missed_searches_posts(self) -> list[tuple[str, float]]:
        """Show missed searches keywords, 响应为 [搜索词, 未命中计数] 二元组数组"""
        # 响应格式未记载于 wiki 文档, 2026-09 实测为上游 reportbooru 的 [搜索词, 未命中计数] 二元组数组
        index_url = f'{self._get_root_url()}/explore/posts/missed_searches.json'

        return parse_obj_as(list[tuple[str, float]], await self.get_resource_as_json(url=index_url))

    async def post_random(self) -> Post:
        """Show random post data"""
        url = f'{self._get_root_url()}/posts/random.json'

        return Post.model_validate(await self.get_resource_as_json(url=url))

    async def post_show(self, id_: int) -> Post:
        """Show post data"""
        url = f'{self._get_root_url()}/posts/{id_}.json'

        return Post.model_validate(await self.get_resource_as_json(url=url))

    async def post_show_artist_commentary(self, id_: int) -> ArtistCommentary:
        """Show post's artists commentaries"""
        url = f'{self._get_root_url()}/posts/{id_}/artist_commentary.json'

        return ArtistCommentary.model_validate(await self.get_resource_as_json(url=url))

    """Versioned Type: Wiki"""

    async def wikis_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Wiki]:
        """Show wikis index"""
        index_url = f'{self._get_root_url()}/wiki_pages.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Wiki], await self.get_resource_as_json(url=index_url, params=params))

    async def wiki_show(self, id_: int | str) -> Wiki:
        """Show wiki data, id_ 为 wiki 页面 ID 或标题"""
        url = f'{self._get_root_url()}/wiki_pages/{id_}.json'

        return Wiki.model_validate(await self.get_resource_as_json(url=url))

    """Type Version: ArtistVersion"""

    async def artist_versions_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[ArtistVersion]:
        """Show artist versions index"""
        index_url = f'{self._get_root_url()}/artist_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ArtistVersion], await self.get_resource_as_json(url=index_url, params=params))

    async def artist_version_show(self, id_: int) -> ArtistVersion:
        """Show artist version data"""
        url = f'{self._get_root_url()}/artist_versions/{id_}.json'

        return ArtistVersion.model_validate(await self.get_resource_as_json(url=url))

    """Type Version: ArtistCommentaryVersion"""

    async def artist_commentary_versions_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[ArtistCommentaryVersion]:
        """Show artist commentary versions index"""
        index_url = f'{self._get_root_url()}/artist_commentary_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ArtistCommentaryVersion],
                            await self.get_resource_as_json(url=index_url, params=params))

    async def artist_commentary_version_show(self, id_: int) -> ArtistCommentaryVersion:
        """Show artist commentary version data"""
        url = f'{self._get_root_url()}/artist_commentary_versions/{id_}.json'

        return ArtistCommentaryVersion.model_validate(await self.get_resource_as_json(url=url))

    """Type Version: NoteVersion"""

    async def note_versions_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[NoteVersion]:
        """Show note versions index"""
        index_url = f'{self._get_root_url()}/note_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[NoteVersion], await self.get_resource_as_json(url=index_url, params=params))

    async def note_version_show(self, id_: int) -> NoteVersion:
        """Show note version data"""
        url = f'{self._get_root_url()}/note_versions/{id_}.json'

        return NoteVersion.model_validate(await self.get_resource_as_json(url=url))

    """Type Version: PoolVersion"""

    async def pool_versions_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[PoolVersion]:
        """Show pool versions index"""
        index_url = f'{self._get_root_url()}/pool_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[PoolVersion], await self.get_resource_as_json(url=index_url, params=params))

    """Type Version: PostVersion"""

    async def post_versions_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[PostVersion]:
        """Show post versions index"""
        index_url = f'{self._get_root_url()}/post_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[PostVersion], await self.get_resource_as_json(url=index_url, params=params))

    """Type Version: WikiPageVersion"""

    async def wiki_page_versions_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[WikiPageVersion]:
        """Show wiki page versions index"""
        index_url = f'{self._get_root_url()}/wiki_page_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[WikiPageVersion], await self.get_resource_as_json(url=index_url, params=params))

    async def wiki_page_version_show(self, id_: int) -> WikiPageVersion:
        """Show wiki page version data"""
        url = f'{self._get_root_url()}/wiki_page_versions/{id_}.json'

        return WikiPageVersion.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: Comment"""

    async def comments_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Comment]:
        """Show comments index"""
        index_url = f'{self._get_root_url()}/comments.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        # ApiComments 文档要求 group_by 必须为 comment, 否则上游返回 posts; 调用方可显式覆盖
        params.setdefault('group_by', 'comment')
        return parse_obj_as(list[Comment], await self.get_resource_as_json(url=index_url, params=params))

    async def comment_show(self, id_: int) -> Comment:
        """Show comment data"""
        url = f'{self._get_root_url()}/comments/{id_}.json'

        return Comment.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: Dmail"""

    async def dmails_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Dmail]:
        """Show dmails index"""
        index_url = f'{self._get_root_url()}/dmails.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Dmail], await self.get_resource_as_json(url=index_url, params=params))

    async def dmail_show(self, id_: int, key: str | None = None) -> Dmail:
        """Show dmail data"""
        url = f'{self._get_root_url()}/dmails/{id_}.json'

        params = {'key': key} if key is not None else None
        return Dmail.model_validate(await self.get_resource_as_json(url=url, params=params))

    """Non-versioned Type: ForumPost"""

    async def forum_posts_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[ForumPost]:
        """Show forum posts index"""
        index_url = f'{self._get_root_url()}/forum_posts.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ForumPost], await self.get_resource_as_json(url=index_url, params=params))

    async def forum_post_show(self, id_: int) -> ForumPost:
        """Show forum post data"""
        url = f'{self._get_root_url()}/forum_posts/{id_}.json'

        return ForumPost.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: ForumTopic"""

    async def forum_topics_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[ForumTopic]:
        """Show forum topics index"""
        index_url = f'{self._get_root_url()}/forum_topics.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ForumTopic], await self.get_resource_as_json(url=index_url, params=params))

    async def forum_topic_show(self, id_: int) -> ForumTopic:
        """Show forum topic data"""
        url = f'{self._get_root_url()}/forum_topics/{id_}.json'

        return ForumTopic.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: PostAppeal"""

    async def post_appeals_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[PostAppeal]:
        """Show post appeals index"""
        index_url = f'{self._get_root_url()}/post_appeals.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[PostAppeal], await self.get_resource_as_json(url=index_url, params=params))

    async def post_appeal_show(self, id_: int) -> PostAppeal:
        """Show post appeal data"""
        url = f'{self._get_root_url()}/post_appeals/{id_}.json'

        return PostAppeal.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: PostFlag"""

    async def post_flags_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[PostFlag]:
        """Show post flags index"""
        index_url = f'{self._get_root_url()}/post_flags.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[PostFlag], await self.get_resource_as_json(url=index_url, params=params))

    async def post_flag_show(self, id_: int) -> PostFlag:
        """Show post flag data"""
        url = f'{self._get_root_url()}/post_flags/{id_}.json'

        return PostFlag.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: Tag"""

    async def tags_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Tag]:
        """Show tags index"""
        index_url = f'{self._get_root_url()}/tags.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Tag], await self.get_resource_as_json(url=index_url, params=params))

    async def tag_show(self, id_: int) -> Tag:
        """Show tag data"""
        url = f'{self._get_root_url()}/tags/{id_}.json'

        return Tag.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: TagAlias"""

    async def tag_aliases_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[TagAlias]:
        """Show tag aliases index"""
        index_url = f'{self._get_root_url()}/tag_aliases.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[TagAlias], await self.get_resource_as_json(url=index_url, params=params))

    async def tag_alias_show(self, id_: int) -> TagAlias:
        """Show tag alias data"""
        url = f'{self._get_root_url()}/tag_aliases/{id_}.json'

        return TagAlias.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: TagImplication"""

    async def tag_implications_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[TagImplication]:
        """Show tag implications index"""
        index_url = f'{self._get_root_url()}/tag_implications.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[TagImplication], await self.get_resource_as_json(url=index_url, params=params))

    async def tag_implication_show(self, id_: int) -> TagImplication:
        """Show tag implication data"""
        url = f'{self._get_root_url()}/tag_implications/{id_}.json'

        return TagImplication.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: Upload"""

    async def uploads_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[Upload]:
        """Show uploads index"""
        index_url = f'{self._get_root_url()}/uploads.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Upload], await self.get_resource_as_json(url=index_url, params=params))

    async def upload_show(self, id_: int) -> Upload:
        """Show upload data"""
        url = f'{self._get_root_url()}/uploads/{id_}.json'

        return Upload.model_validate(await self.get_resource_as_json(url=url))

    """Non-versioned Type: User"""

    async def users_index(
            self,
            *,
            page: int | str | None = None,
            limit: int | None = None,
            **search_kwargs,
    ) -> list[User]:
        """Show users index"""
        index_url = f'{self._get_root_url()}/users.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[User], await self.get_resource_as_json(url=index_url, params=params))

    async def user_profile(self) -> User:
        """Get profile"""
        url = f'{self._get_root_url()}/profile.json'

        return User.model_validate(await self.get_resource_as_json(url=url))

    async def user_show(self, id_: int) -> User:
        """Show user data"""
        url = f'{self._get_root_url()}/users/{id_}.json'

        return User.model_validate(await self.get_resource_as_json(url=url))


class DanbooruAPI(BaseDanbooruAPI):
    """https://danbooru.donmai.us 主站 API"""

    _username: str | None = booru_api_config.danbooru_username
    _api_key: str | None = booru_api_config.danbooru_api_key

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://danbooru.donmai.us'


__all__ = [
    'BaseDanbooruAPI',
    'DanbooruAPI',
]
