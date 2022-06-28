"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : omega_anti_flash.py
@Project        : nonebot2_miya
@Description    : Omega 反闪照插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal
from nonebot.log import logger
from nonebot.plugin import on_command, on_message, PluginMetadata
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, GROUP_ADMIN, GROUP_OWNER
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import InternalBotGroup
from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.rule import group_has_permission_node


__plugin_meta__ = PluginMetadata(
    name="反闪照",
    description="【AntiFlash 反闪照插件】\n"
                "检测闪照并提取原图",
    usage="仅限群聊中群管理员使用:\n"
          "/AntiFlash <ON|OFF>",
    extra={"author": "Ailitonia"},
)


_ANTI_FLASH_CUSTOM_MODULE_NAME: Literal['Omega.AntiFlash'] = 'Omega.AntiFlash'
"""固定写入数据库的 module name 参数"""
_ANTI_FLASH_CUSTOM_PLUGIN_NAME: Literal['omega_anti_flash'] = 'omega_anti_flash'
"""固定写入数据库的 plugin name 参数"""
_ENABLE_ANTI_FLASH_NODE: Literal['enable_anti_flash'] = 'enable_anti_flash'
"""启用反闪照的权限节点"""


# 注册事件响应器
AntiFlashManager = on_command(
    'AntiFlash',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='AntiFlashManager', level=10, auth_node='anti_flash_manager'),
    aliases={'antiflash', '反闪照'},
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True
)


@AntiFlashManager.handle()
async def handle_parse_switch(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    switch = cmd_arg.extract_plain_text().strip().lower()
    if switch in ('on', 'off'):
        state.update({'switch': switch})


@AntiFlashManager.got('switch', prompt='启用或关闭反闪照:\n【ON/OFF】')
async def handle_switch(bot: Bot, matcher: Matcher, event: GroupMessageEvent, switch: str = ArgStr('switch')):
    switch = switch.strip().lower()
    group_id = str(event.group_id)
    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=group_id)

    match switch:
        case 'on':
            switch_result = await run_async_catching_exception(group.set_auth_setting)(
                module=_ANTI_FLASH_CUSTOM_MODULE_NAME, plugin=_ANTI_FLASH_CUSTOM_PLUGIN_NAME,
                node=_ENABLE_ANTI_FLASH_NODE, available=1
            )
        case 'off':
            switch_result = await run_async_catching_exception(group.set_auth_setting)(
                module=_ANTI_FLASH_CUSTOM_MODULE_NAME, plugin=_ANTI_FLASH_CUSTOM_PLUGIN_NAME,
                node=_ENABLE_ANTI_FLASH_NODE, available=0
            )
        case _:
            await matcher.reject('没有这个选项哦, 选择【ON/OFF】以启用或关闭反闪照:')
            return

    if isinstance(switch_result, Exception) or switch_result.error:
        logger.error(f"Group({group_id}) 设置 AntiFlash 反闪照功能开关为 {switch} 失败, {switch_result}")
        await matcher.finish(f'设置 AntiFlash 反闪照功能开关失败QAQ, 请联系管理员处理')
    else:
        logger.success(f"Group({group_id}) 设置 AntiFlash 反闪照功能开关为 {switch} 成功")
        await matcher.finish(f'已设置 AntiFlash 反闪照功能开关为 {switch}!')


AntiFlash = on_message(
    rule=group_has_permission_node(
        module=_ANTI_FLASH_CUSTOM_MODULE_NAME,
        plugin=_ANTI_FLASH_CUSTOM_PLUGIN_NAME,
        node=_ENABLE_ANTI_FLASH_NODE
    ),
    state=init_processor_state(name='AntiFlash', enable_processor=False, echo_processor_result=False),
    permission=GROUP,
    priority=100,
    block=False
)


@AntiFlash.handle()
async def check_flash_img(event: GroupMessageEvent):
    # 不响应自身发送的消息
    if event.sender.user_id == event.self_id:
        return

    for msg_seg in event.message:
        if msg_seg.type == 'image':
            if msg_seg.data.get('type') == 'flash':
                if msg_seg.data.get('url', None):
                    img_file = msg_seg.data.get('url')
                else:
                    img_file = msg_seg.data.get('file')
                img_seq = MessageSegment.image(file=img_file)
                logger.success(f'AntiFlash 反闪照已捕获并处理闪照, 闪照文件: {img_file}')
                await AntiFlash.send('已检测到闪照:\n' + img_seq)
