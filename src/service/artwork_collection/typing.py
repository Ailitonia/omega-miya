"""
@Author         : Ailitonia
@Date           : 2024/8/6 下午10:34
@FileName       : typing
@Project        : nonebot2_miya
@Description    : ArtworkCollection typing
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from .internal import BaseArtworkCollection

ArtworkCollection_T: TypeAlias = type["BaseArtworkCollection"]

__all__ = [
    'ArtworkCollection_T'
]
