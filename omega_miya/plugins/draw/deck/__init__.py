from typing import Callable, Literal
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

from .superpower import superpower
from .course import course
from .arknights import draw_one_arknights, draw_ten_arknights


T_DrawDeck = Callable[[int], str | Message | MessageSegment]
"""抽卡函数"""
_DECK: dict[str, T_DrawDeck] = {
    '超能力': superpower,
    '程序员修行': course,
    '明日方舟单抽': draw_one_arknights,
    '明日方舟十连': draw_ten_arknights
}
"""可用的抽卡函数"""


def _draw(draw_deck: T_DrawDeck, draw_seed: int) -> str | Message | MessageSegment:
    result = draw_deck(draw_seed)
    return result


def draw(deck_name: str, draw_seed: int) -> str | Message | MessageSegment:
    draw_deck = _DECK[deck_name]
    result = _draw(draw_deck=draw_deck, draw_seed=draw_seed)
    return result


def get_deck() -> list[str]:
    return [str(x) for x in _DECK.keys()]


__all__ = [
    'draw',
    'get_deck'
]
