"""
@Author         : Ailitonia
@Date           : 2021/09/12 0:09
@FileName       : rate_limiting.py
@Project        : nonebot2_miya 
@Description    : 速率限制
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import time
from datetime import datetime, timedelta
from typing import Union, Dict
from nonebot import get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from omega_miya.database import EventEntityHelper
from omega_miya.result import BoolResult
from omega_miya.utils.process_utils import run_async_catching_exception


global_config = get_driver().config
SUPERUSERS = global_config.superusers

_log_prefix: str = '<lc>Rate Limiting</lc> | '

# 速率限制次数阈值, 触发超过该次数后启用限制
RATE_LIMITING_THRESHOLD: int = 6
# 速率限制时间阈值, 判断连续消息触发的时间间隔小于该值, 单位为秒, 判断依据时间戳为标准
RATE_LIMITING_TIME: float = 1.0
# 启用后判断依据将以处理时的系统时间戳为准, 而不是上报 event 的时间戳
USING_SYSTEM_TIMESTAMP: bool = False
# 触发速率限制时为用户设置的流控冷却时间, 单位秒
RATE_LIMITING_COOL_DOWN: int = 1800
# 记录用户上次消息的时间戳, 作为对比依据
USER_LAST_MSG_TIME: Dict[int, Union[int, float]] = {}
# 记录用户消息在速率限制时间阈值内触发的次数
RATE_LIMITING_COUNT: Dict[int, int] = {}
# 已被限制的用户id及到期时间
RATE_LIMITING_USER_TEMP: Dict[int, datetime] = {}


async def preprocessor_rate_limiting_cooldown(bot: Bot, event: MessageEvent):
    """速率限制冷却处理"""
    global RATE_LIMITING_USER_TEMP

    user_id = event.user_id
    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        logger.opt(colors=True).debug(f'{_log_prefix}ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    user_id = event.user_id

    rate_limiting_tag = False

    # 检查用户限制
    user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
    user_check_result = await run_async_catching_exception(user.check_rate_limiting_cooldown_expired)()
    if not isinstance(user_check_result, Exception):
        user_expired, user_expired_time = user_check_result
        if not user_expired:
            logger.opt(colors=True).info(f'{_log_prefix}User({user.tid}) 被速率限制中, 到期时间 {user_expired_time}')
            RATE_LIMITING_USER_TEMP.update({user_id: user_expired_time})
            rate_limiting_tag = True

    # 检查群组/频道限制
    group = EventEntityHelper(bot=bot, event=event).get_event_entity()
    if not rate_limiting_tag and group.relation_type != 'bot_user':
        group_check_result = await run_async_catching_exception(group.check_rate_limiting_cooldown_expired)()
        if not isinstance(group_check_result, Exception):
            group_expired, group_expired_time = group_check_result
            if not group_expired:
                logger.opt(colors=True).info(f'{_log_prefix}Group({group.tid}) 被速率限制中, 到期时间 {group_expired_time}')
                rate_limiting_tag = True

    if rate_limiting_tag:
        raise IgnoredException('速率限制中')


async def preprocessor_rate_limiting(bot: Bot, event: MessageEvent):
    """针对用户的速率限制处理"""
    global USER_LAST_MSG_TIME
    global RATE_LIMITING_COUNT
    global RATE_LIMITING_USER_TEMP

    user_id = event.user_id
    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        logger.opt(colors=True).debug(f'{_log_prefix}ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    # 检测该用户是否已经被速率限制
    if RATE_LIMITING_USER_TEMP.get(user_id, datetime.now()) > datetime.now():
        logger.opt(colors=True).info(
            f'{_log_prefix}User({user_id}) 仍在速率限制中, 到期时间 {RATE_LIMITING_USER_TEMP.get(user_id)}')
        raise IgnoredException('速率限制中')

    # 获取上条消息的时间戳
    last_msg_timestamp = USER_LAST_MSG_TIME.get(user_id, None)

    # 获取当前消息时间戳
    if USING_SYSTEM_TIMESTAMP:
        this_msg_timestamp = time.time()
    else:
        this_msg_timestamp = event.time

    # 更新上次消息时间戳为本次消息时间戳
    if last_msg_timestamp is None:
        USER_LAST_MSG_TIME.update({user_id: this_msg_timestamp})
        # 上次消息时间戳为空则这是第一条消息
        return
    else:
        USER_LAST_MSG_TIME.update({user_id: this_msg_timestamp})

    # 获取速录限制触发计数
    over_limiting_count = RATE_LIMITING_COUNT.get(user_id, 0)

    # 进行速率判断
    if this_msg_timestamp - last_msg_timestamp <= RATE_LIMITING_TIME:
        # 小于等于时间阈值则计数 +1
        over_limiting_count += 1
        logger.opt(colors=True).debug(
            f'{_log_prefix}User({user_id}) over rate limiting, count {over_limiting_count}/{RATE_LIMITING_THRESHOLD}')
    else:
        # 否则重置计数
        over_limiting_count = 0

    # 更新计数
    RATE_LIMITING_COUNT.update({user_id: over_limiting_count})

    # 判断计数大于阈值则触发限制, 为用户设置限流冷却并重置计数
    if over_limiting_count > RATE_LIMITING_THRESHOLD:
        RATE_LIMITING_USER_TEMP.update({user_id: datetime.now() + timedelta(seconds=RATE_LIMITING_COOL_DOWN)})
        logger.opt(colors=True).info(
            f'{_log_prefix}User({user_id}) 触发速率限制, 已设置用户限制 {RATE_LIMITING_COOL_DOWN} 秒')

        rate_limiting_cooldown_result = await _set_user_rate_limiting_cooldown(
            bot=bot, event=event, cooldown_time=RATE_LIMITING_COOL_DOWN,
            add_user_name=event.sender.nickname
        )
        RATE_LIMITING_COUNT.update({user_id: 0})

        if isinstance(rate_limiting_cooldown_result, Exception):
            logger.opt(colors=True).error(
                f'{_log_prefix}Set User({event.user_id}) rate limiting cooldown failed with exception, '
                f'error: {rate_limiting_cooldown_result}')
        elif rate_limiting_cooldown_result.error:
            logger.opt(colors=True).error(
                f'{_log_prefix}Set User({event.user_id}) rate limiting cooldown failed, '
                f'database operation error: {rate_limiting_cooldown_result.info}')
        else:
            logger.opt(colors=True).info(f'{_log_prefix}User({event.user_id}) 触发速率限制, '
                                         f'已设置 {RATE_LIMITING_COOL_DOWN} 秒流控冷却')
        raise IgnoredException('触发速率限制')


@run_async_catching_exception
async def _set_user_rate_limiting_cooldown(
        bot: Bot,
        event: MessageEvent,
        cooldown_time: int,
        *,
        add_user_name: str = ''
) -> BoolResult:
    """设置用户流控冷却, 若用户不存在则在数据库中初始化用户 Entity"""
    user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
    try:
        set_result = await user.set_rate_limiting_cooldown(expired_time=timedelta(seconds=cooldown_time))
    except Exception as e:
        logger.opt(colors=True).debug(f'{_log_prefix}Set User({user.tid}) rate_limiting cooldown failed, {e}')
        add_user = await user.add_only(entity_name=add_user_name, related_entity_name=add_user_name)
        if add_user.success:
            logger.opt(colors=True).debug(f'{_log_prefix}Add and init User({user.tid}) succeed')
        else:
            logger.opt(colors=True).debug(f'{_log_prefix}Add User({user.tid}) failed, {add_user.info}')
        set_result = await user.set_rate_limiting_cooldown(expired_time=timedelta(seconds=cooldown_time))
    return set_result


__all__ = [
    'preprocessor_rate_limiting',
    'preprocessor_rate_limiting_cooldown'
]
