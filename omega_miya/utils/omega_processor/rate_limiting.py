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
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent
from omega_miya.database import DBBot, DBBotGroup, DBCoolDownEvent


global_config = get_driver().config
SUPERUSERS = global_config.superusers

# 速率限制次数阈值, 触发超过该次数后启用限制
RATE_LIMITING_THRESHOLD: int = 8
# 速率限制时间阈值, 判断连续消息触发的时间间隔小于该值, 单位为秒, 判断依据时间戳为标准
RATE_LIMITING_TIME: float = 1.0
# 启用后判断依据将以处理时的系统时间戳为准, 而不是上报 event 的时间戳
USING_SYSTEM_TIMESTAMP: bool = False
# 记录用户上次消息的时间戳, 作为对比依据
USER_LAST_MSG_TIME: Dict[int, Union[int, float]] = {}
# 记录用户消息在速率限制时间阈值内触发的次数
RATE_LIMITING_COUNT: Dict[int, int] = {}
# 触发速率限制时为用户设置的全局冷却时间, 单位秒
RATE_LIMITING_COOL_DOWN: int = 1800
# 缓存的已被限制的用户id及到期时间, 避免多次查数据库
RATE_LIMITING_USER_TEMP: Dict[int, datetime] = {}
# 群组流控配置冷却时间, 与 plugins.omega_rate_limiting 中配置保持一致
GROUP_GLOBAL_CD_SETTING_NAME: str = 'group_global_cd'


async def preprocessor_rate_limiting(bot: Bot, event: MessageEvent, state: T_State):
    """
    速率限制处理 T_EventPreProcessor
    """
    global USER_LAST_MSG_TIME
    global RATE_LIMITING_COUNT
    global RATE_LIMITING_USER_TEMP

    user_id = event.user_id
    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        return

    # 检测该用户是否已经被速率限制
    if RATE_LIMITING_USER_TEMP.get(user_id, datetime.now()) > datetime.now():
        logger.info(f'Rate Limiting | User: {user_id} 仍在速率限制中, 到期时间 {RATE_LIMITING_USER_TEMP.get(user_id)}')
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
        logger.info(f'Rate Limiting | User: {user_id} over rate limiting, '
                    f'counting {over_limiting_count}/{RATE_LIMITING_THRESHOLD}')
    else:
        # 否则重置计数
        over_limiting_count = 0

    # 更新计数
    RATE_LIMITING_COUNT.update({user_id: over_limiting_count})

    # 判断计数大于阈值则触发限制, 为用户设置一个全局冷却并重置计数
    if over_limiting_count > RATE_LIMITING_THRESHOLD:
        RATE_LIMITING_USER_TEMP.update({user_id: datetime.now() + timedelta(seconds=RATE_LIMITING_COOL_DOWN)})
        logger.success(f'Rate Limiting | User: {user_id} 触发速率限制, Upgrade RATE_LIMITING_USER_TEMP completed')

        result = await DBCoolDownEvent.add_global_user_cool_down_event(
            user_id=user_id,
            stop_at=datetime.now() + timedelta(seconds=RATE_LIMITING_COOL_DOWN),
            description='Rate Limiting CoolDown')
        RATE_LIMITING_COUNT.update({user_id: 0})

        if result.error:
            logger.error(f'Rate Limiting | Set rate limiting cool down failed: {result.info}')
        else:
            logger.success(f'Rate Limiting | User: {user_id} 触发速率限制, 已设置 {RATE_LIMITING_COOL_DOWN} 秒全局冷却限制')
        raise IgnoredException('触发速率限制')


async def postprocessor_rate_limiting(bot: Bot, event: MessageEvent, state: T_State):
    """
    速率限制事件后处理 T_EventPostProcessor
    """
    if not state.get('_prefix', {}).get('raw_command') and not state.get('_suffix', {}).get('raw_command'):
        # 限流仅能由命令触发
        logger.debug(f'Rate Limiting | Not command event, ignore global group cool down')
        return

    self_bot = DBBot(self_qq=int(bot.self_id))
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBBotGroup(group_id=group_id, self_bot=self_bot)

        # 验证群组是否已有全局 cd, 有的话就跳过
        global_group_check = await DBCoolDownEvent.check_global_group_cool_down_event(group_id=group_id)
        if global_group_check.success() and global_group_check.result == 1:
            logger.opt(colors=True).debug(
                'Rate Limiting | Group: {group_id} global group cool down exists, <lc>ignore</lc>')
            return

        setting_result = await group.setting_get(setting_name=GROUP_GLOBAL_CD_SETTING_NAME)
        if setting_result.success():
            main, second, extra = setting_result.result
            if main:
                # 配置有效, 为群组设置一个全局冷却
                result = await DBCoolDownEvent.add_global_group_cool_down_event(
                    group_id=group_id,
                    stop_at=datetime.now() + timedelta(seconds=int(main)),
                    description='Rate Limiting Global Group CoolDown')
                if result.error:
                    logger.error(f'Rate Limiting | Set global group cool down failed: {result.info}')
                else:
                    logger.opt(colors=True).debug(
                        f'Rate Limiting | Set Group: {group_id} global group cool down, <ly>times: {main}</ly>')
            else:
                logger.error(f'Rate Limiting | Group: {group_id} global group cool down setting not found')
        elif setting_result.error and setting_result.info == 'NoResultFound':
            logger.debug(f'Rate Limiting | Group: {group_id} not set global group cool down, pass')
        else:
            logger.error(f'Rate Limiting | Set global group cool down getting setting failed: {setting_result.info}')


__all__ = [
    'preprocessor_rate_limiting',
    'postprocessor_rate_limiting'
]
