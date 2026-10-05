"""
@Author         : Ailitonia
@Date           : 2026/10/5 12:37
@FileName       : database
@Project        : omega-miya
@Description    : 数据库存量作品源
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from typing import IO, TYPE_CHECKING

from nonebot.log import logger

from src.service.artwork_proxy import get_artwork_proxy
from src.utils import semaphore_gather
from ..data_source import BaseArtworkSource
from ..model import CurrentArtwork

if TYPE_CHECKING:
    from os import PathLike
    from src.service.artwork_proxy.internal import BaseArtworkProxy

    type SourceOpenFp = str | bytes | PathLike[str] | IO[bytes]


class _DatabaseArtworkSource(BaseArtworkSource, abc.ABC):
    """数据库中存量作品基类"""

    def __init__(self, origin_name: str) -> None:
        super().__init__()
        self._origin_name = origin_name

    @property
    def source_origin(self) -> str:
        return self._origin_name

    @property
    def _artwork_proxy_cls(self) -> type['BaseArtworkProxy']:
        return get_artwork_proxy(origin_name=self.source_origin)

    @property
    def _current_artwork_proxy(self) -> 'BaseArtworkProxy':
        return self._artwork_proxy_cls(artwork_id=self._current_source.aid)

    @abc.abstractmethod
    async def query_some_artworks_from_database(self) -> list['BaseArtworkProxy']:
        """从数据库中获取作品 ID 序列"""
        raise NotImplementedError

    async def _load_current_source(self) -> 'SourceOpenFp':
        logger.info(f'获取作品 {self._current_source.aid} 图片中, 请稍候')
        file = await self._current_artwork_proxy.get_page_file()
        return file.resolve_path

    async def _select_current_source(self) -> None:
        return

    async def _init_working_path(self) -> None:
        artworks = await self.query_some_artworks_from_database()
        artworks_data = await semaphore_gather(
            tasks=[x.query(use_cache=True) for x in artworks],
            semaphore_num=8,
            return_exceptions=False,
        )
        logger.info(f'已从数据中获取作品 {len(artworks)} 个, 正在初始化处理队列')

        self._remaining_source = sorted(
            (
                CurrentArtwork.model_validate({
                    'aid': x.aid,
                    'source_path': x.cover_page_url,
                })
                for x in artworks_data
            ),
            key=lambda x: int(x.aid),
            reverse=True
        )


class DatabaseNonRatingArtworkSource(_DatabaseArtworkSource):
    """数据库中尚未分类分级的作品"""

    @property
    def source_type(self) -> str:
        return 'database_non_rating_artwork'

    @property
    def title_name(self) -> str:
        return '数据库中未分类分级作品'

    async def query_some_artworks_from_database(self) -> list['BaseArtworkProxy']:
        return await self._artwork_proxy_cls.query_db_by_condition(
            keywords=None,
            page=1,
            size=200,
            allow_classification_range=(-1, 0),
            allow_rating_range=(-1, 3),
            order_mode='aid_desc',
        )


class DatabaseNonReviewRecordArtworkSource(_DatabaseArtworkSource):
    """数据库中尚未人工评审的作品"""

    @property
    def source_type(self) -> str:
        return 'database_non_review_record_artwork'

    @property
    def title_name(self) -> str:
        return '数据库中未人工评审作品'

    async def query_some_artworks_from_database(self) -> list['BaseArtworkProxy']:
        return await self._artwork_proxy_cls.query_db_by_condition(
            keywords=None,
            page=1,
            size=200,
            allow_classification_range=(-1, 4),
            allow_rating_range=(-1, 3),
            order_mode='aid_desc',
            has_review_record=False,
        )


__all__ = [
    'DatabaseNonRatingArtworkSource',
    'DatabaseNonReviewRecordArtworkSource',
]
