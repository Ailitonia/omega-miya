"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : helpers.py
@Project        : nonebot2_miya
@Description    : 求签结果生成工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import hashlib
import random
from datetime import datetime


def query_divination(divination_text: str, user_id: str | int) -> str:
    """根据用户 id, 事项和当前日期生成求签结果"""
    # 用qq、日期、所求事项生成随机种子
    random_seed_str = ', '.join(str(x) for x in (divination_text, user_id, datetime.now().date()))
    md5 = hashlib.md5()
    md5.update(random_seed_str.encode('utf-8'))
    random_seed = md5.hexdigest()
    random.seed(random_seed)
    # 生成求签随机数
    divination_result = random.randint(1, 108)
    # 大吉・中吉・小吉・吉・半吉・末吉・末小吉・凶・小凶・半凶・末凶・大凶
    if divination_result < 4:
        divination_star = 0
        divination_text = '大凶'
    elif divination_result < 9:
        divination_star = 1
        divination_text = '末凶'
    elif divination_result < 16:
        divination_star = 2
        divination_text = '半凶'
    elif divination_result < 25:
        divination_star = 3
        divination_text = '小凶'
    elif divination_result < 36:
        divination_star = 4
        divination_text = '凶'
    elif divination_result < 48:
        divination_star = 5
        divination_text = '末小吉'
    elif divination_result < 60:
        divination_star = 6
        divination_text = '末吉'
    elif divination_result < 72:
        divination_star = 7
        divination_text = '半吉'
    elif divination_result < 84:
        divination_star = 8
        divination_text = '吉'
    elif divination_result < 96:
        divination_star = 9
        divination_text = '小吉'
    elif divination_result < 102:
        divination_star = 10
        divination_text = '中吉'
    else:
        divination_star = 11
        divination_text = '大吉'

    msg = (
        f'所求之事: “{divination_text}”\n\n'
        f'结果: 【{divination_text}】\n'
        f'{"★" * divination_star}{"☆" * (11 - divination_star)}'
    )

    # 重置随机种子
    random.seed()

    return msg


__all__ = [
    'query_divination',
]
