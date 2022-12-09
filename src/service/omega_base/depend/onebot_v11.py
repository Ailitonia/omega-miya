"""
@Author         : Ailitonia
@Date           : 2022/12/08 21:54
@FileName       : onebot_v11.py
@Project        : nonebot2_miya 
@Description    : Onebot v11 support
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from nonebot.params import Depends
from nonebot.adapters.onebot.v11 import Event, MessageEvent, GroupMessageEvent, PrivateMessageEvent
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.utils import get_db_session
from src.service.gocqhttp_guild_patch import GuildMessageEvent

from ..internal.entity import InternalEntity


class EntityDepend(object):
    """Onebot V11 事件对应的 Entity 依赖类"""

    def __init__(self, acquire_type: Literal['event', 'user']):
        self.acquire_type = acquire_type

    def __call__(self, event: Event, session: AsyncSession = Depends(get_db_session)) -> InternalEntity:
        match self.acquire_type:
            case 'event':
                return InternalEntity(session=session, **self.generate_event_entity_params_from_event(event=event))
            case 'user':
                return InternalEntity(session=session, **self.generate_user_entity_params_from_event(event=event))
            case _:
                raise ValueError(f'illegal acquire_type: "{self.acquire_type}"')

    @staticmethod
    def generate_event_entity_params_from_event(event: Event) -> dict:
        """根据 Event 生成对应 Entity 的构造参数"""
        params = {'bot_id': str(event.self_id), 'parent_id': str(event.self_id)}

        if isinstance(event, GroupMessageEvent):
            params.update({'entity_id': str(event.group_id), 'entity_type': 'qq_group'})
        elif isinstance(event, GuildMessageEvent):
            params.update({'entity_id': str(event.channel_id), 'entity_type': 'qq_guild_channel',
                           'parent_id': str(event.guild_id)})
        elif isinstance(event, PrivateMessageEvent):
            params.update({'entity_id': str(event.user_id), 'entity_type': 'qq_user'})
        elif group_id := getattr(event, 'group_id', None):
            params.update({'entity_id': str(group_id), 'entity_type': 'qq_group'})
        elif (guild_id := getattr(event, 'guild_id', None)) and (channel_id := getattr(event, 'channel_id', None)):
            params.update({'entity_id': str(channel_id), 'entity_type': 'qq_guild_channel', 'parent_id': str(guild_id)})
        elif user_id := getattr(event, 'user_id', None):
            params.update({'entity_id': str(user_id), 'entity_type': 'qq_user'})
        else:
            params.update({'entity_id': str(event.self_id), 'entity_type': 'qq_user'})

        return params

    @staticmethod
    def generate_user_entity_params_from_event(event: Event) -> dict:
        """根据 Event 生成对应 Entity 的构造参数"""
        params = {'bot_id': str(event.self_id), 'parent_id': str(event.self_id)}

        if isinstance(event, GuildMessageEvent):
            params.update({'entity_id': str(event.user_id), 'entity_type': 'qq_guild_user',
                           'parent_id': str(event.guild_id)})
        elif isinstance(event, MessageEvent):  # event type: GroupMessageEvent | PrivateMessageEvent
            params.update({'entity_id': str(event.user_id), 'entity_type': 'qq_user'})
        elif user_id := getattr(event, 'user_id', None):
            params.update({'entity_id': str(user_id), 'entity_type': 'qq_user'})
        else:
            params.update({'entity_id': str(event.self_id), 'entity_type': 'qq_user'})

        return params


__all__ = [
    'EntityDepend'
]
