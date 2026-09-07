"""
@Author         : Ailitonia
@Date           : 2023/3/19 21:13
@FileName       : permission
@Project        : nonebot2_miya
@Description    : 权限检查
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import IgnoredException
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER

from src.database import DATABASE_SESSION
from .processor_utils import parse_processor_state
from ...omega_base import OmegaEntity, OmegaMatcherInterface

_LOG_PREFIX: str = '<lc>Permission Manager</lc> | '
"""日志前缀"""


async def _check_entity_permission(
        entity: 'OmegaEntity',
        module_name: str,
        plugin_name: str,
        node: str,
        level: int,
) -> bool:
    """检查 Entity 是否具备权限

    权限判断机制:
        - node 验证通过: 不论 level 是否通过均视为通过
        - node 未配置: level 通过视为通过, 否则视为不通过
        - node 被拒绝: 视为不通过
    """
    node_checked = await entity.verify_auth_setting(module=module_name, plugin=plugin_name, node=node)

    match node_checked:
        case 1:  # node 通过: 不论 level 是否通过均视为通过
            is_allowed = True
        case 0:  # node 未配置: level 通过视为通过, 否则视为不通过
            is_allowed = await entity.check_permission_level(level=level)
        case -1 | _:  # node 不通过: 视为不通过
            is_allowed = False

    return is_allowed


async def preprocessor_permission(
        bot: BaseBot,
        event: BaseEvent,
        matcher: Matcher,
        db_session: DATABASE_SESSION,
) -> None:
    """运行预处理, 检查是否具备权限"""

    # 跳过非插件创建的 Matcher
    if matcher.plugin is None:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Non-plugin matcher, ignore')
        return

    # 从 state 中解析已配置的权限要求
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过超级用户
    if await SUPERUSER(bot=bot, event=event):
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored by <ly>SUPERUSER</ly>')
        return

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored with disabled processor')
        return

    event_entity = OmegaMatcherInterface(
        bot=bot,
        event=event,
        matcher=matcher,
        acquire_type='event',
    ).get_current_entity(db_session=db_session)

    user_entity = OmegaMatcherInterface(
        bot=bot,
        event=event,
        matcher=matcher,
        acquire_type='user',
    ).get_current_entity(db_session=db_session)

    # 全局权限检查只确认当前事件(以当前事件确定是否启用), 插件权限检查才同时检查触发用户
    global_checked = await event_entity.check_global_permission()

    if not global_checked:
        logger.opt(colors=True).info(
            f'{_LOG_PREFIX}{plugin_name} blocked <ly>{event_entity.tid}</ly>, global permission <ly>deny</ly>'
        )
        if processor_state.echo_processor_result:
            try:
                echo_message = 'Omega Miya 未启用, 请尝试使用 "/Start" 命令初始化, 或联系管理员处理'
                await matcher.send(message=echo_message)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'{_LOG_PREFIX}{plugin_name} send permission blocked message failed, {e}'
                )
        raise IgnoredException('权限不足')

    # 检查事件及用户是否具备插件要求权限
    permission_checked = await _check_entity_permission(
        entity=event_entity,
        module_name=module_name,
        plugin_name=plugin_name,
        node=processor_state.auth_node,
        level=processor_state.level,
    )
    if not permission_checked:
        permission_checked = await _check_entity_permission(
            entity=user_entity,
            module_name=module_name,
            plugin_name=plugin_name,
            node=processor_state.auth_node,
            level=processor_state.level,
        )

    if not permission_checked:
        logger.opt(colors=True).info(
            f'{_LOG_PREFIX}{plugin_name} <r>Denied</r> <ly{event_entity.tid}/{user_entity.tid}</ly> request'
        )
        if processor_state.echo_processor_result:
            try:
                echo_message = '权限不足! 需要'
                if processor_state.level <= 100:
                    echo_message += f'权限等级 Level-{processor_state.level} 或'
                    echo_message += f'权限节点 "{plugin_name}.{processor_state.auth_node}", '
                    echo_message += '请联系管理员提升权限等级或配置插件对应权限节点'
                else:
                    echo_message += f'权限节点 "{plugin_name}.{processor_state.auth_node}", '
                    echo_message += '请联系管理员配置插件对应权限节点'
                await matcher.send(message=echo_message)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'{_LOG_PREFIX}{plugin_name} send permission blocked message failed, {e}'
                )
        raise IgnoredException('权限不足')

    logger.opt(colors=True).debug(
        f'{_LOG_PREFIX}{plugin_name} <g>Allowed</g> <ly{event_entity.tid}/{user_entity.tid}</ly> request'
    )


__all__ = [
    'preprocessor_permission',
]
