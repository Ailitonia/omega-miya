"""
@Author         : Ailitonia
@Date           : 2025/8/12 09:44:58
@FileName       : interface.py
@Project        : omega-miya
@Description    : Omega 中间件接口子依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.params import Depends

from src.database import DATABASE_SESSION
from ..internal import OmegaEntity
from ..middlewares.interface import OmegaEntityInterface as OmEI
from ..middlewares.interface import OmegaMatcherInterface as OmMI
from ..middlewares.models import EntityInitParams

type EVENT_MATCHER_INTERFACE = Annotated[OmMI, Depends(OmMI.depend(acquire_type='event'))]
"""子依赖: 事件对象的 OmegaMatcherInterface"""

type USER_MATCHER_INTERFACE = Annotated[OmMI, Depends(OmMI.depend(acquire_type='user'))]
"""子依赖: 用户对象的 OmegaMatcherInterface"""


def _extract_event_entity_params(bot: BaseBot, event: BaseEvent) -> EntityInitParams:
    """提取事件本身对应 Entity 实例化参数"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).extract_entity_params('event')


type EVENT_ENTITY_PARAMS = Annotated[EntityInitParams, Depends(_extract_event_entity_params, use_cache=True)]
"""子依赖: 事件本身对应 Entity 实例化参数"""


def _extract_user_entity_params(bot: BaseBot, event: BaseEvent) -> EntityInitParams:
    """提取触发事件用户 Entity 实例化参数"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).extract_entity_params('user')


type USER_ENTITY_PARAMS = Annotated[EntityInitParams, Depends(_extract_user_entity_params, use_cache=True)]
"""子依赖: 触发事件用户 Entity 实例化参数"""


async def _get_event_internal_entity_instance(
        event_entity_params: EVENT_ENTITY_PARAMS,
        session: DATABASE_SESSION,
) -> AsyncGenerator[OmegaEntity, None]:
    """获取事件对象的 InternalEntity 实例"""
    async with OmegaEntity(session=session, **event_entity_params.kwargs) as entity:
        yield entity


type EVENT_INTERNAL_ENTITY = Annotated[OmegaEntity, Depends(_get_event_internal_entity_instance)]
"""子依赖: 事件对象的 InternalEntity 实例"""


async def _get_user_internal_entity_instance(
        user_entity_params: USER_ENTITY_PARAMS,
        session: DATABASE_SESSION,
) -> AsyncGenerator[OmegaEntity, None]:
    """获取事件对象的 InternalEntity 实例"""
    async with OmegaEntity(session=session, **user_entity_params.kwargs) as entity:
        yield entity


type USER_INTERNAL_ENTITY = Annotated[OmegaEntity, Depends(_get_user_internal_entity_instance)]
"""子依赖: 用户对象的 InternalEntity 实例"""


async def _event_entity_interface_depend(entity: EVENT_INTERNAL_ENTITY) -> AsyncGenerator[OmEI, None]:
    """获取事件对象的 OmegaEntityInterface"""
    async with OmEI(entity=entity) as interface:
        yield interface


type EVENT_ENTITY_INTERFACE = Annotated[OmEI, Depends(_event_entity_interface_depend)]
"""子依赖: 事件对象的 OmegaEntityInterface"""


async def _user_entity_interface_depend(entity: USER_INTERNAL_ENTITY) -> AsyncGenerator[OmEI, None]:
    """获取用户对象的 OmegaEntityInterface"""
    async with OmEI(entity=entity) as interface:
        yield interface


type USER_ENTITY_INTERFACE = Annotated[OmEI, Depends(_user_entity_interface_depend)]
"""子依赖: 用户对象的 OmegaEntityInterface"""


async def _get_event_entity_name(entity_interface: EVENT_ENTITY_INTERFACE) -> str:
    """获取事件对象的名称/昵称"""
    return await entity_interface.get_entity_name()


type EVENT_ENTITY_NAME = Annotated[str, Depends(_get_event_entity_name, use_cache=True)]
"""子依赖: 事件对象的名称/昵称"""


async def _get_user_entity_name(entity_interface: USER_ENTITY_INTERFACE) -> str:
    """获取用户对象的名称/昵称"""
    return await entity_interface.get_entity_name()


type USER_ENTITY_NAME = Annotated[str, Depends(_get_user_entity_name, use_cache=True)]
"""子依赖: 用户对象的名称/昵称"""


async def _get_event_entity_profile_image_url(entity_interface: EVENT_ENTITY_INTERFACE) -> str:
    """获取事件对象头像/图标"""
    return await entity_interface.get_entity_profile_image_url()


type EVENT_ENTITY_PROFILE_IMAGE_URL = Annotated[str, Depends(_get_event_entity_profile_image_url, use_cache=True)]
"""子依赖: 事件对象头像/图标"""


async def _get_user_entity_profile_image_url(entity_interface: USER_ENTITY_INTERFACE) -> str:
    """获取用户对象头像/图标"""
    return await entity_interface.get_entity_profile_image_url()


type USER_ENTITY_PROFILE_IMAGE_URL = Annotated[str, Depends(_get_user_entity_profile_image_url, use_cache=True)]
"""子依赖: 用户对象头像/图标"""


def _event_user_nickname(bot: BaseBot, event: BaseEvent) -> str:
    """获取当前事件用户昵称"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).get_user_nickname()


type EVENT_USER_NICKNAME = Annotated[str, Depends(_event_user_nickname, use_cache=True)]
"""子依赖: 获取当前事件用户昵称"""


def _event_msg_mentioned_user_ids(bot: BaseBot, event: BaseEvent) -> list[str]:
    """获取当前事件消息中被 @ 所有用户对象 ID 列表"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).get_msg_mentioned_user_ids()


type EVENT_MSG_MENTIONED_USER_IDS = Annotated[list[str], Depends(_event_msg_mentioned_user_ids, use_cache=True)]
"""子依赖: 获取当前事件消息中被 @ 所有用户对象 ID 列表"""


def _event_msg_image_urls(bot: BaseBot, event: BaseEvent) -> list[str]:
    """获取当前事件消息中的全部图片链接"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).get_msg_image_urls()


type EVENT_MSG_IMAGE_URLS = Annotated[list[str], Depends(_event_msg_image_urls, use_cache=True)]
"""子依赖: 获取当前事件消息中的全部图片链接"""


def _event_reply_message_id(bot: BaseBot, event: BaseEvent) -> str | None:
    """获取事件回复或引用消息 ID"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).get_reply_msg_id()


type OPTIONAL_EVENT_REPLY_MESSAGE_ID = Annotated[str | None, Depends(_event_reply_message_id, use_cache=True)]
"""子依赖: 获取事件回复或引用消息 ID"""


def _event_reply_msg_image_urls(bot: BaseBot, event: BaseEvent) -> list[str]:
    """获取当前事件回复消息中的全部图片链接"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).get_reply_msg_image_urls()


type EVENT_REPLY_MSG_IMAGE_URLS = Annotated[list[str], Depends(_event_reply_msg_image_urls, use_cache=True)]
"""子依赖: 获取当前事件回复消息中的全部图片链接"""


def _event_reply_msg_plain_text(bot: BaseBot, event: BaseEvent) -> str | None:
    """获取当前事件回复消息的文本"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).get_reply_msg_plain_text()


type OPTIONAL_EVENT_REPLY_MSG_PLAIN_TEXT = Annotated[str | None, Depends(_event_reply_msg_plain_text, use_cache=True)]
"""子依赖: 获取当前事件回复消息的文本"""

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
]
