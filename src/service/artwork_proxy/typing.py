"""
@Author         : Ailitonia
@Date           : 2024/8/6 下午10:39
@FileName       : typing
@Project        : nonebot2_miya
@Description    : ArtworkProxy typing
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from collections.abc import Callable
from functools import wraps
from typing import Literal, TypeVar, cast

from .internal import BaseArtworkProxy

type ArtworkPageParamType = Literal['preview', 'regular', 'original']
"""作品页面可选类型参数"""

type ArtworkProxyType = type[BaseArtworkProxy]
"""ArtworkProxy 基类类型"""

type ProxiedArtwork = BaseArtworkProxy
"""ArtworkProxy 实例"""

ArtworkProxy_T = TypeVar('ArtworkProxy_T', bound=ProxiedArtwork)
ArtworkProxyClass_T = TypeVar('ArtworkProxyClass_T', bound=ArtworkProxyType)


def mark_as_artwork_proxy_mixin(class_: type) -> ArtworkProxyType:
    """标注类为 ArtworkProxy 类型, 方便类型检查, 仅供工具插件 Mixin 类使用"""
    return cast(ArtworkProxyType, class_)


def mark_as_mixin(class_t: ArtworkProxyClass_T) -> Callable[[type], ArtworkProxyClass_T]:
    """标注类为指定的类, 方便类型检查, 仅供工具插件 Mixin 类使用"""

    @wraps(class_t)
    def _decorator(class_: type) -> ArtworkProxyClass_T:
        return cast(class_t, class_)

    return _decorator


__all__ = [
    'ArtworkPageParamType',
    'ArtworkProxy_T',
    'ArtworkProxyClass_T',
    'ArtworkProxyType',
    'ProxiedArtwork',
    'mark_as_artwork_proxy_mixin',
    'mark_as_mixin',
]
