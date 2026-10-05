"""
@Author         : Ailitonia
@Date           : 2026/10/4 23:12
@FileName       : sources
@Project        : omega-miya
@Description    : 各个数据源实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .database import (
    DatabaseNonRatingArtworkSource,
    DatabaseNonReviewRecordArtworkSource,
)
from .pixiv import (
    PixivLocalArtworkFileSource,
    PixivRelatedArtworkSource,
    PixivSearchPopularArtworkSource,
    PixivTopRecommendArtworkSource,
)

__all__ = [
    'DatabaseNonRatingArtworkSource',
    'DatabaseNonReviewRecordArtworkSource',
    'PixivLocalArtworkFileSource',
    'PixivRelatedArtworkSource',
    'PixivSearchPopularArtworkSource',
    'PixivTopRecommendArtworkSource',
]
