"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : nbnhhsh.py
@Project        : nonebot2_miya
@Description    : 能不能好好说话
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD

from .data_source import get_guess


__plugin_meta__ = PluginMetadata(
    name="好好说话",
    description="【能不能好好说话？】\n"
                "拼音首字母缩写释义",
    usage="/好好说话 [缩写]",
    extra={"author": "Ailitonia"},
)


# 注册事件响应器
nbnhhsh = on_command(
    'nbnhhsh',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='nbnhhsh', level=20),
    aliases={'hhsh', '好好说话', '能不能好好说话'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@nbnhhsh.handle()
async def handle_parse_word(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    word = cmd_arg.extract_plain_text().strip()
    if word:
        state.update({'word': word})


@nbnhhsh.got('word', prompt='有啥缩写搞不懂?')
async def handle_httpcat(word: str = ArgStr('word')):
    word = word.strip()

    guess_result = await get_guess(guess=word)
    if isinstance(guess_result, Exception):
        await nbnhhsh.finish('发生了意外的错误QAQ, 请稍后再试')
    else:
        trans = '\n'.join(guess_result)
        msg = f"为你找到了{word}的以下解释:\n\n{trans}"
        await nbnhhsh.finish(msg)
