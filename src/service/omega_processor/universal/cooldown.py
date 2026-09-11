"""
@Author         : Ailitonia
@Date           : 2023/3/19 22:49
@FileName       : cooldown
@Project        : nonebot2_miya
@Description    : 冷却检查
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime, timedelta

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import IgnoredException
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from pydantic import BaseModel, ConfigDict

from src.database import DATABASE_SESSION
from ...omega_base import OmegaEntity, OmegaMatcherInterface
from .processor_utils import parse_processor_state

_PLUGIN_CD_EVENT_PREFIX: str = 'plugin_cd_'
"""插件冷却事件前缀"""
_LOG_PREFIX: str = '<lc>Cooldown Manager</lc> | '
"""日志前缀"""


class _CooldownCheckingResult(BaseModel):
    """冷却检查结果"""
    is_expired: bool
    expired_time: datetime
    allow_skip: bool

    model_config = ConfigDict(extra='ignore', frozen=True)


async def _check_entity_cooldown(
        entity: 'OmegaEntity',
        cooldown_event: str,
        plugin_name: str,
        module_name: str,
) -> _CooldownCheckingResult:
    """检查对象是否在冷却期限内"""
    can_skip_cd = await entity.check_permission_skip_cooldown(module=module_name, plugin=plugin_name)

    if can_skip_cd:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{entity.tid} skip {plugin_name} cooldown with permission')
        return _CooldownCheckingResult(is_expired=True, expired_time=datetime.now(), allow_skip=True)

    is_expired, expired_time = await entity.check_cooldown_expired(cooldown_event=cooldown_event)

    return _CooldownCheckingResult(is_expired=is_expired, expired_time=expired_time, allow_skip=False)


async def preprocessor_cooldown(
        bot: BaseBot,
        event: BaseEvent,
        matcher: Matcher,
        db_session: DATABASE_SESSION,
) -> None:
    """运行预处理, 冷却处理"""

    # 跳过临时会话, 避免冷却在命令交互中被不正常触发
    if matcher.temp:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Temp matcher, ignore')
        return

    # 跳过非插件创建的 Matcher
    if matcher.plugin is None:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Non-plugin matcher, ignore')
        return

    # 从 state 中解析已配置的权限要求
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)
    cooldown_event = f'{_PLUGIN_CD_EVENT_PREFIX}{plugin_name}_{processor_state.name}'
    cooldown_type = processor_state.cooldown_type

    # 跳过超级用户
    if await SUPERUSER(bot=bot, event=event):
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored by <ly>SUPERUSER</ly>')
        return

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored with disabled processor')
        return

    # 跳过声明无冷却时间的
    if processor_state.cooldown <= 0:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored with non-cooldown')
        return

    allow_skip: bool = False
    is_expired: bool = True
    expired_time: datetime = datetime.now()
    tid: str

    match cooldown_type:
        case 'global':
            # 全局冷却需要同时检查事件和用户的冷却
            event_entity = OmegaMatcherInterface(
                bot=bot,
                event=event,
                matcher=matcher,
                acquire_type='event',
            ).get_current_entity(db_session=db_session)

            event_is_expired, event_expired_time = await event_entity.check_global_cooldown_expired()

            is_expired = event_is_expired and is_expired
            expired_time = event_expired_time if event_expired_time > expired_time else expired_time

            user_entity = OmegaMatcherInterface(
                bot=bot,
                event=event,
                matcher=matcher,
                acquire_type='user',
            ).get_current_entity(db_session=db_session)

            user_is_expired, user_expired_time = await user_entity.check_global_cooldown_expired()

            is_expired = user_is_expired and is_expired
            expired_time = user_expired_time if user_expired_time > expired_time else expired_time
            tid = f'{event_entity.tid}/{user_entity.tid}'
        case 'event':
            entity = OmegaMatcherInterface(
                bot=bot,
                event=event,
                matcher=matcher,
                acquire_type='event',
            ).get_current_entity(db_session=db_session)

            checked = await _check_entity_cooldown(entity, cooldown_event, plugin_name, module_name)

            allow_skip = checked.allow_skip or allow_skip
            is_expired = checked.is_expired and is_expired
            expired_time = checked.expired_time if checked.expired_time > expired_time else expired_time
            tid = entity.tid
        case 'user':
            entity = OmegaMatcherInterface(
                bot=bot,
                event=event,
                matcher=matcher,
                acquire_type='user',
            ).get_current_entity(db_session=db_session)

            checked = await _check_entity_cooldown(entity, cooldown_event, plugin_name, module_name)

            allow_skip = checked.allow_skip or allow_skip
            is_expired = checked.is_expired and is_expired
            expired_time = checked.expired_time if checked.expired_time > expired_time else expired_time
            tid = entity.tid
        case _:
            logger.opt(colors=True).warning(f'{_LOG_PREFIX}{plugin_name} ignored with undefined cooldown type')
            return

    if allow_skip:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} allowed to skip cooldown')
        return

    # 冷却过期后就要新增冷却
    if is_expired:
        match cooldown_type:
            case 'global':
                event_entity = OmegaMatcherInterface(
                    bot=bot,
                    event=event,
                    matcher=matcher,
                    acquire_type='event',
                ).get_current_entity(db_session=db_session)
                await event_entity.set_global_cooldown(
                    expired_time=timedelta(seconds=processor_state.cooldown),
                )

                user_entity = OmegaMatcherInterface(
                    bot=bot,
                    event=event,
                    matcher=matcher,
                    acquire_type='user',
                ).get_current_entity(db_session=db_session)
                cooldown = await user_entity.set_global_cooldown(
                    expired_time=timedelta(seconds=processor_state.cooldown),
                )
            case 'event':
                entity = OmegaMatcherInterface(
                    bot=bot,
                    event=event,
                    matcher=matcher,
                    acquire_type='event',
                ).get_current_entity(db_session=db_session)
                cooldown = await entity.set_cooldown(
                    cooldown_event=cooldown_event,
                    expired_time=timedelta(seconds=processor_state.cooldown),
                )
            case 'user':
                entity = OmegaMatcherInterface(
                    bot=bot,
                    event=event,
                    matcher=matcher,
                    acquire_type='user',
                ).get_current_entity(db_session=db_session)
                cooldown = await entity.set_cooldown(
                    cooldown_event=cooldown_event,
                    expired_time=timedelta(seconds=processor_state.cooldown),
                )
        logger.opt(colors=True).debug(
            f'{_LOG_PREFIX}{plugin_name} <ly>{tid}</ly> cooldown expired and refreshed at {cooldown.stop_at}'
        )
        return

    # 冷却未过期则发送提示消息并忽略事件
    logger.opt(colors=True).info(
        f'{_LOG_PREFIX}{plugin_name} <ly>{tid}</ly> still in cooldown, will expired at: {expired_time}'
    )
    if processor_state.echo_processor_result:
        try:
            echo_message = f'冷却中, 请稍后再试!\n冷却结束时间: {expired_time.strftime("%Y-%m-%d %H:%M:%S")}'
            await matcher.send(message=echo_message)
        except Exception as e:
            logger.opt(colors=True).warning(
                f'{_LOG_PREFIX}{plugin_name} send cooldown holding message failed, {e}'
            )
    raise IgnoredException('冷却中')


__all__ = [
    'preprocessor_cooldown',
]
