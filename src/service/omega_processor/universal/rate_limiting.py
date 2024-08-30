"""
@Author         : Ailitonia
@Date           : 2021/09/12 0:09
@FileName       : rate_limiting
@Project        : nonebot2_miya 
@Description    : 速率限制
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import time
from datetime import datetime, timedelta
from typing import Union, Dict

from nonebot import get_driver, logger
from nonebot.adapters import Bot, Event
from nonebot.exception import IgnoredException

SUPERUSERS = get_driver().config.superusers
LOG_PREFIX: str = '<lc>Rate Limiting</lc> | '


# 速率限制次数阈值, 触发超过该次数后启用限制
RATE_LIMITING_THRESHOLD: int = 10
# 速率限制时间阈值, 判断连续消息触发的时间间隔小于该值, 单位为秒, 判断依据时间戳为标准
RATE_LIMITING_TIME: float = 1.0
# 触发速率限制时为用户设置的流控冷却时间, 单位秒
RATE_LIMITING_COOL_DOWN: int = 1800
# 记录用户上次消息的时间戳, 作为对比依据
USER_LAST_MSG_TIME: Dict[str, Union[int, float]] = {}
# 记录用户消息在速率限制时间阈值内触发的次数
RATE_LIMITING_COUNT: Dict[str, int] = {}
# 已被限制的用户id及到期时间
RATE_LIMITING_USER_TEMP: Dict[str, datetime] = {}


async def preprocessor_rate_limiting(bot: Bot, event: Event):
    """事件预处理, 针对用户的速率限制处理"""
    try:
        _ = event.get_message()
        user_id = event.get_user_id()
    except (NotImplementedError, ValueError):
        logger.opt(colors=True).trace(f'{LOG_PREFIX}Ignored with no-message event')
        return
    except Exception as e:
        logger.opt(colors=True).error(f'{LOG_PREFIX}Detecting event type failed, {e}')
        return

    # 忽略 Bot 本身
    if bot.self_id == event.get_user_id():
        logger.opt(colors=True).trace(f'{LOG_PREFIX}Ignored with <ly>BotSelf({user_id})</ly>')
        return

    # 忽略超级用户
    if user_id in SUPERUSERS:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    global USER_LAST_MSG_TIME
    global RATE_LIMITING_COUNT
    global RATE_LIMITING_USER_TEMP

    # 用户标识符根据 bot 生成
    user_flag = f'{bot.type}_{bot.self_id}_{user_id}'

    # 检测该用户是否已经被速率限制
    if RATE_LIMITING_USER_TEMP.get(user_flag, datetime.now()) > datetime.now():
        logger.opt(colors=True).info(
            f'{LOG_PREFIX}User({user_flag}) 仍在速率限制中, 到期时间 {RATE_LIMITING_USER_TEMP.get(user_flag)}'
        )
        raise IgnoredException('速率限制中')

    # 获取上条消息的时间戳
    last_msg_timestamp = USER_LAST_MSG_TIME.get(user_flag, None)
    # 获取当前时间戳
    this_msg_timestamp = time.time()
    # 更新上次消息时间戳为本次消息时间戳
    if last_msg_timestamp is None:
        USER_LAST_MSG_TIME.update({user_flag: this_msg_timestamp})
        # 上次消息时间戳为空则这是第一条消息
        return
    else:
        USER_LAST_MSG_TIME.update({user_flag: this_msg_timestamp})

    # 获取速录限制触发计数
    over_limiting_count = RATE_LIMITING_COUNT.get(user_flag, 0)

    # 进行速率判断
    if this_msg_timestamp - last_msg_timestamp <= RATE_LIMITING_TIME:
        # 小于等于时间阈值则计数 +1
        over_limiting_count += 1
        logger.opt(colors=True).debug(
            f'{LOG_PREFIX}User({user_flag}) over rate limiting, count {over_limiting_count}/{RATE_LIMITING_THRESHOLD}'
        )
    else:
        # 否则重置计数
        over_limiting_count = 0
        logger.opt(colors=True).trace(
            f'{LOG_PREFIX}User({user_flag}) under rate limiting, last: {last_msg_timestamp}, now: {this_msg_timestamp}'
        )

    # 更新计数
    RATE_LIMITING_COUNT.update({user_flag: over_limiting_count})

    # 判断计数大于阈值则触发限制, 为用户设置限流冷却并重置计数
    if over_limiting_count > RATE_LIMITING_THRESHOLD:
        RATE_LIMITING_USER_TEMP.update({user_flag: datetime.now() + timedelta(seconds=RATE_LIMITING_COOL_DOWN)})
        logger.opt(colors=True).info(
            f'{LOG_PREFIX}User({user_flag}) 触发速率限制, 已设置用户限制 {RATE_LIMITING_COOL_DOWN} 秒'
        )
        RATE_LIMITING_COUNT.update({user_flag: 0})
        raise IgnoredException('触发速率限制')


__all__ = [
    'preprocessor_rate_limiting',
]
