from .deck import *


# Deck事件
deck_list = {
    '单张塔罗牌': one_tarot,
    '超能力': superpower,
    '程序员修行': course,
    '明日方舟单抽': draw_one_arknights,
    '明日方舟十连': draw_ten_arknights
}


def draw_deck(deck: str):
    return deck_list.get(deck)
