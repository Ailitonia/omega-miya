"""
@Author         : Ailitonia
@Date           : 2024/8/12 10:38:22
@FileName       : none.py
@Project        : omega-miya
@Description    : 空适配, 仅提供基类共有方法
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from ..internal import BaseArtworkProxy
from ..models import ArtworkProxyData, ArtistUserData, ArtworkPoolData


class NoneArtworkProxy(BaseArtworkProxy):
    """空适配, 仅提供基类共有方法"""

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'none'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        raise NotImplementedError

    @classmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        raise NotImplementedError

    @classmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        raise NotImplementedError

    async def _query(self) -> ArtworkProxyData:
        raise NotImplementedError

    async def get_std_desc(self, *, split_len: int = 128) -> str:
        raise NotImplementedError

    async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
        raise NotImplementedError

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
    'NoneArtworkProxy',
]
