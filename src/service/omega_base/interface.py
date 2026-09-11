"""
@Author         : Ailitonia
@Date           : 2024/3/24 4:12
@FileName       : interface
@Project        : nonebot2_miya
@Description    : Omega 平台中间件统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator, Callable, Sequence
from contextlib import asynccontextmanager
from typing import NoReturn, Self

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import FinishedException, PausedException, RejectedException
from nonebot.matcher import Matcher
from nonebot_plugin_alconna.uniseg import Receipt, Segment, UniMessage

from src.database import DATABASE_SESSION, database_session
from src.database.internal.entity import EntityType
from .internal import (
    ENTITY_TARGET_REGISTER,
    EVENT_DEPEND_REGISTER,
    BaseEntityTarget,
    BaseEventDepend,
    EntityAcquireType,
    EntityInitParams,
    OmegaEntity,
)


class OmegaEntityInterface:
    """Omega 基于对象 (Entity) 的统一接口, 用于在 Event/Matcher 之外调用平台 Bot 相关方法"""

    __slots__ = ('entity_params',)

    def __init__(self, entity_params: 'EntityInitParams') -> None:
        self.entity_params = entity_params

    @property
    def type(self) -> 'EntityType':
        return self.entity_params.entity_type

    def get_entity_target(self) -> 'BaseEntityTarget':
        """获取 Entity 的中间件平台 API 适配器"""
        entity_target_cls = ENTITY_TARGET_REGISTER.get_target(target_name=self.type)
        return entity_target_cls(entity_params=self.entity_params)

    def get_bot(self) -> 'BaseBot':
        """获取 Entity 对应的 Bot 实例, 对应 self_id 的 Bot 不在线时抛出 KeyError"""
        return self.get_entity_target().get_bot()

    # ------------------------------------------------------------------ #
    # 发送消息相关方法, 在 Event/Matcher 之外向目标 Entity 直接发送消息
    # ------------------------------------------------------------------ #

    async def send_entity_message(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
            *,
            at_sender: bool = False,
            reply_to: bool = False,
            **kwargs,
    ) -> 'Receipt':
        """向 Entity 直接发送消息"""
        return await self.get_entity_target().send_message(
            message=message,
            at_sender=at_sender,
            reply_to=reply_to,
            **kwargs,
        )

    async def send_entity_message_auto_revoke(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
            revoke_delay: int = 60,
            *,
            at_sender: bool = False,
            reply_to: bool = False,
            **kwargs,
    ) -> None:
        """向 Entity 直接发送消息并在一定时间后撤回"""
        return await self.get_entity_target().send_message_auto_revoke(
            message=message,
            revoke_delay=revoke_delay,
            at_sender=at_sender,
            reply_to=reply_to,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    # 对象通用方法
    # ------------------------------------------------------------------ #

    async def get_entity_name(self) -> str:
        """获取对象名称/昵称"""
        return await self.get_entity_target().call_api_get_entity_name()

    async def get_entity_profile_image_url(self) -> str:
        """获取对象头像/图标

        目标对象没有头像/图标时可能抛出 ValueError
        """
        return await self.get_entity_target().call_api_get_entity_profile_image_url()


class OmegaMatcherInterface:
    """Omega 基于事件 (Event) 的统一接口, 用于在 Event/Matcher 中调用平台 Bot 相关方法和进行流程交互"""

    __slots__ = ('bot', 'event', 'matcher', 'acquire_type',)

    def __init__(
            self,
            bot: BaseBot,
            event: BaseEvent,
            matcher: Matcher,
            acquire_type: EntityAcquireType = 'event',
    ) -> None:
        self.bot = bot
        self.event = event
        self.matcher = matcher
        self.acquire_type: EntityAcquireType = acquire_type

    @classmethod
    def depend(
            cls,
            acquire_type: EntityAcquireType = 'event',
    ) -> Callable[[BaseBot, BaseEvent, Matcher], Self]:
        """获取注入依赖, 用于 Event/Matcher 中初始化"""

        def _depend(bot: BaseBot, event: BaseEvent, matcher: Matcher) -> Self:
            return cls(bot=bot, event=event, matcher=matcher, acquire_type=acquire_type)

        return _depend

    # ------------------------------------------------------------------ #
    # 平台事件及对象接口及导出方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_event_depend_cls(target_event: 'BaseEvent') -> type['BaseEventDepend']:
        """获取事件对应的对象解析器"""
        return EVENT_DEPEND_REGISTER.get_depend(target_event=target_event)

    @classmethod
    def get_target_entity(
            cls,
            bot: 'BaseBot',
            event: 'BaseEvent',
            db_session: DATABASE_SESSION,
            *,
            acquire_type: EntityAcquireType = 'event',
    ) -> OmegaEntity:
        """使用已有数据库会话创建对应事件的 OmegaEntity 实例"""
        event_depend_cls = cls.get_event_depend_cls(target_event=event)
        event_depend = event_depend_cls(bot=bot, event=event)
        entity_params = event_depend.extract_entity_params(acquire_type=acquire_type)
        return OmegaEntity(session=db_session, **entity_params.model_dump())

    def get_event_depend(self) -> 'BaseEventDepend':
        """获取的中间件平台事件对象解析器"""
        event_depend_cls = self.get_event_depend_cls(target_event=self.event)
        return event_depend_cls(bot=self.bot, event=self.event)

    def extract_current_entity_params(self) -> 'EntityInitParams':
        """提取当前事件对应 Entity 实例化参数, 提取对象由 acquire_type 决定 (默认 event 即事件所在场景对象)"""
        return self.get_event_depend().extract_entity_params(acquire_type=self.acquire_type)

    def get_current_entity_interface(self) -> 'OmegaEntityInterface':
        """获取对应的 OmegaEntityInterface 实例"""
        entity_params = self.extract_current_entity_params()
        return OmegaEntityInterface(entity_params=entity_params)

    def get_current_entity(self, db_session: DATABASE_SESSION) -> OmegaEntity:
        """使用已有数据库会话创建 OmegaEntity 实例"""
        return OmegaEntity(session=db_session, **self.extract_current_entity_params().model_dump())

    @asynccontextmanager
    async def create_current_entity_session(self) -> AsyncGenerator[OmegaEntity, None]:
        """创建 OmegaEntity 实例并开始新的数据库会话"""
        async with database_session() as session:
            yield self.get_current_entity(db_session=session)

    # ------------------------------------------------------------------ #
    # Matcher 及流程控制相关方法
    # ------------------------------------------------------------------ #

    async def send(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
            *,
            at_sender: bool = False,
            reply_to: bool = False,
            **kwargs,
    ) -> 'Receipt':
        return await self.get_event_depend().send(
            message=message,
            at_sender=at_sender,
            reply_to=reply_to,
            **kwargs,
        )

    async def send_at_sender(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> 'Receipt':
        return await self.send(message=message, at_sender=True)

    async def send_reply(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> 'Receipt':
        return await self.send(message=message, reply_to=True)

    async def revoke_bot_sent_msg(self, receipt: 'Receipt', *, revoke_delay: int = 0) -> None:
        return await self.get_event_depend().revoke_bot_sent_msg(receipt=receipt, revoke_delay=revoke_delay)

    async def send_auto_revoke(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
            *,
            at_sender: bool = False,
            reply_to: bool = False,
            revoke_delay: int = 60,
    ) -> None:
        """发送消息指定时间后自动撤回

        revoke_delay 默认值与 BaseEntityTarget.send_message_auto_revoke 保持一致
        """
        receipt = await self.send(message=message, at_sender=at_sender, reply_to=reply_to)
        return await self.revoke_bot_sent_msg(receipt=receipt, revoke_delay=revoke_delay)

    async def finish(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send(message=message)
        raise FinishedException

    async def finish_at_sender(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_at_sender(message=message)
        raise FinishedException

    async def finish_reply(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_reply(message=message)
        raise FinishedException

    async def pause(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send(message=message)
        raise PausedException

    async def pause_at_sender(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_at_sender(message=message)
        raise PausedException

    async def pause_reply(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_reply(message=message)
        raise PausedException

    async def reject(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send(message=message)
        raise RejectedException

    async def reject_at_sender(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_at_sender(message=message)
        raise RejectedException

    async def reject_reply(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_reply(message=message)
        raise RejectedException

    async def reject_arg(
            self,
            key: str,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send(message=message)
        await self.matcher.reject_arg(key)

    async def reject_arg_at_sender(
            self,
            key: str,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send_at_sender(message=message)
        await self.matcher.reject_arg(key)

    async def reject_arg_reply(
            self,
            key: str,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send_reply(message=message)
        await self.matcher.reject_arg(key)

    async def reject_receive(
            self,
            key: str, message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send(message=message)
        await self.matcher.reject_receive(key)

    async def reject_receive_at_sender(
            self,
            key: str,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send_at_sender(message=message)
        await self.matcher.reject_receive(key)

    async def reject_receive_reply(
            self,
            key: str, message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send_reply(message=message)
        await self.matcher.reject_receive(key)


__all__ = [
    'OmegaEntityInterface',
    'OmegaMatcherInterface',
]
