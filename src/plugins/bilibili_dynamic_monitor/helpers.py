"""
@Author         : Ailitonia
@Date           : 2022/05/02 23:52
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Bilibili Dynamic utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from sqlalchemy.exc import NoResultFound
from typing import Iterable

from nonebot import logger
from nonebot.adapters import Message
from nonebot.exception import ActionFailed

from src.database import BiliDynamicDAL, begin_db_session
from src.database.internal.entity import Entity
from src.database.internal.subscription_source import SubscriptionSource
from src.service import OmegaInterface, OmegaEntity, OmegaMessageSegment
from src.service.omega_base.internal import OmegaBiliDynamicSubSource
from src.utils.bilibili_api import BilibiliDynamic, BilibiliUser
from src.utils.bilibili_api.model import BilibiliDynamicCard
from src.utils.bilibili_api.exception import BilibiliApiError
from src.utils.process_utils import run_async_delay, semaphore_gather

from .consts import BILI_DYNAMIC_SUB_TYPE, NOTICE_AT_ALL, MODULE_NAME, PLUGIN_NAME


async def _query_dynamic_sub_source(uid: int) -> SubscriptionSource:
    """从数据库查询动态订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaBiliDynamicSubSource(session=session, uid=uid).query_subscription_source()
    return source_res


async def _check_new_dynamic(cards: Iterable[BilibiliDynamicCard]) -> list[BilibiliDynamicCard]:
    """检查新的动态(数据库中没有的)"""
    async with begin_db_session() as session:
        all_ids = [x.desc.dynamic_id for x in cards]
        new_ids = await BiliDynamicDAL(session=session).query_not_exists_ids(dynamic_ids=all_ids)
    return [x for x in cards if x.desc.dynamic_id in new_ids]


async def _add_upgrade_dynamic_content(card: BilibiliDynamicCard) -> None:
    """在数据库中添加动态信息"""
    async with begin_db_session() as session:
        dal = BiliDynamicDAL(session=session)
        try:
            dynamic = await dal.query_unique(dynamic_id=card.desc.dynamic_id)
            await dal.update(id_=dynamic.id, content=card.card.output_std_model().content)
        except NoResultFound:
            await dal.add(dynamic_id=card.desc.dynamic_id, dynamic_type=card.desc.type,
                          uid=card.desc.uid, content=card.card.output_std_model().content)


async def _add_user_new_dynamic_content(bili_user: BilibiliUser) -> None:
    """在数据库中更新目标用户的所有动态(仅新增不更新)"""
    dynamic_data = await bili_user.query_dynamics()
    new_dynamic_card = await _check_new_dynamic(cards=dynamic_data.all_cards)

    tasks = [_add_upgrade_dynamic_content(card=card) for card in new_dynamic_card]
    await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)


async def _add_upgrade_dynamic_sub_source(bili_user: BilibiliUser) -> SubscriptionSource:
    """在数据库中新更新动态订阅源"""
    user_data = await bili_user.query_user_data()
    if user_data.error:
        raise BilibiliApiError(f'query {bili_user} data failed, {user_data.message}')

    await _add_user_new_dynamic_content(bili_user=bili_user)

    async with begin_db_session() as session:
        sub_source = OmegaBiliDynamicSubSource(session=session, uid=bili_user.uid)
        await sub_source.add_upgrade(sub_user_name=user_data.uname, sub_info='Bilibili用户动态订阅')
        source_res = await sub_source.query_subscription_source()
    return source_res


async def add_dynamic_sub(interface: OmegaInterface, bili_user: BilibiliUser) -> None:
    """为目标对象添加 Bilibili 用户动态订阅"""
    source_res = await _add_upgrade_dynamic_sub_source(bili_user=bili_user)
    await interface.entity.add_subscription(subscription_source=source_res,
                                            sub_info=f'Bilibili用户动态订阅(uid={bili_user.uid})')


async def delete_dynamic_sub(interface: OmegaInterface, uid: int) -> None:
    """为目标对象删除 Bilibili 用户动态订阅"""
    source_res = await _query_dynamic_sub_source(uid=uid)
    await interface.entity.delete_subscription(subscription_source=source_res)


async def query_entity_subscribed_dynamic_sub_source(interface: OmegaInterface) -> dict[str, str]:
    """获取目标对象已订阅的 Bilibili 用户动态

    :return: {用户 UID: 用户昵称} 的字典"""
    subscribed_source = await interface.entity.query_subscribed_source(sub_type=BILI_DYNAMIC_SUB_TYPE)
    return {x.sub_id: x.sub_user_name for x in subscribed_source}


async def query_all_subscribed_dynamic_sub_source() -> list[int]:
    """获取所有已添加的 Bilibili 用户动态订阅源

    :return: 用户 UID 列表
    """
    async with begin_db_session() as session:
        source_res = await OmegaBiliDynamicSubSource.query_type_all(session=session)
    return [int(x.sub_id) for x in source_res]


async def query_subscribed_entity_by_bili_user(uid: int) -> list[Entity]:
    """根据 Bilibili 用户查询已经订阅了这个用户的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaBiliDynamicSubSource(session=session, uid=uid)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def _format_dynamic_update_message(dynamic: BilibiliDynamicCard) -> str | Message:
    """处理动态为消息"""
    send_message = f'【bilibili】{dynamic.output_text}\n'

    # 下载动态中包含的图片
    if dynamic.output_img_urls:
        img_download_tasks = [BilibiliDynamic.download_resource(url=url) for url in dynamic.output_img_urls]
        img_download_res = await semaphore_gather(tasks=img_download_tasks, semaphore_num=9, filter_exception=True)
        for img in img_download_res:
            send_message += OmegaMessageSegment.image(url=img.path)
        send_message += '\n'

    send_message += f'\n动态链接: https://t.bilibili.com/{dynamic.desc.dynamic_id}'
    return send_message


async def _has_notice_at_all_node(entity: OmegaEntity) -> bool:
    """检查目标是否有通知@所有人的权限"""
    try:
        return await entity.check_auth_setting(module=MODULE_NAME, plugin=PLUGIN_NAME, node=NOTICE_AT_ALL)
    except Exception as e:
        logger.warning(f'BilibiliDynamicMonitor | Checking {entity} notice at all node failed, {e!r}')
        return False


async def _msg_sender(entity: Entity, message: str | Message) -> None:
    """向 entity 发送动态消息"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            interface = OmegaInterface(entity=internal_entity)

            if await _has_notice_at_all_node(internal_entity):
                message = OmegaMessageSegment.at_all() + message

            await interface.send_msg(message=message)
    except ActionFailed as e:
        logger.warning(f'BilibiliDynamicMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'BilibiliDynamicMonitor | Sending message to {entity} failed, {e!r}')


@run_async_delay(delay_time=5)
async def bili_dynamic_monitor_main(uid: int) -> None:
    """向已订阅的用户或群发送 Bilibili 用户动态更新"""
    bili_user = BilibiliUser(uid=uid)
    logger.debug(f'BilibiliDynamicMonitor | Start checking {bili_user} new dynamics')
    dynamic_data = await bili_user.query_dynamics()

    new_dynamic_card = await _check_new_dynamic(cards=dynamic_data.all_cards)
    if new_dynamic_card:
        logger.info(f'BilibiliDynamicMonitor | Confirmed {bili_user} '
                    f'new dynamic: {", ".join(str(x.desc.dynamic_id) for x in new_dynamic_card)}')
    else:
        logger.debug(f'BilibiliDynamicMonitor | {bili_user} has not new dynamics')
        return

    # 获取动态消息内容
    format_msg_tasks = [_format_dynamic_update_message(dynamic=card) for card in new_dynamic_card]
    send_messages = await semaphore_gather(tasks=format_msg_tasks, semaphore_num=3, return_exceptions=False)

    # 数据库中插入新动态信息
    add_artwork_tasks = [_add_upgrade_dynamic_content(card=card) for card in new_dynamic_card]
    await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=10, return_exceptions=False)

    # 向订阅者发送新动态信息
    subscribed_entity = await query_subscribed_entity_by_bili_user(uid=bili_user.uid)
    send_tasks = [
        _msg_sender(entity=entity, message=send_msg)
        for entity in subscribed_entity for send_msg in send_messages
    ]
    await semaphore_gather(tasks=send_tasks, semaphore_num=2)


__all__ = [
    'add_dynamic_sub',
    'delete_dynamic_sub',
    'query_entity_subscribed_dynamic_sub_source',
    'query_all_subscribed_dynamic_sub_source',
    'bili_dynamic_monitor_main'
]
