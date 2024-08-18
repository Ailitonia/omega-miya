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
from contextlib import asynccontextmanager
from functools import wraps, partial
from typing import Annotated, Any, Callable, Iterable, Literal, NoReturn, Optional, ParamSpec, Type, TypeVar, Union

from nonebot.exception import PausedException, FinishedException, RejectedException
from nonebot.internal.adapter.bot import Bot as BaseBot
from nonebot.internal.adapter.event import Event as BaseEvent
from nonebot.log import logger
from nonebot.matcher import Matcher, current_bot, current_event, current_matcher
from nonebot.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import begin_db_session, get_db_session
from src.service.omega_multibot_support import get_online_bots
from .exception import BotNoFound
from .register import PlatformRegister
from .types import ApiCaller, EntityDepend, EventHandler, MessageBuilder, MessageExtractor, MessageSender, RevokeParams
from ..internal import OmegaEntity
from ..message import (
    Message as OmegaMessage,
    MessageSegment as OmegaMessageSegment
)

P = ParamSpec("P")
R = TypeVar("R")


class OmegaInterface(object):
    """Omega 中间件统一接口"""

    def __init__(self, acquire_type: Literal['event', 'user'] = 'event', *, entity: Optional[OmegaEntity] = None):
        """初始化时判断调用位置及平台类型"""
        self.acquire_type = acquire_type
        self.entity = entity

        self.bot: Optional[BaseBot] = None
        self.event: Optional[BaseEvent] = None
        self.matcher: Optional[Matcher] = None

        try:
            self.bot = current_bot.get()
            self.event = current_event.get()
            self.matcher = current_matcher.get()
        except LookupError as e:
            logger.trace(f'OmegaInterface 在事件响应器之外实例化, {e}')

    def __call__(
            self,
            bot: BaseBot,
            event: BaseEvent,
            session: Annotated[AsyncSession, Depends(get_db_session)]
    ) -> "OmegaInterface":
        """依赖注入: OmegaInterface(OmegaEntity)"""
        entity_depend_type: Type[EntityDepend] = PlatformRegister.entity_depend.get_target(event)
        entity = entity_depend_type(acquire_type=self.acquire_type)(bot=bot, event=event, session=session)
        self.bot = bot
        self.event = event
        self.entity = entity
        return self

    def __getattr__(self, name: str) -> "partial":
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(f'{self.__class__.__name__!r} object has no attribute {name!r}')
        return partial(self.run_entity_method, name)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(type={self.acquire_type}, entity={self.entity})'

    @staticmethod
    def _ensure_entity(func: Callable[P, R]) -> Callable[P, R]:
        """装饰一个方法, 需要 self.entity 为实例时才能运行"""
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self: "OmegaInterface" = args[0]
            if isinstance(self.entity, OmegaEntity):
                return func(*args, **kwargs)
            else:
                raise RuntimeError(f'{self} entity is not initialized')

        return _wrapper

    @staticmethod
    def _ensure_matcher(func: Callable[P, R]) -> Callable[P, R]:
        """装饰一个方法, 需要 self.matcher 为实例时才能运行"""
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self: "OmegaInterface" = args[0]
            if isinstance(self.matcher, Matcher):
                return func(*args, **kwargs)
            else:
                raise RuntimeError(f'{self} matcher is not initialized, using refresh_matcher_state() in matcher first')

        return _wrapper

    @staticmethod
    def _ensure_session(func: Callable[P, R]) -> Callable[P, R]:
        """装饰一个异步方法, 确保 Session 可用状态

        Issue reference: https://github.com/sqlalchemy/sqlalchemy/discussions/9312
        """
        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self: "OmegaInterface" = args[0]
            if self.entity.db_session.is_active:
                return await func(*args, **kwargs)

            del self.entity.db_session
            async with begin_db_session() as session:
                self.entity.db_session = session
                return await func(*args, **kwargs)
        return _wrapper

    def refresh_bot_state(self) -> None:
        self.bot = current_bot.get()

    def refresh_event_state(self) -> None:
        self.event = current_event.get()

    def refresh_matcher_state(self) -> None:
        self.matcher = current_matcher.get()

    def refresh_interface_state(self) -> None:
        self.bot = current_bot.get()
        self.event = current_event.get()
        self.matcher = current_matcher.get()

    def get_api_caller(self, *, bot: BaseBot) -> ApiCaller:
        bot = bot if bot is not None else self.bot
        if bot is None:
            raise ValueError('bot is not instantiated')

        api_caller: Type[ApiCaller] = PlatformRegister.api_caller.get_target(bot)
        return api_caller(bot=bot)

    def get_event_handler(self, *, bot: Optional[BaseBot] = None, event: Optional[BaseEvent] = None) -> EventHandler:
        bot = bot if bot is not None else self.bot
        event = event if event is not None else self.event

        if bot is None or event is None:
            raise ValueError('bot or event is not instantiated')

        event_handler: Type[EventHandler] = PlatformRegister.event_handler.get_target(event)
        return event_handler(bot=bot, event=event)

    def get_msg_builder(self, *, bot: Optional[BaseBot] = None) -> Type[MessageBuilder]:
        bot = bot if bot is not None else self.bot
        if bot is None:
            raise ValueError('bot is not instantiated')

        message_builder: Type[MessageBuilder] = PlatformRegister.message_builder.get_target(bot)
        return message_builder

    def get_msg_extractor(self, *, bot: Optional[BaseBot] = None) -> Type[MessageExtractor]:
        bot = bot if bot is not None else self.bot
        if bot is None:
            raise ValueError('bot is not instantiated')

        message_extractor: Type[MessageExtractor] = PlatformRegister.message_extractor.get_target(bot)
        return message_extractor

    @asynccontextmanager
    async def get_entity(self, *, bot: Optional[BaseBot] = None, event: Optional[BaseEvent] = None):
        """获取 OmegaEntity 并开始事务"""
        bot = bot if bot is not None else self.bot
        event = event if event is not None else self.event

        if bot is None or event is None:
            raise ValueError('bot or event is not instantiated')

        async with begin_db_session() as session:
            entity = self(bot=bot, event=event, session=session).entity
            yield entity

    # Platform/Entity 接口

    @_ensure_session
    @_ensure_entity
    async def get_bot(self) -> BaseBot:
        bot_self = await self.entity.query_bot_self()
        bot = get_online_bots().get(bot_self.bot_type.value, {}).get(bot_self.self_id)
        if not bot:
            raise BotNoFound(f'{bot_self} not online')
        return bot

    @_ensure_session
    @_ensure_entity
    async def get_entity_name(self) -> str:
        bot = await self.get_bot()
        api_caller = self.get_api_caller(bot=bot)
        return await api_caller.get_name(entity=self.entity)

    @_ensure_session
    @_ensure_entity
    async def get_entity_profile_photo_url(self) -> str:
        bot = await self.get_bot()
        api_caller = self.get_api_caller(bot=bot)
        return await api_caller.get_profile_photo_url(entity=self.entity)

    @_ensure_session
    @_ensure_entity
    async def send_msg(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs):
        bot = await self.get_bot()
        builder = self.get_msg_builder(bot=bot)
        msg_sender_t: Type[MessageSender] = PlatformRegister.message_sender.get_target(self.entity)

        send_params = msg_sender_t(target_entity=self.entity).to_send_msg(**kwargs)
        send_message = builder(message=message).message

        params = {send_params.message_param_name: send_message, **send_params.params}

        return await getattr(bot, send_params.api)(**params)

    @_ensure_session
    @_ensure_entity
    async def send_multi_msgs(self, messages: Iterable[Union[str, None, OmegaMessage, OmegaMessageSegment]], **kwargs):
        bot = await self.get_bot()
        builder = self.get_msg_builder(bot=bot)
        msg_sender_t: Type[MessageSender] = PlatformRegister.message_sender.get_target(self.entity)

        sender = msg_sender_t(target_entity=self.entity)
        send_params = sender.to_send_multi_msgs(**kwargs)
        send_message = sender.construct_multi_msgs(messages=(builder(message=message).message for message in messages))

        params = {send_params.message_param_name: send_message, **send_params.params}

        return await getattr(bot, send_params.api)(**params)

    @staticmethod
    async def _create_revoke_tasks(bot: BaseBot, revoke_params: Union[RevokeParams, Iterable[RevokeParams]]):
        if isinstance(revoke_params, RevokeParams):
            return await getattr(bot, revoke_params.api)(**revoke_params.params)
        else:
            return await asyncio.gather(
                *(getattr(bot, params.api)(**params.params) for params in revoke_params), return_exceptions=True
            )

    @_ensure_session
    @_ensure_entity
    async def send_msg_auto_revoke(
            self,
            message: Union[str, None, OmegaMessage, OmegaMessageSegment],
            revoke_interval: int = 60,
            **kwargs
    ) -> asyncio.TimerHandle:
        """发出消息指定时间后自动撤回"""
        bot = await self.get_bot()
        msg_sender_t: Type[MessageSender] = PlatformRegister.message_sender.get_target(self.entity)

        sender = msg_sender_t(target_entity=self.entity)
        sent_data = await self.send_msg(message=message)
        revoke_params = sender.parse_revoke_sent_params(content=sent_data, **kwargs)

        loop = asyncio.get_running_loop()
        return loop.call_later(
            revoke_interval,
            lambda: loop.create_task(self._create_revoke_tasks(bot=bot, revoke_params=revoke_params)),
        )

    @_ensure_session
    @_ensure_entity
    async def send_multi_msgs_auto_revoke(
            self,
            messages: Iterable[Union[str, None, OmegaMessage, OmegaMessageSegment]],
            revoke_interval: int = 60,
            **kwargs
    ) -> asyncio.TimerHandle:
        """发出消息指定时间后自动撤回"""
        bot = await self.get_bot()
        msg_sender_t: Type[MessageSender] = PlatformRegister.message_sender.get_target(self.entity)

        sender = msg_sender_t(target_entity=self.entity)
        sent_data = await self.send_multi_msgs(messages=messages)
        revoke_params = sender.parse_revoke_sent_params(content=sent_data, **kwargs)

        loop = asyncio.get_running_loop()
        return loop.call_later(
            revoke_interval,
            lambda: loop.create_task(self._create_revoke_tasks(bot=bot, revoke_params=revoke_params)),
        )

    @_ensure_session
    @_ensure_entity
    async def run_entity_method(self, method_name: str, **kwargs: Any) -> Any:
        """调用 Entity 方法"""
        entity_method = getattr(self.entity, method_name)
        if entity_method is None:
            raise AttributeError(f'Entity method {method_name} is not exists')
        if not inspect.iscoroutinefunction(entity_method):
            raise RuntimeError(f'Entity method {method_name} is not coroutine function')
        return await entity_method(**kwargs)

    # Matcher 接口

    @_ensure_matcher
    def extract_event_message(self) -> OmegaMessage:
        message = self.event.get_message()
        extractor = self.get_msg_extractor()
        return extractor(message).message

    @_ensure_matcher
    async def send(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs):
        """发送消息"""
        builder = self.get_msg_builder()
        send_message = builder(message=message).message
        return await self.matcher.send(message=send_message, **kwargs)

    @_ensure_matcher
    async def send_at_sender(self, message: Union[str, OmegaMessage, OmegaMessageSegment], **kwargs):
        """发送消息并@上条消息发送者"""
        builder = self.get_msg_builder()
        send_message = builder(message=message).message
        return await self.get_event_handler().send_at_sender(message=send_message, **kwargs)

    @_ensure_matcher
    async def send_reply(self, message: Union[str, OmegaMessage, OmegaMessageSegment], **kwargs):
        """发送消息并回复/引用上条消息"""
        builder = self.get_msg_builder()
        send_message = builder(message=message).message
        return await self.get_event_handler().send_reply(message=send_message, **kwargs)

    @_ensure_matcher
    async def finish(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.finish()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        raise FinishedException

    @_ensure_matcher
    async def finish_at_sender(self, message: Union[str, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.finish()` 作用相同，仅能用在事件响应器中"""
        await self.send_at_sender(message=message, **kwargs)
        raise FinishedException

    @_ensure_matcher
    async def finish_reply(self, message: Union[str, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.finish()` 作用相同，仅能用在事件响应器中"""
        await self.send_reply(message=message, **kwargs)
        raise FinishedException

    @_ensure_matcher
    async def pause(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.pause()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        raise PausedException

    @_ensure_matcher
    async def pause_at_sender(self, message: Union[str, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.pause()` 作用相同，仅能用在事件响应器中"""
        await self.send_at_sender(message=message, **kwargs)
        raise PausedException

    @_ensure_matcher
    async def pause_reply(self, message: Union[str, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.pause()` 作用相同，仅能用在事件响应器中"""
        await self.send_reply(message=message, **kwargs)
        raise PausedException

    @_ensure_matcher
    async def reject(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.reject()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        raise RejectedException

    @_ensure_matcher
    async def reject_at_sender(self, message: Union[str, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.reject()` 作用相同，仅能用在事件响应器中"""
        await self.send_at_sender(message=message, **kwargs)
        raise RejectedException

    @_ensure_matcher
    async def reject_reply(self, message: Union[str, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.reject()` 作用相同，仅能用在事件响应器中"""
        await self.send_reply(message=message, **kwargs)
        raise RejectedException

    @_ensure_matcher
    async def reject_arg(
            self,
            key: str,
            message: Union[str, None, OmegaMessage, OmegaMessageSegment],
            **kwargs
    ) -> NoReturn:
        """与 `matcher.reject_arg()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @_ensure_matcher
    async def reject_arg_at_sender(
            self,
            key: str,
            message: Union[str, OmegaMessage, OmegaMessageSegment],
            **kwargs
    ) -> NoReturn:
        """与 `matcher.reject_arg()` 作用相同，仅能用在事件响应器中"""
        await self.send_at_sender(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @_ensure_matcher
    async def reject_arg_reply(
            self,
            key: str,
            message: Union[str, OmegaMessage, OmegaMessageSegment],
            **kwargs
    ) -> NoReturn:
        """与 `matcher.reject_arg()` 作用相同，仅能用在事件响应器中"""
        await self.send_reply(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @_ensure_matcher
    async def reject_receive(
            self,
            key: str,
            message: Union[str, None, OmegaMessage, OmegaMessageSegment],
            **kwargs
    ) -> NoReturn:
        """与 `matcher.reject_receive()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        await self.matcher.reject_receive(key)

    @_ensure_matcher
    async def reject_receive_at_sender(
            self,
            key: str,
            message: Union[str, OmegaMessage, OmegaMessageSegment],
            **kwargs
    ) -> NoReturn:
        """与 `matcher.reject_receive()` 作用相同，仅能用在事件响应器中"""
        await self.send_at_sender(message=message, **kwargs)
        await self.matcher.reject_receive(key)

    @_ensure_matcher
    async def reject_receive_reply(
            self,
            key: str,
            message: Union[str, OmegaMessage, OmegaMessageSegment],
            **kwargs
    ) -> NoReturn:
        """与 `matcher.reject_receive()` 作用相同，仅能用在事件响应器中"""
        await self.send_reply(message=message, **kwargs)
        await self.matcher.reject_receive(key)


__all__ = [
    'OmegaInterface',
]
