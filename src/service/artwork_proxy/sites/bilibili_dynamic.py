"""
@Author         : Ailitonia
@Date           : 2026/10/1 16:21
@FileName       : bilibili_dynamic
@Project        : omega-miya
@Description    : bilibili 动态发布图片图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime

from src.utils.bilibili_api import BilibiliDynamic
from ..internal import BaseArtworkProxy
from ..models import ArtworkProxyData, ArtistUserData, ArtworkPoolData


class BilibiliDynamicPicArtworkProxy(BaseArtworkProxy):
    """bilibili 动态发布图片图库统一接口实现"""

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'bilibili_dynamic_pic'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        return await BilibiliDynamic.get_resource_as_bytes(url=url, timeout=timeout)

    @classmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    async def _query(self) -> ArtworkProxyData:
        dynamic_data = await BilibiliDynamic.query_dynamic_detail(id_=self.s_aid)

        if (opus_data := getattr(dynamic_data.data.item.modules.module_dynamic.major, 'opus')) is None:
            raise ValueError(f'bilibili_dynamic {self.s_aid} has no opus major content')
        if not (pics := list(opus_data.pics)):
            raise ValueError(f'bilibili_dynamic {self.s_aid} has no image content')

        """bilibili 动态图片默认分类分级
        (classification, rating)
                (0, -1)
        默认图片分类分级未知, 虽然大概不会有 r18 图片, 但 nsfw 的涩图还是有的, 导入数据库的本地图片另作处理
        """

        return ArtworkProxyData.model_validate({
            'origin': self._get_base_origin_name(),
            'aid': dynamic_data.data.item.id_str,
            'uid': dynamic_data.data.item.modules.module_author.mid,
            'title': opus_data.title,
            'uname': dynamic_data.data.item.modules.module_author.name,
            'classification': 0,
            'rating': -1,
            'width': pics[0].width,
            'height': pics[0].height,
            'tags': [],
            'description': dynamic_data.data.item.dyn_text,
            'source': f'https://t.bilibili.com/{dynamic_data.data.item.id_str}',
            'pages': [
                {
                    'page_index': index,
                    'preview_file': {
                        'url': pic.url,
                        'file_ext': self.parse_url_file_suffix(pic.url),
                        'width': pic.width,
                        'height': pic.height,
                    },
                    'regular_file': {
                        'url': pic.url,
                        'file_ext': self.parse_url_file_suffix(pic.url),
                        'width': pic.width,
                        'height': pic.height,
                    },
                    'original_file': {
                        'url': pic.url,
                        'file_ext': self.parse_url_file_suffix(pic.url),
                        'width': pic.width,
                        'height': pic.height,
                    }
                }
                for index, pic in enumerate(pics)
            ],
            'published_at': datetime.fromtimestamp(dynamic_data.data.item.modules.module_author.pub_ts),
        })

    async def get_std_desc(self, *, split_len: int = 128) -> str:
        artwork_data = await self.query()
        return artwork_data.description[:split_len]

    async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
        artwork_data = await self.query()
        return f'{artwork_data.uname}的动态'

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
    async def _query_follow_latest(cls, page: int, *, filter_tag: str | None = None) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError


__all__ = [
    'BilibiliDynamicPicArtworkProxy',
]
