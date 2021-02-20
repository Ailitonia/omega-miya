# 要替换的标点, key为替换前, value为替换后
punctuation_replace = {
    '。。。': '...',
    '。': ' ',
    '‘': '「',
    '’': '」',
    '・・・': '...',
    '···': '...',
    '“': '「',
    '”': '」',
    '、': ' ',
    '~': '～',
    '!': '！',
    '?': '？',
    '　': ' ',
    '【': '「',
    '】': '」'
}

# 不知道咋换的标点（逗号是因为可能会有注释）
punctuation_ignore = ["'", '"', ',', '，']


# 定义ass格式中加时间的函数
# 输入的时间增量单位为秒
# 只能进位一次（这本身就是拿来加几百毫秒时间的）


def timeplus(time, plus):
    h, m, s=list(map(float, time.split(':')))
    jnw_s = 0                             # 秒向分钟进位
    jnw_m = 0                             # 分向小时进位

    # 算秒
    if s+plus > 60:
        jnw_s = 1
        tp_s = s+plus-60
    else:
        tp_s = s+plus
    # 算分
    if m+jnw_s > 60:
        jnw_m = 1
        tp_m = m+jnw_s-60
    else:
        tp_m = m+jnw_s
    # 算时
    tp_h = h+jnw_m

    return '{}:{:0>2d}:{:0>5.2f}'.format(int(tp_h), int(tp_m), tp_s)

# 定义计算ass格式中减时间的函数
# 输入ass格式的时间和要减去的时间（单位秒），输出减完了之后的时间
# 只能借位一次（尽量只拿来计算几百毫秒的）


def timeminus(time, minus):
    h, m, s=list(map(float, time.split(':')))
    jew_s = 0                 # 秒向分钟借位
    jew_m = 0                 # 分向小时借位

    if s-minus < 0:
        jew_s = 1
        tm_s = s-minus+60
    else:
        tm_s = s-minus
    if m-jew_s < 0:
        jew_m = 1
        tm_m = m-jew_m+60
    else:
        tm_m = m-jew_s
    tm_h = h-jew_m
    return '{}:{:0>2d}:{:0>5.2f}'.format(int(tm_h), int(tm_m), tm_s)

# 定义计算ass格式的时间差的函数
# 前减后(tm1-tm2)
# 输出时间差（单位为秒）


def timedelta(tm1, tm2):
    h1, m1, s1=list(map(float, tm1.split(':')))
    h2, m2, s2=list(map(float, tm2.split(':')))
    jiewei_m, jiewei_h = 0, 0   # 借位数

    jk_s = s1-s2
    if jk_s < 0:     # 秒向分钟借位
        jiewei_m = 1
        jk_s += 60

    jk_m = m1-m2-jiewei_m
    if jk_m < 0:    # 分向小时借位
        jiewei_h = 1
        jk_m += 60

    jk_h = h1-h2-jiewei_h

    return float('%.2f' % (jk_h*3600+jk_m*60+jk_s))


__all__ = [
    'punctuation_replace',
    'punctuation_ignore',
    'timedelta',
    'timeplus',
    'timeminus'
]
