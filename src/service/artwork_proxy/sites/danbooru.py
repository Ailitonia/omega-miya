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

from src.utils.booru_api import danbooru_api
from ..add_ons import ImageOpsMixin
from ..internal import BaseArtworkProxy
from ..models import ArtworkData, ArtworkPageFile

if TYPE_CHECKING:
    from src.utils.booru_api.models.danbooru import PostMediaAsset, PostVariantTypes


class _DanbooruArtworkProxy(BaseArtworkProxy):
    """Danbooru 图库统一接口实现"""

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'danbooru'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        return await danbooru_api.get_resource_as_bytes(url=url, timeout=timeout)

    @classmethod
    async def _get_resource_as_text(cls, url: str, *, timeout: int = 10) -> str:
        return await danbooru_api.get_resource_as_text(url=url, timeout=timeout)

    @staticmethod
    def _get_variant_page_file(variant: Optional["PostVariantTypes"]) -> ArtworkPageFile:
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
    def _get_preview_file(cls, media_asset: "PostMediaAsset") -> ArtworkPageFile:
        return cls._get_variant_page_file(variant=media_asset.variant_type_180)

    @classmethod
    def _get_regular_file(cls, media_asset: "PostMediaAsset") -> ArtworkPageFile:
        if media_asset.variant_type_sample is not None:
            return cls._get_variant_page_file(variant=media_asset.variant_type_sample)
        elif media_asset.variant_type_720 is not None:
            return cls._get_variant_page_file(variant=media_asset.variant_type_720)
        else:
            return cls._get_variant_page_file(variant=media_asset.variant_type_360)

    @classmethod
    def _get_original_file(cls, media_asset: "PostMediaAsset") -> ArtworkPageFile:
        if media_asset.variant_type_full is not None:
            return cls._get_variant_page_file(variant=media_asset.variant_type_full)
        else:
            return cls._get_variant_page_file(variant=media_asset.variant_type_original)

    @classmethod
    async def _search(cls, keyword: Optional[str]) -> list[str | int]:
        if keyword is None:
            artwork_data = await danbooru_api.Post.random()
            return [artwork_data.id]
        else:
            artworks_data = await danbooru_api.Post.index(tags=keyword)
            return [x.id for x in artworks_data]

    async def _query(self) -> ArtworkData:
        artwork_data = await danbooru_api.Post(id_=self.i_aid).show()

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

        return ArtworkData.model_validate({
            'origin': self.get_base_origin_name(),
            'aid': artwork_data.id,
            'title': artwork_data.tag_string_copyright,
            'uid': artwork_data.uploader_id,
            'uname': artwork_data.tag_string_artist,
            'classification': classification,
            'rating': rating,
            'width': artwork_data.image_width,
            'height': artwork_data.image_height,
            'tags': tags_general,
            'description': None,
            'source': artwork_data.source,
            'pages': [{
                'preview_file': self._get_preview_file(media_asset=artwork_data.media_asset),
                'regular_file': self._get_regular_file(media_asset=artwork_data.media_asset),
                'original_file': self._get_original_file(media_asset=artwork_data.media_asset)
            }]
        })

    async def get_std_desc(self, *, desc_len_limit: int = 128) -> str:
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

    async def get_std_preview_desc(self, *, text_len_limit: int = 12) -> str:
        artwork_data = await self.query()

        artist = f"Artist: {artwork_data.uname}"
        artist = f"{artist[:text_len_limit]}..." if len(artist) > text_len_limit else artist

        return f'{artwork_data.origin.title()}\nID: {artwork_data.aid}\n {artist}'


class DanbooruArtworkProxy(_DanbooruArtworkProxy, ImageOpsMixin):
    """Danbooru 图库统一接口实现"""


__all__ = [
    'DanbooruArtworkProxy',
]
