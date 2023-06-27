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
from pydantic import BaseModel

from nonebot import get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.internal.adapter import Bot, Event


from src.service.omega_base import OmegaEntity, EntityInterface

from ..plugin_utils import parse_processor_state


SUPERUSERS = get_driver().config.superusers
PLUGIN_CD_PREFIX: str = 'plugin_cd'
LOG_PREFIX: str = '<lc>Cooldown Manager</lc> | '


class _CooldownCheckingResult(BaseModel):
    """冷却检查结果"""
    is_expired: bool
    expired_time: datetime
    allow_skip: bool


async def preprocessor_global_cooldown(matcher: Matcher, bot: Bot, event: Event):
    """运行预处理, 冷却全局处理"""

    user_id = event.get_user_id()
    # 忽略超级用户
    if user_id in SUPERUSERS:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    plugin_name = matcher.plugin.name
    is_expired: bool = True
    expired_time: datetime = datetime.now()

    async with EntityInterface(acquire_type='event').get_entity(bot=bot, event=event) as event_entity:
        event_global_is_expired, event_global_expired_time = await event_entity.check_global_cooldown_expired()
    if not event_global_is_expired:
        is_expired = False
        expired_time = event_global_expired_time if event_global_expired_time > expired_time else expired_time

    async with EntityInterface(acquire_type='user').get_entity(bot=bot, event=event) as user_entity:
        user_global_is_expired, user_global_expired_time = await user_entity.check_global_cooldown_expired()
    if not user_global_is_expired:
        is_expired = False
        expired_time = user_global_expired_time if user_global_expired_time > expired_time else expired_time

    if not is_expired:
        logger.opt(colors=True).info(
            f'{LOG_PREFIX}{matcher}/Plugin({plugin_name}) <ly>Entity({event_entity.tid}/{user_entity.tid})</ly> '
            f'still in <ly>Global Cooldown</ly>, expired time: {expired_time}'
        )
        echo_message = f'全局冷却中, 请稍后再试!\n冷却结束时间: {expired_time.strftime("%Y-%m-%d %H:%M:%S")}'
        await matcher.send(message=echo_message, at_sender=True)
        raise IgnoredException('全局冷却中')


async def preprocessor_plugin_cooldown(matcher: Matcher, bot: Bot, event: Event):
    """运行预处理, 冷却插件处理"""

    # 跳过由 got 等事件处理函数创建临时 matcher 避免冷却在命令交互中被不正常触发
    if matcher.temp:
        return

    # 从 state 中解析已配置的权限要求
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) ignored with disable processor')
        return

    # 跳过声明无冷却时间的
    if processor_state.cooldown <= 0:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) ignored with disable cooldown')
        return

    user_id = event.get_user_id()
    # 忽略超级用户
    if user_id in SUPERUSERS:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    cooldown_event = f'{PLUGIN_CD_PREFIX}_{plugin_name}_{processor_state.name}'
    entity_depend = EntityInterface(acquire_type=processor_state.cooldown_type)

    # 检查冷却
    async with entity_depend.get_entity(bot=bot, event=event) as entity:
        cooldown_checking_result = await _check_entity_cooldown(
            entity=entity, cooldown_event=cooldown_event, plugin_name=plugin_name, module_name=module_name
        )

    allow_skip = cooldown_checking_result.allow_skip
    is_expired = cooldown_checking_result.is_expired
    expired_time = cooldown_checking_result.expired_time

    if allow_skip:
        logger.opt(colors=True).debug(
            f'{LOG_PREFIX}{matcher}/Plugin({plugin_name}) <ly>Entity({entity.tid})</ly> allowed to skip cooldown'
        )
        return
    elif is_expired:
        # 冷却过期后就要新增冷却
        async with entity_depend.get_entity(bot=bot, event=event) as entity:
            await entity.set_cooldown(
                cooldown_event=cooldown_event, expired_time=timedelta(seconds=processor_state.cooldown)
            )
        logger.opt(colors=True).debug(
            f'{LOG_PREFIX}{matcher}/Plugin({plugin_name}) <ly>Entity({entity.tid})</ly> '
            f'cooldown is expired and has been refresh'
        )
        return
    else:
        logger.opt(colors=True).info(
            f'{LOG_PREFIX}{matcher}/Plugin({plugin_name}) <ly>Entity({entity.tid})</ly> still in cooldown, '
            f'expired time: {expired_time}'
        )
        if processor_state.echo_processor_result:
            echo_message = f'冷却中, 请稍后再试!\n冷却结束时间: {expired_time.strftime("%Y-%m-%d %H:%M:%S")}'
            await matcher.send(message=echo_message, at_sender=True)
        raise IgnoredException('冷却中')


async def _check_entity_cooldown(
        entity: OmegaEntity,
        cooldown_event: str,
        plugin_name: str,
        module_name: str,
) -> _CooldownCheckingResult:
    """检查用户/群组/频道冷却"""

    # 先检查是否有跳过冷却权限
    can_skip_cd = await entity.check_permission_skip_cooldown(module=module_name, plugin=plugin_name)
    if can_skip_cd:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) skip cd by Entity({entity.tid}) permission')
        return _CooldownCheckingResult(is_expired=True, expired_time=datetime.now(), allow_skip=True)

    # 检查并处理冷却
    is_expired, expired_time = await entity.check_cooldown_expired(cooldown_event=cooldown_event)

    return _CooldownCheckingResult(is_expired=is_expired, expired_time=expired_time, allow_skip=False)


__all__ = [
    'preprocessor_global_cooldown',
    'preprocessor_plugin_cooldown'
]
