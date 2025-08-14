"""
@Author         : Ailitonia
@Date           : 2025/8/12 09:44:06
@FileName       : depends.py
@Project        : omega-miya
@Description    : Omega 内置子依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .interface import (
    EVENT_ENTITY_INTERFACE,
    EVENT_ENTITY_NAME,
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
    USER_ENTITY_PROFILE_IMAGE_URL,
    USER_MATCHER_INTERFACE,
    get_entity_interface,
    get_entity_interface_from_index,
)
from .internal import (
    EVENT_ENTITY_PARAMS,
    EVENT_INTERNAL_ENTITY,
    USER_ENTITY_PARAMS,
    USER_INTERNAL_ENTITY,
    extract_entity_params,
    get_entity_session,
    get_entity_session_from_index,
)

__all__ = [
    'EVENT_ENTITY_INTERFACE',
    'EVENT_ENTITY_NAME',
    'EVENT_ENTITY_PARAMS',
    'EVENT_ENTITY_PROFILE_IMAGE_URL',
    'EVENT_INTERNAL_ENTITY',
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
    'USER_INTERNAL_ENTITY',
    'USER_MATCHER_INTERFACE',
    'extract_entity_params',
    'get_entity_interface',
    'get_entity_interface_from_index',
    'get_entity_session',
    'get_entity_session_from_index',
]
