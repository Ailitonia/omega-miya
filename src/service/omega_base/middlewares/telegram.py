"""
@Author         : Ailitonia
@Date           : 2023/6/10 4:19
@FileName       : telegram
@Project        : nonebot2_miya
@Description    : Telegram 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from urllib.parse import quote

from nonebot.adapters.telegram import Bot as TelegramBot
from nonebot.adapters.telegram import Event as TelegramEvent
from nonebot.adapters.telegram.event import ChannelPostEvent as TelegramChannelPostEvent
from nonebot.adapters.telegram.event import GroupMessageEvent as TelegramGroupMessageEvent
from nonebot.adapters.telegram.event import MessageEvent as TelegramMessageEvent
from nonebot.adapters.telegram.event import PrivateMessageEvent as TelegramPrivateMessageEvent
from nonebot.log import logger
from nonebot.message import event_preprocessor
from nonebot_plugin_alconna.uniseg import Reply, SupportScope, Target

from src.database.internal.bot import BotSelfDAL
from src.database.internal.entity import EntityType
from ..internal import (
    ENTITY_TARGET_REGISTER,
    EVENT_DEPEND_REGISTER,
    BaseEntityTarget,
    BaseEventDepend,
    BotConnectEvent,
    BotDisconnectEvent,
    EntityInitParams,
)


@event_preprocessor
async def __telegram_bot_connect(bot: TelegramBot, event: BotConnectEvent) -> None:
    """处理 Telegram Bot 连接事件"""
    if str(bot.self_id) != str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    # 更新 bot 状态
    bot_info = await bot.get_me()
    info = f'{bot_info.id}-{bot_info.first_name}@{bot_info.username}'
    async with BotSelfDAL.create() as bot_dal:
        await bot_dal.add_update_exist(event.bot_type, bot.self_id, bot_status=1, bot_info=info)

    logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot 状态已更新')


@event_preprocessor
async def __telegram_bot_disconnect(bot: TelegramBot, event: BotDisconnectEvent) -> None:
    """处理 Telegram Bot 断开连接事件"""
    if not str(bot.self_id) == str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    async with BotSelfDAL.create() as bot_dal:
        await bot_dal.add_update_exist(event.bot_type, bot.self_id, bot_status=1, bot_info='Bot Offline')

    logger.opt(colors=True).warning(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot 状态已更新')


class BaseTelegramEntityTarget(BaseEntityTarget[TelegramBot]):

    def _construct_target(self) -> Target:
        return Target(
            self.entity_params.entity_id,
            private=self.entity_params.entity_extra['is_private'],
            adapter=self.entity_params.bot_type,
            self_id=self.entity_params.bot_id,
            scope=SupportScope.telegram,
            extra={'message_thread_id': self.entity_params.entity_extra.get('message_thread_id', None)},
        )

    async def call_api_get_entity_name(self) -> str:
        bot = self.get_bot()
        chat_data = await bot.call_api('get_chat', chat_id=self.entity_params.entity_id)

        title = getattr(chat_data, 'title', None)
        first_name = getattr(chat_data, 'first_name', None)

        return str(title) if title is not None else str(first_name) if first_name is not None else ''

    async def call_api_get_entity_profile_image_url(self) -> str:
        bot = self.get_bot()
        chat_data = await bot.call_api('get_chat', chat_id=self.entity_params.entity_id)

        if (photo := getattr(chat_data, 'photo', None)) is None:
            raise ValueError('chat has no photo')

        file = await bot.call_api('get_file', file_id=getattr(photo, 'big_file_id', ''))
        return f'https://api.telegram.org/file/bot{quote(bot.bot_config.token)}/{quote(file.file_path)}'


@ENTITY_TARGET_REGISTER.register_target(EntityType.TELEGRAM_USER)
class TelegramUserEntityTarget(BaseTelegramEntityTarget):
    ...


@ENTITY_TARGET_REGISTER.register_target(EntityType.TELEGRAM_GROUP)
class TelegramGroupEntityTarget(BaseTelegramEntityTarget):
    ...


@ENTITY_TARGET_REGISTER.register_target(EntityType.TELEGRAM_CHANNEL)
class TelegramChannelEntityTarget(BaseTelegramEntityTarget):
    ...


@EVENT_DEPEND_REGISTER.register_depend(TelegramEvent)
class TelegramEventDepend[Event_T: TelegramEvent](BaseEventDepend[TelegramBot, Event_T]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.TELEGRAM_USER,
            'entity_id': self.bot.self_id,
            'entity_name': 'Telegram Bot Self',
            'entity_extra': {},
            'entity_info': None,
        })

    def get_user_nickname(self) -> str:
        # 基类事件, 不予实现
        raise NotImplementedError

    def get_reply_msg_image_urls(self) -> list[str]:
        # 基类事件, 不予实现
        raise NotImplementedError


@EVENT_DEPEND_REGISTER.register_depend(TelegramMessageEvent)
class TelegramMessageEventDepend[Event_T: TelegramMessageEvent](TelegramEventDepend[Event_T]):

    def get_user_nickname(self) -> str:
        return self.event.chat.username if self.event.chat.username else ''

    def get_reply_msg_image_urls(self) -> list[str]:
        reply_messages = self.get_uni_message()[Reply]
        image_urls = [
            msg_seg.data.get('origin_url', None) or msg_seg.data.get('file', None)
            for msg_seg in reply_messages
            if msg_seg.type == 'photo'
        ]

        if image_urls:
            return [str(url) for url in image_urls if url is not None]
        else:
            return []


@EVENT_DEPEND_REGISTER.register_depend(TelegramGroupMessageEvent)
class TelegramGroupMessageEventDepend(TelegramMessageEventDepend[TelegramGroupMessageEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.TELEGRAM_GROUP,
            'entity_id': str(self.event.chat.id),
            'entity_name': self.event.chat.title,
            'entity_extra': {
                'is_private': self.event.chat.type == 'private',
                'message_thread_id': getattr(self.event, 'message_thread_id', None),
            },
            'entity_info': self.event.chat.type,
        })

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.TELEGRAM_USER,
            'entity_id': str(self.event.from_.id),
            'entity_name': self.event.from_.first_name,
            'entity_extra': {
                'is_private': self.event.chat.type == 'private',
                'message_thread_id': getattr(self.event, 'message_thread_id', None),
            },
            'entity_info': f'{self.event.from_.first_name}@{self.event.from_.username}',
        })

    def get_user_nickname(self) -> str:
        return self.event.from_.first_name


@EVENT_DEPEND_REGISTER.register_depend(TelegramPrivateMessageEvent)
class TelegramPrivateMessageEventDepend(TelegramMessageEventDepend[TelegramPrivateMessageEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.TELEGRAM_USER,
            'entity_id': str(self.event.from_.id),
            'entity_name': self.event.from_.first_name,
            'entity_extra': {
                'is_private': self.event.chat.type == 'private',
                'message_thread_id': getattr(self.event, 'message_thread_id', None),
            },
            'entity_info': f'{self.event.from_.first_name}@{self.event.from_.username}',
        })

    def get_user_nickname(self) -> str:
        return self.event.from_.first_name


@EVENT_DEPEND_REGISTER.register_depend(TelegramChannelPostEvent)
class TelegramChannelPostEventDepend(TelegramMessageEventDepend[TelegramChannelPostEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.TELEGRAM_CHANNEL,
            'entity_id': str(self.event.chat.id),
            'entity_name': self.event.chat.title,
            'entity_extra': {
                'is_private': self.event.chat.type == 'private',
                'message_thread_id': getattr(self.event, 'message_thread_id', None),
            },
            'entity_info': self.event.chat.type,
        })

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return self._extract_event_entity_params()


__all__ = []
