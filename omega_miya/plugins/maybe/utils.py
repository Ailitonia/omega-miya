import datetime
import random
import hashlib


def query_maybe(sign_text: str, user_id: int) -> str:
    """根据用户qq, 事项和当前日期生成求签结果"""
    # 用qq、日期、所求事项生成随机种子
    random_seed_str = str([sign_text, user_id, datetime.date.today()])
    md5 = hashlib.md5()
    md5.update(random_seed_str.encode('utf-8'))
    random_seed = md5.hexdigest()
    random.seed(random_seed)
    # 生成求签随机数, 9分一级
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

    msg = f'所求事项: “{sign_text}”\n\n结果: 【{result_text}】'

    # 重置随机种子
    random.seed()

    return msg


__all__ = [
    'query_maybe'
]
