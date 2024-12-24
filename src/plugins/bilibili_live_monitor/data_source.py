"""
@Author         : Ailitonia
@Date           : 2023/8/4 2:11
@FileName       : data_source
@Project        : nonebot2_miya
@Description    : 直播间开播信息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from nonebot import get_driver, logger

from src.database import begin_db_session
from src.service.omega_base.internal import OmegaBiliLiveSubSource
from src.utils.bilibili_api.future import BilibiliLive
from .model import BilibiliLiveRoomStatus, BilibiliLiveRoomStatusUpdate

if TYPE_CHECKING:
    from src.utils.bilibili_api.future.models.live import RoomInfoData


__LIVE_ROOM_STATUS: dict[str, BilibiliLiveRoomStatus] = {}
"""Bilibili 直播间状态缓存, {直播间房间号: 直播间状态}"""


def _convert_room_info(room_info: 'RoomInfoData') -> BilibiliLiveRoomStatus:
    return BilibiliLiveRoomStatus.model_validate({
        'live_room_id': room_info.room_id,
        'live_status': room_info.live_status,
        'live_title': room_info.title,
        'live_user_name': room_info.uname
    })


async def get_all_subscribed_live_room_ids() -> list[str]:
    """获取所有已订阅的直播间房间号列表"""
    async with begin_db_session() as session:
        source_result = await OmegaBiliLiveSubSource.query_type_all(session=session)
    return [x.sub_id for x in source_result]


def check_and_upgrade_live_status(room_info: 'RoomInfoData') -> BilibiliLiveRoomStatusUpdate:
    """检查并更新直播间状态缓存

    :return: 更新后的直播间状态(如有)
    """
    new_status = _convert_room_info(room_info)
    exist_status = __LIVE_ROOM_STATUS.setdefault(room_info.room_id, new_status)

    __LIVE_ROOM_STATUS.update({room_info.room_id: new_status})
    logger.debug(f'Upgrade live room({room_info.room_id}) status: {new_status}')

    return new_status - exist_status


async def query_live_room_status(room_id: int | str, *, use_cache: bool = True) -> BilibiliLiveRoomStatus:
    """查询单个直播间状态"""
    if use_cache and (status := __LIVE_ROOM_STATUS.get(str(room_id), None)) is not None:
        return status

    rooms_info = await BilibiliLive.query_room_info_by_room_id_list(room_id_list=[room_id])

    # 针对直播间短号进行处理
    room_info = rooms_info.data.by_room_ids.get(str(room_id), None)
    if room_info is None:
        room_info = {x.short_id: x for x in rooms_info.data.by_room_ids.values()}[str(room_id)]

    return _convert_room_info(room_info)


@get_driver().on_startup
async def _init_all_live_room_subscription_source_status() -> None:
    """启动时初始化所有订阅源中直播间的状态"""
    logger.opt(colors=True).info('<lc>BilibiliLiveRoomMonitor</lc> | Initializing live room status')

    try:
        room_id_list = await get_all_subscribed_live_room_ids()
        rooms_info = await BilibiliLive.query_room_info_by_room_id_list(room_id_list=room_id_list)
        if rooms_info.error:
            logger.error(f'BilibiliLiveRoomMonitor | Failed to query live room status, {rooms_info}')
            return

        __LIVE_ROOM_STATUS.update({
            room_id: _convert_room_info(room_info=room_info)
            for room_id, room_info in rooms_info.data.by_room_ids.items()
        })
        logger.opt(colors=True).success('<lc>BilibiliLiveRoomMonitor</lc> | Live room status initializing completed')
    except Exception as e:
        logger.error(f'BilibiliLiveRoomMonitor | Live room status initializing failed, {e!r}')
        raise e


__all__ = [
    'check_and_upgrade_live_status',
    'get_all_subscribed_live_room_ids',
    'query_live_room_status',
]
