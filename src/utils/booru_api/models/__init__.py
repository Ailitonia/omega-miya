"""
@Author         : Ailitonia
@Date           : 2024/8/13 13:54:32
@FileName       : models
@Project        : omega-miya
@Description    : booru models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .danbooru import Artist as DanbooruArtist
from .danbooru import ArtistCommentary as DanbooruArtistCommentary
from .danbooru import ArtistCommentaryVersion as DanbooruArtistCommentaryVersion
from .danbooru import ArtistVersion as DanbooruArtistVersion
from .danbooru import Comment as DanbooruComment
from .danbooru import Dmail as DanbooruDmail
from .danbooru import ForumPost as DanbooruForumPost
from .danbooru import ForumTopic as DanbooruForumTopic
from .danbooru import Note as DanbooruNote
from .danbooru import NoteVersion as DanbooruNoteVersion
from .danbooru import Pool as DanbooruPool
from .danbooru import PoolVersion as DanbooruPoolVersion
from .danbooru import Post as DanbooruPost
from .danbooru import PostAppeal as DanbooruPostAppeal
from .danbooru import PostFlag as DanbooruPostFlag
from .danbooru import PostMediaAsset as DanbooruPostMediaAsset
from .danbooru import PostVariantTypes as DanbooruPostVariantTypes
from .danbooru import PostVersion as DanbooruPostVersion
from .danbooru import Tag as DanbooruTag
from .danbooru import TagAlias as DanbooruTagAlias
from .danbooru import TagImplication as DanbooruTagImplication
from .danbooru import Upload as DanbooruUpload
from .danbooru import User as DanbooruUser
from .danbooru import Wiki as DanbooruWiki
from .danbooru import WikiPageVersion as DanbooruWikiPageVersion
from .gelbooru import CommentsData as GelbooruCommentsData
from .gelbooru import PostsData as GelbooruPostsData
from .gelbooru import TagsData as GelbooruTagsData
from .gelbooru import UsersData as GelbooruUsersData

__all__ = [
    'DanbooruArtist',
    'DanbooruArtistCommentary',
    'DanbooruNote',
    'DanbooruPool',
    'DanbooruPost',
    'DanbooruPostMediaAsset',
    'DanbooruPostVariantTypes',
    'DanbooruWiki',
    'DanbooruArtistVersion',
    'DanbooruArtistCommentaryVersion',
    'DanbooruNoteVersion',
    'DanbooruPoolVersion',
    'DanbooruPostVersion',
    'DanbooruWikiPageVersion',
    'DanbooruComment',
    'DanbooruDmail',
    'DanbooruForumPost',
    'DanbooruForumTopic',
    'DanbooruPostAppeal',
    'DanbooruPostFlag',
    'DanbooruTag',
    'DanbooruTagAlias',
    'DanbooruTagImplication',
    'DanbooruUpload',
    'DanbooruUser',
    'GelbooruPostsData',
    'GelbooruTagsData',
    'GelbooruUsersData',
    'GelbooruCommentsData',
]
