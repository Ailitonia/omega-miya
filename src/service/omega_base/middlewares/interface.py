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
from functools import wraps
from typing import TYPE_CHECKING, Annotated, Any, Callable, NoReturn, Optional, Self

from nonebot.exception import PausedException, FinishedException, RejectedException
from nonebot.internal.adapter import Bot as BaseBot, Event as BaseEvent
from nonebot.log import logger
from nonebot.matcher import Matcher, current_bot, current_event, current_matcher
from nonebot.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from .const import SupportedPlatform, SupportedTarget
from .exception import AdapterNotSupported, TargetNotSupported
from .platform_interface import entity_target_register, event_depend_register, message_builder_register
from .typing import EntityAcquireType, BaseSentMessageType

if TYPE_CHECKING:
    from .platform_interface.entity_target import BaseEntityTarget
    from .platform_interface.event_depend import EventDepend
    from .platform_interface.message_builder import Builder, Extractor
    from ..internal import OmegaEntity
    from ..message import Message as OmegaMessage

type SentOmegaMessage = BaseSentMessageType["OmegaMessage"]


class OmegaEntityInterface(object):
    """Omega 基于对象 (Entity) 的统一接口, 用于在 Event/Matcher 之外调用平台 Bot 相关方法"""

    __slots__ = ('_entity',)

    def __init__(self, entity: "OmegaEntity") -> None:
        self._entity = entity

    @classmethod
    def depend(cls, acquire_type: EntityAcquireType = 'event') -> Callable[[BaseBot, BaseEvent, AsyncSession], Self]:
        """获取注入依赖, 用于 Event/Matcher 中初始化"""

        def _depend(
                bot: BaseBot,
                event: BaseEvent,
                session: Annotated[AsyncSession, Depends(get_db_session)]
        ) -> Self:
            event_depend = event_depend_register.get_depend(target_event=event)(bot=bot, event=event)
            match acquire_type:
                case 'event':
                    entity_depend = event_depend.event_entity_depend
                case 'user':
                    entity_depend = event_depend.user_entity_depend
                case _:
                    raise ValueError(f'Not supported entity acquire_type: {acquire_type!r}')
            return cls(entity_depend(session))

        return _depend

    @staticmethod
    def check_implemented(func):
        """装饰一个方法, 检查该方法调用的函数/方法是否实现, 如未实现则统一抛出 TargetNotSupported 异常"""

        @wraps(func)
        def _wrapper(self: Self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except NotImplementedError:
                logger.warning(f'{self._entity} not support method {func.__name__!r}')
                raise TargetNotSupported(self._entity.entity_type)

        return _wrapper

    def get_entity_target(self) -> "BaseEntityTarget":
        """获取 Entity 的中间件平台 API 适配器"""
        entity_target_t = entity_target_register.get_target(target_name=SupportedTarget(self._entity.entity_type))
        return entity_target_t(entity=self._entity)

    async def get_bot(self) -> "BaseBot":
        """获取 Entity 对应的 Bot 实例, 未在线则会抛出 BotNoFound 异常"""
        return await self.get_entity_target().get_bot()

    async def get_message_builder(self) -> type["Builder"]:
        """获取 Entity 对应平台的消息构造器"""
        bot = await self.get_bot()
        return message_builder_register.get_builder(platform_name=SupportedPlatform(bot.adapter.get_name()))

    async def get_message_extractor(self) -> type["Extractor"]:
        """获取 Entity 对应平台的消息解析器"""
        bot = await self.get_bot()
        return message_builder_register.get_extractor(platform_name=SupportedPlatform(bot.adapter.get_name()))

    """在 Event/Matcher 之外向目标 Entity 直接发送消息的相关方法"""

    @check_implemented
    async def send_entity_message(self, message: "SentOmegaMessage", **kwargs) -> Any:
        """向 Entity 直接发送消息"""
        bot = await self.get_bot()
        message_builder = await self.get_message_builder()

        send_params = self.get_entity_target().get_api_to_send_msg(**kwargs)
        send_message = message_builder(message=message).message

        bot_api_params = {send_params.message_param_name: send_message, **send_params.params}
        return await getattr(bot, send_params.api)(**bot_api_params)

    @check_implemented
    async def send_entity_message_auto_revoke(
            self,
            message: "SentOmegaMessage",
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

    @check_implemented
    async def get_entity_name(self) -> str:
        return await self.get_entity_target().call_api_get_entity_name()

    @check_implemented
    async def get_entity_profile_image_url(self) -> str:
        return await self.get_entity_target().call_api_get_entity_profile_image_url()


class OmegaMatcherInterface(object):
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
    ) -> "OmegaEntity":
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
    def check_implemented(func):
        """装饰一个方法, 检查该方法调用的函数/方法是否实现, 如未实现则统一抛出 AdapterNotSupported 异常"""

        @wraps(func)
        def _wrapper(self: Self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except NotImplementedError:
                logger.warning(f'{self.bot}/{self.event} not support method {func.__name__!r}')
                raise AdapterNotSupported(self.bot.adapter.get_name())

        return _wrapper

    def get_entity_interface(self) -> OmegaEntityInterface:
        """获取事件 Entity 的 OmegaEntityInterface 实例"""
        return OmegaEntityInterface(entity=self.entity)

    def get_event_depend(self) -> "EventDepend":
        return event_depend_register.get_depend(target_event=self.event)(bot=self.bot, event=self.event)

    def get_message_builder(self) -> type["Builder"]:
        """获取 Bot 对应平台的消息构造器"""
        return self.get_event_depend().get_omega_message_builder()

    def get_message_extractor(self) -> type["Extractor"]:
        """获取 Bot 对应平台的消息解析器"""
        return self.get_event_depend().get_omega_message_extractor()

    def refresh_interface_state(self) -> None:
        self.bot = current_bot.get()
        self.event = current_event.get()
        self.matcher = current_matcher.get()

    """平台事件信息提取相关方法"""

    @check_implemented
    def get_event_user_nickname(self) -> str:
        """获取当前事件用户昵称"""
        return self.get_event_depend().get_user_nickname()

    @check_implemented
    def get_event_msg_image_urls(self) -> list[str]:
        """获取当前事件消息中的全部图片链接"""
        return self.get_event_depend().get_msg_image_urls()

    @check_implemented
    def get_event_reply_msg_image_urls(self) -> list[str]:
        """获取当前事件回复消息中的全部图片链接"""
        return self.get_event_depend().get_reply_msg_image_urls()

    @check_implemented
    def get_event_reply_msg_plain_text(self) -> Optional[str]:
        """获取当前事件回复消息的文本"""
        return self.get_event_depend().get_reply_msg_plain_text()

    """Matcher 及流程控制相关方法"""

    @check_implemented
    async def send(self, message: SentOmegaMessage, **kwargs) -> Any:
        return await self.get_event_depend().send(message=message, **kwargs)

    @check_implemented
    async def send_at_sender(self, message: SentOmegaMessage, **kwargs) -> Any:
        return await self.get_event_depend().send_at_sender(message=message, **kwargs)

    @check_implemented
    async def send_reply(self, message: SentOmegaMessage, **kwargs) -> Any:
        return await self.get_event_depend().send_reply(message=message, **kwargs)

    @check_implemented
    async def send_auto_revoke(self, message: SentOmegaMessage, revoke_interval: int = 60, **kwargs) -> Any:
        sent_return = await self.get_event_depend().send(message=message)

        loop = asyncio.get_running_loop()
        return loop.call_later(
            revoke_interval,
            lambda: loop.create_task(self.get_event_depend().revoke(sent_return=sent_return, **kwargs)),
        )

    @check_implemented
    async def finish(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        raise FinishedException

    @check_implemented
    async def finish_at_sender(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        raise FinishedException

    @check_implemented
    async def finish_reply(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        raise FinishedException

    @check_implemented
    async def pause(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        raise PausedException

    @check_implemented
    async def pause_at_sender(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        raise PausedException

    @check_implemented
    async def pause_reply(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        raise PausedException

    @check_implemented
    async def reject(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        raise RejectedException

    @check_implemented
    async def reject_at_sender(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        raise RejectedException

    @check_implemented
    async def reject_reply(self, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        raise RejectedException

    @check_implemented
    async def reject_arg(self, key: str, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @check_implemented
    async def reject_arg_at_sender(self, key: str, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @check_implemented
    async def reject_arg_reply(self, key: str, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    @check_implemented
    async def reject_receive(self, key: str, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send(message=message, **kwargs)
        await self.matcher.reject_receive(key)

    @check_implemented
    async def reject_receive_at_sender(self, key: str, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_at_sender(message=message, **kwargs)
        await self.matcher.reject_receive(key)

    @check_implemented
    async def reject_receive_reply(self, key: str, message: SentOmegaMessage, **kwargs) -> NoReturn:
        await self.send_reply(message=message, **kwargs)
        await self.matcher.reject_receive(key)





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
        bot = get_online_bots().get(bot_self.bot_type, {}).get(bot_self.self_id)
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
    'OmegaEntityInterface',
    'OmegaMatcherInterface',
]
