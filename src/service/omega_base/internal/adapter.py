"""
@Author         : Ailitonia
@Date           : 2026/9/5 20:58
@FileName       : adapter
@Project        : omega-miya
@Description    : 平台 API 及 Entity 方法适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Sequence

from nonebot import get_bot, logger
from nonebot_plugin_alconna.uniseg import At, Image, Target, Receipt, Reply, Segment, UniMessage, get_target

from src.database.internal.entity import EntityType
from ..exception import BotNoFound, TargetNotSupported

if TYPE_CHECKING:
    from nonebot.adapters import Bot as BaseBot, Event as BaseEvent
    from .entity import EntityAcquireType, EntityInitParams


class BaseEntityTarget(abc.ABC):
    """平台 API 适配器, 统一实现平台特有 API 及 Entity 方法适配工具基类"""

    def __init__(self, entity_params: 'EntityInitParams') -> None:
        self.entity_params = entity_params

    @abc.abstractmethod
    def _construct_target(self) -> Target:
        """构造 Entity 的 Target 对象"""
        raise NotImplementedError

    def get_bot(self) -> 'BaseBot':
        try:
            return get_bot(self.entity_params.bot_id)
        except Exception as e:
            raise BotNoFound(bot_self_id=self.entity_params.bot_id) from e

    # ------------------------------------------------------------------ #
    # 发送消息相关方法, 使用 nonebot-plugin-alconn 的 uniseg 通用消息组件实现
    # ------------------------------------------------------------------ #

    async def send_message(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
            *,
            at_sender: bool = False,
            reply_to: bool = False,
            **kwargs,
    ) -> Receipt:
        """主动发送消息"""
        target = self._construct_target()
        bot = self.get_bot()
        uni_message = UniMessage(message)
        return await uni_message.send(target=target, bot=bot, at_sender=at_sender, reply_to=reply_to, **kwargs)

    async def send_message_auto_revoke(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
            revoke_delay: int = 60,
            *,
            at_sender: bool = False,
            reply_to: bool = False,
            **kwargs,
    ) -> None:
        """主动发送消息并在一定时间后撤回"""
        receipt = await self.send_message(message=message, at_sender=at_sender, reply_to=reply_to, **kwargs)
        await receipt.recall(delay=revoke_delay)

    # ------------------------------------------------------------------ #
    # 对象通用方法平台 API 调用适配
    # ------------------------------------------------------------------ #

    @abc.abstractmethod
    async def call_api_get_entity_name(self) -> str:
        """调用平台 API: 获取对象名称/昵称"""
        raise NotImplementedError

    @abc.abstractmethod
    async def call_api_get_entity_profile_image_url(self) -> str:
        """调用平台 API: 获取对象头像/图标"""
        raise NotImplementedError


class BaseEventDepend(abc.ABC):
    """事件对象解析器, 解析平台事件及对象依赖适配基类"""

    def __init__(self, bot: 'BaseBot', event: 'BaseEvent') -> None:
        self.bot = bot
        self.event = event

    def get_target(self) -> Target:
        """获取当前事件的 Target 对象"""
        return get_target(event=self.event, bot=self.bot)

    # ------------------------------------------------------------------ #
    # 事件 Entity 对象依赖提取方法适配
    # ------------------------------------------------------------------ #

    @abc.abstractmethod
    def _extract_event_entity_params(self) -> 'EntityInitParams':
        """根据 Event 提取事件本身对应 Entity 实例化参数"""
        raise NotImplementedError

    @abc.abstractmethod
    def _extract_user_entity_params(self) -> 'EntityInitParams':
        """根据 Event 提取触发事件用户 Entity 实例化参数"""
        raise NotImplementedError

    def extract_entity_params(self, acquire_type: 'EntityAcquireType' = 'event') -> 'EntityInitParams':
        """根据 Event 提取 Entity 实例化参数(对外暴露方法)"""
        match acquire_type:
            case 'event':
                entity_params = self._extract_event_entity_params()
            case 'user':
                entity_params = self._extract_user_entity_params()
            case _:
                raise ValueError(f'Not supported entity acquire_type: {acquire_type!r}')
        return entity_params

    # ------------------------------------------------------------------ #
    # 平台事件消息交互及流程处理方法适配
    # ------------------------------------------------------------------ #

    async def send(
            self,
            message: str | Segment | Sequence[Segment] | UniMessage,
            *,
            at_sender: bool = False,
            reply_to: bool = False,
            **kwargs,
    ) -> Receipt:
        """发送消息"""
        target = self.get_target()
        uni_message = UniMessage(message)
        return await uni_message.send(
            target=target,
            bot=self.bot,
            at_sender=at_sender,
            reply_to=reply_to,
            **kwargs,
        )

    async def send_at_sender(self, message: str | Segment | Sequence[Segment] | UniMessage) -> Receipt:
        """发送消息并 at 事件消息发送者"""
        return await self.send(message=message, at_sender=True)

    async def send_reply(self, message: str | Segment | Sequence[Segment] | UniMessage) -> Receipt:
        """发送消息作为原消息的回复"""
        return await self.send(message=message, reply_to=True)

    @staticmethod
    async def revoke_bot_sent_msg(receipt: Receipt, *, revoke_delay: int = 0) -> None:
        """撤回/删除一条由 Bot 发送的消息"""
        await receipt.recall(delay=revoke_delay)

    # ------------------------------------------------------------------ #
    # 平台事件常用信息提取及处理方法适配
    # ------------------------------------------------------------------ #

    @abc.abstractmethod
    def get_user_nickname(self) -> str:
        """获取事件用户昵称"""
        raise NotImplementedError

    @staticmethod
    def get_msg_mentioned_user_ids(message: UniMessage) -> list[str]:
        """获取消息中被 @ 所有用户对象 ID 列表"""
        return [x.target for x in message[At]]

    @staticmethod
    def get_msg_image_urls(message: UniMessage) -> list[str]:
        """获取当前事件消息中的全部图片链接"""
        return [x.url for x in message.select(Image) if x.url is not None]

    @staticmethod
    def get_reply_message(message: UniMessage) -> Reply | None:
        """获取回复消息"""
        reply_messages = message[Reply]
        return reply_messages[0] if reply_messages else None

    @staticmethod
    @abc.abstractmethod
    def get_reply_msg_image_urls(message: UniMessage) -> list[str]:
        """获取回复消息中的全部图片链接"""
        raise NotImplementedError

    @staticmethod
    def get_reply_msg_plain_text(message: UniMessage) -> str | None:
        """获取回复消息的文本"""
        reply_messages = message[Reply]
        if not reply_messages:
            return None

        if isinstance(reply_message := reply_messages[0].msg, str):
            return reply_message
        elif reply_message is not None:
            return reply_message.extract_plain_text()
        else:
            return None


@dataclass
class _EntityTargetRegister:
    """中间件平台 API 适配器的注册工具, 用于引入平台适配"""

    _map: dict[EntityType, type[BaseEntityTarget]] = field(default_factory=dict)

    def register_target[T: type[BaseEntityTarget]](self, target_name: EntityType) -> Callable[[T], T]:
        """注册中间件平台 API 适配器"""

        def _decorator(target_type: T) -> T:
            if target_name not in EntityType:
                raise TargetNotSupported(target_name=target_name)

            if target_name in self._map.keys():
                logger.error(f'Duplicate entity {target_name!r} for {target_type.__name__!r} has been registered')
                raise ValueError(f'Duplicate entity {target_name!r}')

            self._map[target_name] = target_type
            logger.opt(colors=True).debug(f'<e>{target_type.__name__!r}</e> is registered to {target_name!r}')
            return target_type

        return _decorator

    def get_target(self, target_name: EntityType) -> type[BaseEntityTarget]:
        """提取 Entity 对应的中间件平台 API 适配器"""
        if target_name not in EntityType:
            raise TargetNotSupported(target_name=target_name)

        if target_name not in self._map.keys():
            logger.error(f'Entity {target_name!r} has no registered EntityTarget')
            raise ValueError('EntityTarget not registered')

        return self._map[target_name]


@dataclass
class _EventDependRegister:
    """中间件事件对象解析器的注册工具, 用于引入平台适配"""

    _map: dict[type['BaseEvent'], type[BaseEventDepend]] = field(default_factory=dict)

    def register_depend[Depend_T: type[BaseEventDepend]](
            self,
            target_event_type: type['BaseEvent'],
    ) -> Callable[[Depend_T], Depend_T]:
        """注册对应事件的事件对象解析器"""

        def _decorator(depend: Depend_T) -> Depend_T:
            if target_event_type in self._map.keys():
                logger.error(f'Duplicate event {target_event_type.__name__!r} has been registered')
                raise ValueError(f'Duplicate event {target_event_type.__name__!r}')

            self._map[target_event_type] = depend
            logger.opt(colors=True).debug(f'<e>{depend.__name__!r}</e> is registered to {target_event_type!r}')
            return depend

        return _decorator

    def get_depend(self, target_event: 'BaseEvent') -> type[BaseEventDepend]:
        """从事件中提取对应的事件对象解析器"""
        for event_type in target_event.__class__.mro():
            if event_type in self._map.keys():
                if issubclass(event_type, BaseEvent):
                    target_event_type = event_type
                    break
                else:
                    continue
        else:
            logger.error(f'Event {target_event.__class__.__name__!r} has no registered EventDepend')
            raise ValueError('Event not supported')

        return self._map[target_event_type]


ENTITY_TARGET_REGISTER: _EntityTargetRegister = _EntityTargetRegister()
"""全局中间件平台 API 适配器注册工具"""

EVENT_DEPEND_REGISTER: _EventDependRegister = _EventDependRegister()
"""全局中间件事件对象解析器的注册工具"""


__all__ = [
    'BaseEntityTarget',
    'ENTITY_TARGET_REGISTER',
    'EVENT_DEPEND_REGISTER',
]
