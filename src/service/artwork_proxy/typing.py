"""
@Author         : Ailitonia
@Date           : 2024/8/6 下午10:39
@FileName       : typing
@Project        : nonebot2_miya
@Description    : ArtworkProxy typing
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Literal, TypeAlias, cast

if TYPE_CHECKING:
    from .internal import BaseArtworkProxy

ArtworkPageParamType: TypeAlias = Literal['preview', 'regular', 'original']
"""作品页面可选类型参数"""

ArtworkProxy_T: TypeAlias = type["BaseArtworkProxy"]


def mark_as_artwork_proxy_mixin(class_: type) -> ArtworkProxy_T:
    """标注类为 ArtworkProxy 方便类型检查, 仅供工具插件 Mixin 类使用"""
    return cast(ArtworkProxy_T, class_)


__all__ = [
    'ArtworkPageParamType',
    'ArtworkProxy_T',
    'mark_as_artwork_proxy_mixin',
]
