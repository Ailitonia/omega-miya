"""
@Author         : Ailitonia
@Date           : 2024/3/24 4:12
@FileName       : interface
@Project        : nonebot2_miya
@Description    : Omega 平台中间件统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
import inspect
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import TYPE_CHECKING, Annotated, Any, NoReturn, Self, cast

from nonebot.exception import FinishedException, PausedException, RejectedException
from nonebot.internal.adapter import Bot as BaseBot
from nonebot.internal.adapter import Event as BaseEvent
from nonebot.log import logger
from nonebot.matcher import Matcher, current_bot, current_event, current_matcher
from nonebot.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from .const import SupportedPlatform, SupportedTarget
from .exception import AdapterNotSupported, TargetNotSupported
from .platform_interface import entity_target_register, event_depend_register, message_builder_register
from .typing import BaseSentMessageType, EntityAcquireType

if TYPE_CHECKING:
    from pathlib import Path

    from ..internal import OmegaEntity
    from .platform_interface.entity_target import BaseEntityTarget
    from .platform_interface.event_depend import EventDepend
    from .platform_interface.message_builder import Builder, Extractor

type SentOmegaMessage = BaseSentMessageType['OmegaMessage']


class OmegaEntityInterface:
    """Omega 基于对象 (Entity) 的统一接口, 用于在 Event/Matcher 之外调用平台 Bot 相关方法"""

    __slots__ = ('_entity',)

    def __init__(self, entity: 'OmegaEntity') -> None:
        self._entity = entity

    @staticmethod
    def check_target_implemented[** P, R](
            func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        """装饰一个调用平台 API 的异步方法, 检查该方法调用的函数/方法是否实现, 如未实现则统一抛出 TargetNotSupported 异常"""
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f'{func.__name__} is not coroutine function')

        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(*args, **kwargs)
            except NotImplementedError:
                self: Self = cast(Self, args[0])
                logger.warning(f'{self._entity} not support method {func.__name__!r}')
                raise TargetNotSupported(self._entity.entity_type, f'method {func.__name__!r} is not implemented')

        return _wrapper

    def get_entity_target(self) -> 'BaseEntityTarget':
        """获取 Entity 的中间件平台 API 适配器"""
        entity_target_t = entity_target_register.get_target(target_name=SupportedTarget(self._entity.entity_type))
        return entity_target_t(entity=self._entity)

    async def get_bot(self) -> 'BaseBot':
        """获取 Entity 对应的 Bot 实例, 未在线则会抛出 BotNoFound 异常"""
        return await self.get_entity_target().get_bot()

    async def get_message_builder(self) -> type['Builder']:
        """获取 Entity 对应平台的消息构造器"""
        bot = await self.get_bot()
        return message_builder_register.get_builder(platform_name=SupportedPlatform(bot.adapter.get_name()))

    async def get_message_extractor(self) -> type['Extractor']:
        """获取 Entity 对应平台的消息解析器"""
        bot = await self.get_bot()
        return message_builder_register.get_extractor(platform_name=SupportedPlatform(bot.adapter.get_name()))

    """在 Event/Matcher 之外向目标 Entity 直接发送消息的相关方法"""

    @check_target_implemented
    async def send_entity_message(self, message: 'SentOmegaMessage', **kwargs) -> Any:
        """向 Entity 直接发送消息"""
        bot = await self.get_bot()
        message_builder = await self.get_message_builder()

        send_params = self.get_entity_target().get_api_to_send_msg(**kwargs)
        send_message = message_builder(message=message).message

        bot_api_params = {send_params.message_param_name: send_message, **send_params.params}
        return await getattr(bot, send_params.api)(**bot_api_params)

    @check_target_implemented
    async def send_entity_message_auto_revoke(
            self,
            message: 'SentOmegaMessage',
            revoke_interval: int = 60,
            **kwargs
    ) -> Any:
        """向 Entity 直接发送消息并在一定时间后撤回"""
        bot = await self.get_bot()
        sent_return = await self.send_entity_message(message=message)
        revoke_params = self.get_entity_target().get_api_to_revoke_msgs(sent_return=sent_return, **kwargs)

        loop = asyncio.get_running_loop()
        return loop.call_later(
            revoke_interval,
            lambda: loop.create_task(getattr(bot, revoke_params.api)(**revoke_params.params)),
        )

    """Entity 相关信息获取方法"""

    @check_target_implemented
    async def get_entity_name(self) -> str:
        """获取对象名称/昵称"""
        return await self.get_entity_target().call_api_get_entity_name()

    @check_target_implemented
    async def get_entity_profile_image_url(self) -> str:
        """获取对象头像/图标"""
        return await self.get_entity_target().call_api_get_entity_profile_image_url()

    @check_target_implemented
    async def send_entity_file(self, file: 'Path', *, file_name: str | None = None) -> None:
        """向对象发送本地文件"""
        if file_name is None:
            file_name = file.name

        return await self.get_entity_target().call_api_send_file(file_path=file.as_posix(), file_name=file_name)


class OmegaMatcherInterface:
    """Omega 基于事件 (Event) 的统一接口, 用于在 Event/Matcher 中调用平台 Bot 相关方法和进行流程交互"""

    __slots__ = ('bot', 'event', 'matcher', 'session', 'entity',)

    def __init__(
            self,
            bot: BaseBot,
            event: BaseEvent,
            matcher: Matcher,
            session: AsyncSession,
            acquire_type: EntityAcquireType = 'event',
    ) -> None:
        self.bot = bot
        self.event = event
        self.matcher = matcher
        self.session = session
        self.entity = self.get_entity(bot=bot, event=event, session=session, acquire_type=acquire_type)

    @classmethod
    def get_entity(
            cls,
            bot: BaseBot,
            event: BaseEvent,
            session: AsyncSession,
            acquire_type: EntityAcquireType = 'event',
    ) -> 'OmegaEntity':
        """获取事件对应的 Entity 对象"""
        event_depend = event_depend_register.get_depend(target_event=event)(bot=bot, event=event)
        match acquire_type:
            case 'event':
                entity_depend = event_depend.event_entity_depend
            case 'user':
                entity_depend = event_depend.user_entity_depend
            case _:
                raise ValueError(f'Not supported entity acquire_type: {acquire_type!r}')
        return entity_depend(session)

    @classmethod
    def depend(
            cls,
            acquire_type: EntityAcquireType = 'event'
    ) -> Callable[[BaseBot, BaseEvent, Matcher, AsyncSession], Self]:
        """获取注入依赖, 用于 Event/Matcher 中初始化"""

        def _depend(
                bot: BaseBot,
                event: BaseEvent,
                matcher: Matcher,
                session: Annotated[AsyncSession, Depends(get_db_session)],
        ) -> Self:
            return cls(bot=bot, event=event, matcher=matcher, session=session, acquire_type=acquire_type)

        return _depend

    @staticmethod
    def check_adapter_implemented[** P, R](
            func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        """装饰一个调用平台 API 的异步方法, 检查该方法调用的函数/方法是否实现, 如未实现则统一抛出 AdapterNotSupported 异常"""
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f'{func.__name__} is not coroutine function')

        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(*args, **kwargs)
            except NotImplementedError:
                self: Self = cast(Self, args[0])
                logger.warning(f'{self.bot}/{self.event} not support method {func.__name__!r}')
                raise AdapterNotSupported(self.bot.adapter.get_name(), f'method {func.__name__!r} is not implemented')

        return _wrapper

    @staticmethod
    def check_event_implemented[** P, R](func: Callable[P, R]) -> Callable[P, R]:
        """装饰一个事件依赖的同步方法, 检查该方法调用的函数/方法是否实现, 如未实现则统一抛出 AdapterNotSupported 异常"""

        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except NotImplementedError:
                self: Self = cast(Self, args[0])
                logger.warning(f'{self.bot}/{self.event} not support method {func.__name__!r}')
                raise AdapterNotSupported(self.bot.adapter.get_name(), f'method {func.__name__!r} is not implemented')

        return _wrapper

    def get_entity_interface(self) -> OmegaEntityInterface:
        """获取事件 Entity 的 OmegaEntityInterface 实例"""
        return OmegaEntityInterface(entity=self.entity)

    def get_event_depend(self) -> 'EventDepend':
        return event_depend_register.get_depend(target_event=self.event)(bot=self.bot, event=self.event)

    def get_message_builder(self) -> type['Builder']:
        """获取 Bot 对应平台的消息构造器"""
        return self.get_event_depend().get_omega_message_builder()

    def get_message_extractor(self) -> type['Extractor']:
        """获取 Bot 对应平台的消息解析器"""
        return self.get_event_depend().get_omega_message_extractor()

    def refresh_interface_state(self) -> None:
        self.bot = current_bot.get()
        self.event = current_event.get()
        self.matcher = current_matcher.get()

    """平台事件信息提取相关方法"""

    @check_event_implemented
    def get_event_user_nickname(self) -> str:
        """获取当前事件用户昵称"""
        return self.get_event_depend().get_user_nickname()

    @check_event_implemented
    def get_event_msg_image_urls(self) -> list[str]:
        """获取当前事件消息中的全部图片链接"""
        return self.get_event_depend().get_msg_image_urls()

    @check_event_implemented
    def get_event_reply_msg_image_urls(self) -> list[str]:
        """获取当前事件回复消息中的全部图片链接"""
        return self.get_event_depend().get_reply_msg_image_urls()

    @check_event_implemented
    def get_event_reply_msg_plain_text(self) -> str | None:
        """获取当前事件回复消息的文本"""
        return self.get_event_depend().get_reply_msg_plain_text()

    """Matcher 及流程控制相关方法"""

    @check_adapter_implemented
    async def send(self, message: 'SentOmegaMessage', **kwargs) -> Any:
        return await self.get_event_depend().send(message=message, **kwargs)

    @check_adapter_implemented
    async def send_at_sender(self, message: 'SentOmegaMessage', **kwargs) -> Any:
        return await self.get_event_depend().send_at_sender(message=message, **kwargs)

    @check_adapter_implemented
    async def send_reply(self, message: 'SentOmegaMessage', **kwargs) -> Any:
        return await self.get_event_depend().send_reply(message=message, **kwargs)

    @check_adapter_implemented
    async def send_auto_revoke(
            self,
            message: 'SentOmegaMessage',
            revoke_interval: int = 60,
            **revoke_kwargs
    ) -> asyncio.TimerHandle:
        """发送消息指定时间后自动撤回"""
        sent_return = await self.send(message=message)

        loop = asyncio.get_running_loop()
        return loop.call_later(
            revoke_interval,
            lambda: loop.create_task(self.get_event_depend().revoke(sent_return=sent_return, **revoke_kwargs)),
        )

    @check_adapter_implemented
    async def send_reply_auto_revoke(
            self,
            message: 'SentOmegaMessage',
            revoke_interval: int = 60,
            **revoke_kwargs
    ) -> asyncio.TimerHandle:
        """发送消息指定时间后自动撤回"""
        sent_return = await self.send_reply(message=message)

        loop = asyncio.get_running_loop()
        return loop.call_later(
            revoke_interval,
            lambda: loop.create_task(self.get_event_depend().revoke(sent_return=sent_return, **revoke_kwargs)),
        )

    @check_adapter_implemented
    async def finish(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        raise FinishedException

    @check_adapter_implemented
    async def finish_at_sender(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        raise FinishedException

    @check_adapter_implemented
    async def finish_reply(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        raise FinishedException

    @check_adapter_implemented
    async def pause(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        raise PausedException

    @check_adapter_implemented
    async def pause_at_sender(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        raise PausedException

    @check_adapter_implemented
    async def pause_reply(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        raise PausedException

    @check_adapter_implemented
    async def reject(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        raise RejectedException

    @check_adapter_implemented
    async def reject_at_sender(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        raise RejectedException

    @check_adapter_implemented
    async def reject_reply(self, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        raise RejectedException

    @check_adapter_implemented
    async def reject_arg(self, key: str, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @check_adapter_implemented
    async def reject_arg_at_sender(self, key: str, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @check_adapter_implemented
    async def reject_arg_reply(self, key: str, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @check_adapter_implemented
    async def reject_receive(self, key: str, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        await self.matcher.reject_receive(key)

    @check_adapter_implemented
    async def reject_receive_at_sender(self, key: str, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        await self.matcher.reject_receive(key)

    @check_adapter_implemented
    async def reject_receive_reply(self, key: str, message: 'SentOmegaMessage', **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        await self.matcher.reject_receive(key)


__all__ = [
    'OmegaEntityInterface',
    'OmegaMatcherInterface',
]
