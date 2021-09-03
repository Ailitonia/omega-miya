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
from .tarot_typing import TarotPack, TarotResourceFile, TarotResource
from .tarot_data import TarotPacks


global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
RESOURCES_PATH = global_config.resources_path_
TAROT_RESOURCES_PATH = os.path.abspath(os.path.join(RESOURCES_PATH, 'images', 'tarot'))


class BaseTarotResource(object):
    """
    资源基类
    """
    def __init__(self, pack: TarotPack, source_name: str, file_format: str, source_folder_name: str):
        self.pack: TarotPack = pack

        self.files: List[TarotResourceFile] = [
            TarotResourceFile(id=card.id, index=card.index) for card in self.pack.cards]

        self.resources: TarotResource = TarotResource(
            source_name=source_name,
            file_format=file_format,
            file_path=os.path.abspath(os.path.join(TAROT_RESOURCES_PATH, source_folder_name)),
            files=self.files
        )

        self.resources.check_source()


class TarotResources(object):
    # 内置资源 BiliBili幻星集
    BiliTarotResources = BaseTarotResource(
        pack=TarotPacks.RiderWaite,
        source_name='BiliBili幻星集',
        file_format='png',
        source_folder_name='bilibili')

    # 内置资源 莱德韦特塔罗
    RWSTarotResources = BaseTarotResource(
        pack=TarotPacks.RiderWaite,
        source_name='莱德韦特塔罗',
        file_format='jpg',
        source_folder_name='RWS')

    # 内置资源 莱德韦特塔罗 大阿卡那
    RWSMTarotResources = BaseTarotResource(
        pack=TarotPacks.MajorArcana,
        source_name='莱德韦特塔罗_大阿卡那',
        file_format='jpg',
        source_folder_name='RWS_M')

    # 内置资源 通用塔罗
    UWTTarotResources = BaseTarotResource(
        pack=TarotPacks.RiderWaite,
        source_name='Universal Waite Tarot',
        file_format='jpg',
        source_folder_name='UWT')

    # 在这里自定义你的资源文件
    # CustomTarotResources = BaseTarotResource(
    #     pack=TarotPacks.MajorArcana,
    #     source_name='Custom',
    #     file_format='png',
    #     source_folder_name='Custom')


__all__ = [
    'BaseTarotResource',
    'TarotResources'
]
