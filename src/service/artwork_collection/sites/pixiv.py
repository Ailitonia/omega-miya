"""
@Author         : Ailitonia
@Date           : 2024/8/6 17:28:37
@FileName       : pixiv.py
@Project        : omega-miya
@Description    : Pixiv 适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from ..internal import BaseArtworkCollection


class PixivArtworkCollection(BaseArtworkCollection):
    @property
    def origin_desc(self) -> str:
        return f'Pixiv | {self.aid}'

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'pixiv'


__all__ = [
    'PixivArtworkCollection'
]
