"""
@Author         : Ailitonia
@Date           : 2021/09/01 0:22
@FileName       : tarot_resources.py
@Project        : nonebot2_miya 
@Description    : 卡片资源 同样是硬编码在这里了:(
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.resource import StaticResource

from .config import tarot_local_resource_config
from .model import TarotCards, TarotPack


class TarotResource(object):
    """塔罗牌资源基类"""
    def __init__(self, source_name: str, pack: TarotPack, file_format: str):
        self.resource_folder: StaticResource = tarot_local_resource_config.image_resource_folder(source_name)
        self.pack: TarotPack = pack
        self.file_format: str = file_format
        self.check_source(resource_folder=self.resource_folder, pack=self.pack, file_format=self.file_format)

    @staticmethod
    def check_source(resource_folder: StaticResource, pack: TarotPack, file_format: str) -> None:
        for card in pack.cards:
            card_file = resource_folder(f'{card.id}.{file_format}')
            if not card_file.path.exists() or not card_file.path.is_file():
                raise ValueError(f'TarotResource {card_file.resolve_path} missing')

    def get_file_by_id(self, id_: int) -> StaticResource:
        card = self.pack.get_card_by_id(id_=id_)
        card_file = self.resource_folder(f'{card.id}.{self.file_format}')
        if not card_file.path.exists() or not card_file.path.is_file():
            raise ValueError(f'TarotResource {card_file.resolve_path} missing')
        return card_file

    def get_file_by_index(self, index_: str) -> StaticResource:
        card = self.pack.get_card_by_index(index_=index_)
        card_file = self.resource_folder(f'{card.id}.{self.file_format}')
        if not card_file.path.exists() or not card_file.path.is_file():
            raise ValueError(f'TarotResource {card_file.resolve_path} missing')
        return card_file

    def get_file_by_name(self, name: str) -> StaticResource:
        card = self.pack.get_card_by_name(name=name)
        card_file = self.resource_folder(f'{card.id}.{self.file_format}')
        if not card_file.path.exists() or not card_file.path.is_file():
            raise ValueError(f'TarotResource {card_file.resolve_path} missing')
        return card_file


_MAJOR_ARCANA: TarotPack = TarotPack(cards=TarotCards.get_cards_by_type('major_arcana'))
"""Major Arcana tarot deck"""
_MINOR_ARCANA: TarotPack = TarotPack(cards=TarotCards.get_cards_by_type('minor_arcana'))
"""Minor Arcana tarot deck"""
_RIDER_WAITE: TarotPack = TarotPack(cards=TarotCards.get_cards_by_type('major_arcana', 'minor_arcana'))
"""Rider–Waite–Smith tarot deck"""


bili_tarot_resource: TarotResource = TarotResource(source_name='bilibili', pack=_RIDER_WAITE, file_format='png')
"""内置资源 BiliBili幻星集"""
rws_tarot_resource: TarotResource = TarotResource(source_name='RWS', pack=_RIDER_WAITE, file_format='jpg')
"""内置资源 莱德韦特塔罗"""
rws_major_tarot_resource: TarotResource = TarotResource(source_name='RWS_M', pack=_MAJOR_ARCANA, file_format='jpg')
"""内置资源 莱德韦特塔罗 大阿卡那"""
uwt_tarot_resource: TarotResource = TarotResource(source_name='UWT', pack=_RIDER_WAITE, file_format='jpg')
"""内置资源 Universal Waite Tarot"""
biddy_tarot_resource: TarotResource = TarotResource(source_name='Biddy', pack=_RIDER_WAITE, file_format='png')
"""内置资源 Biddy Tarot Deck"""


_INTERNAL_TAROT_RESOURCE: dict[str, TarotResource] = {
    'Bilibili幻星集': bili_tarot_resource,
    '莱德韦特塔罗': rws_tarot_resource,
    '莱德韦特塔罗-大阿卡那': rws_major_tarot_resource,
    'UniversalWaiteTarot': uwt_tarot_resource,
    'BiddyTarotDeck': biddy_tarot_resource,
}


_DEFAULT_TAROT_RESOURCE: TarotResource = bili_tarot_resource
"""默认的塔罗牌资源"""


def get_tarot_resource(resource_name: str | None = None) -> TarotResource:
    if resource_name is None:
        return _DEFAULT_TAROT_RESOURCE
    return _INTERNAL_TAROT_RESOURCE.get(resource_name, _DEFAULT_TAROT_RESOURCE)


def get_available_tarot_resource() -> list[str]:
    return [x for x in _INTERNAL_TAROT_RESOURCE.keys()]


__all__ = [
    'TarotResource',
    'get_tarot_resource',
    'get_available_tarot_resource'
]
