"""
@Author         : Ailitonia
@Date           : 2023/7/3 22:25
@FileName       : console
@Project        : nonebot2_miya
@Description    : nonebot-console-adapter support
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.adapters.console import Bot as ConsoleBot
from nonebot.log import logger
from nonebot.message import event_preprocessor
from sqlalchemy.exc import NoResultFound

from src.database import BOT_SELF_DAL
from src.service.omega_base.event import BotConnectEvent, BotDisconnectEvent


@event_preprocessor
async def __console_bot_connect(
        bot: ConsoleBot,
        event: BotConnectEvent,
        bot_dal: BOT_SELF_DAL,
) -> None:
    """处理 nonebot-console Bot 连接事件"""
    if not str(bot.self_id) == str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    try:
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        await bot_dal.update(id_=exist_bot.id, bot_type=event.bot_type, bot_status=1, bot_info='ConsoleBot')
        logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot status upgraded Success')
    except NoResultFound:
        await bot_dal.add(self_id=bot.self_id, bot_type=event.bot_type, bot_status=1, bot_info='ConsoleBot')
        logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot status added Success')


@event_preprocessor
async def __console_bot_disconnect(
        bot: ConsoleBot,
        event: BotDisconnectEvent,
        bot_dal: BOT_SELF_DAL,
) -> None:
    """处理 nonebot-console Bot 断开连接事件"""
    if not str(bot.self_id) == str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    try:
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        await bot_dal.update(id_=exist_bot.id, bot_type=event.bot_type, bot_status=0)
        logger.opt(colors=True).success(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot status upgraded Success')
    except NoResultFound:
        await bot_dal.add(self_id=bot.self_id, bot_type=event.bot_type, bot_status=0)
        logger.opt(colors=True).success(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot status added Success')


__all__ = []
