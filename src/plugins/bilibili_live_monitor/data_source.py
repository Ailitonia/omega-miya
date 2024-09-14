"""
@Author         : Ailitonia
@Date           : 2023/8/4 2:11
@FileName       : data_source
@Project        : nonebot2_miya
@Description    : 直播间开播信息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from copy import deepcopy
from typing import TYPE_CHECKING

from nonebot import get_driver, logger

from src.database import begin_db_session
from src.exception import WebSourceException
from src.service.omega_base.internal import OmegaBiliLiveSubSource
from src.utils.bilibili_api import BilibiliLiveRoom
from src.utils.process_utils import semaphore_gather
from .model import BilibiliLiveRoomStatus, BilibiliLiveRoomStatusUpdate

if TYPE_CHECKING:
    from src.utils.bilibili_api.model.live_room import BilibiliLiveRoomDataModel


__LIVE_STATUS: dict[int, BilibiliLiveRoomStatus] = {}
"""Bilibili 直播间状态缓存, {用户UID: 直播间状态}"""


def check_and_upgrade_live_status(
        live_room_data: "BilibiliLiveRoomDataModel",
        *,
        live_user_name: str | None = None
) -> BilibiliLiveRoomStatusUpdate | None:
    """检查并更新 Bilibili 直播间状态缓存

    :return: 更新后的直播间状态(如有)
    """
    exist_status = __LIVE_STATUS.get(live_room_data.uid, None)

    if exist_status is None and live_user_name is None:
        raise ValueError('Add new live room status must provide "live_user_name" parameter')

    if exist_status is None:  # make typing checker happy
        new_live_user_name = live_user_name if live_user_name is not None else f'bilibili直播间{live_room_data.room_id}'
    else:
        new_live_user_name = exist_status.live_user_name if live_user_name is None else live_user_name

    new_status = BilibiliLiveRoomStatus.model_validate({
        'live_room_id': live_room_data.room_id,
        'live_status': live_room_data.live_status,
        'live_title': live_room_data.title,
        'live_user_name': new_live_user_name
    })
    __LIVE_STATUS.update({live_room_data.uid: new_status})
    logger.trace(f'Upgrade live room({live_room_data.room_id}) status: {new_status}')

    if isinstance(exist_status, BilibiliLiveRoomStatus):
        update = new_status - exist_status
    else:
        update = None
    return update


def get_all_live_room_status_uid() -> list[int]:
    """获取缓存的直播间所有用户 uid 列表"""
    return list(set(deepcopy(__LIVE_STATUS).keys()))


def get_live_room_status(room_id: int) -> BilibiliLiveRoomStatus | None:
    """获取缓存的直播间信息"""
    return {x.live_room_id: x for x in deepcopy(__LIVE_STATUS).values()}.get(room_id, None)


def get_user_live_room_status(uid: int) -> BilibiliLiveRoomStatus | None:
    """获取缓存的用户直播间信息"""
    return deepcopy(__LIVE_STATUS).get(uid, None)


async def query_and_upgrade_live_room_status(live_room: BilibiliLiveRoom) -> BilibiliLiveRoomStatusUpdate | None:
    """查询并更新 Bilibili 直播间状态"""
    logger.debug(f'BilibiliLiveRoomMonitor | Updating live room({live_room.room_id}) status')

    live_room_data = await live_room.query_live_room_data()
    if live_room_data.error or live_room_data.data is None:
        raise WebSourceException(404, f'query {live_room} data failed, {live_room_data.message}')

    live_room_user_data = await live_room.query_live_room_user_data()
    if live_room_user_data.error or live_room_user_data.data is None:
        raise WebSourceException(404, f'query {live_room} user data failed, {live_room_user_data.message}')

    return check_and_upgrade_live_status(live_room_data.data, live_user_name=live_room_user_data.data.name)


@get_driver().on_startup
async def _init_all_live_room_subscription_source_status() -> None:
    """启动时初始化所有订阅源中直播间的状态"""
    logger.opt(colors=True).info('<lc>BilibiliLiveRoomMonitor</lc> | Initializing live room status')

    try:
        async with begin_db_session() as session:
            source_result = await OmegaBiliLiveSubSource.query_type_all(session=session)
            tasks = [
                query_and_upgrade_live_room_status(live_room=BilibiliLiveRoom(room_id=int(source.sub_id)))
                for source in source_result
            ]
        await semaphore_gather(tasks=tasks, semaphore_num=10)
        logger.opt(colors=True).success('<lc>BilibiliLiveRoomMonitor</lc> | Live room status initializing completed')
    except Exception as e:
        logger.error(f'BilibiliLiveRoomMonitor | Live room status initializing failed, {e!r}')
        raise e


__all__ = [
    'check_and_upgrade_live_status',
    'get_all_live_room_status_uid',
    'get_live_room_status',
    'get_user_live_room_status',
    'query_and_upgrade_live_room_status',
]
