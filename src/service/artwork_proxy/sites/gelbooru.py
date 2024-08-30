"""
@Author         : Ailitonia
@Date           : 2024/8/15 10:17:11
@FileName       : gelbooru.py
@Project        : omega-miya
@Description    : Gelbooru 图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from typing import Optional

from src.utils.booru_api import gelbooru_api
from src.utils.booru_api.gelbooru import BaseGelbooruAPI, GelbooruAPI
from ..add_ons import ImageOpsMixin
from ..internal import BaseArtworkProxy
from ..models import ArtworkData


class BaseGelbooruArtworkProxy(BaseArtworkProxy, abc.ABC):
    """Gelbooru 图库统一接口实现"""

    @classmethod
    @abc.abstractmethod
    def _get_api(cls) -> BaseGelbooruAPI:
        """内部方法, 获取 API 实例"""
        raise NotImplementedError

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        return await cls._get_api().get_resource_as_bytes(url=url, timeout=timeout)

    @classmethod
    async def _get_resource_as_text(cls, url: str, *, timeout: int = 10) -> str:
        return await cls._get_api().get_resource_as_text(url=url, timeout=timeout)

    @classmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        artworks_data = await cls._get_api().posts_index(tags='sort:random', limit=limit)
        return [x.id for x in artworks_data.post]

    @classmethod
    async def _search(cls, keyword: str, *, page: Optional[int] = None, **kwargs) -> list[str | int]:
        artworks_data = await cls._get_api().posts_index(tags=keyword, page=page, **kwargs)
        return [x.id for x in artworks_data.post]

    async def _query(self) -> ArtworkData:
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

        original_url = 'https://example.com/FileNotFound' if not artwork_data.file_url else artwork_data.file_url
        regular_url = original_url if not artwork_data.sample_url else artwork_data.sample_url
        preview_url = regular_url if not artwork_data.preview_url else artwork_data.preview_url

        return ArtworkData.model_validate({
            'origin': self.get_base_origin_name(),
            'aid': artwork_data.id,
            'title': artwork_data.title,
            'uid': artwork_data.creator_id,
            'uname': 'Unknown',
            'classification': classification,
            'rating': rating,
            'width': artwork_data.width,
            'height': artwork_data.height,
            'tags': tags,
            'description': None,
            'source': artwork_data.source,
            'pages': [{
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
            }]
        })

    async def get_std_desc(self, *, desc_len_limit: int = 128) -> str:
        artwork_data = await self.query()

        tag_t = ' '.join(f'#{x.strip()}' for x in artwork_data.tags)
        desc_t = (
            f'ID: {artwork_data.aid}\n'
            f'Rating: {artwork_data.rating.name}\n'
            f'Source: {artwork_data.source}\n\n'
            f'Tags: {tag_t}'
        )
        return desc_t.strip()

    async def get_std_preview_desc(self, *, text_len_limit: int = 12) -> str:
        artwork_data = await self.query()
        return f'{artwork_data.origin.title()}\nID: {artwork_data.aid}'


class GelbooruArtworkProxy(BaseGelbooruArtworkProxy, ImageOpsMixin):
    """https://gelbooru.com 主站图库统一接口实现"""

    @classmethod
    def _get_api(cls) -> GelbooruAPI:
        return gelbooru_api

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'gelbooru'


__all__ = [
    'GelbooruArtworkProxy',
]
