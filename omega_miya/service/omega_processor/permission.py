from nonebot import get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from omega_miya.service.omega_processor_tools import parse_processor_state
from omega_miya.database import EventEntityHelper
from omega_miya.database.internal.entity import BaseInternalEntity
from omega_miya.utils.process_utils import run_async_catching_exception


global_config = get_driver().config
SUPERUSERS = global_config.superusers

_log_prefix: str = '<lc>PermissionPreprocessor</lc> | '


async def preprocessor_permission(matcher: Matcher, bot: Bot, event: MessageEvent):
    """权限处理"""

    # 从 state 中解析已配置的权限要求
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name}) ignored with disable processor')
        return

    user_id = event.user_id

    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name}) ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    permission_allow_tag = False

    # 检查用户权限
    user_entity = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
    user_permission_result = await _check_entity_permission(
        entity=user_entity, module_name=module_name, plugin_name=plugin_name,
        level=processor_state.level, auth_node=processor_state.auth_node, add_entity_name=event.sender.nickname
    )
    if not isinstance(user_permission_result, Exception) and user_permission_result:
        permission_allow_tag = True

    # 检查群组/频道权限
    group_entity = EventEntityHelper(bot=bot, event=event).get_event_entity()
    if not permission_allow_tag and group_entity.relation_type != 'bot_user':
        group_permission_result = await _check_entity_permission(
            entity=group_entity, module_name=module_name, plugin_name=plugin_name,
            level=processor_state.level, auth_node=processor_state.auth_node
        )
        if not isinstance(group_permission_result, Exception) and group_permission_result:
            permission_allow_tag = True

    if permission_allow_tag:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name})/Matcher({processor_state.name}) '
                                      f'<g>Allowed</g> <ly>Entity({group_entity.tid}/{user_entity.tid})</ly> '
                                      f'permission request')
    else:
        logger.opt(colors=True).info(f'{_log_prefix}Plugin({plugin_name})/Matcher({processor_state.name}) '
                                     f'<r>Denied</r> <ly>Entity({group_entity.tid}/{user_entity.tid})</ly> '
                                     f'permission request')
        if processor_state.echo_processor_result:
            echo_message = f'权限不足QAQ, 请向管理员申请{processor_state.name}相关权限'
            await run_async_catching_exception(bot.send)(event=event, message=echo_message, at_sender=True)
        raise IgnoredException('权限不足')


@run_async_catching_exception
async def _check_entity_permission(
        entity: BaseInternalEntity,
        module_name: str,
        plugin_name: str,
        level: int,
        auth_node: str | None,
        *,
        add_entity_name: str = ''
) -> bool:
    """检查用户/群组/频道权限, 若用户不存在则在数据库中初始化用户 Entity

    权限判断机制:
        - global_permission: 一票否决
        - 无 node 声明: level 通过则视为通过
        - 有 node 声明:
            - node 通过: 不论 level 是否通过均视为通过
            - node 未配置: level 通过视为通过, 否则视为不通过
            - node 不通过: 视为不通过
    """
    permission_allow_tag = False

    try:
        entity_permission_level = await entity.check_permission_level(level=level)
        if auth_node is None:
            # 无 node 声明: level 通过则视为通过
            if entity_permission_level:
                permission_allow_tag = True
        else:
            # 有 node 声明
            entity_node_permission = await entity.verify_auth_setting(module=module_name, plugin=plugin_name,
                                                                      node=auth_node, require_available=False)
            match entity_node_permission:
                case 1:  # node 通过: 不论 level 是否通过均视为通过
                    permission_allow_tag = True
                case 0:  # node 未配置: level 通过视为通过, 否则视为不通过
                    if entity_permission_level:
                        permission_allow_tag = True
                case -1:  # node 不通过: 视为不通过
                    permission_allow_tag = False

        entity_global_permission = await entity.check_global_permission()
        if not entity_global_permission:
            # global_permission: 一票否决
            permission_allow_tag = False
    except Exception as e:
        logger.opt(colors=True).debug(
            f'{_log_prefix}Plugin({plugin_name}) check Entity({entity.tid}) permission failed, {e}')
        add_entity = await entity.add_only(entity_name=add_entity_name, related_entity_name=add_entity_name)
        if add_entity.success:
            logger.opt(colors=True).debug(f'{_log_prefix}Add and init Entity({entity.tid}) succeed')
        else:
            logger.opt(colors=True).error(f'{_log_prefix}Add Entity({entity.tid}) failed, {add_entity.info}')

    return permission_allow_tag


__all__ = [
    'preprocessor_permission'
]
