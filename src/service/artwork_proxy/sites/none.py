"""
@Author         : Ailitonia
@Date           : 2024/8/12 10:38:22
@FileName       : none.py
@Project        : omega-miya
@Description    : 空适配, 仅提供基类方法
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional

from ..internal import BaseArtworkProxy
from ..models import ArtworkData


class NoneArtworkProxy(BaseArtworkProxy):
    """空适配, 仅提供基类方法"""

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'none'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        raise NotImplementedError

    @classmethod
    async def _get_resource_as_text(cls, url: str, *, timeout: int = 10) -> str:
        raise NotImplementedError

    @classmethod
    async def _search(cls, keyword: Optional[str], **kwargs) -> list[str | int]:
        raise NotImplementedError

    async def _query(self) -> ArtworkData:
        raise NotImplementedError

    async def get_std_desc(self, *, desc_len_limit: int = 128) -> str:
        raise NotImplementedError

    async def get_std_preview_desc(self, *, text_len_limit: int = 12) -> str:
        raise NotImplementedError


__all__ = [
    'NoneArtworkProxy',
]
