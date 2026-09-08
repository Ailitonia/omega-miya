"""
@Author         : Ailitonia
@Date           : 2023/7/3 22:31
@FileName       : console
@Project        : nonebot2_miya
@Description    : nonebot-console 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.adapters.console import Bot as ConsoleBot
from nonebot.adapters.console import Event as ConsoleEvent
from nonebot.log import logger
from nonebot.message import event_preprocessor
from nonebot_plugin_alconna.uniseg import SupportScope, Target
from nonechat.model import DIRECT

from src.database.internal.bot import BotSelfDAL, BotStatus
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
async def __console_bot_connect(bot: ConsoleBot, event: BotConnectEvent) -> None:
    """处理 nonebot-console Bot 连接事件"""
    if str(bot.self_id) != str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    async with BotSelfDAL.create() as bot_dal:
        await bot_dal.add_update_exist(event.bot_type, bot.self_id, BotStatus.ENABLED, bot_info='Bot Online')

    logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot 状态已更新')


@event_preprocessor
async def __console_bot_disconnect(bot: ConsoleBot, event: BotDisconnectEvent) -> None:
    """处理 nonebot-console Bot 断开连接事件"""
    if not str(bot.self_id) == str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    async with BotSelfDAL.create() as bot_dal:
        await bot_dal.add_update_exist(event.bot_type, bot.self_id, BotStatus.DISABLED, bot_info='Bot Offline')

    logger.opt(colors=True).warning(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot 状态已更新')


@ENTITY_TARGET_REGISTER.register_target(EntityType.CONSOLE_USER)
class ConsoleUserEntityTarget(BaseEntityTarget[ConsoleBot]):

    def _construct_target(self) -> Target:
        return Target(
            self.entity_params.entity_id,
            private=True,
            adapter=self.entity_params.bot_type,
            self_id=self.entity_params.bot_id,
            scope=SupportScope.console,
        )

    async def call_api_get_entity_name(self) -> str:
        return self.entity_params.entity_name or 'ConsoleUser'

    async def call_api_get_entity_profile_image_url(self) -> str:
        return ''


@ENTITY_TARGET_REGISTER.register_target(EntityType.CONSOLE_CHANNEL)
class ConsoleChannelEntityTarget(BaseEntityTarget[ConsoleBot]):

    def _construct_target(self) -> Target:
        return Target(
            self.entity_params.entity_id,
            private=False,
            adapter=self.entity_params.bot_type,
            self_id=self.entity_params.bot_id,
            scope=SupportScope.console,
        )

    async def call_api_get_entity_name(self) -> str:
        return self.entity_params.entity_name or 'ConsoleChannel'

    async def call_api_get_entity_profile_image_url(self) -> str:
        return ''


@EVENT_DEPEND_REGISTER.register_depend(ConsoleEvent)
class ConsoleEventDepend(BaseEventDepend[ConsoleBot, ConsoleEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.CONSOLE_CHANNEL,
            'entity_id': self.event.channel.id,
            'entity_name': self.event.channel.name,
            'entity_extra': {},
            'entity_info': self.event.channel.description,
        })

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        if self.event.channel.id == DIRECT.id or self.event.channel.id.startswith("private:"):
            # If the event is a direct message, we can use the user ID as the target ID
            return EntityInitParams.model_validate({
                'bot_type': self.bot.adapter.get_name(),
                'bot_id': self.bot.self_id,
                'entity_type': EntityType.CONSOLE_USER,
                'entity_id': self.event.user.id,
                'entity_name': self.event.user.nickname,
                'entity_extra': {},
                'entity_info': self.event.user.avatar,
            })
        else:
            return EntityInitParams.model_validate({
                'bot_type': self.bot.adapter.get_name(),
                'bot_id': self.bot.self_id,
                'entity_type': EntityType.CONSOLE_CHANNEL,
                'entity_id': self.event.channel.id,
                'entity_name': self.event.channel.name,
                'entity_extra': {},
                'entity_info': self.event.channel.description,
            })

    def get_user_nickname(self) -> str:
        return self.event.user.nickname

    def get_reply_msg_image_urls(self) -> list[str]:
        return []


__all__ = []
