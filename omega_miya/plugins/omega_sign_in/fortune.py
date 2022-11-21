import random
import hashlib
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, parse_obj_as
from .do_something import do_somethong


class Fortune(BaseModel):
    """求签结果"""
    star: str
    text: Literal['大凶', '末凶', '半凶', '小凶', '凶', '末小吉', '末吉', '半吉', '吉', '小吉', '中吉', '大吉']
    good_do_st: str
    good_do_nd: str
    bad_do_st: str
    bad_do_nd: str


class Something(BaseModel):
    """老黄历宜和不宜内容"""
    name: str
    good: str
    bad: str


def get_fortune(user_id: int, *, date: datetime | None = None) -> Fortune:
    """根据 qq 号和当天日期生成老黄历"""
    if date is None:
        date_str = str(datetime.today().date())
    else:
        date_str = str(date.date())
    # 用qq、日期生成随机种子
    random_seed_str = str([user_id, date_str])
    md5 = hashlib.md5()
    md5.update(random_seed_str.encode('utf-8'))
    random_seed = md5.hexdigest()
    random.seed(random_seed)
    # 今日运势
    # 生成运势随机数
    fortune_result = random.randint(1, 108)
    # 大吉・中吉・小吉・吉・半吉・末吉・末小吉・凶・小凶・半凶・末凶・大凶
    if fortune_result < 4:
        fortune_star = '☆' * 11
        fortune_text = '大凶'
    elif fortune_result < 9:
        fortune_star = '★' * 1 + '☆' * 10
        fortune_text = '末凶'
    elif fortune_result < 16:
        fortune_star = '★' * 2 + '☆' * 9
        fortune_text = '半凶'
    elif fortune_result < 25:
        fortune_star = '★' * 3 + '☆' * 8
        fortune_text = '小凶'
    elif fortune_result < 36:
        fortune_star = '★' * 4 + '☆' * 7
        fortune_text = '凶'
    elif fortune_result < 48:
        fortune_star = '★' * 5 + '☆' * 6
        fortune_text = '末小吉'
    elif fortune_result < 60:
        fortune_star = '★' * 6 + '☆' * 5
        fortune_text = '末吉'
    elif fortune_result < 72:
        fortune_star = '★' * 7 + '☆' * 4
        fortune_text = '半吉'
    elif fortune_result < 84:
        fortune_star = '★' * 8 + '☆' * 3
        fortune_text = '吉'
    elif fortune_result < 96:
        fortune_star = '★' * 9 + '☆' * 2
        fortune_text = '小吉'
    elif fortune_result < 102:
        fortune_star = '★' * 10 + '☆' * 1
        fortune_text = '中吉'
    else:
        fortune_star = '★' * 11
        fortune_text = '大吉'

    # 宜做和不宜做
    do_and_not = random.sample(parse_obj_as(list[Something], do_something), k=4)

    result = {
        'star': fortune_star,
        'text': fortune_text,
        'good_do_st': f"{do_and_not[0].name} —— {do_and_not[0].good}",
        'good_do_nd': f"{do_and_not[2].name} —— {do_and_not[2].good}",
        'bad_do_st': f"{do_and_not[1].name} —— {do_and_not[1].bad}",
        'bad_do_nd': f"{do_and_not[3].name} —— {do_and_not[3].bad}"
    }

    # 重置随机种子
    random.seed()

    return Fortune.parse_obj(result)


__all__ = [
    'get_fortune'
]
