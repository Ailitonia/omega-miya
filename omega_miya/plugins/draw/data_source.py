import datetime
import random
import hashlib
from .deck import *


# 普通事件
def maybe(draw: str, user_id: int) -> str:
    # 用qq、日期、所求事项生成随机种子
    random_seed_str = str([draw, user_id, datetime.date.today()])
    md5 = hashlib.md5()
    md5.update(random_seed_str.encode('utf-8'))
    random_seed = md5.hexdigest()
    random.seed(random_seed)
    # 生成求签种子, 9分一级
    divination_result = random.randint(1, 109)
    # 大吉・中吉・小吉・吉・半吉・末吉・末小吉・凶・小凶・半凶・末凶・大凶
    if divination_result < 9:
        result_text = '大凶'
    elif divination_result < 18:
        result_text = '末凶'
    elif divination_result < 27:
        result_text = '半凶'
    elif divination_result < 36:
        result_text = '小凶'
    elif divination_result < 45:
        result_text = '凶'
    elif divination_result < 54:
        result_text = '末小吉'
    elif divination_result < 63:
        result_text = '末吉'
    elif divination_result < 72:
        result_text = '半吉'
    elif divination_result < 81:
        result_text = '吉'
    elif divination_result < 90:
        result_text = '小吉'
    elif divination_result < 99:
        result_text = '中吉'
    else:
        result_text = '大吉'
    msg = f'所求事项: 【{draw}】\n\n结果: 【{result_text}】'
    return msg


# 特殊事件
sp = {
    '打钱': '别问, 问就是大吉, 建议马上转账',
    'gachi': '大凶, 你明明是个anti',
    '单推': '大凶, 明明就是DD, 我还在别的女人直播间见过你'
}


def sp_event(event: str):
    msg = f'所求事项: 【{event}】\n\n结果: 【{sp.get(event)}】'
    return msg


# Draw事件
deck_list = {
    '单张塔罗牌': one_tarot,
    '超能力': superpower,
    'dd老黄历': old_almanac,
    '程序员修行': course
}


def draw_deck(deck: str):
    return deck_list.get(deck)
