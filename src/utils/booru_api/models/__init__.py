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
from .gelbooru import Comment as GelbooruComment
from .gelbooru import CommentsData as GelbooruCommentsData
from .gelbooru import Post as GelbooruPost
from .gelbooru import PostRating as GelbooruPostRating
from .gelbooru import PostsData as GelbooruPostsData
from .gelbooru import Tag as GelbooruTag
from .gelbooru import TagsData as GelbooruTagsData
from .gelbooru import User as GelbooruUser
from .gelbooru import UsersData as GelbooruUsersData
from .moebooru import Artist as MoebooruArtist
from .moebooru import Comment as MoebooruComment
from .moebooru import FavoritedUsers as MoebooruFavoritedUsers
from .moebooru import Forum as MoebooruForum
from .moebooru import Note as MoebooruNote
from .moebooru import NoteHistory as MoebooruNoteHistory
from .moebooru import Pool as MoebooruPool
from .moebooru import Post as MoebooruPost
from .moebooru import SimilarPosts as MoebooruSimilarPosts
from .moebooru import Tag as MoebooruTag
from .moebooru import TagsRelated as MoebooruTagsRelated
from .moebooru import User as MoebooruUser
from .moebooru import Wiki as MoebooruWiki


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
    'GelbooruPost',
    'GelbooruPostRating',
    'GelbooruTag',
    'GelbooruUser',
    'GelbooruComment',
    'GelbooruPostsData',
    'GelbooruTagsData',
    'GelbooruUsersData',
    'GelbooruCommentsData',
    'MoebooruPost',
    'MoebooruSimilarPosts',
    'MoebooruTag',
    'MoebooruTagsRelated',
    'MoebooruArtist',
    'MoebooruComment',
    'MoebooruWiki',
    'MoebooruNote',
    'MoebooruNoteHistory',
    'MoebooruUser',
    'MoebooruForum',
    'MoebooruPool',
    'MoebooruFavoritedUsers',
]
