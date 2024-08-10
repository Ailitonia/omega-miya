"""
@Author         : Ailitonia
@Date           : 2024/8/9 下午8:47
@FileName       : danbooru
@Project        : nonebot2_miya
@Description    : Danbooru 图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.utils.danbooru_api import danbooru_api

from ..add_ons import ImageOpsMixin
from ..internal import BaseArtworkProxy
from ..models import ArtworkData


class _DanbooruArtworkProxy(BaseArtworkProxy):
    """Danbooru 图库统一接口实现"""

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'danbooru'

    @classmethod
    async def _get_resource(cls, url: str, *, timeout: int = 30) -> str | bytes | None:
        return await danbooru_api.get_resource(url=url, timeout=timeout)

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
                'preview_file': artwork_data.preview_file_model,
                'regular_file': artwork_data.regular_file_model,
                'original_file': artwork_data.original_file_model
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
