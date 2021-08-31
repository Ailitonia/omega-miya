"""
@Author         : Ailitonia
@Date           : 2021/09/01 0:22
@FileName       : tarot_resources.py
@Project        : nonebot2_miya 
@Description    : 卡片资源 同样是硬编码在这里了:(
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
from typing import List
from nonebot import get_driver
from .tarot_typing import TarotPack, TarotResourcesFile, TarotResources
from .tarot_data import MajorArcana


global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
RESOURCES_PATH = global_config.resources_path_
TAROT_RESOURCES_PATH = os.path.abspath(os.path.join(RESOURCES_PATH, 'images', 'tarot'))


class BaseTarotResources(object):
    """
    资源基类
    """
    pack: TarotPack
    files: List[TarotResourcesFile]
    resources: TarotResources


class BiliTarotResources(BaseTarotResources):
    pack: TarotPack = MajorArcana

    def __init__(self):
        self.files: List[TarotResourcesFile] = [
            TarotResourcesFile(id=card.id, index=card.index) for card in self.pack.cards]

        self.resources: TarotResources = TarotResources(
            source_name='BiliBili幻星集',
            file_format='png',
            file_path=os.path.abspath(os.path.join(TAROT_RESOURCES_PATH, 'bilibili')),
            files=self.files
        )

        self.resources.check_source()


class RWSTarotResources(BaseTarotResources):
    pack: TarotPack = MajorArcana

    def __init__(self):
        self.files: List[TarotResourcesFile] = [
            TarotResourcesFile(id=card.id, index=card.index) for card in self.pack.cards]

        self.resources: TarotResources = TarotResources(
            source_name='RWS',
            file_format='jpg',
            file_path=os.path.abspath(os.path.join(TAROT_RESOURCES_PATH, 'RWS')),
            files=self.files
        )

        self.resources.check_source()


__all__ = [
    'BaseTarotResources',
    'BiliTarotResources',
    'RWSTarotResources'
]
