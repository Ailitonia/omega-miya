"""
@Author         : Ailitonia
@Date           : 2022/12/03 21:45
@FileName       : onebot_v11.py
@Project        : nonebot2_miya
@Description    : OneBot V11(go-cqhttp) support
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event
from nonebot.exception import AdapterException, IgnoredException
from nonebot.log import logger
from nonebot.message import event_preprocessor, run_preprocessor
from nonebot.params import Depends
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from src.compat import parse_obj_as
from src.database import BotSelfDAL, EntityDAL, get_db_session
from src.service.omega_base.event import BotConnectEvent, BotDisconnectEvent


@run_preprocessor
async def __obv11_unique_bot_responding_rule_updater(bot: Bot, event: Event):
    # 对于多协议端同时接入, 需匹配event.self_id与bot.self_id, 以保证会话不会被跨bot, 跨群, 跨用户触发
    event_self_id = str(event.self_id)
    if bot.self_id != event_self_id:
        logger.debug(f'Bot {bot.self_id} ignored event which not match self_id {event_self_id}')
        raise IgnoredException(f'Bot {bot.self_id} ignored event which not match self_id {event_self_id}')


class BaseOneBotModel(BaseModel):
    """OneBot v11 基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class FriendInfo(BaseOneBotModel):
    """好友信息

    - user_id: QQ 号
    - nickname: QQ 昵称
    - remark: 备注名
    """
    user_id: str
    nickname: str
    remark: str


class GroupInfo(BaseOneBotModel):
    """群信息

    - group_id, 群号
    - group_name, 群名称
    - group_memo, 群备注
    - group_create_time, 群创建时间
    - group_level, 群等级
    - member_count, 成员数
    - max_member_count, 最大成员数（群容量）
    """
    group_id: str
    group_name: str
    member_count: int
    max_member_count: int
    group_memo: str | None = ''
    group_create_time: int = 0
    group_level: int = 0


class GuildServiceProfile(BaseOneBotModel):
    """API /get_guild_service_profile 频道系统内BOT的资料 返回值

    - nickname: 昵称
    - tiny_id: 自身的ID
    - avatar_url: 头像链接
    """
    nickname: str
    tiny_id: str
    avatar_url: AnyHttpUrl


class GuildInfo(BaseOneBotModel):
    """API /get_guild_list 频道列表
    正常情况下响应 GuildInfo 数组, 未加入任何频道响应 null

    - guild_id, 频道ID
    - guild_name, 频道名称
    - guild_display_id, 频道显示ID, 公测后可能作为搜索ID使用
    """
    guild_id: str
    guild_name: str
    guild_display_id: int


class ChannelInfo(BaseOneBotModel):
    """API /get_guild_channel_list 子频道信息

    - owner_guild_id: 所属频道ID
    - channel_id: 子频道ID
    - channel_type: 子频道类型
    - channel_name: 子频道名称
    - create_time: 创建时间
    - creator_tiny_id: 创建者ID
    - talk_permission: 发言权限类型
    - visible_type: 可视性类型
    - current_slow_mode: 当前启用的慢速模式Key
    - slow_modes: 频道内可用慢速模式类型列表

    已知子频道类型列表
        - 1: 文字频道
        - 2: 语音频道
        - 5: 直播频道
        - 7: 主题频道

    """

    class _SlowModeInfo(BaseOneBotModel):
        """慢速模式信息

        - slow_mode_key: 慢速模式Key
        - slow_mode_text: 慢速模式说明
        - speak_frequency: 周期内发言频率限制
        - slow_mode_circle: 单位周期时间, 单位秒
        """
        slow_mode_key: int
        slow_mode_text: str
        speak_frequency: int
        slow_mode_circle: int

    owner_guild_id: str
    channel_id: str
    channel_type: int
    channel_name: str
    create_time: int
    creator_tiny_id: str
    talk_permission: int
    visible_type: int
    current_slow_mode: int
    slow_modes: list[_SlowModeInfo]


class VersionInfo(BaseOneBotModel):
    """go-cqhttp 版本信息

    - app_name: 应用标识, 如 mirai-native
    - app_version: 应用版本, 如 1.2.3
    - protocol_version: OneBot 标准版本, 如 v11
    - app_full_name: 应用完整名称
    - coolq_edition: 原 Coolq 版本, 固定值
    - coolq_directory: 原 Coolq 路径, 固定值
    - go-cqhttp: 是否为 go-cqhttp, 固定值
    - protocol_name: 当前 go-cqhttp 登陆使用协议类型
    - plugin_version: 固定值
    - plugin_build_number: 固定值
    - plugin_build_configuration: 固定值
    - runtime_version
    - runtime_os
    - version: 应用版本, 如 v0.9.40-fix4
    """
    app_name: str
    app_version: str
    protocol_version: str
    app_full_name: str | None = None
    coolq_edition: str | None = None
    coolq_directory: str | None = None
    is_go_cqhttp: bool = Field(default=False, alias='go-cqhttp')
    protocol: int | None = Field(None, alias='protocol_name')
    plugin_version: str | None = None
    plugin_build_number: int | None = None
    plugin_build_configuration: str | None = None
    runtime_version: str | None = None
    runtime_os: str | None = None
    version: str | None = None

    model_config = ConfigDict(extra='ignore')


@event_preprocessor
async def __obv11_bot_connect(
        bot: Bot,
        event: BotConnectEvent,
        session: Annotated[AsyncSession, Depends(get_db_session)]
) -> None:
    """处理 OneBot V11(go-cqhttp) Bot 连接事件"""
    if not str(bot.self_id) == str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    bot_dal = BotSelfDAL(session=session)
    entity_dal = EntityDAL(session=session)
    allowed_entity_type = entity_dal.entity_type

    # 更新 bot 状态
    bot_version_info = VersionInfo.model_validate(await bot.get_version_info())
    info = '||'.join([f'{k}:{v}' for (k, v) in bot_version_info.model_dump().items()])
    try:
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        await bot_dal.update(id_=exist_bot.id, bot_type=event.bot_type, bot_status=1, bot_info=info)
        logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot status upgraded Success')
    except NoResultFound:
        await bot_dal.add(self_id=bot.self_id, bot_type=event.bot_type, bot_status=1, bot_info=info)
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot status added Success')

    # 更新群组相关信息
    groups = parse_obj_as(list[GroupInfo], await bot.get_group_list())
    for group in groups:
        group_query_data = {
            'bot_index_id': exist_bot.id,
            'entity_id': group.group_id,
            'entity_type': allowed_entity_type.onebot_v11_group.value,
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
            logger.error(f'{event.bot_type}: {bot.self_id}, Upgrade group {group.group_id} data failed, {e}')
            continue

    # 更新用户相关信息
    friends = parse_obj_as(list[FriendInfo], await bot.get_friend_list())
    for user in friends:
        user_query_data = {
            'bot_index_id': exist_bot.id,
            'entity_id': user.user_id,
            'entity_type': allowed_entity_type.onebot_v11_user.value,
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
            logger.error(f'{event.bot_type}: {bot.self_id}, Upgrade friend {user.user_id} data failed, {e}')
            continue

    try:
        guild_profile = GuildServiceProfile.model_validate(await bot.get_guild_service_profile())
        guilds = parse_obj_as(list[GuildInfo], await bot.get_guild_list())

        # 更新频道相关信息
        for guild in guilds:
            guild_query_data = {
                'bot_index_id': exist_bot.id,
                'entity_id': guild.guild_id,
                'entity_type': allowed_entity_type.onebot_v11_guild.value,
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
                logger.error(f'{event.bot_type}: {bot.self_id}, Upgrade guild {guild.guild_id} data failed, {e}')
                continue

        # 更新子频道相关信息
        for guild in guilds:
            channels = parse_obj_as(list[ChannelInfo], await bot.get_guild_channel_list(guild_id=guild.guild_id))
            for channel in channels:
                channel_query_data = {
                    'bot_index_id': exist_bot.id,
                    'entity_id': channel.channel_id,
                    'entity_type': allowed_entity_type.onebot_v11_guild_channel.value,
                    'parent_id': channel.owner_guild_id
                }
                chan_info = f'owner_guild: {channel.owner_guild_id}/{guild.guild_name}'
                try:
                    exist_channel = await entity_dal.query_unique(**channel_query_data)
                    await entity_dal.update(id_=exist_channel.id, entity_name=channel.channel_name,
                                            entity_info=chan_info)
                    logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded channel {channel.channel_id} data')
                except NoResultFound:
                    channel_query_data.update({'entity_name': channel.channel_name, 'entity_info': chan_info})
                    await entity_dal.add(**channel_query_data)
                    logger.debug(f'{event.bot_type}: {bot.self_id}, Added channel {channel.channel_id} data')
                except Exception as e:
                    logger.error(
                        f'{event.bot_type}: {bot.self_id}, Upgrade channel {channel.channel_id} data failed, {e}')
                    continue

    except AdapterException as e:
        logger.warning(
            f'{event.bot_type}: {bot.self_id}, Upgrade guild/channel data failed, '
            f'the OneBot V11 client does not support the guild API, {e}'
        )
    except ValidationError as e:
        logger.warning(
            f'{event.bot_type}: {bot.self_id}, Upgrade guild/channel data failed, '
            f'the OneBot V11 client guild API returns data out of expected, {e}'
        )
    except Exception as e:
        logger.error(f'{event.bot_type}: {bot.self_id}, Upgrade guild/channel data failed, {e}')

    logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, All entity data upgraded Success')


@event_preprocessor
async def __obv11_bot_disconnect(
        bot: Bot,
        event: BotDisconnectEvent,
        session: Annotated[AsyncSession, Depends(get_db_session)]
) -> None:
    """处理 OneBot V11(go-cqhttp) Bot 断开连接事件"""
    if not str(bot.self_id) == str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    bot_dal = BotSelfDAL(session)
    try:
        exist_bot = await bot_dal.query_unique(self_id=bot.self_id)
        await bot_dal.update(id_=exist_bot.id, bot_type=event.bot_type, bot_status=0)
        logger.opt(colors=True).success(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot status upgraded Success')
    except NoResultFound:
        await bot_dal.add(self_id=bot.self_id, bot_type=event.bot_type, bot_status=0)
        logger.opt(colors=True).success(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot status added Success')


__all__ = []
