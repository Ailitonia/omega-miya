"""
@Author         : Ailitonia
@Date           : 2025/8/8 10:13:02
@FileName       : depends.py
@Project        : omega-miya
@Description    : 通用子依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

from nonebot.adapters import Message as BaseMessage
from nonebot.params import Depends
from nonebot.typing import T_State

from .base import (
    EVENT_ENTITY_INTERFACE,
    EVENT_ENTITY_NAME,
    EVENT_ENTITY_PARAMS,
    EVENT_ENTITY_PROFILE_IMAGE_URL,
    EVENT_MATCHER_INTERFACE,
    EVENT_MSG_IMAGE_URLS,
    EVENT_MSG_MENTIONED_USER_IDS,
    EVENT_REPLY_MSG_IMAGE_URLS,
    EVENT_USER_NICKNAME,
    OPTIONAL_EVENT_REPLY_MESSAGE_ID,
    OPTIONAL_EVENT_REPLY_MSG_PLAIN_TEXT,
    USER_ENTITY_INTERFACE,
    USER_ENTITY_NAME,
    USER_ENTITY_PARAMS,
    USER_ENTITY_PROFILE_IMAGE_URL,
    USER_MATCHER_INTERFACE,
)


class StatePlainTextInner:
    """State 中的纯文本值"""

    def __init__(self, key: Any):
        self.key = key

    def __call__(self, state: T_State) -> str:
        value = state.get(self.key, None)
        if value is None:
            raise KeyError(f'State has not key: {self.key}')
        elif isinstance(value, str):
            return value
        elif isinstance(value, BaseMessage):
            return value.extract_plain_text()
        else:
            return str(value)


def state_plain_text(key: str) -> str:
    """子依赖: 获取 State 中的纯文本值"""
    return Depends(StatePlainTextInner(key=key), use_cache=True)


__all__ = [
    'EVENT_ENTITY_INTERFACE',
    'EVENT_ENTITY_NAME',
    'EVENT_ENTITY_PARAMS',
    'EVENT_ENTITY_PROFILE_IMAGE_URL',
    'EVENT_MSG_MENTIONED_USER_IDS',
    'EVENT_MSG_IMAGE_URLS',
    'EVENT_MATCHER_INTERFACE',
    'EVENT_REPLY_MSG_IMAGE_URLS',
    'EVENT_USER_NICKNAME',
    'OPTIONAL_EVENT_REPLY_MESSAGE_ID',
    'OPTIONAL_EVENT_REPLY_MSG_PLAIN_TEXT',
    'USER_ENTITY_INTERFACE',
    'USER_ENTITY_NAME',
    'USER_ENTITY_PARAMS',
    'USER_ENTITY_PROFILE_IMAGE_URL',
    'USER_MATCHER_INTERFACE',
    'state_plain_text',
]
