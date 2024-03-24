"""
@Author         : Ailitonia
@Date           : 2023/8/6 2:26
@FileName       : helpers
@Project        : nonebot2_miya
@Description    : weibo utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from sqlalchemy.exc import NoResultFound
from typing import Iterable

from nonebot import logger
from nonebot.adapters import Message
from nonebot.exception import ActionFailed

from src.database import WeiboDetailDAL, begin_db_session
from src.database.internal.entity import Entity
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType
from src.service import OmegaInterface, OmegaEntity, OmegaMessageSegment
from src.service.omega_base.internal import OmegaWeiboUserSubSource
from src.utils.weibo_api import Weibo
from src.utils.weibo_api.model import WeiboCard
from src.utils.process_utils import run_async_delay, semaphore_gather


WEIBO_SUB_TYPE: str = SubscriptionSourceType.weibo_user.value
"""微博用户订阅类型"""


async def _query_weibo_sub_source(uid: int) -> SubscriptionSource:
    """从数据库查询微博订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaWeiboUserSubSource(session=session, uid=uid).query_subscription_source()
    return source_res


async def _check_new_weibo(cards: Iterable[WeiboCard]) -> list[WeiboCard]:
    """检查新的微博(数据库中没有的)"""
    async with begin_db_session() as session:
        all_mids = [x.mblog.id for x in cards]
        new_mids = await WeiboDetailDAL(session=session).query_not_exists_ids(mids=all_mids)
    return [x for x in cards if x.mblog.id in new_mids]


async def _add_upgrade_weibo_content(card: WeiboCard) -> None:
    """在数据库中添加微博内容"""
    retweeted_content = card.mblog.retweeted_status.text if card.mblog.is_retweeted else ''
    async with begin_db_session() as session:
        dal = WeiboDetailDAL(session=session)
        try:
            weibo = await dal.query_unique(mid=card.mblog.id)
            await dal.update(id_=weibo.id, content=card.mblog.text, retweeted_content=retweeted_content)
        except NoResultFound:
            await dal.add(mid=card.mblog.id, uid=card.mblog.user.id,
                          content=card.mblog.text, retweeted_content=retweeted_content)


async def _add_user_new_weibo_content(uid: int) -> None:
    """在数据库中更新目标用户的所有微博(仅新增不更新)"""
    user_cards = await Weibo.query_user_weibo_cards(uid=uid)
    new_weibo_cards = await _check_new_weibo(cards=user_cards)

    tasks = [_add_upgrade_weibo_content(card=card) for card in new_weibo_cards]
    await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)


async def _add_upgrade_weibo_user_sub_source(uid: int) -> SubscriptionSource:
    """在数据库中新更新微博用户订阅源"""
    user_data = await Weibo.query_user_data(uid=uid)

    await _add_user_new_weibo_content(uid=uid)

    async with begin_db_session() as session:
        sub_source = OmegaWeiboUserSubSource(session=session, uid=uid)
        await sub_source.add_upgrade(sub_user_name=user_data.screen_name, sub_info='微博用户订阅')
        source_res = await sub_source.query_subscription_source()
    return source_res


async def add_weibo_user_sub(interface: OmegaInterface, uid: int) -> None:
    """为目标对象添加微博用户订阅"""
    source_res = await _add_upgrade_weibo_user_sub_source(uid=uid)
    await interface.entity.add_subscription(subscription_source=source_res, sub_info=f'微博用户订阅(uid={uid})')


async def delete_weibo_user_sub(interface: OmegaInterface, uid: int) -> None:
    """为目标对象删除微博用户订阅"""
    source_res = await _query_weibo_sub_source(uid=uid)
    await interface.entity.delete_subscription(subscription_source=source_res)


async def query_entity_subscribed_weibo_user_sub_source(interface: OmegaInterface) -> dict[str, str]:
    """获取目标对象已订阅的微博用户

    :return: {用户 UID: 用户昵称} 的字典"""
    subscribed_source = await interface.entity.query_subscribed_source(sub_type=WEIBO_SUB_TYPE)
    return {x.sub_id: x.sub_user_name for x in subscribed_source}


async def query_all_subscribed_weibo_user_sub_source() -> list[int]:
    """获取所有已添加的微博用户订阅源

    :return: 用户 UID 列表
    """
    async with begin_db_session() as session:
        source_res = await OmegaWeiboUserSubSource.query_type_all(session=session)
    return [int(x.sub_id) for x in source_res]


async def query_subscribed_entity_by_weibo_user(uid: int) -> list[Entity]:
    """根据微博用户查询已经订阅了这个用户的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaWeiboUserSubSource(session=session, uid=uid)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def _format_weibo_update_message(card: WeiboCard) -> str | Message:
    """处理微博内容为消息"""
    send_message = f'【微博】{card.mblog.user.screen_name}'
    img_urls = []

    # 检测转发
    if card.mblog.is_retweeted:
        retweeted_username = card.mblog.retweeted_status.user.screen_name
        send_message += f'转发了{retweeted_username}的微博!\n'
        # 获取转发微博全文
        retweeted_content = await Weibo.query_weibo_extend_text(mid=card.mblog.retweeted_status.mid)
        text = f'“{card.mblog.text}”\n{"=" * 16}\n@{retweeted_username}:\n“{retweeted_content}”\n'
        if card.mblog.retweeted_status.pics is not None:
            img_urls.extend(x.large.url for x in card.mblog.retweeted_status.pics)
        if card.mblog.retweeted_status.page_info is not None:
            img_urls.append(card.mblog.retweeted_status.page_info.pic_url)
    else:
        send_message += f'发布了新微博!\n'
        text = f'“{card.mblog.text}”\n'
        if card.mblog.pics is not None:
            img_urls.extend(x.large.url for x in card.mblog.pics)
        if card.mblog.page_info is not None:
            img_urls.append(card.mblog.page_info.pic_url)

    # 添加发布来源和内容
    send_message += f'{card.mblog.format_created_at} 来自{card.mblog.source}\n'
    if card.mblog.region_name is not None:
        send_message += f'{card.mblog.region_name}\n\n'
    else:
        send_message += '\n'
    send_message += text

    # 下载微博中包含的图片
    if img_urls:
        img_download_tasks = [Weibo.download_resource(url=url) for url in img_urls]
        img_download_res = await semaphore_gather(tasks=img_download_tasks, semaphore_num=9, filter_exception=True)
        for img in img_download_res:
            send_message += OmegaMessageSegment.image(url=img.path)
        send_message += '\n'

    send_message += f'\n微博链接: https://weibo.com/detail/{card.mblog.mid}'
    return send_message


async def _msg_sender(entity: Entity, message: str | Message) -> None:
    """向 entity 发送消息"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            interface = OmegaInterface(entity=internal_entity)
            await interface.send_msg(message=message)
    except ActionFailed as e:
        logger.warning(f'WeiboMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'WeiboMonitor | Sending message to {entity} failed, {e!r}')


@run_async_delay(delay_time=7)
async def weibo_user_monitor_main(uid: int) -> None:
    """向已订阅的对象发送微博用户更新"""
    logger.debug(f'WeiboMonitor | Start checking user {uid} updated content')
    weibo_user_cards = await Weibo.query_user_weibo_cards(uid=uid)

    new_weibo_cards = await _check_new_weibo(cards=weibo_user_cards)
    if new_weibo_cards:
        logger.info(f'WeiboMonitor | Confirmed user {uid} '
                    f'new weibo: {", ".join(str(x.mblog.mid) for x in new_weibo_cards)}')
    else:
        logger.debug(f'WeiboMonitor | User {uid} has not new weibo')
        return

    # 获取微博内容
    format_msg_tasks = [_format_weibo_update_message(card=card) for card in new_weibo_cards]
    send_messages = await semaphore_gather(tasks=format_msg_tasks, semaphore_num=3, return_exceptions=False)

    # 数据库中插入新微博信息
    add_artwork_tasks = [_add_upgrade_weibo_content(card=card) for card in new_weibo_cards]
    await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=10, return_exceptions=False)

    # 向订阅者发送新微博信息
    subscribed_entity = await query_subscribed_entity_by_weibo_user(uid=uid)
    send_tasks = [
        _msg_sender(entity=entity, message=send_msg)
        for entity in subscribed_entity for send_msg in send_messages
    ]
    await semaphore_gather(tasks=send_tasks, semaphore_num=2)


__all__ = [
    'add_weibo_user_sub',
    'delete_weibo_user_sub',
    'query_entity_subscribed_weibo_user_sub_source',
    'query_all_subscribed_weibo_user_sub_source',
    'weibo_user_monitor_main'
]
