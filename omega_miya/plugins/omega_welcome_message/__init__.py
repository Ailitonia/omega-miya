"""
@Author         : Ailitonia
@Date           : 2021/08/14 19:09
@FileName       : omega_welcome_message.py
@Project        : nonebot2_miya 
@Description    : 群自定义欢迎消息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.plugin import on_notice, on_command
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, GroupIncreaseNoticeEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.params import CommandArg, Arg

from omega_miya.database import InternalBotGroup
from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.rule import group_has_permission_level
from omega_miya.utils.message_tools import MessageTools


# Custom plugin usage text
__plugin_custom_name__ = '群欢迎消息'
__plugin_usage__ = r'''【群自定义欢迎消息插件】
向新入群的成员发送欢迎消息

用法:
/设置欢迎消息 [消息内容]
/移除欢迎消息'''


_SETTING_NAME: str = 'group_welcome_message'
"""数据库配置节点名称"""
_DEFAULT_WELCOME_MSG: str = '欢迎新朋友～\n进群请先看群公告～\n一起愉快地聊天吧!'
"""默认欢迎消息"""


set_welcome_msg = on_command(
    'SetWelcomeMsg',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='SetWelcomeMsg', level=10),
    aliases={'设置欢迎消息'},
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True
)


@set_welcome_msg.handle()
async def handle_parse_message(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    if cmd_arg:
        state.update({'message': cmd_arg})


@set_welcome_msg.got('message', prompt='请发送你要设置的欢迎消息:')
async def handle_switch(bot: Bot, matcher: Matcher, event: GroupMessageEvent, message: Message = Arg('message')):
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.group_id))
    message_data = MessageTools.dumps(message=message)

    setting_result = await run_async_catching_exception(group.set_auth_setting)(
        module=module_name, plugin=plugin_name, node=_SETTING_NAME, available=1, value=message_data)

    if isinstance(setting_result, Exception) or setting_result.error:
        logger.error(f'为群组: {event.group_id} 设置自定义欢迎消息失败, {setting_result}')
        await matcher.finish(f'为本群设定欢迎消息失败了QAQ, 请稍后再试或联系管理员处理')
    else:
        logger.success(f'已为群组: {event.group_id} 设置自定义欢迎消息: {message}')
        await matcher.finish(f'已为本群设定了欢迎消息:\n{"="*8}\n' + message)


remove_welcome_msg = on_command(
    'RemoveWelcomeMsg',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='RemoveWelcomeMsg', level=10),
    aliases={'移除欢迎消息'},
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True
)


@remove_welcome_msg.handle()
async def handle_remove(bot: Bot, matcher: Matcher, event: GroupMessageEvent):
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.group_id))

    setting_result = await run_async_catching_exception(group.set_auth_setting)(
        module=module_name, plugin=plugin_name, node=_SETTING_NAME, available=0)

    if isinstance(setting_result, Exception) or setting_result.error:
        logger.error(f'为群组: {event.group_id} 清除自定义欢迎消息失败, {setting_result}')
        await matcher.finish(f'为本群清除欢迎消息失败了QAQ, 请稍后再试或联系管理员处理')
    else:
        logger.success(f'已为群组: {event.group_id} 清除自定义欢迎消息')
        await matcher.finish(f'已清除了本群设定的欢迎消息!')


# 注册事件响应器, 新增群成员
welcome_message = on_notice(
    rule=group_has_permission_level(level=10),
    state=init_processor_state(name='WelcomeMessage', enable_processor=False),
    priority=90,
    block=False
)


@welcome_message.handle()
async def handle_group_increase(bot: Bot, matcher: Matcher, event: GroupIncreaseNoticeEvent):
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.group_id))

    setting_result = await run_async_catching_exception(group.query_auth_setting)(
        module=module_name, plugin=plugin_name, node=_SETTING_NAME)

    if isinstance(setting_result, Exception):
        logger.error(f'获取群组: {event.group_id} 自定义欢迎消息内容失败, {setting_result}')
        # 获取失败大概率就是没配置, 直接发送默认消息
        # await matcher.send(_DEFAULT_WELCOME_MSG)
        return
    elif setting_result is None or setting_result.available != 1:
        logger.info(f'群组: {event.group_id} 未配置自定义欢迎消息')
        return
    else:
        logger.success(f'群组: {event.group_id}, 有新用户: {event.user_id} 进群, 发送欢迎消息')
        message = MessageTools.loads(message_data=setting_result.value)
        await matcher.send(MessageSegment.at(user_id=event.user_id) + message)
