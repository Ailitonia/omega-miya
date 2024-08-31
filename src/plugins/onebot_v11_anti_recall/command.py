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
from typing import Annotated, Literal

from nonebot.adapters.onebot.v11 import (
    Bot as OneBotV11Bot,
    Message as OneBotV11Message,
    MessageSegment as OneBotV11MessageSegment,
    GroupMessageEvent as OneBotV11GroupMessageEvent,
    GroupRecallNoticeEvent as OneBotV11GroupRecallNoticeEvent
)
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, CommandArg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command, on_notice
from nonebot.typing import T_State

from src.compat import parse_obj_as
from src.params.rule import event_has_permission_node
from src.service import OmegaMatcherInterface as OmMI, enable_processor_state

_ANTI_RECALL_CUSTOM_MODULE_NAME: Literal['Omega.AntiRecall'] = 'Omega.AntiRecall'
"""固定写入数据库的 module name 参数"""
_ANTI_RECALL_CUSTOM_PLUGIN_NAME: Literal['OneBotV11AntiRecall'] = 'OneBotV11AntiRecall'
"""固定写入数据库的 plugin name 参数"""
_ENABLE_ANTI_RECALL_NODE: Literal['enable_anti_recall'] = 'enable_anti_recall'
"""启用反撤回的权限节点"""


async def handle_parse_switch(_: OneBotV11Bot, state: T_State, cmd_arg: Annotated[OneBotV11Message, CommandArg()]):
    """首次运行时解析命令参数"""
    switch = cmd_arg.extract_plain_text().strip().lower()
    if switch in ['on', 'off']:
        state.update({'switch': switch})


@on_command(
    'anti_recall',
    aliases={'AntiRecall', '反撤回'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    handlers=[handle_parse_switch],
    priority=20,
    block=True,
    state=enable_processor_state(name='AntiRecallManager', level=10)
).got('switch', prompt='启用或关闭反撤回:\n【ON/OFF】')
async def handle_set_anti_recall(
        _: OneBotV11GroupMessageEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        switch: Annotated[str, ArgStr('switch')],
) -> None:
    switch = switch.strip().lower()

    try:
        match switch:
            case 'on':
                await interface.entity.set_auth_setting(
                    module=_ANTI_RECALL_CUSTOM_MODULE_NAME,
                    plugin=_ANTI_RECALL_CUSTOM_PLUGIN_NAME,
                    node=_ENABLE_ANTI_RECALL_NODE,
                    available=1
                )
            case 'off':
                await interface.entity.set_auth_setting(
                    module=_ANTI_RECALL_CUSTOM_MODULE_NAME,
                    plugin=_ANTI_RECALL_CUSTOM_PLUGIN_NAME,
                    node=_ENABLE_ANTI_RECALL_NODE,
                    available=0
                )
            case _:
                await interface.send_reply(f'无效输入{switch!r}, 操作已取消')
                return
    except Exception as e:
        logger.error(f'{interface.entity} 设置 AntiRecall 反撤回功能开关为 {switch} 失败, {e!r}')
        await interface.finish_reply('设置 AntiRecall 反撤回功能开关失败, 请稍后再试或联系管理员处理')

    logger.success(f'{interface.entity} 设置 AntiRecall 反撤回功能开关为 {switch} 成功')
    await interface.finish_reply(f'已设置 AntiRecall 反撤回功能开关为 {switch.upper()!r}')


@on_notice(
    rule=event_has_permission_node(
        module=_ANTI_RECALL_CUSTOM_MODULE_NAME,
        plugin=_ANTI_RECALL_CUSTOM_PLUGIN_NAME,
        node=_ENABLE_ANTI_RECALL_NODE
    ),
    priority=92,
    block=False,
    state=enable_processor_state(name='AntiRecall', enable_processor=False, echo_processor_result=False),
).handle()
async def check_recall_notice(bot: OneBotV11Bot, event: OneBotV11GroupRecallNoticeEvent, matcher: Matcher):
    user_id = event.user_id
    # 不响应自己撤回或由自己撤回的消息
    if user_id == event.self_id or event.operator_id == event.self_id:
        return

    message_id = event.message_id

    try:
        message_result = await bot.get_msg(message_id=message_id)
    except Exception as e:
        logger.error(f'AntiRecall 查询历史消息失败, message_id: {message_id}, {e!r}')
        return

    message = parse_obj_as(OneBotV11Message, message_result['message']).include('image', 'text')

    sent_msg = f'已检测到撤回消息:\n{datetime.fromtimestamp(message_result["time"]).strftime("%Y/%m/%d %H:%M:%S")} '
    sent_msg += OneBotV11MessageSegment.at(user_id=user_id)
    sent_msg += '\n----消息内容----\n'
    sent_msg += message

    logger.success(f'AntiRecall 已捕获并处理撤回消息, message_id: {message_id}')
    await matcher.finish(sent_msg)


__all__ = []
