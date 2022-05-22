"""
@Author         : Ailitonia
@Date           : 2021/05/30 16:47
@FileName       : http_cat.py
@Project        : nonebot2_miya 
@Description    : Get http cat
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import on_command
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD

from .data_source import get_http_cat


# Custom plugin usage text
__plugin_custom_name__ = 'HttpCat'
__plugin_usage__ = r'''【HttpCat】
用猫猫表示的http状态码

用法:
/HttpCat <code>'''


# 注册事件响应器
httpcat = on_command(
    'HttpCat',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='httpcat', level=20),
    aliases={'httpcat', 'HTTPCAT'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@httpcat.handle()
async def handle_parse_code(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    code = cmd_arg.extract_plain_text().strip()
    if code:
        state.update({'code': code})
    else:
        state.update({'code': '200'})


@httpcat.got('code', prompt='想看哪个猫猫?')
async def handle_httpcat(code: str = ArgStr('code')):
    code = code.strip()
    if not code.isdigit():
        await httpcat.reject('http状态码应该是数字, 请重新输入:')

    code_image = await get_http_cat(http_code=code)
    if isinstance(code_image, Exception):
        await httpcat.finish('^QAQ^')
    else:
        await httpcat.finish(MessageSegment.image(code_image.file_uri))
