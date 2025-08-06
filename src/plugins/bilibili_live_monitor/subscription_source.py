"""
@Author         : Ailitonia
@Date           : 2022/05/03 19:42
@FileName       : subscription_source.py
@Project        : nonebot2_miya
@Description    : 直播间检查工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from asyncio import Lock as AsyncLock
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, ClassVar, Self

from nonebot import logger

from src.database.internal.social_media_content import SocialMediaContent
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType
from src.exception import WebSourceException
from src.service import OmegaMessage, OmegaMessageSegment
from src.service.omega_subscription_service import BaseSubscriptionManager
from src.utils.bilibili_api import BilibiliLive
from .model import (
    BilibiliLiveRoomStartLiving,
    BilibiliLiveRoomStartLivingWithUpdateTitle,
    BilibiliLiveRoomStatus,
    BilibiliLiveRoomStatusUpdate,
    BilibiliLiveRoomStopLiving,
    BilibiliLiveRoomStopLivingWithPlaylist,
    BilibiliLiveRoomTitleChange,
)

if TYPE_CHECKING:
    from src.utils.bilibili_api.models.live import RoomInfoData

    type SMC_T = BilibiliLiveRoomStatusUpdate

_LIVE_ROOM_STATUS: dict[str, BilibiliLiveRoomStatus] = {}
"""Bilibili 直播间状态缓存, {直播间房间号: 直播间状态}"""


class BilibiliLiveRoomSubscriptionManager(BaseSubscriptionManager['SMC_T']):
    """Bilibili 直播间订阅服务管理"""

    _LATEST_LIVE_ROOM_STATUS_CACHE: ClassVar[dict[str, BilibiliLiveRoomStatus]] = {}
    """类内部直播间状态缓存, 存放最新获取的直播间信息, 用于与全局直播间状态缓存进行比较"""
    _LATEST_LIVE_ROOM_STATUS_CACHE_EXPIRED_AT: datetime = datetime.now() - timedelta(seconds=15)
    """类内部直播间状态缓存的过期时间"""
    _LATEST_LIVE_ROOM_STATUS_UPDATE_LOCK: AsyncLock = AsyncLock()
    """类内部直播间状态缓存更新锁"""

    def __init__(self, room_id: str | int) -> None:
        self.sub_id = str(room_id)

    """直播间状态检查方法"""

    @staticmethod
    def _convert_room_info(room_info: 'RoomInfoData') -> BilibiliLiveRoomStatus:
        """转换直播间状态信息"""
        return BilibiliLiveRoomStatus.model_validate({
            'live_room_id': room_info.room_id,
            'live_room_short_id': room_info.short_id,
            'live_status': room_info.live_status,
            'live_title': room_info.title,
            'live_user_name': room_info.uname,
            'live_user_id': room_info.uid,
            'live_time': room_info.live_time,
            'live_description': room_info.description,
            'live_tags': room_info.tags,
            'live_attention': room_info.attention,
            'live_online': room_info.online,
            'live_url': room_info.live_url,
            'live_cover_url': room_info.cover_url,
        })

    @classmethod
    async def _update_internal_live_room_status(cls, room_ids: Sequence[int | str]) -> None:
        """更新类内部直播间状态缓存并刷新过期时间"""
        try:
            rooms_info = await BilibiliLive.query_room_info_by_room_id_list(room_id_list=room_ids)
            if rooms_info.error:
                raise WebSourceException(500, f'{rooms_info.code}, {rooms_info.message}')

            cls._LATEST_LIVE_ROOM_STATUS_CACHE.update({
                room_id: cls._convert_room_info(room_info=room_info)
                for room_id, room_info in rooms_info.data.by_room_ids.items()
            })
            cls._LATEST_LIVE_ROOM_STATUS_CACHE_EXPIRED_AT = datetime.now() + timedelta(seconds=15)
            logger.debug(
                f'{cls.__name__} | Update internal live room status success, '
                f'expired at {cls._LATEST_LIVE_ROOM_STATUS_CACHE_EXPIRED_AT}'
            )
        except Exception as e:
            logger.error(f'{cls.__name__} | Failed to query and update internal live room status, {e}')
            raise e

    @classmethod
    async def _update_all_subscribed_live_room_internal_status(cls) -> None:
        """更新类所有已被订阅的内部直播间状态缓存并刷新过期时间"""
        async with cls._LATEST_LIVE_ROOM_STATUS_UPDATE_LOCK:
            if datetime.now() >= cls._LATEST_LIVE_ROOM_STATUS_CACHE_EXPIRED_AT:
                room_id_list = await cls.query_all_subscribed_sub_source_ids()
                await cls._update_internal_live_room_status(room_ids=room_id_list)

    @classmethod
    def _check_and_upgrade_live_status(cls, new_status: 'BilibiliLiveRoomStatus') -> 'SMC_T':
        """检查、对比并更新直播间全局状态缓存

        :return: 更新后的直播间状态(如有)
        """
        global _LIVE_ROOM_STATUS

        exist_status = _LIVE_ROOM_STATUS.setdefault(new_status.live_room_id, new_status)

        _LIVE_ROOM_STATUS.update({new_status.live_room_id: new_status})
        logger.debug(f'Upgrade live room({new_status.live_room_id}) status: {new_status}')

        return new_status - exist_status

    async def _query_live_room_latest_status(self) -> 'BilibiliLiveRoomStatus':
        """内部方法, 获取单个直播间最新状态, 按需刷新内部直播间状态缓存"""
        if datetime.now() >= self._LATEST_LIVE_ROOM_STATUS_CACHE_EXPIRED_AT:
            await self._update_all_subscribed_live_room_internal_status()

        # 针对直播间短号进行处理
        room_info = self._LATEST_LIVE_ROOM_STATUS_CACHE.get(self.sub_id, None)
        if room_info is None:
            # 此处短号也没有的话则直播间不是已订阅的, 此处抛出 `KeyError` 由上层继续处理
            room_info = {x.live_room_short_id: x for x in self._LATEST_LIVE_ROOM_STATUS_CACHE.values()}[self.sub_id]
        return room_info

    async def query_live_room_status(self) -> 'BilibiliLiveRoomStatus':
        """从全局缓存中获取单个直播间最新状态"""
        global _LIVE_ROOM_STATUS

        if (status := _LIVE_ROOM_STATUS.get(self.sub_id, None)) is not None:
            return status

        return await self._query_live_room_latest_status()

    """订阅服务管理基类方法实现"""

    @classmethod
    def init_from_sub_id(cls, sub_id: str | int) -> Self:
        return cls(room_id=sub_id)

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.bili_live.value

    @staticmethod
    def _get_smc_item_mid(smc_item: 'SMC_T') -> str:
        return smc_item.status.live_room_id

    @classmethod
    def _parse_smc_item(cls, smc_item: 'SMC_T') -> 'SocialMediaContent':
        return SocialMediaContent.model_validate({
            'source': cls.get_sub_type(),
            'm_id': f'{smc_item.status.live_room_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'm_type': smc_item.update_type,
            'm_uid': smc_item.status.live_user_id,
            'title': '直播间状态变更',
            'content': f'{smc_item.status.live_user_name}的直播间-{smc_item.status.live_title}',
            'ref_content': smc_item.status.model_dump_json(),
        })

    @classmethod
    async def _check_new_smc_item(cls, smc_items: 'Sequence[SMC_T]') -> 'list[SMC_T]':
        return [x for x in smc_items if x.is_update]

    async def _query_sub_source_smc_items(self) -> 'list[SMC_T]':
        live_room_status = await self._query_live_room_latest_status()
        return [self._check_and_upgrade_live_status(live_room_status)]

    async def query_sub_source_data(self) -> 'SubscriptionSource':
        live_room_data = await self.query_live_room_status()
        return SubscriptionSource.model_validate({
            'id': -1,
            'sub_type': self.get_sub_type(),
            'sub_id': self.sub_id,
            'sub_user_name': live_room_data.live_user_name,
            'sub_info': 'Bilibili直播间订阅',
        })

    @classmethod
    async def _format_smc_item_message(cls, smc_item: 'SMC_T') -> str | OmegaMessage | None:
        send_message = '【bilibili直播间】\n'
        need_url = False

        if isinstance(smc_item.update, BilibiliLiveRoomStartLivingWithUpdateTitle | BilibiliLiveRoomStartLiving):
            # 开播
            if isinstance(smc_item.status.live_time, datetime):
                start_time = smc_item.status.live_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_time = str(smc_item.status.live_time)
            send_message += f'{start_time}\n{smc_item.status.live_user_name}开播啦！\n\n【{smc_item.status.live_title}】'
            need_url = True
        elif isinstance(smc_item.update, BilibiliLiveRoomStopLiving):
            # 下播
            send_message += f'{smc_item.status.live_user_name}下播了'
        elif isinstance(smc_item.update, BilibiliLiveRoomStopLivingWithPlaylist):
            # 下播转轮播
            send_message += f'{smc_item.status.live_user_name}下播了（轮播中）'
        elif isinstance(smc_item.update, BilibiliLiveRoomTitleChange) and smc_item.status.live_status == 1:
            # 直播中换标题
            send_message += f'{smc_item.status.live_user_name}的直播间换标题啦！\n\n【{smc_item.status.live_title}】'
            need_url = True
        else:
            return None

        # 下载直播间封面图
        if smc_item.status.live_cover_url:
            try:
                cover_img = await BilibiliLive.download_resource(url=smc_item.status.live_cover_url)
                send_message += '\n'
                send_message += OmegaMessageSegment.image(await cover_img.get_hosting_path())
            except Exception as e:
                logger.warning(f'BilibiliLiveRoomMonitor | Download live room cover failed, {e!r}')

        if need_url:
            send_message += f'\n传送门: https://live.bilibili.com/{smc_item.status.live_room_id}'

        return send_message


__all__ = [
    'BilibiliLiveRoomSubscriptionManager',
]
