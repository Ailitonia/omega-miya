"""
@Author         : Ailitonia
@Date           : 2022/05/03 19:42
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Bilibili Live utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from datetime import datetime
from nonebot import get_driver, logger
from nonebot.exception import ActionFailed
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment, Message

from omega_miya.database import (InternalBotUser, InternalBotGroup, InternalGuildChannel,
                                 InternalSubscriptionSource, EventEntityHelper)
from omega_miya.database.internal.entity import BaseInternalEntity
from omega_miya.result import BoolResult
from omega_miya.web_resource.bilibili import BilibiliLiveRoom
from omega_miya.web_resource.bilibili.model.live_room import BilibiliLiveRoomDataModel
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather
from omega_miya.utils.message_tools import MessageSender

from .config import bilibili_live_monitor_plugin_config as plugin_config
from .model import (BilibiliLiveRoomStatus, BilibiliLiveRoomTitleChange, BilibiliLiveRoomStartLiving,
                    BilibiliLiveRoomStartLivingWithUpdateTitle, BilibiliLiveRoomStopLiving,
                    BilibiliLiveRoomStopLivingWithPlaylist, BilibiliLiveRoomStatusUpdate)


_LIVE_SUB_TYPE: Literal['bili_live'] = 'bili_live'
"""Bilibili 直播间订阅 SubscriptionSource 的 sub_type"""
_LIVE_STATUS: dict[int, BilibiliLiveRoomStatus] = {}
"""Bilibili 直播间状态缓存, {用户UID: 直播间状态}"""


def upgrade_live_room_status(
        live_room_data: BilibiliLiveRoomDataModel,
        *,
        live_user_name: str | None = None
) -> BilibiliLiveRoomStatusUpdate | None:
    """更新 Bilibili 直播间状态缓存

    :return: 更新后的直播间状态(如有)
    """
    global _LIVE_STATUS
    exist_status = _LIVE_STATUS.get(live_room_data.uid, None)
    if exist_status is None and live_user_name is None:
        raise ValueError(f'upgrade new live room status must provide "live_user_name" parameter')
    else:
        live_user_name = exist_status.live_user_name if live_user_name is None else live_user_name

    new_status = BilibiliLiveRoomStatus.parse_obj({
        'live_room_id': live_room_data.room_id,
        'live_status': live_room_data.live_status,
        'live_title': live_room_data.title,
        'live_user_name': live_user_name
    })
    _LIVE_STATUS.update({live_room_data.uid: new_status})
    if isinstance(exist_status, BilibiliLiveRoomStatus):
        update = new_status - exist_status
    else:
        update = None
    return update


async def _query_and_upgrade_live_room_status(live_room: BilibiliLiveRoom) -> BoolResult:
    """查询并更新 Bilibili 直播间状态"""
    logger.debug(f'BilibiliLiveRoomMonitor | Updating live room({live_room.room_id}) status')
    live_room_data = await live_room.get_live_room_model()
    if live_room_data.error:
        return BoolResult(error=True, info=live_room_data.message, result=False)
    live_room_user_data = await live_room.get_live_room_user_model()
    if live_room_user_data.error:
        return BoolResult(error=True, info=live_room_user_data.message, result=False)
    upgrade_live_room_status(live_room_data=live_room_data.data, live_user_name=live_room_user_data.data.name)
    return BoolResult(error=False, info='Success', result=True)


@get_driver().on_startup
@run_async_catching_exception
async def _init_all_subscription_source_live_room_status() -> None:
    """启动时初始化所有订阅源中直播间的状态"""
    logger.opt(colors=True).info(f'<lc>BilibiliLiveRoomMonitor</lc> | Initializing live room status')
    source_result = await InternalSubscriptionSource.query_all_by_sub_type(sub_type=_LIVE_SUB_TYPE)
    init_tasks = [_query_and_upgrade_live_room_status(live_room=BilibiliLiveRoom(room_id=int(sub.sub_id)))
                  for sub in source_result]
    await semaphore_gather(tasks=init_tasks, semaphore_num=10, return_exceptions=False)
    logger.opt(colors=True).success(f'<lc>BilibiliLiveRoomMonitor</lc> | Live room status initializing completed')


async def _add_bili_live_room_sub_source(live_room: BilibiliLiveRoom) -> BoolResult:
    """在数据库中新增目标用户订阅源"""
    sub_source = InternalSubscriptionSource(sub_type=_LIVE_SUB_TYPE, sub_id=live_room.rid)
    # 订阅源已存在则直接返回
    if await sub_source.exist():
        return BoolResult(error=False, info='BilibiliLiveRoomSubscriptionSource exist', result=True)

    upgrade_status_result = await _query_and_upgrade_live_room_status(live_room=live_room)
    if upgrade_status_result.error:
        return upgrade_status_result

    room_data = await live_room.get_live_room_model()
    room_username = _LIVE_STATUS.get(room_data.data.uid).live_user_name
    add_source_result = await sub_source.add_upgrade(sub_user_name=room_username, sub_info='Bilibili直播间订阅')
    return add_source_result


@run_async_catching_exception
async def add_bili_live_room_sub(bot: Bot, event: MessageEvent, live_room: BilibiliLiveRoom) -> BoolResult:
    """根据 event 为群或用户添加 Bilibili 直播间订阅"""
    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()
    add_source_result = await _add_bili_live_room_sub_source(live_room=live_room)
    if add_source_result.error:
        return add_source_result

    add_sub_result = await entity.add_subscription(sub_type=_LIVE_SUB_TYPE, sub_id=live_room.rid,
                                                   sub_info=f'Bilibili直播间订阅(rid={live_room.rid})')
    return add_sub_result


@run_async_catching_exception
async def delete_bili_live_room_sub(bot: Bot, event: MessageEvent, room_id: str) -> BoolResult:
    """根据 event 为群或用户删除 Bilibili 直播间订阅"""
    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()
    add_sub_result = await entity.delete_subscription(sub_type=_LIVE_SUB_TYPE, sub_id=room_id)
    return add_sub_result


@run_async_catching_exception
async def query_subscribed_bili_live_room_sub_source(bot: Bot, event: MessageEvent) -> list[tuple[str, str]]:
    """根据 event 获取群或用户已订阅的 Bilibili 直播间

    :return: 房间号, 用户昵称 的列表"""
    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()
    subscribed_source = await entity.query_all_subscribed_source(sub_type=_LIVE_SUB_TYPE)
    sub_id_result = [(x.sub_id, x.sub_user_name) for x in subscribed_source]
    return sub_id_result


async def _query_subscribed_entity_by_live_room(room_id: str) -> list[BaseInternalEntity]:
    """根据 Bilibili 直播间房间号查询已经订阅了这个用户的内部 Entity 对象"""
    sub_source = InternalSubscriptionSource(sub_type=_LIVE_SUB_TYPE, sub_id=room_id)
    subscribed_related_entity = await sub_source.query_all_subscribed_related_entity()

    init_tasks = []
    for related_entity in subscribed_related_entity:
        match related_entity.relation_type:
            case 'bot_group':
                init_tasks.append(InternalBotGroup.init_from_index_id(id_=related_entity.id))
            case 'bot_user':
                init_tasks.append(InternalBotUser.init_from_index_id(id_=related_entity.id))
            case 'guild_channel':
                init_tasks.append(InternalGuildChannel.init_from_index_id(id_=related_entity.id))

    entity_result = await semaphore_gather(tasks=init_tasks, semaphore_num=50, return_exceptions=False)
    return list(entity_result)


async def _get_live_room_update_message(
        live_room_data: BilibiliLiveRoomDataModel,
        update_data: BilibiliLiveRoomStatusUpdate
) -> str | Message | None:
    """处理直播间更新为消息"""
    send_message = '【bilibili直播间】\n'
    user_name = _LIVE_STATUS.get(live_room_data.uid).live_user_name
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
        cover_img = await run_async_catching_exception(BilibiliLiveRoom.download_file)(url=live_room_data.cover)
        if not isinstance(cover_img, Exception):
            send_message += '\n'
            send_message += MessageSegment.image(file=cover_img.file_uri)

    if need_url:
        send_message += f'\n传送门: https://live.bilibili.com/{live_room_data.room_id}'

    return send_message


async def _msg_sender(entity: BaseInternalEntity, message: str | Message) -> int:
    """向 entity 发送消息"""
    try:
        msg_sender = MessageSender.init_from_bot_id(bot_id=entity.bot_id)

        # 通知群组时检查能不能@全体成员
        if plugin_config.bilibili_live_monitor_enable_group_at_all_notice and entity.relation_type == 'bot_group':
            at_all_remain = await run_async_catching_exception(msg_sender.bot.get_group_at_all_remain)(
                group_id=entity.entity_id)
            if (not isinstance(at_all_remain, Exception)
                    and at_all_remain.can_at_all
                    and at_all_remain.remain_at_all_count_for_group
                    and at_all_remain.remain_at_all_count_for_uin):
                message = MessageSegment.at(user_id='all') + message

        sent_msg_id = await msg_sender.send_internal_entity_msg(entity=entity, message=message)
    except KeyError:
        logger.debug(f'BilibiliLiveRoomMonitor | Bot({entity.bot_id}) not online, '
                     f'message to {entity.relation.relation_type.upper()}({entity.entity_id}) has be canceled')
        sent_msg_id = 0
    except ActionFailed as e:
        logger.warning(f'BilibiliLiveRoomMonitor | Bot({entity.bot_id}) failed to send message to '
                       f'{entity.relation.relation_type.upper()}({entity.entity_id}) with ActionFailed, {e}')
        sent_msg_id = 0
    return sent_msg_id


async def _process_bili_live_room_update(live_room_data: BilibiliLiveRoomDataModel) -> None:
    """处理 Bilibili 直播间状态更新"""
    logger.debug(f'BilibiliLiveRoomMonitor | Checking bilibili live room({live_room_data.room_id}) status')
    update_data = upgrade_live_room_status(live_room_data=live_room_data)
    if update_data is None or not update_data.is_update:
        logger.debug(f'BilibiliLiveRoomMonitor | Bilibili live room({live_room_data.room_id}) holding')
        return
    else:
        logger.info(f'BilibiliLiveRoomMonitor | Bilibili live room({live_room_data.room_id}) '
                    f'status update, {update_data.update}')

    send_msg = await _get_live_room_update_message(live_room_data=live_room_data, update_data=update_data)
    subscribed_entity = await _query_subscribed_entity_by_live_room(room_id=str(live_room_data.room_id))

    # 向订阅者发送直播间更新信息
    send_tasks = [_msg_sender(entity=entity, message=send_msg)
                  for entity in subscribed_entity if send_msg is not None]
    await semaphore_gather(tasks=send_tasks, semaphore_num=2, return_exceptions=True)


async def send_bili_live_room_update() -> None:
    """向已订阅的用户或群发送 Bilibili 直播间状态更新"""
    uid_list = [x for x in _LIVE_STATUS.keys()]
    if not uid_list:
        return

    room_status_data = await BilibiliLiveRoom.query_live_room_by_uid_list(uid_list=uid_list)
    if room_status_data.error:
        logger.error(f'BilibiliLiveRoomMonitor | Error occurred in checking live room status, {room_status_data}')
        return

    # 处理直播间状态更新并向订阅者发送直播间更新信息
    send_tasks = [_process_bili_live_room_update(live_room_data=data) for uid, data in room_status_data.data.items()]
    await semaphore_gather(tasks=send_tasks, semaphore_num=3, return_exceptions=True)


__all__ = [
    'add_bili_live_room_sub',
    'delete_bili_live_room_sub',
    'query_subscribed_bili_live_room_sub_source',
    'send_bili_live_room_update'
]
