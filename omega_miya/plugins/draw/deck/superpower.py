import datetime
import random
import hashlib

where_or_when = [
    '家里',
    '学校',
    '食堂',
    '马路上',
    '地球上',
    '火星上',
    '吃饭的时候',
    '写作业的时候',
    '打音游的时候',
    '打小怪兽时',
    '修仙时',
    '渡劫时',
    '极度愤怒时'
]

can_do = [
    '瞬间移动',
    '透视',
    '心灵感应',
    '梦境控制',
    '火系魔法',
    '水系魔法',
    '冰系魔法',
    '雷系魔法',
    '风系魔法',
    '土系魔法',
    '时间停止',
    '重力操控',
    '矢量操作',
    '物品复制',
    '隐身',
    '复活',
    '自爆',
    '意识交换'
]

but = [
    '用一次掉一根头发',
    '用了就会性转',
    '一天只能用一次',
    '只能在没人的时候才能用',
    '用了100%会被别人看见',
    '用了后会饥肠辘辘'
]


def superpower(user_id: int) -> str:
    # 用qq、日期生成随机种子
    random_seed_str = str([user_id, datetime.date.today()])
    md5 = hashlib.md5()
    md5.update(random_seed_str.encode('utf-8'))
    random_seed = md5.hexdigest()
    random.seed(random_seed)
    condition = random.sample(where_or_when, k=1)[0]
    power = random.sample(can_do, k=1)[0]
    effects = random.sample(but, k=1)[0]

    result = f"今天的超能力是:\n在{condition}可以使用【{power}】, 但是{effects}"
    return result
