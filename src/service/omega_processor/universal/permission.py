"""
@Author         : Ailitonia
@Date           : 2023/3/19 21:13
@FileName       : permission
@Project        : nonebot2_miya
@Description    : 权限检查
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.internal.adapter import Bot, Event

from src.service import OmegaEntity, OmegaInterface

from ..plugin_utils import parse_processor_state


SUPERUSERS = get_driver().config.superusers
LOG_PREFIX: str = '<lc>Permission Manager</lc> | '


async def preprocessor_global_permission(matcher: Matcher, bot: Bot, event: Event):
    """运行预处理, 检查是否启用全局权限"""

    # 从 state 中解析已配置的权限要求
    plugin_name = matcher.plugin.name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) ignored global check with disable processor')
        return

    user_id = event.get_user_id()
    # 忽略超级用户
    if user_id in SUPERUSERS:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    async with OmegaInterface(acquire_type='event').get_entity(bot=bot, event=event) as event_entity:
        is_enabled_global_permission = await event_entity.check_global_permission()

    if not is_enabled_global_permission:
        logger.opt(colors=True).info(
            f'{LOG_PREFIX}{matcher}/Plugin({matcher.plugin.name}) is blocked, <ly>global permission not enabled</ly>'
        )
        if processor_state.echo_processor_result:
            try:
                echo_message = f'Omega Miya 未启用, 请尝试使用 "/Start" 命令初始化, 或联系管理员处理'
                await matcher.send(message=echo_message)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'{LOG_PREFIX}{matcher}/Plugin({matcher.plugin.name}) send permission blocked message failed, {e!r}'
                )
        raise IgnoredException('权限不足')


async def preprocessor_plugin_permission(matcher: Matcher, bot: Bot, event: Event):
    """运行预处理, 检查会话对象是否具备插件要求权限"""

    # 从 state 中解析已配置的权限要求
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) ignored with disable processor')
        return

    user_id = event.get_user_id()
    # 忽略超级用户
    if user_id in SUPERUSERS:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    # 检查事件会话对象是否具备插件要求权限
    async with OmegaInterface(acquire_type='event').get_entity(bot=bot, event=event) as event_entity:
        is_permission_allowed = await _check_event_entity_permission(
            entity=event_entity, module_name=module_name, plugin_name=plugin_name,
            level=processor_state.level, auth_node=processor_state.auth_node
        )

    if is_permission_allowed:
        logger.opt(colors=True).debug(
            f'{LOG_PREFIX}{matcher}/Plugin({plugin_name}) <g>Allowed</g> '
            f'<ly>Entity({event_entity.tid})</ly> permission request'
        )
    else:
        logger.opt(colors=True).info(
            f'{LOG_PREFIX}{matcher}/Plugin({plugin_name}) <r>Denied</r> '
            f'<ly>Entity({event_entity.tid})</ly> permission request')
        if processor_state.echo_processor_result:
            try:
                echo_message = f'权限不足! 需要'
                if processor_state.level <= 100:
                    echo_message += f'权限等级 Level-{processor_state.level} 或'
                    echo_message += f'权限节点 "{processor_state.name}.{processor_state.auth_node}", '
                    echo_message += f'请联系管理员使用 "/SetOmegaLevel {processor_state.level}" 提升权限等级或配置插件对应权限节点'
                else:
                    echo_message += f'权限节点 "{processor_state.name}.{processor_state.auth_node}", '
                    echo_message += f'请联系管理员配置插件对应权限节点'
                await matcher.send(message=echo_message)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'{LOG_PREFIX}{matcher}/Plugin({plugin_name}) send permission blocked message failed, {e!r}'
                )
        raise IgnoredException('权限不足')


async def _check_event_entity_permission(
        entity: OmegaEntity,
        module_name: str,
        plugin_name: str,
        level: int,
        auth_node: str | None
) -> bool:
    """检查用户/群组/频道权限

    权限判断机制:
        - 无 node 声明: level 通过则视为通过
        - 有 node 声明:
            - node 通过: 不论 level 是否通过均视为通过
            - node 未配置: level 通过视为通过, 否则视为不通过
            - node 不通过: 视为不通过
    """
    is_permission_allowed: bool = False

    is_level_allowed = await entity.check_permission_level(level=level)

    if auth_node is None:
        # 无 node 声明: level 通过则视为通过
        if is_level_allowed:
            is_permission_allowed = True
    else:
        # 有 node 声明
        node_permission = await entity.verify_auth_setting(module=module_name, plugin=plugin_name, node=auth_node)
        match node_permission:
            case 1:  # node 通过: 不论 level 是否通过均视为通过
                is_permission_allowed = True
            case 0:  # node 未配置: level 通过视为通过, 否则视为不通过
                if is_level_allowed:
                    is_permission_allowed = True
            case -1:  # node 不通过: 视为不通过
                is_permission_allowed = False

    return is_permission_allowed


__all__ = [
    'preprocessor_global_permission',
    'preprocessor_plugin_permission'
]
