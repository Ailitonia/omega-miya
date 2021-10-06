"""
@Author         : Ailitonia
@Date           : 2021/08/31 21:08
@FileName       : tarot_typing.py
@Project        : nonebot2_miya 
@Description    : 类型
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
from typing import List
from dataclasses import dataclass


@dataclass
class Element:
    """
    元素
    """
    id: int
    orig_name: str  # 原始名称
    name: str  # 名称


@dataclass
class Constellation:
    """
    星与星座
    """
    id: int
    orig_name: str  # 原始名称
    name: str  # 名称


@dataclass
class TarotCard:
    """
    塔罗牌
    """
    id: int  # 塔罗牌的序号
    index: str  # 内部名称
    type: str  # 卡片类型
    orig_name: str  # 原始名称
    name: str  # 显示名称
    intro: str  # 卡面描述
    words: str  # 相关词/关键词
    desc: str  # 卡片描述
    upright: str  # 正位释义
    reversed: str  # 逆位释义


@dataclass
class TarotPack:
    """
    套牌
    """
    name: str  # 套牌名称
    cards: List[TarotCard]  # 套牌内容

    @property
    def num(self) -> int:
        return len(self.cards)

    def get_card_by_id(self, id_: int) -> TarotCard:
        if card := [card for card in self.cards if card.id == id_]:
            if len(card) == 1:
                return card[0]
        raise ValueError('Card not found or multi-card error')

    def get_card_by_index(self, index_: str) -> TarotCard:
        if card := [card for card in self.cards if card.index == index_]:
            if len(card) == 1:
                return card[0]
        raise ValueError('Card not found or multi-card error')

    def get_card_by_name(self, name: str) -> TarotCard:
        if card := [card for card in self.cards if card.name == name]:
            if len(card) == 1:
                return card[0]
        raise ValueError('Card not found or multi-card error')


@dataclass
class TarotResourceFile:
    """
    卡片资源文件
    """
    id: int  # 塔罗牌的序号 同时也是存放文件名
    index: str  # 内部名称


@dataclass
class TarotResource:
    """
    卡片资源信息
    """
    source_name: str  # 资源名称
    file_format: str  # 文件格式
    file_path: str  # 资源文件夹
    files: List[TarotResourceFile]  # 卡牌名称列表

    def check_source(self):
        for file in self.files:
            if not os.path.exists(os.path.abspath(os.path.join(self.file_path, f'{file.id}.{self.file_format}'))):
                raise ValueError(f'Tarot | Tarot source: "{self.source_name}", file: "{file}" missing, '
                                 f'please check your "{self.file_path}" folder')

    def get_file_by_id(self, id_: int) -> str:
        if file := [file for file in self.files if file.id == id_]:
            if len(file) == 1:
                return os.path.abspath(os.path.join(self.file_path, f'{file[0].id}.{self.file_format}'))
        raise ValueError('File not found or multi-file error')

    def get_file_by_index(self, index_: str) -> str:
        if file := [file for file in self.files if file.index == index_]:
            if len(file) == 1:
                return os.path.abspath(os.path.join(self.file_path, f'{file[0].id}.{self.file_format}'))
        raise ValueError('File not found or multi-file error')


__all__ = [
    'Element',
    'Constellation',
    'TarotCard',
    'TarotPack',
    'TarotResourceFile',
    'TarotResource'
]
