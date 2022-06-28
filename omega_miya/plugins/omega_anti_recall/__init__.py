"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : omega_anti_recall.py
@Project        : nonebot2_miya
@Description    : Omega 反撤回插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import Literal
from nonebot.log import logger
from nonebot.plugin import on_command, on_notice, PluginMetadata
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, GroupRecallNoticeEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import InternalBotGroup
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.rule import group_has_permission_node
from omega_miya.utils.message_tools import MessageTools


__plugin_meta__ = PluginMetadata(
    name="反撤回",
    description="【AntiRecall 反撤回插件】\n"
                "检测消息撤回并提取原消息",
    usage="仅限群聊中群管理员使用:\n"
          "/AntiRecall <ON|OFF>",
    extra={"author": "Ailitonia"},
)


_ANTI_RECALL_CUSTOM_MODULE_NAME: Literal['Omega.AntiRecall'] = 'Omega.AntiRecall'
"""固定写入数据库的 module name 参数"""
_ANTI_RECALL_CUSTOM_PLUGIN_NAME: Literal['omega_anti_recall'] = 'omega_anti_recall'
"""固定写入数据库的 plugin name 参数"""
_ENABLE_ANTI_RECALL_NODE: Literal['enable_anti_recall'] = 'enable_anti_recall'
"""启用反撤回的权限节点"""


# 注册事件响应器
AntiRecallManager = on_command(
    'AntiRecall',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='AntiRecallManager', level=10, auth_node='anti_recall_manager'),
    aliases={'antirecall', '反撤回'},
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True
)


@AntiRecallManager.handle()
async def handle_parse_switch(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    switch = cmd_arg.extract_plain_text().strip().lower()
    if switch in ('on', 'off'):
        state.update({'switch': switch})


@AntiRecallManager.got('switch', prompt='启用或关闭反撤回:\n【ON/OFF】')
async def handle_switch(bot: Bot, matcher: Matcher, event: GroupMessageEvent, switch: str = ArgStr('switch')):
    switch = switch.strip().lower()
    group_id = str(event.group_id)
    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=group_id)

    match switch:
        case 'on':
            switch_result = await run_async_catching_exception(group.set_auth_setting)(
                module=_ANTI_RECALL_CUSTOM_MODULE_NAME, plugin=_ANTI_RECALL_CUSTOM_PLUGIN_NAME,
                node=_ENABLE_ANTI_RECALL_NODE, available=1
            )
        case 'off':
            switch_result = await run_async_catching_exception(group.set_auth_setting)(
                module=_ANTI_RECALL_CUSTOM_MODULE_NAME, plugin=_ANTI_RECALL_CUSTOM_PLUGIN_NAME,
                node=_ENABLE_ANTI_RECALL_NODE, available=0
            )
        case _:
            await matcher.reject('没有这个选项哦, 选择【ON/OFF】以启用或关闭反撤回:')
            return

    if isinstance(switch_result, Exception) or switch_result.error:
        logger.error(f"Group({group_id}) 设置 AntiRecall 反撤回功能开关为 {switch} 失败, {switch_result}")
        await matcher.finish(f'设置 AntiRecall 反撤回功能开关失败QAQ, 请联系管理员处理')
    else:
        logger.success(f"Group({group_id}) 设置 AntiRecall 反撤回功能开关为 {switch} 成功")
        await matcher.finish(f'已设置 AntiRecall 反撤回功能开关为 {switch}!')


AntiRecall = on_notice(
    rule=group_has_permission_node(
        module=_ANTI_RECALL_CUSTOM_MODULE_NAME,
        plugin=_ANTI_RECALL_CUSTOM_PLUGIN_NAME,
        node=_ENABLE_ANTI_RECALL_NODE
    ),
    state=init_processor_state(name='AntiRecall', enable_processor=False, echo_processor_result=False),
    priority=100,
    block=False
)


@AntiRecall.handle()
async def check_recall_notice(bot: Bot, event: GroupRecallNoticeEvent):
    user_id = event.user_id
    # 不响应自己撤回或由自己撤回的消息
    if user_id == event.self_id or event.operator_id == event.self_id:
        return

    message_id = event.message_id
    gocq_bot = GoCqhttpBot(bot=bot)
    message = await run_async_catching_exception(gocq_bot.get_msg)(message_id=message_id)

    if isinstance(message, Exception):
        logger.error(f'AntiRecall 查询历史消息失败, message_id: {message_id}, {message}')
        return

    filter_msg = MessageTools(message=message.message).filter_message_segment('text', 'image')
    sent_msg = f"已检测到撤回消息:\n"\
               + datetime.fromtimestamp(message.time).strftime('%Y/%m/%d %H:%M:%S')\
               + MessageSegment.at(user_id=user_id)\
               + '\n----消息内容----\n'\
               + filter_msg
    logger.success(f'AntiRecall 已捕获并处理撤回消息, message_id: {message_id}')
    await AntiRecall.finish(sent_msg)
