"""
@Author         : Ailitonia
@Date           : 2024/8/15 10:17:11
@FileName       : gelbooru.py
@Project        : omega-miya
@Description    : Gelbooru 图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.utils.booru_api.gelbooru import GelbooruAPI
from ..internal import BaseArtworkProxy
from ..models import ArtworkProxyData, ArtistUserData, ArtworkPoolData


class GelbooruArtworkProxy(BaseArtworkProxy):
    """https://gelbooru.com 主站图库统一接口实现"""

    _api: GelbooruAPI | None = None

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'gelbooru'

    @classmethod
    def _get_api(cls) -> GelbooruAPI:
        """内部方法, 获取 API 实例"""
        if cls._api is None:
            cls._api = GelbooruAPI()
        return cls._api

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        return await cls._get_api().get_resource_as_bytes(url=url, timeout=timeout)

    @classmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        artworks_data = await cls._get_api().posts_index(tags='sort:random', limit=limit)
        return [x.id for x in artworks_data.post]

    @classmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        artworks_data = await cls._get_api().posts_index(tags=keyword, page=page, **kwargs)
        return [x.id for x in artworks_data.post]

    async def _query(self) -> ArtworkProxyData:
        artwork_data = await self._get_api().post_show(id_=self.i_aid)

        """Gelbooru 图站收录作品默认分类分级
        (classification, rating)
                            has_ai-generated_tag  status_is_active  other_status
        rate: General             (1,  0)             (2,  0)          (0,  0)
        rate: Sensitive           (1,  1)             (2,  1)          (0,  1)
        rate: Questionable        (1,  2)             (2,  2)          (0,  2)
        rate: Explicit            (1,  3)             (2,  3)          (0,  3)
        rate: Unknown             (1, -1)             (2, -1)          (0, -1)
        """

        tags = artwork_data.tags.split()
        ai_generated_tags = {
            'ai-assisted',
            'ai-generated',
            'midjourney',
            'nai_diffusion',
            'stable_diffusion',
        }

        if any(set(tags) & ai_generated_tags):
            classification = 1
        elif artwork_data.status == 'active':
            classification = 2
        else:
            classification = 0

        match artwork_data.rating.value:
            case 'general':
                rating = 0
            case 'sensitive':
                rating = 1
            case 'questionable':
                rating = 2
            case 'explicit':
                rating = 3
            case _:
                rating = -1

        original_url = artwork_data.file_url if artwork_data.file_url else 'https://example.com/FileNotFound'
        regular_url = artwork_data.sample_url if artwork_data.sample_url else original_url
        preview_url = artwork_data.preview_url if artwork_data.preview_url else regular_url

        return ArtworkProxyData.model_validate({
            'origin': self._get_base_origin_name(),
            'aid': artwork_data.id,
            'uid': artwork_data.creator_id,
            'title': artwork_data.title,
            'uname': 'Unknown',
            'classification': classification,
            'rating': rating,
            'width': artwork_data.width,
            'height': artwork_data.height,
            'tags': tags,
            'description': None,
            'like_count': artwork_data.score,
            'source': artwork_data.source,
            'pages': [{
                'page_index': 0,
                'preview_file': {
                    'url': preview_url,
                    'file_ext': self.parse_url_file_suffix(preview_url),
                    'width': artwork_data.preview_width,
                    'height': artwork_data.preview_height,
                },
                'regular_file': {
                    'url': regular_url,
                    'file_ext': self.parse_url_file_suffix(regular_url),
                    'width': artwork_data.sample_width,
                    'height': artwork_data.sample_height,
                },
                'original_file': {
                    'url': original_url,
                    'file_ext': self.parse_url_file_suffix(original_url),
                    'width': artwork_data.width,
                    'height': artwork_data.height,
                },
            }],
        })

    async def get_std_desc(self, *, split_len: int = 128) -> str:
        artwork_data = await self.query()

        tag_t = ' '.join(f'#{x.strip()}' for x in artwork_data.tags)
        desc_t = (
            f'ID: {artwork_data.aid}\n'
            f'Rating: {artwork_data.rating.name}\n'
            f'Source: {artwork_data.source}\n\n'
            f'Tags: {tag_t}'
        )
        return desc_t.strip()

    async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
        artwork_data = await self.query()
        return f'{artwork_data.origin.title()}\nID: {artwork_data.aid}'

    @classmethod
    async def _query_pool(cls, pool_id: str | int) -> ArtworkPoolData:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _discovery(cls, *, limit: int = 20) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _daily_ranking(cls, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _weekly_ranking(cls, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _monthly_ranking(cls, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _query_user(cls, uid: str | int) -> ArtistUserData:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _query_follow_latest(cls, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError


__all__ = [
    'GelbooruArtworkProxy',
]
