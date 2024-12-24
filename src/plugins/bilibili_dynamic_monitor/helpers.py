"""
@Author         : Ailitonia
@Date           : 2022/05/02 23:52
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Bilibili Dynamic utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from nonebot import logger
from nonebot.exception import ActionFailed

from src.database import SocialMediaContentDAL, begin_db_session
from src.exception import WebSourceException
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
from src.service.omega_base.internal import OmegaBiliDynamicSubSource
from src.utils import run_async_delay, semaphore_gather
from src.utils.bilibili_api import BilibiliDynamic, BilibiliUser
from .consts import (
    BILI_DYNAMIC_SUB_TYPE,
    MODULE_NAME,
    NOTICE_AT_ALL,
    PLUGIN_NAME,
)

if TYPE_CHECKING:
    from src.database.internal.entity import Entity
    from src.database.internal.subscription_source import SubscriptionSource
    from src.utils.bilibili_api.future.models.dynamic import DynItem


async def _query_dynamic_sub_source(user_id: int | str) -> 'SubscriptionSource':
    """从数据库查询动态订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaBiliDynamicSubSource(session=session, uid=user_id).query_subscription_source()
    return source_res


async def _check_new_dynamic(items: Sequence['DynItem']) -> list['DynItem']:
    """检查新的动态(数据库中没有的)"""
    async with begin_db_session() as session:
        new_ids = await SocialMediaContentDAL(session=session).query_source_not_exists_mids(
            source=BILI_DYNAMIC_SUB_TYPE, mids=[x.id_str for x in items]
        )
    return [x for x in items if x.id_str in new_ids]


async def _add_upgrade_dynamic_content(item: 'DynItem') -> None:
    """在数据库中添加动态信息"""
    async with begin_db_session() as session:
        await SocialMediaContentDAL(session=session).upsert(
            source=BILI_DYNAMIC_SUB_TYPE,
            m_id=str(item.id_str),
            m_type=str(item.type),
            m_uid=str(item.modules.module_author.mid),
            title=f'{item.modules.module_author.name}的动态',
            content=item.dyn_text,
        )


async def _add_user_new_dynamic_content(user_id: int | str) -> None:
    """在数据库中更新目标用户的所有动态(仅新增不更新)"""
    dynamics = await BilibiliDynamic.query_user_space_dynamics(host_mid=user_id)
    new_dynamic_item = await _check_new_dynamic(items=dynamics.data.items)

    tasks = [_add_upgrade_dynamic_content(item=item) for item in new_dynamic_item]
    await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)


async def _add_upgrade_dynamic_sub_source(user_id: int | str) -> 'SubscriptionSource':
    """在数据库中新更新动态订阅源"""
    user_data = await BilibiliUser.query_user_info(mid=user_id)
    if user_data.error:
        raise WebSourceException(404, f'query user({user_id}) info failed, {user_data.message}')

    await _add_user_new_dynamic_content(user_id=user_id)

    async with begin_db_session() as session:
        sub_source = OmegaBiliDynamicSubSource(session=session, uid=user_id)
        await sub_source.add_upgrade(sub_user_name=user_data.uname, sub_info='Bilibili用户动态订阅')
        source_res = await sub_source.query_subscription_source()
    return source_res


async def add_dynamic_sub(interface: OmMI, user_id: int | str) -> None:
    """为目标对象添加 Bilibili 用户动态订阅"""
    source_res = await _add_upgrade_dynamic_sub_source(user_id=user_id)
    await interface.entity.add_subscription(subscription_source=source_res,
                                            sub_info=f'Bilibili用户动态订阅(uid={user_id})')


async def delete_dynamic_sub(interface: OmMI, user_id: int | str) -> None:
    """为目标对象删除 Bilibili 用户动态订阅"""
    source_res = await _query_dynamic_sub_source(user_id=user_id)
    await interface.entity.delete_subscription(subscription_source=source_res)


async def query_entity_subscribed_dynamic_sub_source(interface: OmMI) -> dict[str, str]:
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


async def query_subscribed_entity_by_bili_user(user_id: int | str) -> list['Entity']:
    """根据 Bilibili 用户查询已经订阅了这个用户的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaBiliDynamicSubSource(session=session, uid=user_id)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def _format_dynamic_update_message(item: 'DynItem') -> str | OmegaMessage:
    """处理动态为消息"""
    send_message = f'【bilibili】{item.dyn_text}\n'

    # 下载动态中包含的图片
    if item.dyn_image_urls:
        img_download_tasks = [BilibiliDynamic.download_resource(url=url) for url in item.dyn_image_urls]
        img_download_res = await semaphore_gather(tasks=img_download_tasks, semaphore_num=9, filter_exception=True)
        for img in img_download_res:
            send_message += OmegaMessageSegment.image(url=img.path)
        send_message += '\n'

    send_message += f'\n动态链接: https://t.bilibili.com/{item.id_str}'
    return send_message


async def _has_notice_at_all_node(entity: OmegaEntity) -> bool:
    """检查目标是否有通知@所有人的权限"""
    try:
        return await entity.check_auth_setting(module=MODULE_NAME, plugin=PLUGIN_NAME, node=NOTICE_AT_ALL)
    except Exception as e:
        logger.warning(f'BilibiliDynamicMonitor | Checking {entity} notice at all node failed, {e!r}')
        return False


async def _msg_sender(entity: 'Entity', message: str | OmegaMessage) -> None:
    """向 entity 发送动态消息"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            interface = OmEI(entity=internal_entity)

            if await _has_notice_at_all_node(internal_entity):
                message = OmegaMessageSegment.at_all() + message

            await interface.send_entity_message(message=message)
    except ActionFailed as e:
        logger.warning(f'BilibiliDynamicMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'BilibiliDynamicMonitor | Sending message to {entity} failed, {e!r}')


@run_async_delay(delay_time=8, random_sigma=4)
async def bili_dynamic_monitor_main(user_id: int | str) -> None:
    """向已订阅的用户或群发送 Bilibili 用户动态更新"""
    logger.debug(f'BilibiliDynamicMonitor | Start checking user({user_id}) new dynamics')
    dynamics = await BilibiliDynamic.query_user_space_dynamics(host_mid=user_id)

    new_dynamic_item = await _check_new_dynamic(items=dynamics.data.items)
    if new_dynamic_item:
        logger.info(
            f'BilibiliDynamicMonitor | Confirmed user({user_id}) '
            f'new dynamic: {", ".join(x.id_str for x in new_dynamic_item)}'
        )
    else:
        logger.debug(f'BilibiliDynamicMonitor | user({user_id}) has not new dynamics')
        return

    # 获取动态消息内容
    format_msg_tasks = [_format_dynamic_update_message(item=item) for item in new_dynamic_item]
    send_messages = await semaphore_gather(tasks=format_msg_tasks, semaphore_num=3, return_exceptions=False)

    # 数据库中插入新动态信息
    add_artwork_tasks = [_add_upgrade_dynamic_content(item=item) for item in new_dynamic_item]
    await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=10, return_exceptions=False)

    # 向订阅者发送新动态信息
    subscribed_entity = await query_subscribed_entity_by_bili_user(user_id=user_id)
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
    'bili_dynamic_monitor_main',
]
