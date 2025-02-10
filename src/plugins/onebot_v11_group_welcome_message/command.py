"""
@Author         : Ailitonia
@Date           : 2021/08/14 19:09
@FileName       : omega_welcome_message.py
@Project        : nonebot2_miya
@Description    : 群自定义欢迎消息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated, Literal

from nonebot.adapters.onebot.v11 import (
    Bot as OneBotV11Bot,
)
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent as OneBotV11GroupIncreaseNoticeEvent,
)
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent as OneBotV11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11 import (
    Message as OneBotV11Message,
)
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.log import logger
from nonebot.params import Arg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import CommandGroup, on_notice
from sqlalchemy.exc import NoResultFound

from src.params.handler import get_command_message_arg_parser_handler
from src.params.rule import event_has_permission_level
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessage, OmegaMessageTransfer, enable_processor_state

_SETTING_NAME: Literal['group_welcome_message'] = 'group_welcome_message'
"""数据库配置节点名称"""


welcome_message_manager = CommandGroup(
    'welcome-message',
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
        _: OneBotV11GroupMessageEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        message: Annotated[OneBotV11Message, Arg('welcome_message')],
) -> None:
    if interface.matcher.plugin is None:
        await interface.matcher.finish()

    plugin_name = interface.matcher.plugin.name
    module_name = interface.matcher.plugin.module_name

    try:
        parsed_message = await OmegaMessageTransfer(interface=interface, origin_message=message).dumps()
        await interface.entity.set_auth_setting(
            module=module_name, plugin=plugin_name, node=_SETTING_NAME, available=1, value=parsed_message.dumps()
        )
        await interface.entity.commit_session()
        logger.success(f'已为 {interface.entity} 设置了自定义欢迎消息: {parsed_message}')
        await interface.send_reply(f'已为本群设置了欢迎消息:\n{"=" * 8}\n' + parsed_message)
    except Exception as e:
        logger.error(f'为 {interface.entity} 设置自定义欢迎消息失败, {e!r}')
        await interface.send_reply('为本群设置欢迎消息失败, 请稍后再试或联系管理员处理')


@welcome_message_manager.command('remove', aliases={'删除欢迎消息', '移除欢迎消息', '取消欢迎消息'}).handle()
async def handle_remove_welcome_message(
        _: OneBotV11GroupMessageEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    if interface.matcher.plugin is None:
        await interface.matcher.finish()

    plugin_name = interface.matcher.plugin.name
    module_name = interface.matcher.plugin.module_name

    try:
        await interface.entity.set_auth_setting(
            module=module_name, plugin=plugin_name, node=_SETTING_NAME, available=0
        )
        await interface.entity.commit_session()
        logger.success(f'已为 {interface.entity} 移除了自定义欢迎消息')
        await interface.send_reply('已移除了本群设置的欢迎消息')
    except Exception as e:
        logger.error(f'为 {interface.entity} 移除自定义欢迎消息失败, {e!r}')
        await interface.send_reply('为本群移除欢迎消息失败, 请稍后再试或联系管理员处理')


@on_notice(
    rule=event_has_permission_level(level=10),
    priority=92,
    block=False,
    state=enable_processor_state(name='OmeBotV11WelcomeMessage', enable_processor=False),
).handle()
async def handle_send_welcome_message(
        _: OneBotV11Bot,
        event: OneBotV11GroupIncreaseNoticeEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    if interface.matcher.plugin is None:
        await interface.matcher.finish()

    plugin_name = interface.matcher.plugin.name
    module_name = interface.matcher.plugin.module_name

    try:
        welcome_message_setting = await interface.entity.query_auth_setting(
            module=module_name, plugin=plugin_name, node=_SETTING_NAME
        )

        if welcome_message_setting.value is None or welcome_message_setting.available != 1:
            logger.info(f'{interface.entity}, 有新用户: {event.user_id} 进群, 未启用欢迎消息, 跳过发送欢迎消息流程')
            return

        logger.info(f'{interface.entity}, 有新用户: {event.user_id} 进群, 发送欢迎消息')
        send_message = OmegaMessage.loads(message_data=welcome_message_setting.value)
        await interface.send_at_sender(message=send_message)
    except NoResultFound:
        logger.info(f'{interface.entity}, 有新用户: {event.user_id} 进群, 该群未配置欢迎消息, 跳过发送欢迎消息流程')
    except Exception as e:
        logger.error(f'{interface.entity} 有新用户: {event.user_id} 进群, 获取欢迎消息配置失败, 或发送消息失败, {e}')


__all__ = []
