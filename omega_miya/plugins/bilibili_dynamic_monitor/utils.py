"""
@Author         : Ailitonia
@Date           : 2022/05/02 23:52
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Bilibili Dynamic utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, Iterable
from nonebot.log import logger
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment, Message

from omega_miya.database import InternalBotUser, InternalBotGroup, InternalSubscriptionSource, BiliDynamic
from omega_miya.database.internal.entity import BaseInternalEntity
from omega_miya.result import BoolResult
from omega_miya.web_resource.bilibili import BilibiliUser, BilibiliDynamic
from omega_miya.web_resource.bilibili.model import BilibiliDynamicCard
from omega_miya.utils.process_utils import run_async_catching_exception, run_async_delay, semaphore_gather
from omega_miya.utils.message_tools import MessageSender


_DYNAMIC_SUB_TYPE: Literal['bili_dynamic'] = 'bili_dynamic'
"""Bilibili 动态订阅 SubscriptionSource 的 sub_type"""


def _get_event_entity(bot: Bot, event: MessageEvent) -> BaseInternalEntity:
    """根据 event 获取不同 entity 对象"""
    if isinstance(event, GroupMessageEvent):
        entity = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.group_id))
    else:
        entity = InternalBotUser(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.user_id))
    return entity


async def add_dynamic_into_database(dynamic: BilibiliDynamicCard) -> BoolResult:
    """在数据库中添加动态信息(仅新增不更新)"""
    result = await BiliDynamic(dynamic_id=dynamic.desc.dynamic_id).add_only(
        dynamic_type=dynamic.desc.type, uid=dynamic.desc.uid, content=dynamic.card.output_std_model().content)
    return result


async def _add_bili_user_dynamics_to_database(bili_user: BilibiliUser) -> BoolResult:
    """在数据库中新增目标用户的最新动态(仅新增不更新)"""
    dynamic_data = await bili_user.query_dynamics()
    tasks = [add_dynamic_into_database(dynamic=card) for card in dynamic_data.all_cards]
    add_result = await semaphore_gather(tasks=tasks, semaphore_num=10)
    if error := [x for x in add_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)
    return BoolResult(error=False, info='Success', result=True)


async def _add_bili_user_dynamic_sub_source(bili_user: BilibiliUser) -> BoolResult:
    """在数据库中新增目标用户订阅源"""
    sub_source = InternalSubscriptionSource(sub_type=_DYNAMIC_SUB_TYPE, sub_id=str(bili_user.uid))
    # 订阅源已存在则直接返回
    if await sub_source.exist():
        return BoolResult(error=False, info='BilibiliUserDynamicSubscriptionSource exist', result=True)

    add_dynamic_result = await _add_bili_user_dynamics_to_database(bili_user=bili_user)
    if add_dynamic_result.error:
        return add_dynamic_result

    user_data = await bili_user.get_user_model()
    if user_data.error:
        return BoolResult(error=True, info=user_data.message, result=False)

    add_source_result = await sub_source.add_upgrade(sub_user_name=user_data.data.name, sub_info='Bilibili用户动态订阅')
    return add_source_result


@run_async_catching_exception
async def add_bili_user_dynamic_sub(bot: Bot, event: MessageEvent, bili_user: BilibiliUser) -> BoolResult:
    """根据 event 为群或用户添加 Bilibili 用户动态订阅"""
    entity = _get_event_entity(bot=bot, event=event)
    add_source_result = await _add_bili_user_dynamic_sub_source(bili_user=bili_user)
    if add_source_result.error:
        return add_source_result

    add_sub_result = await entity.add_subscription(sub_type=_DYNAMIC_SUB_TYPE, sub_id=str(bili_user.uid),
                                                   sub_info=f'Bilibili用户动态订阅(uid={bili_user.uid})')
    return add_sub_result


@run_async_catching_exception
async def delete_bili_user_dynamic_sub(bot: Bot, event: MessageEvent, user_id: str) -> BoolResult:
    """根据 event 为群或用户删除 Bilibili 用户动态订阅"""
    entity = _get_event_entity(bot=bot, event=event)
    add_sub_result = await entity.delete_subscription(sub_type=_DYNAMIC_SUB_TYPE, sub_id=user_id)
    return add_sub_result


@run_async_catching_exception
async def query_subscribed_bili_user_dynamic_sub_source(bot: Bot, event: MessageEvent) -> list[tuple[str, str]]:
    """根据 event 获取群或用户已订阅的 Bilibili 用户动态

    :return: 用户 UID, 用户昵称 的列表"""
    entity = _get_event_entity(bot=bot, event=event)
    subscribed_source = await entity.query_all_subscribed_source(sub_type=_DYNAMIC_SUB_TYPE)
    sub_id_result = [(x.sub_id, x.sub_user_name) for x in subscribed_source]
    return sub_id_result


async def query_all_bili_user_dynamic_subscription_source() -> list[int]:
    """获取所有已添加的 Bilibili 用户动态订阅源

    :return: 用户 UID 列表
    """
    source_result = await InternalSubscriptionSource.query_all_by_sub_type(sub_type=_DYNAMIC_SUB_TYPE)
    result = [int(x.sub_id) for x in source_result]
    return result


async def _query_subscribed_entity_by_bili_user(bili_user: BilibiliUser) -> list[BaseInternalEntity]:
    """根据 Bilibili 用户查询已经订阅了这个用户的内部 Entity 对象"""
    sub_source = InternalSubscriptionSource(sub_type=_DYNAMIC_SUB_TYPE, sub_id=str(bili_user.uid))
    subscribed_related_entity = await sub_source.query_all_subscribed_related_entity()

    init_tasks = []
    for related_entity in subscribed_related_entity:
        match related_entity.relation_type:
            case 'bot_group':
                init_tasks.append(InternalBotGroup.init_from_index_id(id_=related_entity.id))
            case 'bot_user':
                init_tasks.append(InternalBotUser.init_from_index_id(id_=related_entity.id))

    entity_result = await semaphore_gather(tasks=init_tasks, semaphore_num=50)
    if error := [x for x in entity_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)
    return list(entity_result)


async def _check_new_dynamic(dynamics: Iterable[BilibiliDynamicCard]) -> list[BilibiliDynamicCard]:
    """检查的新动态(数据库中没有的)"""

    async def _dynamic_exists(dynamic: BilibiliDynamicCard) -> (BilibiliDynamicCard, bool):
        """判断该动态是否在数据库中已存在"""
        exist = await BiliDynamic(dynamic_id=dynamic.desc.dynamic_id).exist()
        return dynamic, exist

    check_tasks = [_dynamic_exists(dynamic=dynamic) for dynamic in dynamics]
    check_result = await semaphore_gather(tasks=check_tasks, semaphore_num=50)
    if error := [x for x in check_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    new_dynamic = [x[0] for x in check_result if not x[1]]
    return new_dynamic


async def _get_dynamic_message(dynamic: BilibiliDynamicCard) -> str | Message:
    """处理动态为消息"""
    send_message = f'【Bilibili】{dynamic.output_text}\n'

    # 下载动态中包含的图片
    if dynamic.output_img_urls:
        img_download_tasks = [BilibiliDynamic.download_file(url=url) for url in dynamic.output_img_urls]
        img_download_result = await semaphore_gather(tasks=img_download_tasks, semaphore_num=9)
        send_message += Message(MessageSegment.image(file=x.file_uri) for x in img_download_result)
        send_message += '\n'

    send_message += f'\n动态链接: {BilibiliDynamic.dynamic_root_url}{dynamic.desc.dynamic_id}'
    return send_message


async def _msg_sender(entity: BaseInternalEntity, message: str | Message) -> int:
    """向 entity 发送消息"""
    try:
        msg_sender = MessageSender.init_from_bot_id(bot_id=entity.bot_id)
        sent_msg_id = await msg_sender.send_internal_entity_msg(entity=entity, message=message)
    except KeyError:
        logger.debug(f'BilibiliUserDynamicSubscriptionMonitor | Bot({entity.bot_id}) not online, '
                     f'message to {entity.relation.relation_type.upper()}({entity.entity_id}) has be canceled')
        sent_msg_id = 0
    return sent_msg_id


@run_async_delay(delay_time=5)
@run_async_catching_exception
async def send_bili_user_new_dynamics(bili_user: BilibiliUser) -> None:
    """向已订阅的用户或群发送 Bilibili 用户动态更新"""
    logger.debug(f'BilibiliUserDynamicSubscriptionMonitor | Start checking bilibili user({bili_user.uid}) new dynamics')
    dynamic_data = await bili_user.query_dynamics()
    new_dynamics = await _check_new_dynamic(dynamics=dynamic_data.all_cards)
    if new_dynamics:
        logger.info(f'BilibiliUserDynamicSubscriptionMonitor | Confirmed Bilibili user({bili_user.uid}) '
                    f'new dynamic: {", ".join(str(x.desc.dynamic_id) for x in new_dynamics)}')
    else:
        logger.debug(f'BilibiliUserDynamicSubscriptionMonitor | Bilibili user({bili_user.uid}) has not new dynamics')
        return

    subscribed_entity = await _query_subscribed_entity_by_bili_user(bili_user=bili_user)
    # 获取动态消息内容
    preview_msg_tasks = [_get_dynamic_message(dynamic=dynamic) for dynamic in new_dynamics]
    send_messages = await semaphore_gather(tasks=preview_msg_tasks, semaphore_num=5)
    if error := [x for x in send_messages if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    # 数据库中插入新动态信息
    add_artwork_tasks = [add_dynamic_into_database(dynamic=dynamic) for dynamic in new_dynamics]
    add_result = await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=10)
    if error := [x for x in add_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    # 向订阅者发送新动态信息
    send_tasks = [_msg_sender(entity=entity, message=send_message)
                  for entity in subscribed_entity for send_message in send_messages]
    sent_result = await semaphore_gather(tasks=send_tasks, semaphore_num=2)
    if error := [x for x in sent_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)


__all__ = [
    'add_bili_user_dynamic_sub',
    'delete_bili_user_dynamic_sub',
    'query_subscribed_bili_user_dynamic_sub_source',
    'query_all_bili_user_dynamic_subscription_source',
    'send_bili_user_new_dynamics'
]
