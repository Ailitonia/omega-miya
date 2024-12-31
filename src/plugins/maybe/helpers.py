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
        result_star = 0
        result_text = '大凶'
    elif divination_result < 9:
        result_star = 1
        result_text = '末凶'
    elif divination_result < 16:
        result_star = 2
        result_text = '半凶'
    elif divination_result < 25:
        result_star = 3
        result_text = '小凶'
    elif divination_result < 36:
        result_star = 4
        result_text = '凶'
    elif divination_result < 48:
        result_star = 5
        result_text = '末小吉'
    elif divination_result < 60:
        result_star = 6
        result_text = '末吉'
    elif divination_result < 72:
        result_star = 7
        result_text = '半吉'
    elif divination_result < 84:
        result_star = 8
        result_text = '吉'
    elif divination_result < 96:
        result_star = 9
        result_text = '小吉'
    elif divination_result < 102:
        result_star = 10
        result_text = '中吉'
    else:
        result_star = 11
        result_text = '大吉'

    msg = (
        f'所求之事: “{divination_text}”\n\n'
        f'结果: 【{result_text}】\n'
        f'{"★" * result_star}{"☆" * (11 - result_star)}'
    )

    # 重置随机种子
    random.seed()

    return msg


__all__ = [
    'query_divination',
]
