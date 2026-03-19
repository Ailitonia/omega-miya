"""
@Author         : Ailitonia
@Date           : 2026/3/19 17:02
@FileName       : command
@Project        : omega-miya
@Description    : 透明转发插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import Annotated

from nonebot.adapters import Message as BaseMessage
from nonebot.log import logger
from nonebot.params import ArgStr, EventMessage
from nonebot.plugin import MatcherGroup

from src.params.depends import (
    EVENT_ENTITY_PARAMS,
    USER_ENTITY_PARAMS,
    EVENT_MATCHER_INTERFACE,
    get_entity_interface_from_index,
)
from src.params.handler import get_command_str_single_arg_parser_handler
from src.params.permission import IS_ADMIN
from src.service import enable_processor_state
from .bind_utils import (
    generate_bind_verification_code,
    query_verification_code_bind_entity_index_id,
    bind_forward_entity,
    unbind_forward_entity,
    query_bound_target_entities,
    query_bound_target_entity_index_ids,
    event_has_forward_target_setting,
)

transparent_forward = MatcherGroup(
    permission=IS_ADMIN,
    priority=30,
    block=True,
    state=enable_processor_state(name='TransparentForward', level=10),
)


@transparent_forward.on_command(
    'transparent_forward_generate_bind_verification_code',
    aliases={'生成透明转发验证码', }
).handle()
async def _transparent_forward_generate_entity_bind_verification_code(interface: EVENT_MATCHER_INTERFACE) -> None:
    """为当前会话生成透明转发绑定验证码"""
    try:
        code = await generate_bind_verification_code(interface)
        logger.info(f'TransparentForward | {interface.entity.tid!r} 生成了绑定验证码: {code!r}')
        await interface.send_reply(
            f'已生成透明转发绑定验证码: {code!r}, 请在待绑定的会话中验证, 被绑定的会话将会接收本会话的消息')
    except Exception as e:
        logger.error(f'TransparentForward | {interface.entity.tid!r} 生成绑定验证码失败, {e}')
        await interface.send_reply('生成透明转发绑定验证码失败, 请稍后重试或联系管理员处理')


@transparent_forward.on_command(
    'transparent_forward_bind_entity',
    aliases={'绑定透明转发会话', },
    handlers=[get_command_str_single_arg_parser_handler('verification_code', ensure_key=True)],
).got('verification_code', prompt='请发送待绑定会话的验证码, 绑定后将会接收目标会话的消息:')
async def _bind_transparent_forward_entity(
        interface: EVENT_MATCHER_INTERFACE,
        verification_code: Annotated[str | None, ArgStr('verification_code')],
) -> None:
    if not verification_code:
        await interface.reject_arg_reply('verification_code', '请发送待绑定会话的验证码, 绑定后将会接收目标会话的消息:')

    verification_code = verification_code.strip()

    try:
        entity_index_id = await query_verification_code_bind_entity_index_id(verification_code)
    except Exception as e:
        logger.error(f'TransparentForward | 查询绑定验证码: {verification_code!r} 失败, {e}')
        await interface.finish_reply('查询绑定验证码失败, 请稍后重试或联系管理员处理')
        return

    if not entity_index_id:
        await interface.finish_reply('无效的绑定验证码失败, 请确认后重试')
        return

    try:
        target_entity = await interface.entity.query_entity_self()
        async with get_entity_interface_from_index(index_id=entity_index_id) as source_entity:
            if source_entity.entity.tid == interface.entity.tid:
                await interface.send_reply('不能绑定同一会话为转发会话!')
                return

            await bind_forward_entity(
                source_entity=source_entity,
                target_entity_index_id=target_entity.id,
                target_entity_tid=interface.entity.tid,
                target_entity_name=interface.entity.entity_name,
            )
        logger.success(f'TransparentForward | {interface.entity.tid!r} 绑定 {entity_index_id!r} 成功')
        await interface.send_reply('绑定成功')
    except Exception as e:
        logger.error(f'TransparentForward | {interface.entity.tid!r} 绑定 {entity_index_id!r} 失败, {e}')
        await interface.send_reply('绑定失败, 请稍后重试或联系管理员处理')


@transparent_forward.on_command(
    'transparent_forward_unbind_entity',
    aliases={'移除透明转发会话', '取消透明转发会话', },
    handlers=[get_command_str_single_arg_parser_handler('target_entity_id', ensure_key=True)],
).got('target_entity_id', prompt='请输入想要移除的目标会话ID:')
async def _unbind_transparent_forward_entity(
        interface: EVENT_MATCHER_INTERFACE,
        target_entity_id: Annotated[str | None, ArgStr('target_entity_id')],
) -> None:
    bound_target_entities = await query_bound_target_entities(source_entity=interface)

    if not bound_target_entities:
        await interface.finish_reply('没有已绑定的会话')
        return

    if not target_entity_id:
        bound_target_entities_text = '\n'.join(f'{k}: {v}' for k, v in bound_target_entities.items())
        prompt_message = f'当前已绑定的转发对象:\n{bound_target_entities_text}\n\n请输入想要移除的目标会话ID:'
        await interface.reject_arg_reply('target_entity_id', prompt_message)

    target_entity_id = target_entity_id.strip()

    if not target_entity_id.isdigit() or int(target_entity_id) not in bound_target_entities:
        await interface.finish_reply(f'ID: {target_entity_id} 不是已绑定的会话, 请确认后重试')
        return

    try:
        await unbind_forward_entity(source_entity=interface, target_entity_index_id=int(target_entity_id))
        logger.success(f'TransparentForward | {interface.entity.tid!r} 移除绑定 {target_entity_id!r} 成功')
        await interface.send_reply('移除绑定成功')
    except Exception as e:
        logger.error(f'TransparentForward | {interface.entity.tid!r} 移除绑定 {target_entity_id!r} 失败, {e!r}')
        await interface.send_reply('移除绑定成功, 请稍后重试或联系管理员处理')


@transparent_forward.on_message(
    rule=event_has_forward_target_setting(),
    permission=None,
).handle()
async def _handle_transparent_forward(
        interface: EVENT_MATCHER_INTERFACE,
        event_entity_params: EVENT_ENTITY_PARAMS,
        user_entity_params: USER_ENTITY_PARAMS,
        origin_message: Annotated[BaseMessage, EventMessage()]
) -> None:
    source_entity = await interface.entity.query_entity_self()
    bound_target_entity_index_ids = query_bound_target_entity_index_ids(source_entity.id)
    if not bound_target_entity_index_ids:
        return

    source_info = (
        f'From: {event_entity_params.entity_type.split("_")[0][:3]}'
        f' | {event_entity_params.entity_name}@{user_entity_params.entity_name}\n'
        f'{datetime.now().strftime("%Y-%m-%d %H:%M")}\n{"-" * 8}\n\n'
    )

    parsed_message = source_info + interface.get_message_extractor()(message=origin_message).message

    for entity_index_id in bound_target_entity_index_ids:
        try:
            async with get_entity_interface_from_index(index_id=entity_index_id) as target_interface:
                await target_interface.send_entity_message(message=parsed_message)
        except Exception as e:
            logger.error(f'TransparentForward | {interface.entity.tid} forward to {entity_index_id} failed, {e!r}')


__all__ = []
