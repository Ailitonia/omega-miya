"""
@Author         : Ailitonia
@Date           : 2023/3/18 3:16
@FileName       : model
@Project        : nonebot2_miya
@Description    : Go-cqhttp addition event model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal, override

from nonebot.adapters.onebot.v11.adapter import Adapter
from nonebot.adapters.onebot.v11.event import Event, NoticeEvent
from nonebot.log import logger
from pydantic import BaseModel, ConfigDict


def register_event[Event_T: type[Event]](event: Event_T) -> Event_T:
    Adapter.add_custom_model(event)
    logger.opt(colors=True).trace(
        f'Custom event <e>{event.__qualname__!r}</e> registered to adapter <e>{Adapter.get_name()!r}</e> '
        f'from module <g>{event.__module__!r}</g>'
    )
    return event


@register_event
class GroupCardNoticeEvent(NoticeEvent):
    """群成员名片更新提醒事件(此事件不保证时效性, 仅在收到消息时校验卡片)"""

    notice_type: Literal['group_card']
    group_id: int
    user_id: int
    card_new: str
    card_old: str

    @override
    def is_tome(self) -> bool:
        return self.user_id == self.self_id

    @override
    def get_user_id(self) -> str:
        return str(self.user_id)

    @override
    def get_session_id(self) -> str:
        return f'group_{self.group_id}_{self.user_id}'


class OfflineFile(BaseModel):
    name: str
    size: int
    url: str

    model_config = ConfigDict(extra='allow')


@register_event
class OfflineFileNoticeEvent(NoticeEvent):
    """接收到离线文件提醒事件"""

    notice_type: Literal['offline_file']
    user_id: int
    file: OfflineFile

    @override
    def is_tome(self) -> bool:
        return True

    @override
    def get_user_id(self) -> str:
        return str(self.user_id)

    @override
    def get_session_id(self) -> str:
        return f'{self.user_id}_{self.file.name}'


class Device(BaseModel):
    """在线客户端

    - app_id: 客户端ID
    - device_name: 设备名称
    - device_kind: 设备类型
    """
    app_id: int
    device_name: str
    device_kind: str

    model_config = ConfigDict(extra='allow')


@register_event
class ClientStatusNoticeEvent(NoticeEvent):
    """其他客户端在线状态变更"""

    notice_type: Literal['client_status']
    client: Device
    online: bool

    @override
    def is_tome(self) -> bool:
        return True

    @override
    def get_user_id(self) -> str:
        return str(self.self_id)

    @override
    def get_session_id(self) -> str:
        return f'{self.self_id}_{self.client.app_id}'


@register_event
class EssenceNoticeEvent(NoticeEvent):
    """精华消息变更"""

    notice_type: Literal['essence']
    sub_type: Literal['add', 'delete']
    group_id: int
    sender_id: int
    operator_id: int
    message_id: int

    @override
    def is_tome(self) -> bool:
        return self.self_id == self.sender_id or self.self_id == self.operator_id

    @override
    def get_user_id(self) -> str:
        return str(self.sender_id)

    @override
    def get_session_id(self) -> str:
        return f'group_{self.group_id}_{self.sender_id}'


__all__ = [
    'GroupCardNoticeEvent',
    'OfflineFileNoticeEvent',
    'ClientStatusNoticeEvent',
    'EssenceNoticeEvent',
]
