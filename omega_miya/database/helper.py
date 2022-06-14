"""
@Author         : Ailitonia
@Date           : 2022/05/20 20:13
@FileName       : helper.py
@Project        : nonebot2_miya
@Description    : database event model helper
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event, MessageEvent, GroupMessageEvent, PrivateMessageEvent

from omega_miya.result import BoolResult
from omega_miya.service.gocqhttp_guild_patch import GuildMessageEvent
from omega_miya.database.internal.entity import (BaseInternalEntity, InternalBotUser, InternalBotGroup,
                                                 InternalGuildChannel, InternalGuildUser)


class EventEntityHelper(object):
    """Event 事件对象工具"""

    def __init__(self, bot: Bot, event: Event):
        self.bot = bot
        self.event = event

    @property
    def self_id(self) -> str:
        return self.bot.self_id

    async def add_only_entity(self, entity: BaseInternalEntity, *, entity_name: str = '') -> BoolResult:
        assert isinstance(self.event, MessageEvent), f'Can not get entity from event({self.event.post_type})'
        _event = self.event

        if isinstance(entity, InternalBotGroup) and isinstance(_event, GroupMessageEvent):
            related_entity_name = ''
        elif isinstance(entity, InternalGuildChannel) and isinstance(_event, GuildMessageEvent):
            related_entity_name = ''
        else:
            entity_name = str(_event.sender.nickname)
            related_entity_name = str(_event.sender.card) if _event.sender.card else str(_event.sender.nickname)

        add_result = await entity.add_only(entity_name=entity_name, related_entity_name=related_entity_name)
        return add_result

    def get_event_entity(self) -> BaseInternalEntity:
        """根据 event 获取不同 entity 对象"""
        _event = self.event
        _self_id = self.self_id

        if isinstance(_event, GroupMessageEvent):
            entity = InternalBotGroup(bot_id=_self_id, parent_id=_self_id, entity_id=str(_event.group_id))
        elif isinstance(_event, GuildMessageEvent):
            entity = InternalGuildChannel(bot_id=_self_id,
                                          parent_id=str(_event.guild_id), entity_id=str(_event.channel_id))
        elif isinstance(_event, PrivateMessageEvent):
            entity = InternalBotUser(bot_id=_self_id, parent_id=_self_id, entity_id=str(_event.user_id))
        elif group_id := getattr(_event, 'group_id', None):
            entity = InternalBotGroup(bot_id=_self_id, parent_id=_self_id, entity_id=str(group_id))
        elif (guild_id := getattr(_event, 'guild_id', None)) and (channel_id := getattr(_event, 'channel_id', None)):
            entity = InternalGuildChannel(bot_id=_self_id, parent_id=str(guild_id), entity_id=str(channel_id))
        elif user_id := getattr(_event, 'user_id', None):
            entity = InternalBotUser(bot_id=_self_id, parent_id=_self_id, entity_id=str(user_id))
        else:
            raise ValueError(f"Can not get entity from event {_event.get_event_description()!r}")
        return entity

    def get_event_user_entity(self) -> BaseInternalEntity:
        """根据 event 获取对应的用户 entity 对象"""
        _event = self.event
        _self_id = self.self_id

        if isinstance(_event, GuildMessageEvent):
            entity = InternalGuildUser(bot_id=_self_id, parent_id=str(_event.guild_id), entity_id=str(_event.user_id))
        elif isinstance(_event, MessageEvent):  # _event type: GroupMessageEvent | PrivateMessageEvent
            entity = InternalBotUser(bot_id=_self_id, parent_id=_self_id, entity_id=str(_event.user_id))
        elif user_id := getattr(_event, 'user_id', None):
            entity = InternalBotUser(bot_id=_self_id, parent_id=_self_id, entity_id=str(user_id))
        else:
            raise ValueError(f"Can not get entity from event {_event.get_event_description()!r}")
        return entity


__all__ = [
    'EventEntityHelper'
]
