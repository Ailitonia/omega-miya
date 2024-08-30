"""
@Author         : Ailitonia
@Date           : 2023/8/27 20:33
@FileName       : consts
@Project        : nonebot2_miya
@Description    : Moe Plugin Consts
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

type ALLOW_MOE_PLUGIN_ARTWORK_ORIGIN = Literal[
    'pixiv',
    'danbooru',
    'gelbooru',
    'konachan',
    'yandere',
]

ALL_MOE_PLUGIN_ARTWORK_ORIGIN: tuple[str, ...] = (
    'pixiv',
    'danbooru',
    'gelbooru',
    'konachan',
    'yandere',
)


ALLOW_R18_NODE: Literal['allow_r18'] = 'allow_r18'
"""允许预览 r18 作品的权限节点"""


__all__ = [
    'ALL_MOE_PLUGIN_ARTWORK_ORIGIN',
    'ALLOW_MOE_PLUGIN_ARTWORK_ORIGIN',
    'ALLOW_R18_NODE',
]
