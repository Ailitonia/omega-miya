"""
@Author         : Ailitonia
@Date           : 2024/8/5 16:14:50
@FileName       : pixiv.py
@Project        : omega-miya
@Description    : Pixiv 图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random

from src.utils.pixiv_api import PixivArtwork, PixivUser, Pixivision
from ..internal import BaseArtworkProxy
from ..models import ArtistUserData, ArtworkPoolData, ArtworkProxyData


class PixivArtworkProxy(BaseArtworkProxy):
    """Pixiv 图库统一接口实现"""

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'pixiv'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        return await PixivArtwork.get_resource_as_bytes(url=url, timeout=timeout)

    @classmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        artworks_data = await PixivArtwork.query_discovery_artworks()
        recommend_pids = list(artworks_data.recommend_pids)
        return random.sample(recommend_pids, k=min(limit, len(recommend_pids)))

    @classmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        page = 1 if page is None else page
        if kwargs:
            artworks_data = await PixivArtwork.search(word=keyword, page=page, **kwargs)
            return [x.id for x in artworks_data.artworks]
        else:
            artworks_data = await PixivArtwork.search_by_default_popular_condition(word=keyword, page=page)
            return [x.id for x in artworks_data.artworks]

    async def _query(self) -> ArtworkProxyData:
        artwork_data = await PixivArtwork(pid=self.i_aid).query_artwork()

        """Pixiv 主站作品默认分类分级
        (classification, rating)
                    is_ai     not_ai
        is_R18G    (1,  3)    (0,  3)
        is_R18     (1,  2)    (0,  2)
        not_R18    (1, -1)    (0, -1)
        """

        if artwork_data.is_r18:
            if artwork_data.sanity_level > 1:
                rating = 3
            else:
                rating = 2
        else:
            rating = -1

        return ArtworkProxyData.model_validate({
            'origin': self._get_base_origin_name(),
            'aid': artwork_data.pid,
            'uid': artwork_data.uid,
            'title': artwork_data.title,
            'uname': artwork_data.uname,
            'classification': 1 if artwork_data.is_ai else 0,
            'rating': rating,
            'width': artwork_data.width,
            'height': artwork_data.height,
            'tags': artwork_data.tags,
            'description': artwork_data.description,
            'like_count': artwork_data.like_count,
            'bookmark_count': artwork_data.bookmark_count,
            'view_count': artwork_data.view_count,
            'comment_count': artwork_data.comment_count,
            'source': artwork_data.url,
            'pages': [
                {
                    'page_index': index,
                    'preview_file': {
                        'url': page.small,
                        'file_ext': self.parse_url_file_suffix(page.small),
                        'width': None,
                        'height': None,
                    },
                    'regular_file': {
                        'url': page.regular,
                        'file_ext': self.parse_url_file_suffix(page.regular),
                        'width': None,
                        'height': None,
                    },
                    'original_file': {
                        'url': page.original,
                        'file_ext': self.parse_url_file_suffix(page.original),
                        'width': artwork_data.width,
                        'height': artwork_data.height,
                    }
                }
                for index, page in artwork_data.index_pages.items()
            ],
            'extra_resource': (
                [artwork_data.ugoira_meta.originalSrc]
                if artwork_data.ugoira_meta is not None
                else []
            ),
            'published_at': artwork_data.published_at,
        })

    async def get_std_desc(self, *, split_len: int = 128) -> str:
        artwork_data = await self.query()

        tag_t = ' '.join(f'#{x.strip()}' for x in artwork_data.tags)

        if not artwork_data.description:
            desc_t = f'「{artwork_data.title}」/「{artwork_data.uname}」\n{tag_t}\n{artwork_data.source}'
        else:
            desc_t = (
                f'「{artwork_data.title}」/「{artwork_data.uname}」\n{tag_t}\n{artwork_data.source}\n{"-" * 16}\n'
                f'{artwork_data.description[:split_len]}'
                f'{"." * 6 if len(artwork_data.description) > split_len else ""}'
            )
        return desc_t.strip()

    async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
        artwork_data = await self.query()

        origin = f'{artwork_data.origin.title()}: {artwork_data.aid}'
        title = (
            f'{artwork_data.title[:split_len]}...'
            if len(artwork_data.title) > split_len
            else artwork_data.title
        )

        author = f'Author: {artwork_data.uname}'
        author = f'{author[:split_len]}...' if len(author) > split_len else author

        return f'{origin}\n{title}\n{author}'

    @classmethod
    async def _query_pool(cls, pool_id: str | int) -> ArtworkPoolData:
        pool_data = await Pixivision(aid=pool_id).query_article()
        return ArtworkPoolData.model_validate({
            'origin': cls._get_base_origin_name(),
            'pool_id': str(pool_id),
            'name': pool_data.title,
            'description': pool_data.description,
            'artwork_ids': [x.artwork_id for x in pool_data.artwork_list],
        })

    @classmethod
    async def _discovery(cls, *, limit: int = 20) -> list[str | int]:
        artwork_ids = (await PixivArtwork.query_discovery_artworks(limit=limit)).recommend_pids
        return list(artwork_ids[:limit])

    @classmethod
    async def _recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[str | int]:
        if isinstance(base_aid, int) or (isinstance(base_aid, str) and base_aid.isdecimal()):
            artwork_ids = (await PixivArtwork(pid=base_aid).query_recommend(init_limit=limit)).illust_ids
        else:
            artwork_ids = (await PixivArtwork.query_top_illust()).recommend_pids
        return list(artwork_ids[:limit])

    @classmethod
    async def _daily_ranking(cls, page: int) -> list[str | int]:
        ranking_data = await PixivArtwork.query_ranking(mode='daily', page=page, content='illust')
        return [x.illust_id for x in ranking_data.contents]

    @classmethod
    async def _weekly_ranking(cls, page: int) -> list[str | int]:
        ranking_data = await PixivArtwork.query_ranking(mode='weekly', page=page, content='illust')
        return [x.illust_id for x in ranking_data.contents]

    @classmethod
    async def _monthly_ranking(cls, page: int) -> list[str | int]:
        ranking_data = await PixivArtwork.query_ranking(mode='monthly', page=page, content='illust')
        return [x.illust_id for x in ranking_data.contents]

    @classmethod
    async def _query_user(cls, uid: str | int) -> ArtistUserData:
        user_data = await PixivUser(uid=uid).query_user()
        return ArtistUserData.model_validate({
            'origin': cls._get_base_origin_name(),
            'uid': user_data.user_id,
            'name': user_data.name,
            'profile_image': user_data.image,
            'artwork_ids': user_data.manga_illusts,
        })

    @classmethod
    async def _query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[str | int]:
        return list((await PixivUser(uid=uid).query_user_bookmarks(page=page)).illust_ids)

    @classmethod
    async def _query_follow_latest(cls, page: int, *, filter_tag: str | None = None) -> list[str | int]:
        return list(
            (await PixivArtwork.query_following_user_latest_illust(page=page, tag=filter_tag)).illust_ids
        )


__all__ = [
    'PixivArtworkProxy',
]
