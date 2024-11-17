"""
@Author         : Ailitonia
@Date           : 2022/06/04 16:19
@FileName       : params.py
@Project        : nonebot2_miya 
@Description    : Omega 插件所使用的依赖注入的各类参数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any

from nonebot.internal.adapter.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot.typing import T_State


class StatePlainTextInner:
    """State 中的纯文本值"""

    def __init__(self, key: Any):
        self.key = key

    def __call__(self, matcher: Matcher, state: T_State) -> str:
        value = state.get(self.key, None)
        if value is None:
            raise KeyError(f'State has not key: {self.key}')
        elif isinstance(value, str):
            return value
        elif isinstance(value, Message):
            return value.extract_plain_text()
        else:
            return str(value)


def state_plain_text(key: str) -> str:
    """依赖: 获取 State 中的纯文本值"""
    return Depends(StatePlainTextInner(key=key))


__all__ = [
    'state_plain_text'
]
