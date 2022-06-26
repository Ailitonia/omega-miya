"""
@Author         : Ailitonia
@Date           : 2021/12/24 22:43
@FileName       : miya_button.py
@Project        : nonebot2_miya
@Description    : 猫按钮
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from nonebot import on_command, on_regex, logger
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.params import CommandArg, ArgStr, EventMessage

from omega_miya.service import init_processor_state

from .resources import (Voice, get_voice_resource, get_available_voice_resource,
                        get_voice_resource_name, set_voice_resource)


# Custom plugin usage text
__plugin_custom_name__ = '猫按钮'
__plugin_usage__ = r'''【猫按钮】
发出可爱的猫叫

用法:
@bot 喵一个'''


button_pattern = r'^(.*?)喵一个$'
miya_button = on_regex(
    button_pattern,
    rule=to_me(),
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='miya_button', level=10, echo_processor_result=False),
    permission=GROUP,
    priority=50,
    block=False
)


@miya_button.handle()
async def handle_miya_button(bot: Bot, event: GroupMessageEvent, matcher: Matcher, message: Message = EventMessage()):
    message = message.extract_plain_text().strip()
    search_result = re.search(button_pattern, message)
    keyword = search_result.group(1)
    keyword = keyword if keyword else None
    resource_name = await get_voice_resource_name(bot=bot, event=event, matcher=matcher)
    voice_resource = get_voice_resource(resource_name=resource_name)
    voice_file = voice_resource.get_random_voice(keyword=keyword)
    voice_msg = MessageSegment.record(file=voice_file.file_uri)
    await matcher.finish(voice_msg)


set_resource = on_command(
    'SetButtonVoiceResource',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='SetButtonVoiceResource',
        level=10,
        auth_node='set_button_voice_resource'
    ),
    aliases={'设置猫按钮语音'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=20,
    block=True
)


@set_resource.handle()
async def handle_parse_resource_name(state: T_State, matcher: Matcher, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    resource_name = cmd_arg.extract_plain_text().strip()
    if resource_name:
        state.update({'resource_name': resource_name})
    else:
        resource_msg = '\n'.join(get_available_voice_resource())
        await matcher.send(f'当前可用的猫按钮语音有:\n\n{resource_msg}')


@set_resource.got('resource_name', prompt='请输入想要配置的猫按钮语音名称:')
async def handle_delete_user_sub(bot: Bot, event: GroupMessageEvent, matcher: Matcher,
                                 resource_name: str = ArgStr('resource_name')):
    resource_name = resource_name.strip()
    if resource_name not in get_available_voice_resource():
        await matcher.reject(f'{resource_name}不是可用的猫按钮语音, 重新输入:')

    setting_result = await set_voice_resource(resource_name=resource_name, bot=bot, event=event, matcher=matcher)
    if isinstance(setting_result, Exception):
        logger.error(f"SetButtonVoiceResource | 配置猫按钮语音失败, {setting_result}")
        await matcher.finish(f'设置猫按钮语音失败了QAQ, 请稍后重试或联系管理员处理')
    else:
        logger.success(f"SetButtonVoiceResource | 配置猫按钮语音成功")
        await matcher.finish(f'已将猫按钮语音设置为: {resource_name}')
