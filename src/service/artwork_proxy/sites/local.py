"""
@Author         : Ailitonia
@Date           : 2024/8/12 16:13:15
@FileName       : local.py
@Project        : omega-miya
@Description    : 本地图片适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Optional

from ..internal import BaseArtworkProxy
from ..models import ArtworkData

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from ..typing import ArtworkPageParamType


class LocalCollectedArtworkProxy(BaseArtworkProxy):
    """本地图片适配, 需要自行将图片添加到对应目录中, 缺省 artwork_id 为文件名 (含后缀)"""

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'local_collected_artwork'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        raise NotImplementedError

    @classmethod
    async def _get_resource_as_text(cls, url: str, *, timeout: int = 10) -> str:
        raise NotImplementedError

    @classmethod
    async def _search(cls, keyword: Optional[str]) -> list[str | int]:
        path_config = cls._generate_path_config()

        if keyword is None:
            return [file.path.name for file in path_config.artwork_path.list_all_files()]
        else:
            return [file.path.name for file in path_config.artwork_path.list_all_files() if keyword in file.path.name]

    @property
    def self_file(self) -> "TemporaryResource":
        return self.path_config.artwork_path(self.s_aid)

    async def _query(self) -> ArtworkData:
        self.self_file.raise_not_file()

        """本地图片默认分类分级
        (classification, rating)
                (3, -1)
        默认本地图片都是人工筛选后才放进来的, 分级未知
        """

        return ArtworkData.model_validate({
            'origin': self.get_base_origin_name(),
            'aid': self.self_file.path.name,
            'title': 'Unknown',
            'uid': 'Unknown',
            'uname': 'Unknown',
            'classification': 3,
            'rating': -1,
            'width': -1,
            'height': -1,
            'tags': [],
            'description': None,
            'source': 'Unknown',
            'pages': [
                {
                    'preview_file': {
                        'url': f'https://example.com/{self.self_file.path.name}',
                        'file_ext': self.self_file.path.suffix,
                        'width': None,
                        'height': None,
                    },
                    'regular_file': {
                        'url': f'https://example.com/{self.self_file.path.name}',
                        'file_ext': self.self_file.path.suffix,
                        'width': None,
                        'height': None,
                    },
                    'original_file': {
                        'url': f'https://example.com/{self.self_file.path.name}',
                        'file_ext': self.self_file.path.suffix,
                        'width': None,
                        'height': None,
                    }
                }
            ]
        })

    async def get_std_desc(self, *, desc_len_limit: int = 128) -> str:
        return f'Local collected artwork: {self.self_file.path.name}'

    async def get_std_preview_desc(self, *, text_len_limit: int = 12) -> str:
        return 'Local collected artwork'

    async def _save_page(
            self,
            page_index: int = 0,
            page_type: "ArtworkPageParamType" = 'regular'
    ) -> "TemporaryResource":
        return self.self_file


__all__ = [
    'LocalCollectedArtworkProxy',
]
