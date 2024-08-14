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
from typing import TYPE_CHECKING, Any, Optional

from src.compat import parse_obj_as
from src.utils.common_api import BaseCommonAPI
from .models.danbooru import (
    Artist,
    ArtistCommentary,
    Note,
    Pool,
    Post,
    Wiki,
    ArtistVersion,
    ArtistCommentaryVersion,
    NoteVersion,
    PoolVersion,
    PostVersion,
    WikiPageVersion,
    Comment,
    Dmail,
    ForumPost,
    ForumTopic,
    PostAppeal,
    PostFlag,
    Tag,
    TagAlias,
    TagImplication,
    Upload,
    User,
)

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes, HeaderTypes, QueryTypes


class BaseDanbooruAPI(BaseCommonAPI, abc.ABC):
    """Danbooru API 基类, 文档见 https://danbooru.donmai.us/wiki_pages/help:api"""

    def __init__(self, *, username: Optional[str] = None, api_key: Optional[str] = None):
        self.__username = username
        self.__api_key = api_key

    @property
    def _auth_params(self) -> dict[str, str]:
        if self.__username is None or self.__api_key is None:
            return {}

        return {'login': self.__username, 'api_key': self.__api_key}

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

    @staticmethod
    def generate_common_search_params(
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> dict[str, Any]:
        """全站通用搜索参数"""
        params = {}
        if page:
            params.update({'page': page})
        if limit:
            params.update({'limit': limit})
        if search_kwargs:
            for k, v in search_kwargs.items():
                if k.startswith('search_'):
                    params.update({f'search[{k.removeprefix("search_")}]': v})
                else:
                    params.update({k: v})
        return params

    """Versioned Type: Artist"""

    async def artists_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Artist]:
        """Show artists index"""
        index_url = f'{self._get_root_url()}/artists.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Artist], await self.get_json(url=index_url, params=params))

    async def artists_index_banned(self) -> list[Artist]:
        """Show banned artists index"""
        index_url = f'{self._get_root_url()}/artists/banned.json'

        return parse_obj_as(list[Artist], await self.get_json(url=index_url))

    async def artist_show(self, id_: int) -> Artist:
        """Show artist data"""
        url = f'{self._get_root_url()}/artists/{id_}.json'

        return Artist.model_validate(await self.get_json(url=url))

    """Versioned Type: Artist Commentary"""

    async def artist_commentaries_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ArtistCommentary]:
        """Show artist commentaries index"""
        index_url = f'{self._get_root_url()}/artist_commentaries.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ArtistCommentary], await self.get_json(url=index_url, params=params))

    async def artist_commentary_show(self, id_: int) -> ArtistCommentary:
        """Show artist commentary data"""
        url = f'{self._get_root_url()}/artist_commentaries/{id_}.json'

        return ArtistCommentary.model_validate(await self.get_json(url=url))

    """Versioned Type: Note"""

    async def notes_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Note]:
        """Show notes index"""
        index_url = f'{self._get_root_url()}/notes.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Note], await self.get_json(url=index_url, params=params))

    async def note_show(self, id_: int) -> Note:
        """Show note data"""
        url = f'{self._get_root_url()}/notes/{id_}.json'

        return Note.model_validate(await self.get_json(url=url))

    """Versioned Type: Pool"""

    async def pools_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Pool]:
        """Show pools index"""
        index_url = f'{self._get_root_url()}/pools.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Pool], await self.get_json(url=index_url, params=params))

    async def poll_show(self, id_: int) -> Pool:
        """Show pool data"""
        url = f'{self._get_root_url()}/pools/{id_}.json'

        return Pool.model_validate(await self.get_json(url=url))

    """Versioned Type: Post"""

    async def posts_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Post]:
        """Show posts index"""
        index_url = f'{self._get_root_url()}/posts.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Post], await self.get_json(url=index_url, params=params))

    async def explore_popular_posts(self) -> list[Post]:
        index_url = f'{self._get_root_url()}/explore/posts/popular.json'

        return parse_obj_as(list[Post], await self.get_json(url=index_url))

    async def explore_curated_posts(self) -> list[Post]:
        index_url = f'{self._get_root_url()}/explore/posts/curated.json'

        return parse_obj_as(list[Post], await self.get_json(url=index_url))

    async def explore_viewed_posts(self) -> list[Post]:
        index_url = f'{self._get_root_url()}/explore/posts/viewed.json'

        return parse_obj_as(list[Post], await self.get_json(url=index_url))

    async def explore_searches_posts(self) -> list[tuple[str, float]]:
        index_url = f'{self._get_root_url()}/explore/posts/searches.json'

        return parse_obj_as(list[tuple[str, float]], await self.get_json(url=index_url))

    async def explore_missed_searches_posts(self) -> list[tuple[str, float]]:
        index_url = f'{self._get_root_url()}/explore/posts/missed_searches.json'

        return parse_obj_as(list[tuple[str, float]], await self.get_json(url=index_url))

    async def post_random(self) -> Post:
        """Show random post data"""
        url = f'{self._get_root_url()}/posts/random.json'

        return Post.model_validate(await self.get_json(url=url))

    async def post_show(self, id_: int) -> Post:
        """Show post data"""
        url = f'{self._get_root_url()}/posts/{id_}.json'

        return Post.model_validate(await self.get_json(url=url))

    async def post_show_artist_commentary(self, id_: int) -> ArtistCommentary:
        """Show post's artists commentaries"""
        url = f'{self._get_root_url()}/posts/{id_}/artist_commentary.json'

        return ArtistCommentary.model_validate(await self.get_json(url=url))

    """Versioned Type: Wiki"""

    async def wikis_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Wiki]:
        """Show wikis index"""
        index_url = f'{self._get_root_url()}/wiki_pages.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Wiki], await self.get_json(url=index_url, params=params))

    async def wiki_show(self, id_: int) -> Wiki:
        """Show wiki data"""
        url = f'{self._get_root_url()}/wiki_pages/{id_}.json'

        return Wiki.model_validate(await self.get_json(url=url))

    """Type Version: ArtistVersion"""

    async def artist_versions_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ArtistVersion]:
        """Show artist versions index"""
        index_url = f'{self._get_root_url()}/artist_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ArtistVersion], await self.get_json(url=index_url, params=params))

    async def artist_version_show(self, id_: int) -> ArtistVersion:
        """Show artist version data"""
        url = f'{self._get_root_url()}/artist_versions/{id_}.json'

        return ArtistVersion.model_validate(await self.get_json(url=url))

    """Type Version: ArtistCommentaryVersion"""

    async def artist_commentary_versions_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ArtistCommentaryVersion]:
        """Show artist commentary versions index"""
        index_url = f'{self._get_root_url()}/artist_commentary_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ArtistCommentaryVersion], await self.get_json(url=index_url, params=params))

    async def artist_commentary_version_show(self, id_: int) -> ArtistCommentaryVersion:
        """Show artist commentary version data"""
        url = f'{self._get_root_url()}/artist_commentary_versions/{id_}.json'

        return ArtistCommentaryVersion.model_validate(await self.get_json(url=url))

    """Type Version: NoteVersion"""

    async def note_versions_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[NoteVersion]:
        """Show note versions index"""
        index_url = f'{self._get_root_url()}/note_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[NoteVersion], await self.get_json(url=index_url, params=params))

    async def note_version_show(self, id_: int) -> NoteVersion:
        """Show note version data"""
        url = f'{self._get_root_url()}/note_versions/{id_}.json'

        return NoteVersion.model_validate(await self.get_json(url=url))

    """Type Version: PoolVersion"""

    async def pool_versions_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[PoolVersion]:
        """Show pool versions index"""
        index_url = f'{self._get_root_url()}/pool_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[PoolVersion], await self.get_json(url=index_url, params=params))

    """Type Version: PostVersion"""

    async def post_versions_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[PostVersion]:
        """Show post versions index"""
        index_url = f'{self._get_root_url()}/post_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[PostVersion], await self.get_json(url=index_url, params=params))

    """Type Version: WikiPageVersion"""

    async def wiki_page_versions_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[WikiPageVersion]:
        """Show wiki page versions index"""
        index_url = f'{self._get_root_url()}/wiki_page_versions.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[WikiPageVersion], await self.get_json(url=index_url, params=params))

    """Non-versioned Type: Comment"""

    async def comments_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Comment]:
        """Show comments index"""
        index_url = f'{self._get_root_url()}/comments.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Comment], await self.get_json(url=index_url, params=params))

    async def comment_show(self, id_: int) -> Comment:
        """Show comment data"""
        url = f'{self._get_root_url()}/comments/{id_}.json'

        return Comment.model_validate(await self.get_json(url=url))

    """Non-versioned Type: Dmail"""

    async def dmails_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Dmail]:
        """Show dmails index"""
        index_url = f'{self._get_root_url()}/dmails.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Dmail], await self.get_json(url=index_url, params=params))

    async def dmail_show(self, id_: int, key: Optional[str] = None) -> Dmail:
        """Show dmail data"""
        url = f'{self._get_root_url()}/dmails/{id_}.json'

        params = {'key': key} if key is not None else None
        return Dmail.model_validate(await self.get_json(url=url, params=params))

    """Non-versioned Type: ForumPost"""

    async def forum_posts_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ForumPost]:
        """Show forum posts index"""
        index_url = f'{self._get_root_url()}/forum_posts.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ForumPost], await self.get_json(url=index_url, params=params))

    async def forum_post_show(self, id_: int) -> ForumPost:
        """Show forum post data"""
        url = f'{self._get_root_url()}/forum_posts/{id_}.json'

        return ForumPost.model_validate(await self.get_json(url=url))

    """Non-versioned Type: ForumTopic"""

    async def forum_topics_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ForumTopic]:
        """Show forum topics index"""
        index_url = f'{self._get_root_url()}/forum_topics.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[ForumTopic], await self.get_json(url=index_url, params=params))

    async def forum_topic_show(self, id_: int) -> ForumTopic:
        """Show forum topic data"""
        url = f'{self._get_root_url()}/forum_topics/{id_}.json'

        return ForumTopic.model_validate(await self.get_json(url=url))

    """Non-versioned Type: PostAppeal"""

    async def post_appeals_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[PostAppeal]:
        """Show post appeals index"""
        index_url = f'{self._get_root_url()}/post_appeals.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[PostAppeal], await self.get_json(url=index_url, params=params))

    async def post_appeal_show(self, id_: int) -> PostAppeal:
        """Show post appeal data"""
        url = f'{self._get_root_url()}/post_appeals/{id_}.json'

        return PostAppeal.model_validate(await self.get_json(url=url))

    """Non-versioned Type: PostFlag"""

    async def post_flags_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[PostFlag]:
        """Show post flags index"""
        index_url = f'{self._get_root_url()}/post_flags.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[PostFlag], await self.get_json(url=index_url, params=params))

    async def post_flag_show(self, id_: int) -> PostFlag:
        """Show post flag data"""
        url = f'{self._get_root_url()}/post_flags/{id_}.json'

        return PostFlag.model_validate(await self.get_json(url=url))

    """Non-versioned Type: Tag"""

    async def tags_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Tag]:
        """Show tags index"""
        index_url = f'{self._get_root_url()}/tags.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Tag], await self.get_json(url=index_url, params=params))

    async def tag_show(self, id_: int) -> Tag:
        """Show tag data"""
        url = f'{self._get_root_url()}/tags/{id_}.json'

        return Tag.model_validate(await self.get_json(url=url))

    """Non-versioned Type: TagAlias"""

    async def tag_aliases_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[TagAlias]:
        """Show tag aliases index"""
        index_url = f'{self._get_root_url()}/tag_aliases.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[TagAlias], await self.get_json(url=index_url, params=params))

    async def tag_alias_show(self, id_: int) -> TagAlias:
        """Show tag alias data"""
        url = f'{self._get_root_url()}/tag_aliases/{id_}.json'

        return TagAlias.model_validate(await self.get_json(url=url))

    """Non-versioned Type: TagImplication"""

    async def tag_implications_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[TagImplication]:
        """Show tag implications index"""
        index_url = f'{self._get_root_url()}/tag_implications.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[TagImplication], await self.get_json(url=index_url, params=params))

    async def tag_implication_show(self, id_: int) -> TagImplication:
        """Show tag implication data"""
        url = f'{self._get_root_url()}/tag_implications/{id_}.json'

        return TagImplication.model_validate(await self.get_json(url=url))

    """Non-versioned Type: Upload"""

    async def uploads_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Upload]:
        """Show uploads index"""
        index_url = f'{self._get_root_url()}/uploads.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[Upload], await self.get_json(url=index_url, params=params))

    async def upload_show(self, id_: int) -> Upload:
        """Show upload data"""
        url = f'{self._get_root_url()}/uploads/{id_}.json'

        return Upload.model_validate(await self.get_json(url=url))

    """Non-versioned Type: User"""

    async def users_index(
            self,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[User]:
        """Show users index"""
        index_url = f'{self._get_root_url()}/users.json'

        params = self.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return parse_obj_as(list[User], await self.get_json(url=index_url, params=params))

    async def user_profile(self) -> User:
        """Get profile"""
        url = f'{self._get_root_url()}/profile.json'

        return User.model_validate(await self.get_json(url=url))

    async def user_show(self, id_: int) -> User:
        """Show user data"""
        url = f'{self._get_root_url()}/users/{id_}.json'

        return User.model_validate(await self.get_json(url=url))


class DanbooruAPI(BaseDanbooruAPI):
    """Danbooru API"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://danbooru.donmai.us'


__all__ = [
    'DanbooruAPI',
]
