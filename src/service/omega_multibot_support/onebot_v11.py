"""
@Author         : Ailitonia
@Date           : 2022/12/03 21:45
@FileName       : onebot_v11.py
@Project        : nonebot2_miya 
@Description    : OneBot V11 support
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor, run_preprocessor
from nonebot.params import Depends
from nonebot.permission import Permission
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event, MessageEvent, NoticeEvent, RequestEvent

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from src.database import BotSelfDAL, EntityDAL
from src.database.utils import get_db_session
from src.service.omega_event import BotConnectEvent, BotDisconnectEvent
from src.service.onebot_api import Gocqhttp


class __OriginalResponding:
    """检查当前事件是否属于由最初响应的 Bot 发起的指定会话

    参数:
        sessions: 会话 ID 元组
        original: 最初响应的 Bot
        perm: 需同时满足的权限
    """

    __slots__ = ('sessions', 'original', 'perm')

    def __init__(self, sessions: tuple[str, ...], original: str | None = None, perm: Permission | None = None) -> None:
        self.sessions = sessions
        self.original = original
        self.perm = perm

    async def __call__(self, bot: Bot, event: Event) -> bool:
        return bool(
            event.get_session_id() in self.sessions
            and (self.original is None or bot.self_id == self.original)
            and (self.perm is None or await self.perm(bot, event))
        )


async def __original_responding_permission_updater(bot: Bot, event: Event, matcher: Matcher) -> Permission:
    """匹配当前事件是否属于由最初响应的 Bot 发起的指定会话"""
    return Permission(
        __OriginalResponding(
            sessions=(event.get_session_id(),),
            original=bot.self_id,
            perm=matcher.permission
        )
    )


@run_preprocessor
async def __obv11_unique_bot_responding_rule_updater(event: Event, matcher: Matcher):
    # 对于多协议端同时接入, 需要使用 permission_updater 限制 bot 的 self_id 避免响应混乱
    if isinstance(event, (MessageEvent, NoticeEvent, RequestEvent)) and not matcher.temp:
        if not matcher.__class__._default_permission_updater:
            matcher.permission_updater(__original_responding_permission_updater)


@event_preprocessor
async def __obv11_bot_connect(bot: Bot, event: BotConnectEvent, session: AsyncSession = Depends(get_db_session)):
    """处理 Onebot V11 连接事件"""
    assert str(bot.self_id) == str(event.bot_id), 'Bot self_id not match BotActionEvent bot_id'

    bot_api = Gocqhttp(bot=bot)
    bot_dal = BotSelfDAL(session=session)
    entity_dal = EntityDAL(session=session)
    entity_type = entity_dal.entity_type

    # 更新 bot 状态
    bot_version_info = await bot_api.get_version_info()
    info = '||'.join([f'{k}:{v}' for (k, v) in bot_version_info.dict().items()])
    try:
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        await bot_dal.update(id_=exist_bot.id, bot_type=event.bot_type, bot_status=1, bot_info=info)
        logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot status upgraded Success')
    except NoResultFound:
        await bot_dal.add(self_id=bot.self_id, bot_type=event.bot_type, bot_status=1, bot_info=info)
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot status added Success')

    # 更新群组相关信息
    groups = await bot_api.get_group_list()
    for group in groups:
        group_query_data = {
            'bot_index_id': exist_bot.id,
            'entity_id': group.group_id,
            'entity_type': entity_type.qq_group.value,
            'parent_id': bot.self_id
        }
        try:
            exist_group = await entity_dal.query_unique(**group_query_data)
            await entity_dal.update(id_=exist_group.id, entity_name=group.group_name, entity_info=group.group_memo)
            logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded group {group.group_id} data')
        except NoResultFound:
            group_query_data.update({'entity_name': group.group_name, 'entity_info': group.group_memo})
            await entity_dal.add(**group_query_data)
            logger.debug(f'{event.bot_type}: {bot.self_id}, Added group {group.group_id} data')
        except Exception as e:
            logger.error(f'{event.bot_type}: {bot.self_id}, Upgraded group {group.group_id} data failed, {e}')
            continue

    # 更新用户相关信息
    friends = await bot_api.get_friend_list()
    for user in friends:
        user_query_data = {
            'bot_index_id': exist_bot.id,
            'entity_id': user.user_id,
            'entity_type': entity_type.qq_user.value,
            'parent_id': bot.self_id
        }
        try:
            exist_user = await entity_dal.query_unique(**user_query_data)
            await entity_dal.update(id_=exist_user.id, entity_name=user.nickname, entity_info=user.remark)
            logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded friend {user.user_id} data')
        except NoResultFound:
            user_query_data.update({'entity_name': user.nickname, 'entity_info': user.remark})
            await entity_dal.add(**user_query_data)
            logger.debug(f'{event.bot_type}: {bot.self_id}, Added friend {user.user_id} data')
        except Exception as e:
            logger.error(f'{event.bot_type}: {bot.self_id}, Upgraded friend {user.user_id} data failed, {e}')
            continue

    # 更新频道相关信息
    guild_profile = await bot_api.get_guild_service_profile()
    guilds = await bot_api.get_guild_list()
    for guild in guilds:
        guild_query_data = {
            'bot_index_id': exist_bot.id,
            'entity_id': guild.guild_id,
            'entity_type': entity_type.qq_guild.value,
            'parent_id': guild_profile.tiny_id
        }
        guild_info = f'display_id: {guild.guild_display_id}'
        try:
            exist_guild = await entity_dal.query_unique(**guild_query_data)
            await entity_dal.update(id_=exist_guild.id, entity_name=guild.guild_name, entity_info=guild_info)
            logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded guild {guild.guild_id} data')
        except NoResultFound:
            guild_query_data.update({'entity_name': guild.guild_name, 'entity_info': guild_info})
            await entity_dal.add(**guild_query_data)
            logger.debug(f'{event.bot_type}: {bot.self_id}, Added guild {guild.guild_id} data')
        except Exception as e:
            logger.error(f'{event.bot_type}: {bot.self_id}, Upgraded guild {guild.guild_id} data failed, {e}')
            continue

    # 更新子频道相关信息
    for guild in guilds:
        channels = await bot_api.get_guild_channel_list(guild_id=guild.guild_id)
        for channel in channels:
            channel_query_data = {
                'bot_index_id': exist_bot.id,
                'entity_id': channel.channel_id,
                'entity_type': entity_type.qq_guild_channel.value,
                'parent_id': channel.owner_guild_id
            }
            chan_info = f'owner_guild: {channel.owner_guild_id}/{guild.guild_name}'
            try:
                exist_channel = await entity_dal.query_unique(**channel_query_data)
                await entity_dal.update(id_=exist_channel.id, entity_name=channel.channel_name, entity_info=chan_info)
                logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded channel {channel.channel_id} data')
            except NoResultFound:
                channel_query_data.update({'entity_name': channel.channel_name, 'entity_info': chan_info})
                await entity_dal.add(**channel_query_data)
                logger.debug(f'{event.bot_type}: {bot.self_id}, Added channel {channel.channel_id} data')
            except Exception as e:
                logger.error(f'{event.bot_type}: {bot.self_id}, Upgraded channel {channel.channel_id} data failed, {e}')
                continue

    logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, All entity data upgraded Success')


@event_preprocessor
async def __obv11_bot_disconnect(bot: Bot, event: BotDisconnectEvent, session: AsyncSession = Depends(get_db_session)):
    """处理 Onebot V11 断开连接事件"""
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
