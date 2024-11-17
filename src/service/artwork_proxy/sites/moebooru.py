"""
@Author         : Ailitonia
@Date           : 2024/8/15 下午7:01
@FileName       : moebooru
@Project        : nonebot2_miya
@Description    : moebooru 图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc

from src.utils.booru_api import behoimi_api, konachan_api, konachan_safe_api, yandere_api
from src.utils.booru_api.moebooru import BaseMoebooruAPI, BehoimiAPI, KonachanAPI, KonachanSafeAPI, YandereAPI
from ..add_ons import ImageOpsPlusPoolMixin
from ..internal import BaseArtworkProxy
from ..models import ArtworkData, ArtworkPool


class BaseMoebooruArtworkProxy(BaseArtworkProxy, abc.ABC):
    """Moebooru 图库统一接口实现"""

    @classmethod
    @abc.abstractmethod
    def _get_api(cls) -> BaseMoebooruAPI:
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
        artworks_data = await cls._get_api().posts_index(tags='order:random', limit=limit)
        return [x.id for x in artworks_data]

    @classmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        artworks_data = await cls._get_api().posts_index(tags=keyword, page=page, **kwargs)
        return [x.id for x in artworks_data]

    async def _query(self) -> ArtworkData:
        artwork_data = await self._get_api().post_show(id_=self.i_aid)

        """moebooru 图站收录作品默认分类分级
        (classification, rating)
                            has_ai-generated_tag  status_is_active  other_status
        rate: Safe                (1,  0)             (2,  0)          (0,  0)
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

        match artwork_data.rating:
            case 's':
                rating = 0
            case 'q':
                rating = 2
            case 'e':
                rating = 3
            case _:
                rating = -1

        original_url = 'https://example.com/FileNotFound' if not artwork_data.file_url else artwork_data.file_url
        regular_url = original_url if not artwork_data.sample_url else artwork_data.sample_url
        preview_url = regular_url if not artwork_data.preview_url else artwork_data.preview_url

        return ArtworkData.model_validate({
            'origin': self.get_base_origin_name(),
            'aid': artwork_data.id,
            'title': f'Upload by: {artwork_data.author}',
            'uid': -1 if artwork_data.creator_id is None else artwork_data.creator_id,
            'uname': artwork_data.author,
            'classification': classification,
            'rating': rating,
            'width': artwork_data.width,
            'height': artwork_data.height,
            'tags': tags,
            'description': None,
            'like_count': artwork_data.score,
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


class BaseMoebooruPlusPoolArtworkProxy(BaseMoebooruArtworkProxy, ImageOpsPlusPoolMixin, abc.ABC):
    """Moebooru 图库统一接口附加图集处理插件"""

    @classmethod
    async def _query_pool(cls, pool_id: str) -> ArtworkPool:  # 提前实现 ImageOpsPlusPoolMixin 基类方法
        pool_data = await cls._get_api().pool_posts_show(pool_id=int(pool_id))

        return ArtworkPool.model_validate({
            'origin': cls.get_base_origin_name(),
            'pool_id': pool_id,
            'name': pool_data.name,
            'description': pool_data.description,
            'artwork_ids': [] if pool_data.posts is None else pool_data.posts,
        })


class BehoimiArtworkProxy(BaseMoebooruPlusPoolArtworkProxy):
    """http://behoimi.org 主站图库统一接口实现"""

    @classmethod
    def _get_api(cls) -> BehoimiAPI:
        return behoimi_api

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'behoimi'


class KonachanArtworkProxy(BaseMoebooruPlusPoolArtworkProxy):
    """https://konachan.com 主站图库统一接口实现, 主站有 Cloudflare 盾, 建议直接使用全年龄站接口"""

    @classmethod
    def _get_api(cls) -> KonachanAPI:
        return konachan_api

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'konachan'


class KonachanSafeArtworkProxy(BaseMoebooruPlusPoolArtworkProxy):
    """https://konachan.net 全年龄站图库统一接口实现, 与主站共用后端, 只是网站页面不显示 rating:E 的作品"""

    @classmethod
    def _get_api(cls) -> KonachanSafeAPI:
        return konachan_safe_api

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'konachan'


class YandereArtworkProxy(BaseMoebooruPlusPoolArtworkProxy):
    """https://yande.re 主站图库统一接口实现"""

    @classmethod
    def _get_api(cls) -> YandereAPI:
        return yandere_api

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'yandere'


__all__ = [
    'BehoimiArtworkProxy',
    'KonachanArtworkProxy',
    'KonachanSafeArtworkProxy',
    'YandereArtworkProxy',
]
