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
from typing import TYPE_CHECKING

from nonebot import logger
from nonebot.exception import ActionFailed

from src.database import begin_db_session
from src.service import (
    OmegaEntity,
    OmegaMessage,
    OmegaMessageSegment,
)
from src.service import (
    OmegaEntityInterface as OmEI,
)
from src.service import (
    OmegaMatcherInterface as OmMI,
)
from src.service.omega_base.internal import OmegaBiliLiveSubSource
from src.utils import semaphore_gather
from src.utils.bilibili_api import BilibiliLive
from .consts import BILI_LIVE_SUB_TYPE, MODULE_NAME, NOTICE_AT_ALL, PLUGIN_NAME
from .data_source import (
    check_and_upgrade_live_status,
    get_all_subscribed_live_room_ids,
    query_live_room_status,
)
from .model import (
    BilibiliLiveRoomStartLiving,
    BilibiliLiveRoomStartLivingWithUpdateTitle,
    BilibiliLiveRoomStatusUpdate,
    BilibiliLiveRoomStopLiving,
    BilibiliLiveRoomStopLivingWithPlaylist,
    BilibiliLiveRoomTitleChange,
)

if TYPE_CHECKING:
    from src.database.internal.entity import Entity
    from src.database.internal.subscription_source import SubscriptionSource
    from src.utils.bilibili_api.models.live import RoomInfoData


async def _query_room_sub_source(room_id: int | str) -> 'SubscriptionSource':
    """从数据库查询直播间订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaBiliLiveSubSource(session=session, live_room_id=room_id).query_subscription_source()
    return source_res


async def _add_upgrade_room_sub_source(room_id: int | str) -> 'SubscriptionSource':
    """在数据库中更新直播间订阅源"""
    live_room_status = await query_live_room_status(room_id=room_id)
    async with begin_db_session() as session:
        sub_source = OmegaBiliLiveSubSource(session=session, live_room_id=room_id)
        await sub_source.add_upgrade(sub_user_name=live_room_status.live_user_name, sub_info='Bilibili直播间订阅')
        source_res = await sub_source.query_subscription_source()
    return source_res


async def add_live_room_sub(interface: OmMI, room_id: int | str) -> None:
    """为目标对象添加 Bilibili 直播间订阅"""
    source_res = await _add_upgrade_room_sub_source(room_id=room_id)
    await interface.entity.add_subscription(subscription_source=source_res,
                                            sub_info=f'Bilibili直播间订阅(rid={room_id})')


async def delete_live_room_sub(interface: OmMI, room_id: int | str) -> None:
    """为目标对象删除 Bilibili 直播间订阅"""
    source_res = await _query_room_sub_source(room_id=room_id)
    await interface.entity.delete_subscription(subscription_source=source_res)


async def query_subscribed_live_room_sub_source(interface: OmMI) -> dict[str, str]:
    """获取目标对象已订阅的 Bilibili 直播间

    :return: {房间号: 用户昵称}的字典"""
    subscribed_source = await interface.entity.query_subscribed_source(sub_type=BILI_LIVE_SUB_TYPE)
    return {x.sub_id: x.sub_user_name for x in subscribed_source}


async def query_subscribed_entity_by_live_room(room_id: int | str) -> list['Entity']:
    """根据 Bilibili 直播间房间号查询已经订阅了这个用户的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaBiliLiveSubSource(session=session, live_room_id=room_id)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def _format_live_room_update_message(
        room_info: 'RoomInfoData',
        update_data: BilibiliLiveRoomStatusUpdate
) -> str | OmegaMessage | None:
    """处理直播间更新为消息"""
    send_message = '【bilibili直播间】\n'
    need_url = False

    if isinstance(update_data.update, (BilibiliLiveRoomStartLivingWithUpdateTitle, BilibiliLiveRoomStartLiving)):
        # 开播
        if isinstance(room_info.live_time, datetime):
            start_time = room_info.live_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            start_time = str(room_info.live_time)
        send_message += f'{start_time}\n{room_info.uname}开播啦！\n\n【{room_info.title}】'
        need_url = True
    elif isinstance(update_data.update, BilibiliLiveRoomStopLiving):
        # 下播
        send_message += f'{room_info.uname}下播了'
    elif isinstance(update_data.update, BilibiliLiveRoomStopLivingWithPlaylist):
        # 下播转轮播
        send_message += f'{room_info.uname}下播了（轮播中）'
    elif isinstance(update_data.update, BilibiliLiveRoomTitleChange) and room_info.live_status == 1:
        # 直播中换标题
        send_message += f'{room_info.uname}的直播间换标题啦！\n\n【{room_info.title}】'
        need_url = True
    else:
        return None

    # 下载直播间封面图
    if room_info.cover_url:
        try:
            cover_img = await BilibiliLive.download_resource(url=room_info.cover_url)
            send_message += '\n'
            send_message += OmegaMessageSegment.image(url=cover_img.path)
        except Exception as e:
            logger.warning(f'BilibiliLiveRoomMonitor | Download live room cover failed, {e!r}')

    if need_url:
        send_message += f'\n传送门: https://live.bilibili.com/{room_info.room_id}'

    return send_message


async def _has_notice_at_all_node(entity: OmegaEntity) -> bool:
    """检查目标是否有通知@所有人的权限"""
    try:
        return await entity.check_auth_setting(module=MODULE_NAME, plugin=PLUGIN_NAME, node=NOTICE_AT_ALL)
    except Exception as e:
        logger.warning(f'BilibiliLiveRoomMonitor | Checking {entity} notice at all node failed, {e!r}')
        return False


async def _msg_sender(entity: 'Entity', message: str | OmegaMessage) -> None:
    """向 entity 发送直播间通知"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            interface = OmEI(entity=internal_entity)

            if await _has_notice_at_all_node(internal_entity):
                message = OmegaMessageSegment.at_all() + message

            await interface.send_entity_message(message=message)
    except ActionFailed as e:
        logger.warning(f'BilibiliLiveRoomMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'BilibiliLiveRoomMonitor | Sending message to {entity} failed, {e!r}')


async def _process_bili_live_room_update(room_info: 'RoomInfoData') -> None:
    """处理直播间状态更新"""
    logger.debug(f'BilibiliLiveRoomMonitor | Checking live room({room_info.room_id}) status')

    update_data = check_and_upgrade_live_status(room_info=room_info)
    if not update_data.is_update:
        logger.debug(f'BilibiliLiveRoomMonitor | Live room({room_info.room_id}) holding')
        return

    logger.info(f'BilibiliLiveRoomMonitor | Live room({room_info.room_id}) status update, {update_data.update}')
    send_msg = await _format_live_room_update_message(room_info=room_info, update_data=update_data)
    subscribed_entity = await query_subscribed_entity_by_live_room(room_id=room_info.room_id)

    # 向订阅者发送直播间更新信息
    send_tasks = [
        _msg_sender(entity=entity, message=send_msg)
        for entity in subscribed_entity
        if send_msg is not None
    ]
    await semaphore_gather(tasks=send_tasks, semaphore_num=2)


async def bili_live_room_monitor_main() -> None:
    """向已订阅的用户或群发送 Bilibili 直播间状态更新"""
    room_ids = await get_all_subscribed_live_room_ids()
    if not room_ids:
        logger.debug('BilibiliLiveRoomMonitor | None of live room subscription, ignored')
        return

    rooms_info = await BilibiliLive.query_room_info_by_room_id_list(room_id_list=room_ids)
    if rooms_info.error:
        logger.error(f'BilibiliLiveRoomMonitor | Failed to checking live room status, {rooms_info}')
        return

    # 处理直播间状态更新并向订阅者发送直播间更新信息
    send_tasks = [
        _process_bili_live_room_update(room_info=room_info)
        for _, room_info in rooms_info.data.by_room_ids.items()
    ]
    await semaphore_gather(tasks=send_tasks, semaphore_num=3)


__all__ = [
    'add_live_room_sub',
    'delete_live_room_sub',
    'query_subscribed_live_room_sub_source',
    'bili_live_room_monitor_main',
]
