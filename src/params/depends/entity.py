"""
@Author         : Ailitonia
@Date           : 2026/10/7 18:12
@FileName       : entity
@Project        : omega-miya
@Description    : 内置实体对象子依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.params import Depends

from src.service import OmegaEntityInterface, OmegaMatcherInterface

type EVENT_M_IFACE = Annotated[
    OmegaMatcherInterface,
    Depends(OmegaMatcherInterface.depend(acquire_type='event'), use_cache=True)
]
"""子依赖: 事件对象的 OmegaMatcherInterface"""
type USER_M_IFACE = Annotated[
    OmegaMatcherInterface,
    Depends(OmegaMatcherInterface.depend(acquire_type='user'), use_cache=True)
]
"""子依赖: 用户对象的 OmegaMatcherInterface"""


def _event_entity_interface(m_iface: EVENT_M_IFACE) -> OmegaEntityInterface:
    return m_iface.get_current_entity_interface()


def _user_entity_interface(m_iface: USER_M_IFACE) -> OmegaEntityInterface:
    return m_iface.get_current_entity_interface()


type EVENT_E_IFACE = Annotated[
    OmegaEntityInterface,
    Depends(_event_entity_interface)
]
"""子依赖: 事件对象的 OmegaEntityInterface"""
type USER_E_IFACE = Annotated[
    OmegaEntityInterface,
    Depends(_user_entity_interface)
]
"""子依赖: 用户对象的 OmegaEntityInterface"""


async def _get_event_entity_profile_image_url(e_iface: EVENT_E_IFACE) -> str:
    """获取事件对象头像/图标"""
    return await e_iface.get_entity_profile_image_url()


async def _get_user_entity_profile_image_url(e_iface: USER_E_IFACE) -> str:
    """获取用户对象头像/图标"""
    return await e_iface.get_entity_profile_image_url()


type EVENT_ENTITY_PROFILE_IMAGE_URL = Annotated[str, Depends(_get_event_entity_profile_image_url, use_cache=True)]
"""子依赖: 事件对象头像/图标"""
type USER_ENTITY_PROFILE_IMAGE_URL = Annotated[str, Depends(_get_user_entity_profile_image_url, use_cache=True)]
"""子依赖: 用户对象头像/图标"""

__all__ = [
    'EVENT_E_IFACE',
    'EVENT_ENTITY_PROFILE_IMAGE_URL',
    'EVENT_M_IFACE',
    'USER_E_IFACE',
    'USER_ENTITY_PROFILE_IMAGE_URL',
    'USER_M_IFACE',
]
