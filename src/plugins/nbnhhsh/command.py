"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : command.py
@Project        : nonebot2_miya
@Description    : 能不能好好说话
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr
from nonebot.plugin import on_command

from src.params.depends import EVENT_MATCHER_INTERFACE
from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import enable_processor_state
from .config import nbnhhsh_plugin_config
from .data_source import ai_guess, simple_guess


@on_command(
    'nbnhhsh',
    aliases={'hhsh', 'zssm', '好好说话', '能不能好好说话', '这是什么'},
    handlers=[get_command_str_single_arg_parser_handler('guess_word', ensure_key=True)],
    priority=10,
    block=True,
    state=enable_processor_state(name='nbnhhsh', level=30, cooldown=30),
).got('guess_word')
async def handle_guess(
        interface: EVENT_MATCHER_INTERFACE,
        guess_word: Annotated[str | None, ArgStr('guess_word')],
) -> None:
    msg_images = interface.get_event_reply_msg_image_urls() + interface.get_event_msg_image_urls()
    reply_message = interface.get_event_reply_msg_plain_text()

    if not guess_word and not reply_message and not msg_images:
        await interface.reject_arg_reply('guess_word', '有啥搞不懂? 发来帮你看看')

    guess_word = '' if guess_word is None else guess_word.strip()
    reply_message = '' if reply_message is None else reply_message.strip()
    query_message = f'{reply_message}\n{guess_word}'.strip()

    try:
        if nbnhhsh_plugin_config.nbnhhsh_plugin_enable_ai_description:
            await interface.send_reply('正在尝试解析知识概念, 请稍候')
            result_msg = await ai_guess(query_message=query_message, msg_images=msg_images)
        else:
            result_msg = await simple_guess(query_message=query_message)
        await interface.send_reply(result_msg)
    except Exception as e:
        logger.error(f'nbnhhsh | 获取{query_message!r}查询结果失败, {e}')
        await interface.send_reply('发生了意外的错误, 请稍后再试')


__all__ = []
