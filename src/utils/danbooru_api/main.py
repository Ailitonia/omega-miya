"""
@Author         : Ailitonia
@Date           : 2024/8/2 14:30:31
@FileName       : main.py
@Project        : omega-miya
@Description    : Danbooru API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import TYPE_CHECKING, Any, Optional, TypeVar

from src.compat import parse_obj_as
from src.utils.common_api import BaseCommonAPI
from .config import danbooru_config
from .models import (
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
    from src.resource import TemporaryResource


class BaseDanbooruCommon(BaseCommonAPI, abc.ABC):
    """Danbooru API 通用基类"""

    __slots__ = ('id',)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(id={self.id})'

    @classmethod
    @abc.abstractmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        raise NotImplementedError

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _get_default_headers(cls) -> "HeaderTypes":
        return {}

    @classmethod
    def _get_default_cookies(cls) -> "CookieTypes":
        return None

    @classmethod
    async def get_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            enable_auth: bool = True,
    ) -> Any:
        """使用 GET 方法请求 API, 返回 json 内容"""
        if enable_auth and not params:
            params = danbooru_config.auth_params
        elif enable_auth and params:
            params.update(danbooru_config.auth_params)

        response = await cls._request_get(url, params)
        return cls._parse_content_as_json(response)

    @classmethod
    async def get_resource_as_bytes(
            cls,
            url: str,
            params: "QueryTypes" = None,
            *,
            timeout: int = 30,
    ) -> bytes:
        return await cls._get_resource_as_bytes(url, params, timeout=timeout)

    @classmethod
    async def get_resource_as_text(
            cls,
            url: str,
            params: "QueryTypes" = None,
            *,
            timeout: int = 30,
    ) -> str:
        return await cls._get_resource_as_text(url, params, timeout=timeout)

    @classmethod
    async def download_resource(
            cls,
            save_folder: "TemporaryResource",
            url: str,
            *,
            subdir: str | None = None,
            ignore_exist_file: bool = False,
    ) -> "TemporaryResource":
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=save_folder,
            url=url,
            subdir=subdir,
            ignore_exist_file=ignore_exist_file
        )

    @classmethod
    @abc.abstractmethod
    def get_index_url(cls) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def get_target_url(self) -> str:
        raise NotImplementedError

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
            params.update({f'search[{k}]': v for k, v in search_kwargs.items()})
        return params

    @classmethod
    async def _index(
            cls,
            *,
            enable_auth: bool = True,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Any]:
        """Show index"""
        params = cls.generate_common_search_params(page=page, limit=limit, **search_kwargs)
        return await cls.get_json(url=cls.get_index_url(), params=params, enable_auth=enable_auth)

    async def _show(self, *, enable_auth: bool = True, **kwargs) -> Any:
        """Show target data"""
        return await self.get_json(url=self.get_target_url(), params=kwargs, enable_auth=enable_auth)


"""Versioned Types"""


class BaseDanbooruArtist(BaseDanbooruCommon, abc.ABC):
    """Artist, Docs: https://danbooru.donmai.us/wiki_pages/api:artists"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/artists.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/artists/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Artist]:
        """Show artists index"""
        return parse_obj_as(list[Artist], await cls._index(page=page, limit=limit, **search_kwargs))

    @classmethod
    async def index_banned(cls) -> list[Artist]:
        """Show banned artists index"""
        url = f'{cls._get_root_url()}/artists/banned.json'
        return parse_obj_as(list[Artist], await cls.get_json(url=url))

    async def show(self) -> Artist:
        """Show artist data"""
        return Artist.model_validate(await self._show())


class BaseDanbooruArtistCommentary(BaseDanbooruCommon, abc.ABC):
    """ArtistCommentary, Docs: https://danbooru.donmai.us/wiki_pages/api:artist_commentaries"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/artist_commentaries.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/artist_commentaries/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ArtistCommentary]:
        """Show artist commentaries index"""
        return parse_obj_as(list[ArtistCommentary], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> ArtistCommentary:
        """Show artist data"""
        return ArtistCommentary.model_validate(await self._show())


class BaseDanbooruNote(BaseDanbooruCommon, abc.ABC):
    """Note, Docs: https://danbooru.donmai.us/wiki_pages/api:notes"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/notes.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/notes/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Note]:
        """Show notes index"""
        return parse_obj_as(list[Note], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> Note:
        """Show note data"""
        return Note.model_validate(await self._show())


class BaseDanbooruPool(BaseDanbooruCommon, abc.ABC):
    """Pool, Docs: https://danbooru.donmai.us/wiki_pages/api:pools"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/pools.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/pools/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Pool]:
        """Show pools index"""
        return parse_obj_as(list[Pool], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> Pool:
        """Show pool data"""
        return Pool.model_validate(await self._show())


class BaseDanbooruPost(BaseDanbooruCommon, abc.ABC):
    """Post, Docs: https://danbooru.donmai.us/wiki_pages/api:posts"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/posts.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/posts/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Post]:
        """Show posts index"""
        return parse_obj_as(list[Post], await cls._index(page=page, limit=limit, **search_kwargs))

    @classmethod
    async def explore_popular_posts(cls) -> list[Post]:
        url = f'{cls._get_root_url()}/explore/posts/popular.json'
        return parse_obj_as(list[Post], await cls.get_json(url=url))

    @classmethod
    async def explore_curated_posts(cls) -> list[Post]:
        url = f'{cls._get_root_url()}/explore/posts/curated.json'
        return parse_obj_as(list[Post], await cls.get_json(url=url))

    @classmethod
    async def explore_viewed_posts(cls) -> list[Post]:
        url = f'{cls._get_root_url()}/explore/posts/viewed.json'
        return parse_obj_as(list[Post], await cls.get_json(url=url))

    @classmethod
    async def explore_searches_posts(cls) -> list[tuple[str, float]]:
        url = f'{cls._get_root_url()}/explore/posts/searches.json'
        return parse_obj_as(list[tuple[str, float]], await cls.get_json(url=url))

    @classmethod
    async def explore_missed_searches_posts(cls) -> list[tuple[str, float]]:
        url = f'{cls._get_root_url()}/explore/posts/missed_searches.json'
        return parse_obj_as(list[tuple[str, float]], await cls.get_json(url=url))

    @classmethod
    async def random(cls) -> Post:
        url = f'{cls._get_root_url()}/posts/random.json'
        return Post.model_validate(await cls.get_json(url=url))

    async def show(self) -> Post:
        """Show post data"""
        return Post.model_validate(await self._show())

    async def show_artist_commentaries(self) -> ArtistCommentary:
        """Show post's artists commentaries"""
        url = f'{self._get_root_url()}/posts/{self.id}/artist_commentary.json'
        return ArtistCommentary.model_validate(await self.get_json(url=url))


class BaseDanbooruWiki(BaseDanbooruCommon, abc.ABC):
    """Wiki, Docs: https://danbooru.donmai.us/wiki_pages/api:wikis"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/wiki_pages.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/wiki_pages/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Wiki]:
        """Show wikis index"""
        return parse_obj_as(list[Wiki], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> Wiki:
        """Show wiki data"""
        return Wiki.model_validate(await self._show())


"""Type Versions"""


class BaseDanbooruArtistVersion(BaseDanbooruCommon, abc.ABC):
    """ArtistVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:artist_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/artist_versions.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/artist_versions/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ArtistVersion]:
        """Show artist versions index"""
        return parse_obj_as(list[ArtistVersion], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> ArtistVersion:
        """Show artist version data"""
        return ArtistVersion.model_validate(await self._show())


class BaseDanbooruArtistCommentaryVersion(BaseDanbooruCommon, abc.ABC):
    """ArtistCommentaryVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:artist_commentary_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/artist_commentary_versions.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/artist_commentary_versions/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ArtistCommentaryVersion]:
        """Show artist commentary versions index"""
        return parse_obj_as(list[ArtistCommentaryVersion], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> ArtistCommentaryVersion:
        """Show artist commentary version data"""
        return ArtistCommentaryVersion.model_validate(await self._show())


class BaseDanbooruNoteVersion(BaseDanbooruCommon, abc.ABC):
    """NoteVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:note_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/note_versions.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/note_versions/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[NoteVersion]:
        """Show note versions index"""
        return parse_obj_as(list[NoteVersion], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> NoteVersion:
        """Show note version data"""
        return NoteVersion.model_validate(await self._show())


class BaseDanbooruPoolVersion(BaseDanbooruCommon, abc.ABC):
    """PoolVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:pool_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/pool_versions.json'

    def get_target_url(self) -> str:
        raise NotImplementedError

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[PoolVersion]:
        """Show pool versions index"""
        return parse_obj_as(list[PoolVersion], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> PoolVersion:
        """Show pool version data"""
        raise NotImplementedError


class BaseDanbooruPostVersion(BaseDanbooruCommon, abc.ABC):
    """PostVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:post_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/post_versions.json'

    def get_target_url(self) -> str:
        raise NotImplementedError

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[PostVersion]:
        """Show post versions index"""
        return parse_obj_as(list[PostVersion], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> PostVersion:
        """Show post version data"""
        raise NotImplementedError


class BaseDanbooruWikiPageVersion(BaseDanbooruCommon, abc.ABC):
    """WikiPageVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:wiki_page_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/wiki_page_versions.json'

    def get_target_url(self) -> str:
        raise NotImplementedError

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[WikiPageVersion]:
        """Show wiki page versions index"""
        return parse_obj_as(list[WikiPageVersion], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> WikiPageVersion:
        """Show wiki page version data"""
        raise NotImplementedError


"""Non-versioned Types"""


class BaseDanbooruComment(BaseDanbooruCommon, abc.ABC):
    """Comment, Docs: https://danbooru.donmai.us/wiki_pages/api:comments"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/comments.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/comments/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Comment]:
        """Show comments index"""
        return parse_obj_as(list[Comment], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> Comment:
        """Show comment data"""
        return Comment.model_validate(await self._show())


class BaseDanbooruDmail(BaseDanbooruCommon, abc.ABC):
    """Dmail, Docs: https://danbooru.donmai.us/wiki_pages/api:dmails"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/dmails.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/dmails/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Dmail]:
        """Show dmails index"""
        return parse_obj_as(list[Dmail], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self, key: Optional[str] = None) -> Dmail:
        """Show dmail data"""
        if key is not None:
            return Dmail.model_validate(await self._show(key=key))
        else:
            return Dmail.model_validate(await self._show())


class BaseDanbooruForumPost(BaseDanbooruCommon, abc.ABC):
    """ForumPost, Docs: https://danbooru.donmai.us/wiki_pages/api:forum_posts"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/forum_posts.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/forum_posts/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ForumPost]:
        """Show forum posts index"""
        return parse_obj_as(list[ForumPost], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> ForumPost:
        """Show forum post data"""
        return ForumPost.model_validate(await self._show())


class BaseDanbooruForumTopic(BaseDanbooruCommon, abc.ABC):
    """ForumTopic, Docs: https://danbooru.donmai.us/wiki_pages/api:forum_topics"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/forum_topics.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/forum_topics/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[ForumTopic]:
        """Show forum topics index"""
        return parse_obj_as(list[ForumTopic], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> ForumTopic:
        """Show forum topic data"""
        return ForumTopic.model_validate(await self._show())


class BaseDanbooruPostAppeal(BaseDanbooruCommon, abc.ABC):
    """PostAppeal, Docs: https://danbooru.donmai.us/wiki_pages/api:post_appeals"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/post_appeals.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/post_appeals/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[PostAppeal]:
        """Show post appeals index"""
        return parse_obj_as(list[PostAppeal], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> PostAppeal:
        """Show post appeal data"""
        return PostAppeal.model_validate(await self._show())


class BaseDanbooruPostFlag(BaseDanbooruCommon, abc.ABC):
    """PostFlag, Docs: https://danbooru.donmai.us/wiki_pages/api:post_flags"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/post_flags.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/post_flags/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[PostFlag]:
        """Show post flags index"""
        return parse_obj_as(list[PostFlag], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> PostFlag:
        """Show post flag data"""
        return PostFlag.model_validate(await self._show())


class BaseDanbooruTag(BaseDanbooruCommon, abc.ABC):
    """Tag, Docs: https://danbooru.donmai.us/wiki_pages/api:tags"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/tags.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/tags/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Tag]:
        """Show tags index"""
        return parse_obj_as(list[Tag], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> Tag:
        """Show tag data"""
        return Tag.model_validate(await self._show())


class BaseDanbooruTagAlias(BaseDanbooruCommon, abc.ABC):
    """TagAlias, Docs: https://danbooru.donmai.us/wiki_pages/api:tag_aliases"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/tag_aliases.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/tag_aliases/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[TagAlias]:
        """Show tag aliases index"""
        return parse_obj_as(list[TagAlias], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> TagAlias:
        """Show tag alias data"""
        return TagAlias.model_validate(await self._show())


class BaseDanbooruTagImplication(BaseDanbooruCommon, abc.ABC):
    """TagImplication, Docs: https://danbooru.donmai.us/wiki_pages/api:tag_implications"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/tag_implications.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/tag_implications/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[TagImplication]:
        """Show tag implications index"""
        return parse_obj_as(list[TagImplication], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> TagImplication:
        """Show tag implication data"""
        return TagImplication.model_validate(await self._show())


class BaseDanbooruUpload(BaseDanbooruCommon, abc.ABC):
    """Upload, Docs: https://danbooru.donmai.us/wiki_pages/api:uploads"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/uploads.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/uploads/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[Upload]:
        """Show uploads index"""
        return parse_obj_as(list[Upload], await cls._index(page=page, limit=limit, **search_kwargs))

    async def show(self) -> Upload:
        """Show upload data"""
        return Upload.model_validate(await self._show())


class BaseDanbooruUser(BaseDanbooruCommon, abc.ABC):
    """User, Docs: https://danbooru.donmai.us/wiki_pages/api:users"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls._get_root_url()}/users.json'

    def get_target_url(self) -> str:
        return f'{self._get_root_url()}/users/{self.id}.json'

    @classmethod
    async def index(
            cls,
            *,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            **search_kwargs
    ) -> list[User]:
        """Show users index"""
        return parse_obj_as(list[User], await cls._index(page=page, limit=limit, **search_kwargs))

    @classmethod
    async def profile(cls) -> User:
        """Get profile"""
        url = f'{cls._get_root_url()}/profile.json'
        return User.model_validate(await cls.get_json(url=url))

    async def show(self) -> User:
        """Show user data"""
        return User.model_validate(await self._show())


class BaseDanbooruAPI:
    """Danbooru API 基类"""

    Type_T = TypeVar('Type_T', bound=type[BaseDanbooruCommon]) 

    def __init__(self, root_url: str) -> None:
        self._root_url = root_url

        self.Artist = self._create_new_common_class(BaseDanbooruArtist)
        self.ArtistCommentary = self._create_new_common_class(BaseDanbooruArtistCommentary)
        self.Note = self._create_new_common_class(BaseDanbooruNote)
        self.Pool = self._create_new_common_class(BaseDanbooruPool)
        self.Post = self._create_new_common_class(BaseDanbooruPost)
        self.Wiki = self._create_new_common_class(BaseDanbooruWiki)
        self.ArtistVersion = self._create_new_common_class(BaseDanbooruArtistVersion)
        self.ArtistCommentaryVersion = self._create_new_common_class(BaseDanbooruArtistCommentaryVersion)
        self.NoteVersion = self._create_new_common_class(BaseDanbooruNoteVersion)
        self.PoolVersion = self._create_new_common_class(BaseDanbooruPoolVersion)
        self.PostVersion = self._create_new_common_class(BaseDanbooruPostVersion)
        self.WikiPageVersion = self._create_new_common_class(BaseDanbooruWikiPageVersion)
        self.Comment = self._create_new_common_class(BaseDanbooruComment)
        self.Dmail = self._create_new_common_class(BaseDanbooruDmail)
        self.ForumPost = self._create_new_common_class(BaseDanbooruForumPost)
        self.ForumTopic = self._create_new_common_class(BaseDanbooruForumTopic)
        self.PostAppeal = self._create_new_common_class(BaseDanbooruPostAppeal)
        self.PostFlag = self._create_new_common_class(BaseDanbooruPostFlag)
        self.Tag = self._create_new_common_class(BaseDanbooruTag)
        self.TagAlias = self._create_new_common_class(BaseDanbooruTagAlias)
        self.TagImplication = self._create_new_common_class(BaseDanbooruTagImplication)
        self.Upload = self._create_new_common_class(BaseDanbooruUpload)
        self.User = self._create_new_common_class(BaseDanbooruUser)

    def _create_new_common_class(self, class_: Type_T) -> Type_T:
        class DanbooruCommon(class_):
            __slots__ = ('id',)

            @classmethod
            def _get_root_url(cls) -> str:
                return self._root_url

            def __repr__(self) -> str:
                return f'{class_.__name__.removeprefix("Base")}(id={self.id})'

        return DanbooruCommon  # type: ignore

    @staticmethod
    async def get_resource_as_bytes(
            url: str,
            params: "QueryTypes" = None,
            *,
            timeout: int = 30,
    ) -> bytes:
        return await BaseDanbooruCommon.get_resource_as_bytes(url, params, timeout=timeout)

    @staticmethod
    async def get_resource_as_text(
            url: str,
            params: "QueryTypes" = None,
            *,
            timeout: int = 30,
    ) -> str:
        return await BaseDanbooruCommon.get_resource_as_text(url, params, timeout=timeout)

    @staticmethod
    async def download_resource(
            save_folder: "TemporaryResource",
            url: str,
            *,
            subdir: str | None = None,
            ignore_exist_file: bool = False,
    ) -> "TemporaryResource":
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await BaseDanbooruCommon.download_resource(
            save_folder=save_folder,
            url=url,
            subdir=subdir,
            ignore_exist_file=ignore_exist_file
        )


__all__ = [
    'BaseDanbooruArtist',
    'BaseDanbooruArtistCommentary',
    'BaseDanbooruNote',
    'BaseDanbooruPool',
    'BaseDanbooruPost',
    'BaseDanbooruWiki',
    'BaseDanbooruArtistVersion',
    'BaseDanbooruArtistCommentaryVersion',
    'BaseDanbooruNoteVersion',
    'BaseDanbooruPoolVersion',
    'BaseDanbooruPostVersion',
    'BaseDanbooruWikiPageVersion',
    'BaseDanbooruComment',
    'BaseDanbooruDmail',
    'BaseDanbooruForumPost',
    'BaseDanbooruForumTopic',
    'BaseDanbooruPostAppeal',
    'BaseDanbooruPostFlag',
    'BaseDanbooruTag',
    'BaseDanbooruTagAlias',
    'BaseDanbooruTagImplication',
    'BaseDanbooruUpload',
    'BaseDanbooruUser',
    'BaseDanbooruAPI',
]
