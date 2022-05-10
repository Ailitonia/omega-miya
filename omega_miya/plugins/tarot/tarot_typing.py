"""
@Author         : Ailitonia
@Date           : 2021/08/31 21:08
@FileName       : tarot_typing.py
@Project        : nonebot2_miya 
@Description    : 类型
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from pydantic import BaseModel


TAROT_TYPE = Literal['special', 'major_arcana', 'minor_arcana']
"""塔罗牌类型"""


class TarotBaseModel(BaseModel):
    """塔罗插件 BaseModel"""
    class Config:
        extra = 'ignore'
        allow_mutation = False


class Element(TarotBaseModel):
    """元素"""
    id: int
    orig_name: str  # 原始名称
    name: str  # 名称


class Constellation(TarotBaseModel):
    """星与星座"""
    id: int
    orig_name: str  # 原始名称
    name: str  # 名称


class TarotCard(TarotBaseModel):
    """塔罗牌"""
    id: int  # 塔罗牌的序号
    index: str  # 内部名称
    type: TAROT_TYPE  # 卡片类型
    orig_name: str  # 原始名称
    name: str  # 显示名称
    intro: str  # 卡面描述
    words: str  # 相关词/关键词
    desc: str  # 卡片描述
    upright: str  # 正位释义
    reversed: str  # 逆位释义


class TarotPack(TarotBaseModel):
    """塔罗牌套牌"""
    cards: list[TarotCard]  # 套牌内容

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


__all__ = [
    'TAROT_TYPE',
    'Element',
    'Constellation',
    'TarotCard',
    'TarotPack'
]
