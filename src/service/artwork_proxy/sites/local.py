"""
@Author         : Ailitonia
@Date           : 2024/8/12 16:13:15
@FileName       : local.py
@Project        : omega-miya
@Description    : 本地图片适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from typing import TYPE_CHECKING, Self

from ..internal import ArtworkPageParamType, BaseArtworkProxy
from ..models import ArtworkProxyData, ArtistUserData, ArtworkPoolData

if TYPE_CHECKING:
    from src.resource import TemporaryResource


class LocalCollectedArtworkProxy(BaseArtworkProxy):
    """本地收藏图片适配, 需要自行将图片添加到对应目录中, 缺省 artwork_id 为文件名 (含后缀)"""

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'local_collected_artwork'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        raise NotImplementedError

    @classmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        artwork_path = cls._get_path_config().artwork_path
        return [file.name for file in random.sample(artwork_path.list_all_files(), k=limit)]

    @classmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        artwork_path = cls._get_path_config().artwork_path
        return [file.name for file in artwork_path.list_all_files() if keyword in file.name]

    @classmethod
    async def list_all_artwork(cls) -> list[Self]:
        """列出所有的本地图片作品"""
        artwork_path = cls._get_path_config().artwork_path
        return [cls(file.name) for file in artwork_path.list_all_files()]

    @property
    def self_file(self) -> 'TemporaryResource':
        return self.path_config.artwork_path(self.s_aid)

    async def _query(self) -> ArtworkProxyData:
        self.self_file.raise_not_file()

        """本地图片默认分类分级
        (classification, rating)
                (-1, -1)
        默认本地图片分类分级未知, 导入数据库的本地图片另作处理
        """

        return ArtworkProxyData.model_validate({
            'origin': self._get_base_origin_name(),
            'aid': self.self_file.name,
            'uid': 'Unknown',
            'title': 'Unknown',
            'uname': 'Unknown',
            'classification': -1,
            'rating': -1,
            'width': -1,
            'height': -1,
            'tags': [],
            'description': None,
            'source': 'Unknown',
            'pages': [
                {
                    'page_index': 0,
                    'preview_file': {
                        'url': f'https://example.com/{self.self_file.name}',
                        'file_ext': self.self_file.suffix,
                        'width': None,
                        'height': None,
                    },
                    'regular_file': {
                        'url': f'https://example.com/{self.self_file.name}',
                        'file_ext': self.self_file.suffix,
                        'width': None,
                        'height': None,
                    },
                    'original_file': {
                        'url': f'https://example.com/{self.self_file.name}',
                        'file_ext': self.self_file.suffix,
                        'width': None,
                        'height': None,
                    }
                },
            ],
        })

    async def get_std_desc(self, *, split_len: int = 128) -> str:
        return f'Local collected artwork: {self.self_file.name}'[:split_len]

    async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
        return self.self_file.name[:split_len]

    async def _save_page(
            self,
            page_index: int = 0,
            page_type: 'ArtworkPageParamType' = 'regular',
    ) -> 'TemporaryResource':
        return self.self_file

    @classmethod
    async def _query_pool(cls, pool_id: str | int) -> ArtworkPoolData:
        raise NotImplementedError

    @classmethod
    async def _discovery(cls, *, limit: int = 20) -> list[str | int]:
        raise NotImplementedError

    @classmethod
    async def _recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[str | int]:
        raise NotImplementedError

    @classmethod
    async def _daily_ranking(cls, page: int) -> list[str | int]:
        raise NotImplementedError

    @classmethod
    async def _weekly_ranking(cls, page: int) -> list[str | int]:
        raise NotImplementedError

    @classmethod
    async def _monthly_ranking(cls, page: int) -> list[str | int]:
        raise NotImplementedError

    @classmethod
    async def _query_user(cls, uid: str | int) -> ArtistUserData:
        raise NotImplementedError

    @classmethod
    async def _query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[str | int]:
        raise NotImplementedError

    @classmethod
    async def _query_follow_latest(cls, page: int) -> list[str | int]:
        raise NotImplementedError


__all__ = [
    'LocalCollectedArtworkProxy',
]
