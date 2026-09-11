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

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import IgnoredException
from nonebot.log import logger
from nonebot.permission import SUPERUSER

_LOG_PREFIX: str = '<lc>Rate Limiting</lc> | '
"""日志前缀"""
_RATE_LIMITING_THRESHOLD: int = 10
"""速率限制次数阈值, 触发超过该次数后启用限制"""
_RATE_LIMITING_TIME: float = 2.0
"""速率限制时间阈值, 判断连续消息触发的时间间隔小于该值, 单位为秒, 判断依据时间戳为标准"""
_RATE_LIMITING_COOL_DOWN: int = 1800
"""触发速率限制时为用户设置的流控冷却时间, 单位秒"""
_RATE_LIMITING_PRUNE_THRESHOLD: int = 1024
"""跟踪字典规模清理阈值, 超过该规模时清理长时间未活跃的用户条目, 避免无界增长"""
_USER_LAST_MSG_TIME: dict[str, int] = {}
"""记录用户上次消息的时间戳, 作为对比依据"""
_RATE_LIMITING_COUNT: dict[str, int] = {}
"""记录用户消息在速率限制时间阈值内触发的次数"""
_RATE_LIMITING_USER_TEMP: dict[str, int] = {}
"""已被限制的用户标识符及到期时间"""


def _prune_stale_entries(timestamp_now: int) -> None:
    """清理超过流控冷却时长未活跃的用户跟踪条目 (先收集键再删除, 避免迭代中变异字典)"""
    if len(_USER_LAST_MSG_TIME) <= _RATE_LIMITING_PRUNE_THRESHOLD:
        return

    stale_flags = [
        flag for flag, ts in _USER_LAST_MSG_TIME.items()
        if timestamp_now - ts > _RATE_LIMITING_COOL_DOWN
    ]
    for flag in stale_flags:
        _USER_LAST_MSG_TIME.pop(flag, None)
        _RATE_LIMITING_COUNT.pop(flag, None)
        _RATE_LIMITING_USER_TEMP.pop(flag, None)


async def preprocessor_rate_limiting(bot: BaseBot, event: BaseEvent) -> None:
    """事件预处理, 针对用户的速率限制处理"""
    try:
        _ = event.get_message()
        user_id = event.get_user_id()
    except (NotImplementedError, ValueError):
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Non-message event, ignore')
        return

    # 跳过 Bot 本身
    if bot.self_id == user_id:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Ignored by <ly>BotSelf({user_id})</ly>')
        return

    # 跳过超级用户
    if await SUPERUSER(bot=bot, event=event):
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Ignored by <ly>SUPERUSER({user_id})</ly>')
        return

    # 用户标识符根据 bot 生成
    user_flag = f'{bot.type}_{bot.self_id}_{user_id}'

    # 获取当前时间戳
    timestamp_now = int(time.time())

    # 规模超限时清理长期未活跃的用户条目
    _prune_stale_entries(timestamp_now=timestamp_now)

    # 检测该用户是否已经被速率限制
    if (expired_ts := _RATE_LIMITING_USER_TEMP.get(user_flag, timestamp_now)) > timestamp_now:
        logger.opt(colors=True).info(
            f'{_LOG_PREFIX}User({user_flag}) 仍在速率限制中, 剩余 {expired_ts - timestamp_now} 秒'
        )
        raise IgnoredException('速率限制中')

    # 获取上条消息的时间戳
    last_msg_ts = _USER_LAST_MSG_TIME.get(user_flag, None)

    # 更新上次消息时间戳为本次消息时间戳
    _USER_LAST_MSG_TIME.update({user_flag: timestamp_now})
    # 上次消息时间戳为空则这是第一条消息, 直接返回
    if last_msg_ts is None:
        return

    # 获取速录限制触发计数
    over_limiting_count = _RATE_LIMITING_COUNT.get(user_flag, 0)

    # 进行速率判断
    if timestamp_now - last_msg_ts <= _RATE_LIMITING_TIME:
        # 小于等于时间阈值则计数 +1
        over_limiting_count += 1
        logger.opt(colors=True).debug(
            f'{_LOG_PREFIX}User({user_flag}) over limiting, {over_limiting_count}/{_RATE_LIMITING_THRESHOLD}'
        )
    else:
        # 否则重置计数
        over_limiting_count = 0
        logger.opt(colors=True).debug(
            f'{_LOG_PREFIX}User({user_flag}) under limiting, last: {last_msg_ts}, now: {timestamp_now}'
        )

    # 更新计数
    _RATE_LIMITING_COUNT.update({user_flag: over_limiting_count})

    # 判断计数大于阈值则触发限制, 为用户设置限流冷却并重置计数
    if over_limiting_count > _RATE_LIMITING_THRESHOLD:
        _RATE_LIMITING_USER_TEMP.update({user_flag: timestamp_now + _RATE_LIMITING_COOL_DOWN})
        logger.opt(colors=True).info(
            f'{_LOG_PREFIX}User({user_flag}) 触发速率限制, 已限制用户 {_RATE_LIMITING_COOL_DOWN} 秒'
        )
        _RATE_LIMITING_COUNT.update({user_flag: 0})
        raise IgnoredException('触发速率限制')


__all__ = [
    'preprocessor_rate_limiting',
]
