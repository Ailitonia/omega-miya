"""
@Author         : Ailitonia
@Date           : 2024/3/24 4:12
@FileName       : interface
@Project        : nonebot2_miya
@Description    : Omega 平台中间件统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import inspect
from collections.abc import AsyncGenerator, Callable, Coroutine, Sequence
from contextlib import asynccontextmanager
from functools import wraps
from typing import Concatenate, NoReturn, Self

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import FinishedException, PausedException, RejectedException
from nonebot.log import logger
from nonebot.matcher import Matcher, current_bot, current_event, current_matcher
from nonebot_plugin_alconna.uniseg import Receipt, Segment, UniMessage

from src.database import database_session
from src.database.internal.entity import EntityType
from .exception import AdapterNotSupported, TargetNotSupported
from .internal import (
    EVENT_DEPEND_REGISTER,
    ENTITY_TARGET_REGISTER,
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

    @staticmethod
    def check_target_implemented[**P, R, T1, T2, ST: 'OmegaEntityInterface'](
            func: Callable[Concatenate[ST, P], Coroutine[T1, T2, R]],
    ) -> Callable[Concatenate[ST, P], Coroutine[T1, T2, R]]:
        """装饰一个调用平台 API 的异步方法, 检查该方法调用的函数/方法是否实现, 如未实现则统一抛出 TargetNotSupported 异常"""
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f'{func.__name__} is not coroutine function')

        @wraps(func)
        async def _wrapper(self: ST, *args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(self, *args, **kwargs)
            except NotImplementedError:
                logger.warning(f'{self.type} not support method {func.__name__!r}')
                raise TargetNotSupported(self.type, f'method {func.__name__!r} not implemented')

        return _wrapper

    def get_entity_target(self) -> 'BaseEntityTarget':
        """获取 Entity 的中间件平台 API 适配器"""
        entity_target_cls = ENTITY_TARGET_REGISTER.get_target(target_name=self.type)
        return entity_target_cls(entity_params=self.entity_params)

    def get_bot(self) -> 'BaseBot':
        """获取 Entity 对应的 Bot 实例, 未在线则会抛出 BotNoFound 异常"""
        return self.get_entity_target().get_bot()

    # ------------------------------------------------------------------ #
    # 发送消息相关方法, 在 Event/Matcher 之外向目标 Entity 直接发送消息
    # ------------------------------------------------------------------ #

    @check_target_implemented
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

    @check_target_implemented
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

    @check_target_implemented
    async def get_entity_name(self) -> str:
        """获取对象名称/昵称"""
        return await self.get_entity_target().call_api_get_entity_name()

    @check_target_implemented
    async def get_entity_profile_image_url(self) -> str:
        """获取对象头像/图标"""
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

    @staticmethod
    def check_adapter_implemented[**P, R, T1, T2, ST: 'OmegaMatcherInterface'](
            func: Callable[Concatenate[ST, P], Coroutine[T1, T2, R]],
    ) -> Callable[Concatenate[ST, P], Coroutine[T1, T2, R]]:
        """装饰一个调用平台 API 的异步方法, 检查该方法调用的函数/方法是否实现, 如未实现则统一抛出 AdapterNotSupported 异常"""
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f'{func.__name__} is not coroutine function')

        @wraps(func)
        async def _wrapper(self: ST, *args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(self, *args, **kwargs)
            except NotImplementedError:
                logger.warning(f'{self.bot}/{self.event} not support method {func.__name__!r}')
                raise AdapterNotSupported(self.bot.adapter.get_name(), f'method {func.__name__!r} not implemented')

        return _wrapper

    @staticmethod
    def check_event_implemented[**P, R, ST: 'OmegaMatcherInterface'](
            func: Callable[Concatenate[ST, P], R],
    ) -> Callable[Concatenate[ST, P], R]:
        """装饰一个事件依赖的同步方法, 检查该方法调用的函数/方法是否实现, 如未实现则统一抛出 AdapterNotSupported 异常"""

        @wraps(func)
        def _wrapper(self: ST, *args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(self, *args, **kwargs)
            except NotImplementedError:
                logger.warning(f'{self.bot}/{self.event} not support method {func.__name__!r}')
                raise AdapterNotSupported(self.bot.adapter.get_name(), f'method {func.__name__!r} not implemented')

        return _wrapper

    def get_event_depend(self) -> 'BaseEventDepend':
        """获取的中间件平台事件对象解析器"""
        event_depend_cls = EVENT_DEPEND_REGISTER.get_depend(target_event=self.event)
        return event_depend_cls(bot=self.bot, event=self.event)

    def refresh_interface_state(self) -> None:
        self.bot = current_bot.get()
        self.event = current_event.get()
        self.matcher = current_matcher.get()

    # ------------------------------------------------------------------ #
    # 平台事件信息提取相关方法
    # ------------------------------------------------------------------ #

    @check_event_implemented
    def extract_current_entity_params(self) -> 'EntityInitParams':
        """提取触发事件用户 Entity 实例化参数"""
        return self.get_event_depend().extract_entity_params(acquire_type=self.acquire_type)

    def get_current_entity_interface(self) -> 'OmegaEntityInterface':
        entity_params = self.extract_current_entity_params()
        return OmegaEntityInterface(entity_params=entity_params)

    @asynccontextmanager
    async def create_current_entity_session(self) -> AsyncGenerator[OmegaEntity, None]:
        async with database_session() as session:
            yield OmegaEntity(
                session=session,
                **self.extract_current_entity_params().model_dump(),
            )

    @check_event_implemented
    def get_event_user_nickname(self) -> str:
        """获取当前事件用户昵称"""
        return self.get_event_depend().get_user_nickname()

    # ------------------------------------------------------------------ #
    # Matcher 及流程控制相关方法
    # ------------------------------------------------------------------ #

    @check_adapter_implemented
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

    @check_adapter_implemented
    async def send_at_sender(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> 'Receipt':
        return await self.send(message=message, at_sender=True)

    @check_adapter_implemented
    async def send_reply(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> 'Receipt':
        return await self.send(message=message, reply_to=True)

    @check_adapter_implemented
    async def revoke_bot_sent_msg(self, receipt: 'Receipt', *, revoke_delay: int = 0) -> None:
        return await self.get_event_depend().revoke_bot_sent_msg(receipt=receipt, revoke_delay=revoke_delay)

    @check_adapter_implemented
    async def send_auto_revoke(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
            *,
            at_sender: bool = False,
            reply_to: bool = False,
            revoke_delay: int = 0,
    ) -> None:
        """发送消息指定时间后自动撤回"""
        receipt = await self.send(message=message, at_sender=at_sender, reply_to=reply_to)
        return await self.revoke_bot_sent_msg(receipt=receipt, revoke_delay=revoke_delay)

    @check_adapter_implemented
    async def finish(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send(message=message)
        raise FinishedException

    @check_adapter_implemented
    async def finish_at_sender(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_at_sender(message=message)
        raise FinishedException

    @check_adapter_implemented
    async def finish_reply(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_reply(message=message)
        raise FinishedException

    @check_adapter_implemented
    async def pause(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send(message=message)
        raise PausedException

    @check_adapter_implemented
    async def pause_at_sender(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_at_sender(message=message)
        raise PausedException

    @check_adapter_implemented
    async def pause_reply(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_reply(message=message)
        raise PausedException

    @check_adapter_implemented
    async def reject(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send(message=message)
        raise RejectedException

    @check_adapter_implemented
    async def reject_at_sender(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_at_sender(message=message)
        raise RejectedException

    @check_adapter_implemented
    async def reject_reply(self, message: str | Segment | Sequence[Segment] | UniMessage) -> NoReturn:
        await self.send_reply(message=message)
        raise RejectedException

    @check_adapter_implemented
    async def reject_arg(
            self,
            key: str,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send(message=message)
        await self.matcher.reject_arg(key)

    @check_adapter_implemented
    async def reject_arg_at_sender(
            self,
            key: str,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send_at_sender(message=message)
        await self.matcher.reject_arg(key)

    @check_adapter_implemented
    async def reject_arg_reply(
            self,
            key: str,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send_reply(message=message)
        await self.matcher.reject_arg(key)

    @check_adapter_implemented
    async def reject_receive(
            self,
            key: str, message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send(message=message)
        await self.matcher.reject_receive(key)

    @check_adapter_implemented
    async def reject_receive_at_sender(
            self,
            key: str,
            message: str | Segment | Sequence[Segment] | UniMessage,
    ) -> NoReturn:
        await self.send_at_sender(message=message)
        await self.matcher.reject_receive(key)

    @check_adapter_implemented
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
