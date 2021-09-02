from .deck import *
from typing import Dict, Callable


T_DrawDeck = Callable[[int], str]

# Deck事件
deck_list: Dict[str, T_DrawDeck] = {
    '超能力': superpower,
    '程序员修行': course,
    '明日方舟单抽': draw_one_arknights,
    '明日方舟十连': draw_ten_arknights
}


def draw_deck(deck: str) -> T_DrawDeck:
    return deck_list.get(deck)
