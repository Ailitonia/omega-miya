"""
@Author         : Ailitonia
@Date           : 2024/8/6 下午10:39
@FileName       : typing
@Project        : nonebot2_miya
@Description    : ArtworkProxy typing
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""
from typing import TYPE_CHECKING, Literal, TypeAlias

if TYPE_CHECKING:
    from .internal import BaseArtworkProxy

ArtworkPageParamType: TypeAlias = Literal['preview', 'regular', 'original']
"""作品页面可选类型参数"""

ArtworkProxy_T: TypeAlias = type["BaseArtworkProxy"]

__all__ = [
    'ArtworkPageParamType',
    'ArtworkProxy_T',
]
