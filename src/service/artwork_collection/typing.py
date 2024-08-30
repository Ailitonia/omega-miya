"""
@Author         : Ailitonia
@Date           : 2024/8/6 下午10:34
@FileName       : typing
@Project        : nonebot2_miya
@Description    : ArtworkCollection typing
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TypeVar

from .internal import BaseArtworkCollection

type ArtworkCollectionType = type[BaseArtworkCollection]
"""ArtworkCollection 基类类型"""

type CollectedArtwork = BaseArtworkCollection
"""ArtworkCollection 实例"""

ArtworkCollectionClass_T = TypeVar('ArtworkCollectionClass_T', bound=ArtworkCollectionType)
ArtworkCollection_T = TypeVar('ArtworkCollection_T', bound=CollectedArtwork)


__all__ = [
    'ArtworkCollection_T',
    'ArtworkCollectionClass_T',
    'ArtworkCollectionType',
    'CollectedArtwork',
]
