"""
@Author         : Ailitonia
@Date           : 2022/05/03 19:42
@FileName       : helpers
@Project        : nonebot2_miya
@Description    : 直播间检查工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from sqlalchemy.exc import NoResultFound

from nonebot import logger
from nonebot.adapters import Message
from nonebot.exception import ActionFailed

from src.database import begin_db_session
from src.database.internal.entity import Entity
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType
from src.service import EntityInterface, OmegaEntity, OmegaMessageSegment
from src.service.omega_base.internal import OmegaBiliLiveSubSource
from src.utils.bilibili_api import BilibiliLiveRoom
from src.utils.bilibili_api.model.live_room import BilibiliLiveRoomDataModel
from src.utils.process_utils import semaphore_gather

from .data_source import (
    check_and_upgrade_live_status,
    get_all_live_room_status_uid,
    get_live_room_status,
    get_user_live_room_status,
    query_and_upgrade_live_room_status
)
from .model import (
    BilibiliLiveRoomTitleChange,
    BilibiliLiveRoomStartLiving,
    BilibiliLiveRoomStartLivingWithUpdateTitle,
    BilibiliLiveRoomStopLiving,
    BilibiliLiveRoomStopLivingWithPlaylist,
    BilibiliLiveRoomStatusUpdate
)


BILI_LIVE_SUBTYPE: str = SubscriptionSourceType.bili_live.value
"""b站直播间订阅类型"""


async def _query_room_sub_source(room_id: int) -> SubscriptionSource:
    """从数据库查询直播间订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaBiliLiveSubSource(session=session, live_room_id=room_id).query_subscription_source()
    return source_res


async def _add_upgrade_room_sub_source(live_room: BilibiliLiveRoom) -> SubscriptionSource:
    """在数据库中更新直播间订阅源"""
    await query_and_upgrade_live_room_status(live_room=live_room)
    room_username = get_live_room_status(room_id=live_room.room_id).live_user_name

    async with begin_db_session() as session:
        sub_source = OmegaBiliLiveSubSource(session=session, live_room_id=live_room.room_id)
        try:
            source_res = await sub_source.query_subscription_source()
        except NoResultFound:
            await sub_source.add_upgrade(sub_user_name=room_username, sub_info='Bilibili直播间订阅')
            source_res = await sub_source.query_subscription_source()
    return source_res


async def add_live_room_sub(entity_interface: EntityInterface, live_room: BilibiliLiveRoom) -> None:
    """为目标对象添加 Bilibili 直播间订阅"""
    source_res = await _add_upgrade_room_sub_source(live_room=live_room)
    await entity_interface.entity.add_subscription(subscription_source=source_res,
                                                   sub_info=f'Bilibili直播间订阅(rid={live_room.rid})')


async def delete_live_room_sub(entity_interface: EntityInterface, room_id: int) -> None:
    """为目标对象删除 Bilibili 直播间订阅"""
    source_res = await _query_room_sub_source(room_id=room_id)
    await entity_interface.entity.delete_subscription(subscription_source=source_res)


async def query_subscribed_live_room_sub_source(entity_interface: EntityInterface) -> dict[str, str]:
    """获取目标对象已订阅的 Bilibili 直播间

    :return: {房间号: 用户昵称}的字典"""
    subscribed_source = await entity_interface.entity.query_subscribed_source(sub_type=BILI_LIVE_SUBTYPE)
    return {x.sub_id: x.sub_user_name for x in subscribed_source}


async def query_subscribed_entity_by_live_room(room_id: str) -> list[Entity]:
    """根据 Bilibili 直播间房间号查询已经订阅了这个用户的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaBiliLiveSubSource(session=session, live_room_id=room_id)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def _format_live_room_update_message(
        live_room_data: BilibiliLiveRoomDataModel,
        update_data: BilibiliLiveRoomStatusUpdate
) -> str | Message | None:
    """处理直播间更新为消息"""
    send_message = '【bilibili直播间】\n'
    user_name = get_user_live_room_status(uid=live_room_data.uid).live_user_name
    need_url = False

    if isinstance(update_data.update, (BilibiliLiveRoomStartLivingWithUpdateTitle, BilibiliLiveRoomStartLiving)):
        # 开播
        if isinstance(live_room_data.live_time, datetime):
            start_time = live_room_data.live_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            start_time = str(live_room_data.live_time)
        send_message += f"{start_time}\n{user_name}开播啦！\n\n【{live_room_data.title}】"
        need_url = True
    elif isinstance(update_data.update, BilibiliLiveRoomStopLiving):
        # 下播
        send_message += f'{user_name}下播了'
    elif isinstance(update_data.update, BilibiliLiveRoomStopLivingWithPlaylist):
        # 下播转轮播
        send_message += f'{user_name}下播了（轮播中）'
    elif isinstance(update_data.update, BilibiliLiveRoomTitleChange) and live_room_data.live_status == 1:
        # 直播中换标题
        send_message += f"{user_name}的直播间换标题啦！\n\n【{live_room_data.title}】"
        need_url = True
    else:
        return None

    # 下载直播间封面图
    if live_room_data.cover:
        try:
            cover_img = await BilibiliLiveRoom.download_resource(url=live_room_data.cover)
            send_message += '\n'
            send_message += OmegaMessageSegment.image(url=cover_img.path)
        except Exception as e:
            logger.warning(f'BilibiliLiveRoomMonitor | Download live room cover failed, {e!r}')

    if need_url:
        send_message += f'\n传送门: https://live.bilibili.com/{live_room_data.room_id}'

    return send_message


async def _msg_sender(entity: Entity, message: str | Message) -> None:
    """向 entity 发送消息"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            entity_interface = EntityInterface(entity=internal_entity)
            await entity_interface.send_msg(message=message)
    except ActionFailed as e:
        logger.warning(f'BilibiliLiveRoomMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'BilibiliLiveRoomMonitor | Sending message to {entity} failed, {e!r}')


async def _process_bili_live_room_update(live_room_data: BilibiliLiveRoomDataModel) -> None:
    """处理 Bilibili 直播间状态更新"""
    logger.debug(f'BilibiliLiveRoomMonitor | Checking bilibili live room({live_room_data.room_id}) status')

    update_data = check_and_upgrade_live_status(live_room_data=live_room_data)
    if update_data is None or not update_data.is_update:
        logger.debug(f'BilibiliLiveRoomMonitor | Bilibili live room({live_room_data.room_id}) holding')
        return
    else:
        logger.info(f'BilibiliLiveRoomMonitor | Bilibili live room({live_room_data.room_id}) '
                    f'status update, {update_data.update}')

    send_msg = await _format_live_room_update_message(live_room_data=live_room_data, update_data=update_data)
    subscribed_entity = await query_subscribed_entity_by_live_room(room_id=str(live_room_data.room_id))

    # 向订阅者发送直播间更新信息
    send_tasks = [
        _msg_sender(entity=entity, message=send_msg)
        for entity in subscribed_entity
        if send_msg is not None
    ]
    await semaphore_gather(tasks=send_tasks, semaphore_num=2)


async def bili_live_room_monitor_main() -> None:
    """向已订阅的用户或群发送 Bilibili 直播间状态更新"""
    uid_list = get_all_live_room_status_uid()
    if not uid_list:
        logger.debug(f'BilibiliLiveRoomMonitor | None of live room subscription, ignored')
        return

    room_status_data = await BilibiliLiveRoom.query_live_room_by_uid_list(uid_list=uid_list)
    if room_status_data.error:
        logger.error(f'BilibiliLiveRoomMonitor | Failed to checking live room status, {room_status_data}')
        return

    # 处理直播间状态更新并向订阅者发送直播间更新信息
    send_tasks = [_process_bili_live_room_update(live_room_data=data) for uid, data in room_status_data.data.items()]
    await semaphore_gather(tasks=send_tasks, semaphore_num=3)


__all__ = [
    'add_live_room_sub',
    'delete_live_room_sub',
    'query_subscribed_live_room_sub_source',
    'bili_live_room_monitor_main'
]
