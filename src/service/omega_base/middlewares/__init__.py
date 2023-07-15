"""
@Author         : Ailitonia
@Date           : 2023/3/23 22:03
@FileName       : middlewares
@Project        : nonebot2_miya
@Description    : Omega 平台中间件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Callable, Iterable, Literal, NoReturn, Optional, ParamSpec, Type, TypeVar, Union

from nonebot.exception import PausedException, FinishedException, RejectedException
from nonebot.internal.adapter.bot import Bot as BaseBot
from nonebot.internal.adapter.event import Event as BaseEvent
from nonebot.matcher import Matcher, current_bot, current_event, current_matcher
from nonebot.params import Depends

from src.database import begin_db_session, get_db_session
from src.service.omega_multibot_support import get_online_bots

from . import platform_target as platform_target

from .api_tools import get_api_caller
from .exception import BotNoFound
from .entity_tools import get_entity_depend
from .event_tools import get_event_handler
from .message_tools import get_msg_builder, get_msg_extractor, get_msg_sender
from .types import ApiCaller, EntityDepend, EventHandler, MessageBuilder, MessageExtractor, MessageSender, RevokeParams

from ..message import (
    Message as OmegaMessage,
    MessageSegment as OmegaMessageSegment
)
from ..internal import OmegaEntity


P = ParamSpec("P")
R = TypeVar("R")


class EntityInterface(object):
    """Omega 中间件 Entity 接口"""

    def __init__(self, acquire_type: Literal['event', 'user'] = 'event', *, entity: Optional[OmegaEntity] = None):
        self.acquire_type = acquire_type
        self.entity = entity

    def __call__(
            self,
            bot: BaseBot,
            event: BaseEvent,
            session: Annotated[AsyncSession, Depends(get_db_session)]
    ) -> "EntityInterface":
        """依赖注入: EntityInterface(OmegaEntity)"""
        entity_depend_type = get_entity_depend(event=event)
        entity = entity_depend_type(acquire_type=self.acquire_type)(bot=bot, event=event, session=session)
        self.entity = entity
        return self

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(type={self.acquire_type}, entity={self.entity})'

    @staticmethod
    def _ensure_entity(func: Callable[P, R]) -> Callable[P, R]:
        """装饰一个方法, 需要 Entity 为实例时才能运行"""
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self: "EntityInterface" = args[0]
            if isinstance(self.entity, OmegaEntity):
                return func(*args, **kwargs)
            else:
                raise RuntimeError('entity is not instantiated')

        return _wrapper

    @staticmethod
    def get_api_caller(bot: BaseBot) -> ApiCaller:
        return get_api_caller(platform=bot)(bot=bot)

    @asynccontextmanager
    async def get_entity(self, bot: BaseBot, event: BaseEvent):
        """获取 OmegaEntity 并开始事务"""
        async with begin_db_session() as session:
            entity = self(bot=bot, event=event, session=session).entity
            yield entity

    @_ensure_entity
    async def get_bot(self) -> BaseBot:
        bot_self = await self.entity.query_bot_self()
        bot = get_online_bots().get(bot_self.bot_type.value, {}).get(bot_self.self_id)
        if not bot:
            raise BotNoFound(f'{bot_self} not online')
        return bot

    @_ensure_entity
    async def get_entity_name(self) -> str:
        bot = await self.get_bot()
        api_caller = self.get_api_caller(bot=bot)
        return await api_caller.get_name(entity=self.entity)

    @_ensure_entity
    async def get_entity_profile_photo_url(self) -> str:
        bot = await self.get_bot()
        api_caller = self.get_api_caller(bot=bot)
        return await api_caller.get_profile_photo_url(entity=self.entity)

    @_ensure_entity
    async def send_msg(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment]):
        bot = await self.get_bot()
        builder = get_msg_builder(bot)

        send_params = get_msg_sender(target=self.entity)(target_entity=self.entity).to_send_msg()
        send_message = builder(message=message).message

        params = {send_params.message_param_name: send_message, **send_params.params}

        return await getattr(bot, send_params.api)(**params)

    @_ensure_entity
    async def send_multi_msgs(self, messages: Iterable[Union[str, None, OmegaMessage, OmegaMessageSegment]]):
        bot = await self.get_bot()
        builder = get_msg_builder(bot)

        sender = get_msg_sender(target=self.entity)(target_entity=self.entity)
        send_params = sender.to_send_multi_msgs()
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

    @_ensure_entity
    async def send_msg_auto_revoke(
            self,
            message: Union[str, None, OmegaMessage, OmegaMessageSegment],
            revoke_interval: int = 60
    ) -> asyncio.TimerHandle:
        """发出消息指定时间后自动撤回"""
        bot = await self.get_bot()

        sender = get_msg_sender(target=self.entity)(target_entity=self.entity)
        sent_data = await self.send_msg(message=message)
        revoke_params = sender.parse_revoke_sent_params(content=sent_data)

        loop = asyncio.get_running_loop()
        return loop.call_later(
            revoke_interval,
            lambda: loop.create_task(self._create_revoke_tasks(bot=bot, revoke_params=revoke_params)),
        )

    @_ensure_entity
    async def send_multi_msgs_auto_revoke(
            self,
            messages: Iterable[Union[str, None, OmegaMessage, OmegaMessageSegment]],
            revoke_interval: int = 60
    ) -> asyncio.TimerHandle:
        """发出消息指定时间后自动撤回"""
        bot = await self.get_bot()

        sender = get_msg_sender(target=self.entity)(target_entity=self.entity)
        sent_data = await self.send_multi_msgs(messages=messages)
        revoke_params = sender.parse_revoke_sent_params(content=sent_data)

        loop = asyncio.get_running_loop()
        return loop.call_later(
            revoke_interval,
            lambda: loop.create_task(self._create_revoke_tasks(bot=bot, revoke_params=revoke_params)),
        )


class MatcherInterface(object):
    """Omega 中间件 Matcher 接口"""

    def __init__(self):
        """初始化时判断调用位置及平台类型"""
        try:
            bot = current_bot.get()
            event = current_event.get()
            matcher = current_matcher.get()
        except LookupError as e:
            raise RuntimeError('MatcherInterface 在事件响应器之外实例化') from e

        self.bot: BaseBot = bot
        self.event: BaseEvent = event
        self.matcher: Matcher = matcher

    def get_event_handler(self) -> EventHandler:
        return get_event_handler(self.event)(self.bot, self.event)

    def get_msg_builder(self) -> Type[MessageBuilder]:
        return get_msg_builder(self.bot)

    def get_msg_extractor(self) -> Type[MessageExtractor]:
        return get_msg_extractor(self.bot)

    def extract_event_message(self) -> OmegaMessage:
        message = self.event.get_message()
        extractor = self.get_msg_extractor()
        return extractor(message).message

    async def send(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs):
        """发送消息"""
        builder = self.get_msg_builder()
        send_message = builder(message=message).message
        return await self.matcher.send(message=send_message, **kwargs)

    async def send_at_sender(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs):
        """发送消息并@上条消息发送者"""
        builder = self.get_msg_builder()
        send_message = builder(message=message).message
        return await self.get_event_handler().send_at_sender(message=send_message, **kwargs)

    async def send_reply(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs):
        """发送消息并回复/引用上条消息"""
        builder = self.get_msg_builder()
        send_message = builder(message=message).message
        return await self.get_event_handler().send_reply(message=send_message, **kwargs)

    async def finish(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.finish()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        raise FinishedException

    async def pause(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.pause()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        raise PausedException

    async def reject(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment], **kwargs) -> NoReturn:
        """与 `matcher.reject()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        raise RejectedException

    async def reject_arg(
            self,
            key: str,
            message: Union[str, None, OmegaMessage, OmegaMessageSegment],
            **kwargs
    ) -> NoReturn:
        """与 `matcher.reject_arg()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        await self.matcher.reject_arg(key)

    async def reject_receive(
            self,
            key: str,
            message: Union[str, None, OmegaMessage, OmegaMessageSegment],
            **kwargs
    ) -> NoReturn:
        """与 `matcher.reject_receive()` 作用相同，仅能用在事件响应器中"""
        await self.send(message=message, **kwargs)
        await self.matcher.reject_receive(key)


__all__ = [
    'EntityInterface',
    'MatcherInterface'
]
