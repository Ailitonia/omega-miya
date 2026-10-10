"""
@Author         : Ailitonia
@Date           : 2026/10/7 19:01
@FileName       : handler
@Project        : omega-miya
@Description    : 处理函数中使用的子依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

from nonebot.adapters import Message as BaseMessage
from nonebot.params import Depends
from nonebot.typing import T_State


class StatePlainTextInner:
    """State 中的纯文本值"""

    def __init__(self, key: str):
        self.key = key

    def __call__(self, state: T_State) -> str:
        value = state.get(self.key, None)
        if value is None:
            raise KeyError(f'State has no key: {self.key}')
        elif isinstance(value, str):
            return value
        elif isinstance(value, BaseMessage):
            return value.extract_plain_text()
        else:
            return str(value)


def state_plain_text(key: str) -> Any:
    """子依赖: 获取 State 中的纯文本值"""
    return Depends(StatePlainTextInner(key=key), use_cache=True)


__all__ = [
    'state_plain_text',
]
