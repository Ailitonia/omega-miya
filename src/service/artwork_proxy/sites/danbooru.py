"""
@Author         : Ailitonia
@Date           : 2024/8/9 下午8:47
@FileName       : danbooru
@Project        : nonebot2_miya
@Description    : Danbooru 图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Optional

from src.exception import WebSourceException
from src.utils.booru_api.danbooru import DanbooruAPI
from ..internal import BaseArtworkProxy
from ..models import ArtworkProxyData, ArtistUserData, ArtworkPageFile, ArtworkPoolData

if TYPE_CHECKING:
    from src.utils.booru_api.models.danbooru import PostMediaAsset, PostVariantTypes


class DanbooruArtworkProxy(BaseArtworkProxy):
    """https://danbooru.donmai.us 主站图库统一接口实现"""

    _api: DanbooruAPI | None = None

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'danbooru'

    @classmethod
    def _get_api(cls) -> DanbooruAPI:
        """内部方法, 获取 API 实例"""
        if cls._api is None:
            cls._api = DanbooruAPI()
        return cls._api

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        return await cls._get_api().get_resource_as_bytes(url=url, timeout=timeout)

    @staticmethod
    def _get_variant_page_file(variant: Optional['PostVariantTypes']) -> ArtworkPageFile:
        """内部方法, 根据作品图片类型变种解析对应 Page 信息"""
        if variant is None:
            model_data = {
                'url': 'https://example.com/FileNotFound',
                'file_ext': 'Unknown',
                'width': None,
                'height': None,
            }
        else:
            model_data = {
                'url': variant.url,
                'file_ext': variant.file_ext,
                'width': variant.width,
                'height': variant.height,
            }
        return ArtworkPageFile.model_validate(model_data)

    @classmethod
    def _get_preview_file(cls, media_asset: 'PostMediaAsset') -> ArtworkPageFile:
        return cls._get_variant_page_file(variant=media_asset.variant_type_180)

    @classmethod
    def _get_regular_file(cls, media_asset: 'PostMediaAsset') -> ArtworkPageFile:
        if media_asset.variant_type_sample is not None:
            return cls._get_variant_page_file(variant=media_asset.variant_type_sample)
        elif media_asset.variant_type_720 is not None:
            return cls._get_variant_page_file(variant=media_asset.variant_type_720)
        else:
            return cls._get_variant_page_file(variant=media_asset.variant_type_360)

    @classmethod
    def _get_original_file(cls, media_asset: 'PostMediaAsset') -> ArtworkPageFile:
        if media_asset.variant_type_original is not None:
            return cls._get_variant_page_file(variant=media_asset.variant_type_original)
        else:
            return cls._get_variant_page_file(variant=media_asset.variant_type_full)

    @classmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        # More likely to timeout due to increased database load.
        # artworks_data = await cls._get_api().posts_index(tags='order:random', limit=limit, **kwargs)

        # May be less reliable than order:random, but significantly faster.
        artworks_data = await cls._get_api().posts_index(tags=f'random:{limit}')

        # Return only get one artwork.
        # artwork_data = await cls._get_api().post_random()

        return [x.id for x in artworks_data]

    @classmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        artworks_data = await cls._get_api().posts_index(tags=keyword, page=page, **kwargs)
        return [x.id for x in artworks_data]

    async def _query(self) -> ArtworkProxyData:
        artwork_data = await self._get_api().post_show(id_=self.i_aid)

        """Danbooru 图站收录作品默认分类分级
        (classification, rating)
                            has_ai-generated_tag  status_is_active  other_status
        rate: General             (1,  0)             (2,  0)          (0,  0)
        rate: Sensitive           (1,  1)             (2,  1)          (0,  1)
        rate: Questionable        (1,  2)             (2,  2)          (0,  2)
        rate: Explicit            (1,  3)             (2,  3)          (0,  3)
        rate: Unknown             (1, -1)             (2, -1)          (0, -1)
        """

        tags_all = artwork_data.tag_string.split()
        tags_meta = artwork_data.tag_string_meta.split()
        tags_general = artwork_data.tag_string_general.split()

        ai_generated_tags = {
            'ai-assisted',
            'ai-generated',
            'midjourney',
            'nai_diffusion',
            'stable_diffusion',
        }

        if any(set(tags_all + tags_meta) & ai_generated_tags):
            classification = 1
        elif any((artwork_data.is_banned, artwork_data.is_deleted, artwork_data.is_flagged, artwork_data.is_pending)):
            classification = 0
        elif artwork_data.media_asset.status == 'active':
            classification = 2
        else:
            classification = 0

        match artwork_data.rating:
            case 'g':
                rating = 0
            case 's':
                rating = 1
            case 'q':
                rating = 2
            case 'e':
                rating = 3
            case _:
                rating = -1

        try:
            commentary_data = await self._get_api().post_show_artist_commentary(id_=self.i_aid)
            title = commentary_data.original_title or commentary_data.translated_title
            description = commentary_data.original_description or commentary_data.translated_description
        except WebSourceException:
            title = artwork_data.tag_string_copyright
            description = None

        return ArtworkProxyData.model_validate({
            'origin': self._get_base_origin_name(),
            'aid': artwork_data.id,
            'uid': artwork_data.uploader_id,
            'title': title,
            'uname': artwork_data.tag_string_artist,
            'classification': classification,
            'rating': rating,
            'width': artwork_data.image_width,
            'height': artwork_data.image_height,
            'tags': tags_general,
            'description': description,
            'like_count': artwork_data.score,
            'source': artwork_data.source,
            'pages': [{
                'page_index': 0,
                'preview_file': self._get_preview_file(media_asset=artwork_data.media_asset),
                'regular_file': self._get_regular_file(media_asset=artwork_data.media_asset),
                'original_file': self._get_original_file(media_asset=artwork_data.media_asset)
            }],
        })

    async def get_std_desc(self, *, split_len: int = 128) -> str:
        artwork_data = await self.query()

        tag_t = ' '.join(f'#{x.strip()}' for x in artwork_data.tags)
        desc_t = (
            f'ID: {artwork_data.aid}\n'
            f'Artist: {artwork_data.uname}\n'
            f'Rating: {artwork_data.rating.name}\n'
            f'Source: {artwork_data.source}\n\n'
            f'Tags: {tag_t}'
        )
        return desc_t.strip()

    async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
        artwork_data = await self.query()

        artist = f'Artist: {artwork_data.uname}'
        artist = f'{artist[:split_len]}...' if len(artist) > split_len else artist

        return f'{artwork_data.origin.title()}\nID: {artwork_data.aid}\n{artist}'

    @classmethod
    async def _query_pool(cls, pool_id: str | int) -> ArtworkPoolData:
        pool_data = await cls._get_api().pool_show(id_=int(pool_id))

        return ArtworkPoolData.model_validate({
            'origin': cls._get_base_origin_name(),
            'pool_id': pool_id,
            'name': pool_data.name,
            'description': pool_data.description,
            'artwork_ids': pool_data.post_ids,
        })

    @classmethod
    async def _discovery(cls, *, limit: int = 20) -> list[str | int]:
        artworks_data = await cls._get_api().explore_popular_posts()
        return [x.id for x in artworks_data[:limit]]

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
    'DanbooruArtworkProxy',
]
