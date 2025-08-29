"""
@Author         : Ailitonia
@Date           : 2025/8/28 16:10:20
@FileName       : command.py
@Project        : omega-miya
@Description    : 模仿写作
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr
from nonebot.plugin import on_command
from nonebot.typing import T_State

from src.params.depends import EVENT_MATCHER_INTERFACE
from src.params.handler import get_command_str_multi_args_parser_handler
from src.service import enable_processor_state
from src.utils.openai_api.scenario_app import CustomImitatingWritingApp, TemplateImitatingWritingAppGenerator
from .config import imitating_writing_plugin_config

_APP_MAP: dict[str, str] = {
    '编程哲学': 'programming_philosophy.md',
    '四大名著': 'the_four_great_classical_novels.md',
    '你说得对': 'you_are_right_but.md',
}
"""内置模仿写作应用名称与模板文件名映射"""


imitating_writing = on_command(
    'imitating-writing',
    aliases={'模仿写作', '小作文'},
    handlers=[
        get_command_str_multi_args_parser_handler('writing_arg', ensure_keys_num=2)
    ],
    priority=10,
    block=True,
    state=enable_processor_state(name='ImitatingWriting', level=30, cooldown=60),
)


@imitating_writing.got('writing_arg_0', prompt='请输入你想要模仿写作的内容模板:')
@imitating_writing.got('writing_arg_1', prompt='请输入你想要模仿写作的关键词:')
async def handle_imitating_writing(
        interface: EVENT_MATCHER_INTERFACE,
        template: Annotated[str | None, ArgStr('writing_arg_0')],
        keyword: Annotated[str | None, ArgStr('writing_arg_1')],
        state: T_State,
) -> None:
    reply_message = interface.get_event_reply_msg_plain_text()
    template = template or reply_message or state.get('writing_arg_0', None)
    state['writing_arg_0'] = template

    if template is None:
        await interface.reject_arg_reply('writing_arg_0', '请输入你想要模仿写作的内容模板:')

    template = template.strip()
    if len(template) < 14 and template not in _APP_MAP:
        template_name_text = f'{template!r}不是可用的内置模板, 当前可用模板有:\n\n{"\n".join(x for x in _APP_MAP.keys())}'
        await interface.reject_arg_reply('writing_arg_0', f'{template_name_text}\n\n请输入你想要使用的模板:')

    if keyword is None:
        await interface.reject_arg_reply('writing_arg_1', '请输入你想要模仿写作的关键词:')
    else:
        keyword = keyword.strip()

    await interface.send_reply('创作中, 请稍候')

    try:
        if template in _APP_MAP:
            app_type = TemplateImitatingWritingAppGenerator.generate_internal_imitating_writing_app(
                template_file_name=_APP_MAP[template]
            )
            result = await app_type(
                service_name=imitating_writing_plugin_config.imitating_writing_plugin_ai_service_name,
                model_name=imitating_writing_plugin_config.imitating_writing_plugin_ai_model_name,
            ).write(
                text=keyword,
                temperature=imitating_writing_plugin_config.imitating_writing_plugin_ai_temperature,
                max_tokens=imitating_writing_plugin_config.imitating_writing_plugin_ai_max_tokens,
            )
        else:
            result = await CustomImitatingWritingApp(
                service_name=imitating_writing_plugin_config.imitating_writing_plugin_ai_service_name,
                model_name=imitating_writing_plugin_config.imitating_writing_plugin_ai_model_name,
            ).custom_write(
                template=template,
                keyword=keyword,
                temperature=imitating_writing_plugin_config.imitating_writing_plugin_ai_temperature,
                max_tokens=imitating_writing_plugin_config.imitating_writing_plugin_ai_max_tokens,
            )
        await interface.send_reply(result.strip().removeprefix('```').removesuffix('```').strip())
    except Exception as e:
        logger.error(f'ImitatingWriting | 写作失败, {e}')
        await interface.send_reply('模仿写作失败了QAQ, 发生了意外的错误, 请稍后再试')


__all__ = []
