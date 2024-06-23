"""
@Author         : Ailitonia
@Date           : 2023/8/12 20:57
@FileName       : qq
@Project        : nonebot2_miya
@Description    : QQ 官方协议支持
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Annotated

from nonebot.log import logger
from nonebot.message import event_preprocessor
from nonebot.params import Depends
from nonebot.adapters.qq.bot import Bot

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from src.database import BotSelfDAL, EntityDAL, get_db_session
from src.service.omega_base.event import BotConnectEvent, BotDisconnectEvent

if TYPE_CHECKING:
    from nonebot.adapters.qq.models import Guild, Channel


@event_preprocessor
async def __qq_bot_connect(
        bot: Bot,
        event: BotConnectEvent,
        session: Annotated[AsyncSession, Depends(get_db_session)]
) -> None:
    """处理 QQ Bot 连接事件"""
    assert str(bot.self_id) == str(event.bot_id), 'Bot self_id not match BotActionEvent bot_id'

    bot_dal = BotSelfDAL(session=session)
    entity_dal = EntityDAL(session=session)
    allowed_entity_type = entity_dal.entity_type

    # 更新 bot 状态
    bot_info = await bot.me()
    info = '||'.join([f'{k}:{v}' for (k, v) in bot_info.model_dump().items()])
    try:
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        await bot_dal.update(id_=exist_bot.id, bot_type=event.bot_type, bot_status=1, bot_info=info)
        logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot status upgraded Success')
    except NoResultFound:
        await bot_dal.add(self_id=bot.self_id, bot_type=event.bot_type, bot_status=1, bot_info=info)
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot status added Success')

    # 更新频道相关信息
    guilds: list["Guild"] = await bot.guilds()
    for guild in guilds:
        guild_query_data = {
            'bot_index_id': exist_bot.id,
            'entity_id': guild.id,
            'entity_type': allowed_entity_type.qq_guild.value,
            'parent_id': guild.owner_id
        }
        guild_info = f'QQ Guild: {guild.id}, {guild.description}'
        try:
            exist_guild = await entity_dal.query_unique(**guild_query_data)
            await entity_dal.update(id_=exist_guild.id, entity_name=guild.name, entity_info=guild_info)
            logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded guild {guild.id} data')
        except NoResultFound:
            guild_query_data.update({'entity_name': guild.name, 'entity_info': guild_info})
            await entity_dal.add(**guild_query_data)
            logger.debug(f'{event.bot_type}: {bot.self_id}, Added guild {guild.id} data')
        except Exception as e:
            logger.error(f'{event.bot_type}: {bot.self_id}, Upgrade guild {guild.id} data failed, {e}')
            continue

    # 更新子频道相关信息
    for guild in guilds:
        channels: list["Channel"] = await bot.get_channels(guild_id=guild.id)
        for channel in channels:
            channel_query_data = {
                'bot_index_id': exist_bot.id,
                'entity_id': channel.id,
                'entity_type': allowed_entity_type.qq_channel.value,
                'parent_id': channel.guild_id
            }
            chan_info = f'QQ Channel: {channel.id}, guild: {channel.guild_id}, parent: {channel.parent_id}'
            try:
                exist_channel = await entity_dal.query_unique(**channel_query_data)
                await entity_dal.update(id_=exist_channel.id, entity_name=channel.name, entity_info=chan_info)
                logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded channel {channel.id} data')
            except NoResultFound:
                channel_query_data.update({'entity_name': channel.name, 'entity_info': chan_info})
                await entity_dal.add(**channel_query_data)
                logger.debug(f'{event.bot_type}: {bot.self_id}, Added channel {channel.id} data')
            except Exception as e:
                logger.error(f'{event.bot_type}: {bot.self_id}, Upgrade channel {channel.id} data failed, {e}')
                continue


@event_preprocessor
async def __qq_bot_disconnect(
        bot: Bot,
        event: BotDisconnectEvent,
        session: Annotated[AsyncSession, Depends(get_db_session)]
) -> None:
    """处理 QQ Bot 断开连接事件"""
    assert str(bot.self_id) == str(event.bot_id), 'Bot self_id not match BotActionEvent bot_id'

    bot_dal = BotSelfDAL(session)
    try:
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        await bot_dal.update(id_=exist_bot.id, bot_type=event.bot_type, bot_status=0)
        logger.opt(colors=True).success(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot status upgraded Success')
    except NoResultFound:
        await bot_dal.add(self_id=bot.self_id, bot_type=event.bot_type, bot_status=0)
        logger.opt(colors=True).success(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot status added Success')


__all__ = []
