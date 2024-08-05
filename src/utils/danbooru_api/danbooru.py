"""
@Author         : Ailitonia
@Date           : 2024/8/2 14:30:31
@FileName       : danbooru.py
@Project        : omega-miya
@Description    : Danbooru API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import Any, Optional, Type, TypeVar

from src.compat import parse_obj_as
from .api_base import DanbooruBase
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


class DanbooruCommonBase(DanbooruBase, abc.ABC):
    """Danbooru Common utils"""

    __slots__ = ('id',)

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


class DanbooruArtistBase(DanbooruCommonBase, abc.ABC):
    """Artist, Docs: https://danbooru.donmai.us/wiki_pages/api:artists"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/artists.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/artists/{self.id}.json'

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
        url = f'{cls.get_root_url()}/artists/banned.json'
        return parse_obj_as(list[Artist], await cls.get_json(url=url))

    async def show(self) -> Artist:
        """Show artist data"""
        return Artist.model_validate(await self._show())


class DanbooruArtistCommentaryBase(DanbooruCommonBase, abc.ABC):
    """ArtistCommentary, Docs: https://danbooru.donmai.us/wiki_pages/api:artist_commentaries"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/artist_commentaries.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/artist_commentaries/{self.id}.json'

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


class DanbooruNoteBase(DanbooruCommonBase, abc.ABC):
    """Note, Docs: https://danbooru.donmai.us/wiki_pages/api:notes"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/notes.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/notes/{self.id}.json'

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


class DanbooruPoolBase(DanbooruCommonBase, abc.ABC):
    """Pool, Docs: https://danbooru.donmai.us/wiki_pages/api:pools"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/pools.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/pools/{self.id}.json'

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


class DanbooruPostBase(DanbooruCommonBase, abc.ABC):
    """Post, Docs: https://danbooru.donmai.us/wiki_pages/api:posts"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/posts.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/posts/{self.id}.json'

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
        url = f'{cls.get_root_url()}/explore/posts/popular.json'
        return parse_obj_as(list[Post], await cls.get_json(url=url))

    @classmethod
    async def explore_curated_posts(cls) -> list[Post]:
        url = f'{cls.get_root_url()}/explore/posts/curated.json'
        return parse_obj_as(list[Post], await cls.get_json(url=url))

    @classmethod
    async def explore_viewed_posts(cls) -> list[Post]:
        url = f'{cls.get_root_url()}/explore/posts/viewed.json'
        return parse_obj_as(list[Post], await cls.get_json(url=url))

    @classmethod
    async def explore_searches_posts(cls) -> list[tuple[str, float]]:
        url = f'{cls.get_root_url()}/explore/posts/searches.json'
        return parse_obj_as(list[tuple[str, float]], await cls.get_json(url=url))

    @classmethod
    async def explore_missed_searches_posts(cls) -> list[tuple[str, float]]:
        url = f'{cls.get_root_url()}/explore/posts/missed_searches.json'
        return parse_obj_as(list[tuple[str, float]], await cls.get_json(url=url))

    @classmethod
    async def random(cls) -> Post:
        url = f'{cls.get_root_url()}/posts/random.json'
        return Post.model_validate(await cls.get_json(url=url))

    async def show(self) -> Post:
        """Show post data"""
        return Post.model_validate(await self._show())

    async def show_artist_commentaries(self) -> ArtistCommentary:
        """Show post's artists commentaries"""
        url = f'{self.get_root_url()}/posts/{self.id}/artist_commentary.json'
        return ArtistCommentary.model_validate(await self.get_json(url=url))


class DanbooruWikiBase(DanbooruCommonBase, abc.ABC):
    """Wiki, Docs: https://danbooru.donmai.us/wiki_pages/api:wikis"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/wiki_pages.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/wiki_pages/{self.id}.json'

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


class DanbooruArtistVersionBase(DanbooruCommonBase, abc.ABC):
    """ArtistVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:artist_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/artist_versions.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/artist_versions/{self.id}.json'

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


class DanbooruArtistCommentaryVersionBase(DanbooruCommonBase, abc.ABC):
    """ArtistCommentaryVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:artist_commentary_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/artist_commentary_versions.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/artist_commentary_versions/{self.id}.json'

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


class DanbooruNoteVersionBase(DanbooruCommonBase, abc.ABC):
    """NoteVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:note_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/note_versions.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/note_versions/{self.id}.json'

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


class DanbooruPoolVersionBase(DanbooruCommonBase, abc.ABC):
    """PoolVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:pool_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/pool_versions.json'

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


class DanbooruPostVersionBase(DanbooruCommonBase, abc.ABC):
    """PostVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:post_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/post_versions.json'

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


class DanbooruWikiPageVersionBase(DanbooruCommonBase, abc.ABC):
    """WikiPageVersion, Docs: https://danbooru.donmai.us/wiki_pages/api:wiki_page_versions"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/wiki_page_versions.json'

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


class DanbooruCommentBase(DanbooruCommonBase, abc.ABC):
    """Comment, Docs: https://danbooru.donmai.us/wiki_pages/api:comments"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/comments.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/comments/{self.id}.json'

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


class DanbooruDmailBase(DanbooruCommonBase, abc.ABC):
    """Dmail, Docs: https://danbooru.donmai.us/wiki_pages/api:dmails"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/dmails.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/dmails/{self.id}.json'

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


class DanbooruForumPostBase(DanbooruCommonBase, abc.ABC):
    """ForumPost, Docs: https://danbooru.donmai.us/wiki_pages/api:forum_posts"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/forum_posts.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/forum_posts/{self.id}.json'

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


class DanbooruForumTopicBase(DanbooruCommonBase, abc.ABC):
    """ForumTopic, Docs: https://danbooru.donmai.us/wiki_pages/api:forum_topics"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/forum_topics.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/forum_topics/{self.id}.json'

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


class DanbooruPostAppealBase(DanbooruCommonBase, abc.ABC):
    """PostAppeal, Docs: https://danbooru.donmai.us/wiki_pages/api:post_appeals"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/post_appeals.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/post_appeals/{self.id}.json'

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


class DanbooruPostFlagBase(DanbooruCommonBase, abc.ABC):
    """PostFlag, Docs: https://danbooru.donmai.us/wiki_pages/api:post_flags"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/post_flags.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/post_flags/{self.id}.json'

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


class DanbooruTagBase(DanbooruCommonBase, abc.ABC):
    """Tag, Docs: https://danbooru.donmai.us/wiki_pages/api:tags"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/tags.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/tags/{self.id}.json'

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


class DanbooruTagAliasBase(DanbooruCommonBase, abc.ABC):
    """TagAlias, Docs: https://danbooru.donmai.us/wiki_pages/api:tag_aliases"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/tag_aliases.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/tag_aliases/{self.id}.json'

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


class DanbooruTagImplicationBase(DanbooruCommonBase, abc.ABC):
    """TagImplication, Docs: https://danbooru.donmai.us/wiki_pages/api:tag_implications"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/tag_implications.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/tag_implications/{self.id}.json'

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


class DanbooruUploadBase(DanbooruCommonBase, abc.ABC):
    """Upload, Docs: https://danbooru.donmai.us/wiki_pages/api:uploads"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/uploads.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/uploads/{self.id}.json'

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


class DanbooruUserBase(DanbooruCommonBase, abc.ABC):
    """User, Docs: https://danbooru.donmai.us/wiki_pages/api:users"""

    def __init__(self, id_: int):
        self.id = id_

    @classmethod
    def get_index_url(cls) -> str:
        return f'{cls.get_root_url()}/users.json'

    def get_target_url(self) -> str:
        return f'{self.get_root_url()}/users/{self.id}.json'

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
        url = f'{cls.get_root_url()}/profile.json'
        return User.model_validate(await cls.get_json(url=url))

    async def show(self) -> User:
        """Show user data"""
        return User.model_validate(await self._show())


class DanbooruAPIBase:
    """Danbooru API 基类"""

    Type_T = TypeVar("Type_T", bound=Type[DanbooruCommonBase])

    def __init__(self, root_url: str) -> None:
        self._root_url = root_url

        self.Artist = self.create_new_common_class(DanbooruArtistBase)
        self.ArtistCommentary = self.create_new_common_class(DanbooruArtistCommentaryBase)
        self.Note = self.create_new_common_class(DanbooruNoteBase)
        self.Pool = self.create_new_common_class(DanbooruPoolBase)
        self.Post = self.create_new_common_class(DanbooruPostBase)
        self.Wiki = self.create_new_common_class(DanbooruWikiBase)
        self.ArtistVersion = self.create_new_common_class(DanbooruArtistVersionBase)
        self.ArtistCommentaryVersion = self.create_new_common_class(DanbooruArtistCommentaryVersionBase)
        self.NoteVersion = self.create_new_common_class(DanbooruNoteVersionBase)
        self.PoolVersion = self.create_new_common_class(DanbooruPoolVersionBase)
        self.PostVersion = self.create_new_common_class(DanbooruPostVersionBase)
        self.WikiPageVersion = self.create_new_common_class(DanbooruWikiPageVersionBase)
        self.Comment = self.create_new_common_class(DanbooruCommentBase)
        self.Dmail = self.create_new_common_class(DanbooruDmailBase)
        self.ForumPost = self.create_new_common_class(DanbooruForumPostBase)
        self.ForumTopic = self.create_new_common_class(DanbooruForumTopicBase)
        self.PostAppeal = self.create_new_common_class(DanbooruPostAppealBase)
        self.PostFlag = self.create_new_common_class(DanbooruPostFlagBase)
        self.Tag = self.create_new_common_class(DanbooruTagBase)
        self.TagAlias = self.create_new_common_class(DanbooruTagAliasBase)
        self.TagImplication = self.create_new_common_class(DanbooruTagImplicationBase)
        self.Upload = self.create_new_common_class(DanbooruUploadBase)
        self.User = self.create_new_common_class(DanbooruUserBase)

    def create_new_common_class(self, class_: Type_T) -> Type_T:
        class _NewClass(class_):
            @classmethod
            def get_root_url(cls) -> str:
                return self._root_url

        return _NewClass


__all__ = [
    'DanbooruArtistBase',
    'DanbooruArtistCommentaryBase',
    'DanbooruNoteBase',
    'DanbooruPoolBase',
    'DanbooruPostBase',
    'DanbooruWikiBase',
    'DanbooruArtistVersionBase',
    'DanbooruArtistCommentaryVersionBase',
    'DanbooruNoteVersionBase',
    'DanbooruPoolVersionBase',
    'DanbooruPostVersionBase',
    'DanbooruWikiPageVersionBase',
    'DanbooruCommentBase',
    'DanbooruDmailBase',
    'DanbooruForumPostBase',
    'DanbooruForumTopicBase',
    'DanbooruPostAppealBase',
    'DanbooruPostFlagBase',
    'DanbooruTagBase',
    'DanbooruTagAliasBase',
    'DanbooruTagImplicationBase',
    'DanbooruUploadBase',
    'DanbooruUserBase',
    'DanbooruAPIBase',
]
