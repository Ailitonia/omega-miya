"""
@Author         : Ailitonia
@Date           : 2023/6/10 1:32
@FileName       : onebot_v11
@Project        : nonebot2_miya
@Description    : OneBot V11 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.adapters.onebot.v11 import Event as OneBotV11Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent as OneBotV11GroupMessageEvent
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent
from nonebot.adapters.onebot.v11 import NotifyEvent as OneBotV11NotifyEvent
from nonebot.adapters.onebot.v11 import PokeNotifyEvent as OneBotV11PokeNotifyEvent
from nonebot.adapters.onebot.v11 import PrivateMessageEvent as OneBotV11PrivateMessageEvent
from nonebot.exception import IgnoredException
from nonebot.log import logger
from nonebot.message import event_preprocessor, run_preprocessor
from nonebot_plugin_alconna.uniseg import Reply, SupportScope, Target, UniMessage
from pydantic import BaseModel, ConfigDict, Field

from src.compat import parse_obj_as
from src.database.internal.bot import BotSelfDAL
from src.database.internal.entity import EntityDAL, EntityType
from ..internal import (
    ENTITY_TARGET_REGISTER,
    EVENT_DEPEND_REGISTER,
    BaseEntityTarget,
    BaseEventDepend,
    BotConnectEvent,
    BotDisconnectEvent,
    EntityInitParams,
)


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


class VersionInfo(BaseOneBotModel):
    """客户端版本信息

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


@run_preprocessor
async def __obv11_unique_bot_responding_rule_updater(bot: OneBotV11Bot, event: OneBotV11Event):
    # 对于多协议端同时接入, 需匹配event.self_id与bot.self_id, 以保证会话不会被跨bot, 跨群, 跨用户触发
    event_self_id = str(event.self_id)
    if bot.self_id != event_self_id:
        logger.debug(f'Bot {bot.self_id} ignored event which not match self_id {event_self_id}')
        raise IgnoredException(f'Bot {bot.self_id} ignored event which not match self_id {event_self_id}')


@event_preprocessor
async def __obv11_bot_connect(bot: OneBotV11Bot, event: BotConnectEvent) -> None:
    """处理 OneBot V11 Bot 连接事件"""
    if str(bot.self_id) != str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    # 更新 bot 状态
    version_info = VersionInfo.model_validate(await bot.get_version_info())
    info = f'{version_info.app_name}-{version_info.app_version}-{version_info.protocol_version}'
    async with BotSelfDAL.create() as bot_dal:
        await bot_dal.add_update_exist(event.bot_type, bot.self_id, bot_status=1, bot_info=info)

    # 更新群组相关信息
    groups = parse_obj_as(list[GroupInfo], await bot.get_group_list())
    async with EntityDAL.create() as entity_dal:
        for group in groups:
            group_query_data = {
                'bot_type': bot.adapter.get_name(),
                'bot_self_id': bot.self_id,
                'entity_type': EntityType.ONEBOT_V11_GROUP,
                'entity_id': group.group_id,
                'entity_name': group.group_name,
                'entity_extra': group.model_dump(),
                'entity_info': group.group_memo,
            }
            try:
                await entity_dal.add_update_exist(**group_query_data)
                logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded group {group.group_id} data')
            except Exception as e:
                logger.error(f'{event.bot_type}: {bot.self_id}, Upgrade group {group.group_id} data failed, {e}')
                continue

    # 更新用户相关信息
    friends = parse_obj_as(list[FriendInfo], await bot.get_friend_list())
    async with EntityDAL.create() as entity_dal:
        for user in friends:
            user_query_data = {
                'bot_type': bot.adapter.get_name(),
                'bot_self_id': bot.self_id,
                'entity_type': EntityType.ONEBOT_V11_USER,
                'entity_id': user.user_id,
                'entity_name': user.nickname,
                'entity_extra': user.model_dump(),
                'entity_info': user.remark,
            }
            try:
                await entity_dal.add_update_exist(**user_query_data)
                logger.debug(f'{event.bot_type}: {bot.self_id}, Upgraded friend {user.user_id} data')
            except Exception as e:
                logger.error(f'{event.bot_type}: {bot.self_id}, Upgrade friend {user.user_id} data failed, {e}')
                continue

    logger.opt(colors=True).success(f'{event.bot_type}: <lg>{bot.self_id} 已连接</lg>, Bot 状态和用户群组信息已更新')


@event_preprocessor
async def __obv11_bot_disconnect(bot: OneBotV11Bot, event: BotDisconnectEvent) -> None:
    """处理 OneBot V11 Bot 断开连接事件"""
    if str(bot.self_id) != str(event.bot_id):
        raise ValueError('Bot self_id not match BotActionEvent bot_id')

    async with BotSelfDAL.create() as bot_dal:
        await bot_dal.add_update_exist(event.bot_type, bot.self_id, bot_status=1, bot_info='Bot Offline')

    logger.opt(colors=True).warning(f'{event.bot_type}: <ly>{bot.self_id} 已离线</ly>, Bot 状态已更新')


@ENTITY_TARGET_REGISTER.register_target(EntityType.ONEBOT_V11_USER)
class OneBotV11UserEntityTarget(BaseEntityTarget[OneBotV11Bot]):

    def _construct_target(self) -> Target:
        return Target(
            self.entity_params.entity_id,
            private=True,
            adapter=self.entity_params.bot_type,
            self_id=self.entity_params.bot_id,
            scope=SupportScope.qq_client,
        )

    async def call_api_get_entity_name(self) -> str:
        bot = self.get_bot()
        user_data = await bot.call_api('get_stranger_info', user_id=self.entity_params.entity_id)
        entity_name = user_data.get('nickname', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(
            self,
            head_img_size: Literal[1, 2, 3, 4, 5, 40, 100] = 5,
            url_version: int = 0,
    ) -> str:
        # head_img_size: 1: 40×40px, 2: 40×40px, 3: 100×100px, 4: 140×140px, 5: 640×640px, 40: 40×40px, 100: 100×100px

        match url_version:
            case 2:
                url = f'https://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={self.entity_params.entity_id}'
            case 1:
                url = f'https://q2.qlogo.cn/headimg_dl?dst_uin={self.entity_params.entity_id}&spec={head_img_size}'
            case 0 | _:
                url = f'https://q1.qlogo.cn/g?b=qq&nk={self.entity_params.entity_id}&s={head_img_size}'
        return url


@ENTITY_TARGET_REGISTER.register_target(EntityType.ONEBOT_V11_GROUP)
class OneBotV11GroupEntityTarget(BaseEntityTarget[OneBotV11Bot]):

    def _construct_target(self) -> Target:
        return Target(
            self.entity_params.entity_id,
            private=False,
            adapter=self.entity_params.bot_type,
            self_id=self.entity_params.bot_id,
            scope=SupportScope.qq_client,
        )

    async def call_api_get_entity_name(self) -> str:
        bot = self.get_bot()
        group_data = await bot.call_api('get_group_info', group_id=self.entity_params.entity_id)
        entity_name = group_data.get('group_name', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(
            self,
            head_img_size: Literal[40, 100, 140, 640] = 640,
    ) -> str:
        # head_img_size: 40: 40×40px, 100: 100×100px, 140: 140×140px, 640: 640×640px

        return f'https://p.qlogo.cn/gh/{self.entity_params.entity_id}/{self.entity_params.entity_id}/{head_img_size}/'


@EVENT_DEPEND_REGISTER.register_depend(OneBotV11Event)
class OneBotV11EventDepend[Event_T: OneBotV11Event](BaseEventDepend[OneBotV11Bot, Event_T]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        if (group_id := getattr(self.event, 'group_id', None)) is not None:
            return EntityInitParams.model_validate({
                'bot_type': self.bot.adapter.get_name(),
                'bot_id': self.bot.self_id,
                'entity_type': EntityType.ONEBOT_V11_GROUP,
                'entity_id': str(group_id),
                'entity_name': 'Unknown',
                'entity_extra': {},
                'entity_info': None,
            })
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        if (user_id := getattr(self.event, 'user_id', None)) is not None:
            return EntityInitParams.model_validate({
                'bot_type': self.bot.adapter.get_name(),
                'bot_id': self.bot.self_id,
                'entity_type': EntityType.ONEBOT_V11_USER,
                'entity_id': str(user_id),
                'entity_name': 'Unknown',
                'entity_extra': {},
                'entity_info': None,
            })
        raise NotImplementedError

    def get_user_nickname(self) -> str:
        # 基类事件, 不予实现
        raise NotImplementedError

    @staticmethod
    def get_reply_msg_image_urls(message: UniMessage) -> list[str]:
        # 基类事件, 不予实现
        raise NotImplementedError


@EVENT_DEPEND_REGISTER.register_depend(OneBotV11NotifyEvent)
class OneBotV11NotifyEventDepend[Event_T: OneBotV11NotifyEvent](OneBotV11EventDepend[Event_T]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.ONEBOT_V11_GROUP,
            'entity_id': str(self.event.group_id),
            'entity_name': 'Unknown',
            'entity_extra': {},
            'entity_info': None,
        })

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.ONEBOT_V11_USER,
            'entity_id': str(self.event.user_id),
            'entity_name': 'Unknown',
            'entity_extra': {},
            'entity_info': None,
        })


@EVENT_DEPEND_REGISTER.register_depend(OneBotV11PokeNotifyEvent)
class OneBotV11PokeNotifyEventDepend(OneBotV11NotifyEventDepend[OneBotV11PokeNotifyEvent]):
    def _extract_event_entity_params(self) -> 'EntityInitParams':
        if self.event.group_id is None:
            return self._extract_user_entity_params()

        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.ONEBOT_V11_GROUP,
            'entity_id': str(self.event.group_id),
            'entity_name': 'Unknown',
            'entity_extra': {},
            'entity_info': None,
        })


@EVENT_DEPEND_REGISTER.register_depend(OneBotV11MessageEvent)
class OneBotV11MessageEventDepend[Event_T: OneBotV11MessageEvent](OneBotV11EventDepend[Event_T]):

    def get_user_nickname(self) -> str:
        nickname = self.event.sender.card if self.event.sender.card else self.event.sender.nickname
        return nickname if nickname is not None else ''

    @staticmethod
    def get_reply_msg_image_urls(message: UniMessage) -> list[str]:
        reply_messages = message[Reply]
        image_urls = [msg_seg.data.get('url', None) for msg_seg in reply_messages if msg_seg.type == 'image']

        if image_urls:
            return [str(url) for url in image_urls if url is not None]
        else:
            return []


@EVENT_DEPEND_REGISTER.register_depend(OneBotV11GroupMessageEvent)
class OneBotV11GroupMessageEventDepend(OneBotV11MessageEventDepend[OneBotV11GroupMessageEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.ONEBOT_V11_GROUP,
            'entity_id': str(self.event.group_id),
            'entity_name': 'Unknown',
            'entity_extra': {},
            'entity_info': None,
        })

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.ONEBOT_V11_USER,
            'entity_id': str(self.event.user_id),
            'entity_name': self.event.sender.nickname or self.event.sender.card or 'Unknown',
            'entity_extra': self.event.sender.model_dump(),
            'entity_info': None,
        })


@EVENT_DEPEND_REGISTER.register_depend(OneBotV11PrivateMessageEvent)
class OneBotV11PrivateMessageEventDepend(OneBotV11MessageEventDepend[OneBotV11PrivateMessageEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams.model_validate({
            'bot_type': self.bot.adapter.get_name(),
            'bot_id': self.bot.self_id,
            'entity_type': EntityType.ONEBOT_V11_USER,
            'entity_id': str(self.event.user_id),
            'entity_name': self.event.sender.nickname or 'Unknown',
            'entity_extra': self.event.sender.model_dump(),
            'entity_info': None,
        })


__all__ = []
