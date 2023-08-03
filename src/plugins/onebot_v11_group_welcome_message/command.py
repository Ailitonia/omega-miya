"""
@Author         : Ailitonia
@Date           : 2021/08/14 19:09
@FileName       : omega_welcome_message.py
@Project        : nonebot2_miya 
@Description    : 群自定义欢迎消息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated, cast

from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import Arg, Depends
from nonebot.plugin import CommandGroup, on_notice
from nonebot.permission import SUPERUSER

from nonebot.adapters.onebot.v11 import Bot, Message, GroupMessageEvent, GroupIncreaseNoticeEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

from src.service import EntityInterface, MatcherInterface, OmegaMessage, enable_processor_state
from src.params.handler import get_command_message_arg_parser_handler
from src.params.rule import event_has_permission_level


_SETTING_NAME: str = 'group_welcome_message'
"""数据库配置节点名称"""


welcome_message_manager = CommandGroup(
    'welcome_message',
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=20,
    block=True,
    state=enable_processor_state(name='OmeBotV11WelcomeMessageManager', level=10),
)


@welcome_message_manager.command(
    'set',
    aliases={'设置欢迎消息', '新增欢迎消息'},
    handlers=[get_command_message_arg_parser_handler('welcome_message')]
).got('welcome_message', prompt='请输入要设置的群欢迎消息:')
async def handle_set_welcome_message(
        _: GroupMessageEvent,
        bot: Bot,
        matcher: Matcher,
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface())],
        message: Annotated[Message, Arg('welcome_message')]
) -> None:
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name

    try:
        parsed_message = cast(OmegaMessage, entity_interface.get_msg_extractor(bot=bot)(message=message).message)
        await entity_interface.entity.set_auth_setting(
            module=module_name, plugin=plugin_name, node=_SETTING_NAME, available=1, value=parsed_message.dumps()
        )
        await entity_interface.entity.commit_session()
        logger.success(f'已为 {entity_interface.entity} 设置了自定义欢迎消息: {message}')
        await matcher.send(f'已为本群设置了欢迎消息:\n{"="*8}\n' + message)
    except Exception as e:
        logger.error(f'为 {entity_interface.entity} 设置自定义欢迎消息失败, {e!r}')
        await matcher.send(f'为本群设置欢迎消息失败, 请稍后再试或联系管理员处理')


@welcome_message_manager.command('remove', aliases={'删除欢迎消息', '移除欢迎消息', '取消欢迎消息'}).handle()
async def handle_remove_welcome_message(
        _: GroupMessageEvent,
        matcher: Matcher,
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface())]
) -> None:
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name

    try:
        await entity_interface.entity.set_auth_setting(
            module=module_name, plugin=plugin_name, node=_SETTING_NAME, available=0
        )
        await entity_interface.entity.commit_session()
        logger.success(f'已为 {entity_interface.entity} 移除了自定义欢迎消息')
        await matcher.send(f'已移除了本群设置的欢迎消息')
    except Exception as e:
        logger.error(f'为 {entity_interface.entity} 移除自定义欢迎消息失败, {e!r}')
        await matcher.send(f'为本群移除欢迎消息失败, 请稍后再试或联系管理员处理')


@on_notice(
    rule=event_has_permission_level(level=10),
    priority=92,
    block=False,
    state=enable_processor_state(name='OmeBotV11WelcomeMessage', enable_processor=False),
).handle()
async def handle_send_welcome_message(
        event: GroupIncreaseNoticeEvent,
        matcher: Matcher,
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface())]
) -> None:
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name

    try:
        welcome_message_setting = await entity_interface.entity.query_auth_setting(
            module=module_name, plugin=plugin_name, node=_SETTING_NAME
        )
        if welcome_message_setting.available == 1:
            logger.info(f'{entity_interface.entity}, 有新用户: {event.user_id} 进群, 发送欢迎消息')
            send_message = OmegaMessage.loads(message_data=welcome_message_setting.value)
            send_message = MatcherInterface().get_msg_builder()(send_message).message
            await matcher.send(message=send_message, at_sender=True)
    except Exception as e:
        logger.warning(f'{entity_interface.entity} 未配置自定义欢迎消息, 或发送消息失败, {e!r}')


__all__ = []
