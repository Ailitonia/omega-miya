"""
@Author         : Ailitonia
@Date           : 2022/04/30 18:11
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Pixiv Plugin Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal
from nonebot.log import logger
from nonebot.exception import ActionFailed
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import MessageSegment, Message
from nonebot.adapters.onebot.v11.event import MessageEvent

from omega_miya.result import BoolResult
from omega_miya.database import InternalSubscriptionSource, PixivisionArticle, EventEntityHelper
from omega_miya.database.internal.entity import BaseInternalEntity, InternalBotUser, InternalBotGroup
from omega_miya.web_resource.pixiv import Pixivision
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather
from omega_miya.utils.message_tools import MessageSender


_PIXIVISION_SUB_TYPE: Literal['pixivision'] = 'pixivision'
"""Pixivision 订阅 SubscriptionSource 的 sub_type"""
_PIXIVISION_SUB_ID: Literal['pixivision'] = 'pixivision'
"""Pixivision 订阅 SubscriptionSource 的 sub_id"""


@run_async_catching_exception
async def get_pixivision_article_preview(aid: int, message_prefix: str | None = None) -> Message:
    """获取单个 Pixivision 特辑预览"""
    pixivision = Pixivision(aid=aid)
    pixivision_data = await pixivision.query_article()

    eyecatch_image = await run_async_catching_exception(pixivision.query_eyecatch_image)()
    preview_image = await pixivision.query_article_with_preview()

    send_message = MessageSegment.text(f'《{pixivision_data.title}》\n')
    if not isinstance(eyecatch_image, Exception):
        send_message += MessageSegment.image(eyecatch_image.file_uri)
    send_message += f'\n{pixivision_data.description}\n'
    send_message += MessageSegment.image(preview_image.file_uri)
    send_message += f'\n传送门: {pixivision.url}'

    if message_prefix is not None:
        send_message = message_prefix + send_message
    return send_message


async def _add_pixivision_sub_source() -> BoolResult:
    """在数据库中新增 Pixivision 订阅源"""
    sub_source = InternalSubscriptionSource(sub_type=_PIXIVISION_SUB_TYPE, sub_id=_PIXIVISION_SUB_ID)
    # 订阅源已存在则直接返回
    if await sub_source.exist():
        return BoolResult(error=False, info='PixivisionSubscriptionSource exist', result=True)

    add_source_result = await sub_source.add_upgrade(sub_user_name=_PIXIVISION_SUB_ID, sub_info='Pixivision订阅')
    return add_source_result


@run_async_catching_exception
async def add_pixivision_sub(bot: Bot, event: MessageEvent) -> BoolResult:
    """根据 event 为群或用户添加 Pixivision 订阅"""
    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()
    add_source_result = await _add_pixivision_sub_source()
    if add_source_result.error:
        return add_source_result

    add_sub_result = await entity.add_subscription(sub_type=_PIXIVISION_SUB_TYPE, sub_id=_PIXIVISION_SUB_ID,
                                                   sub_info='Pixivision订阅')
    return add_sub_result


@run_async_catching_exception
async def delete_pixivision_sub(bot: Bot, event: MessageEvent) -> BoolResult:
    """根据 event 为群或用户删除 Pixivision 订阅"""
    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()
    add_sub_result = await entity.delete_subscription(sub_type=_PIXIVISION_SUB_TYPE, sub_id=_PIXIVISION_SUB_ID)
    return add_sub_result


async def _query_subscribed_entity_by_pixiv_user() -> list[BaseInternalEntity]:
    """查询已经订阅了 Pixivision 的内部的内部 Entity 对象"""
    sub_source = InternalSubscriptionSource(sub_type=_PIXIVISION_SUB_TYPE, sub_id=_PIXIVISION_SUB_ID)
    if not await sub_source.exist():
        await _add_pixivision_sub_source()

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


async def _check_pixivision_article_exist(aid: int) -> (int, bool):
    """判断该 Pixivision 特辑是否在数据库中已存在

    :return: aid, 是否存在
    """
    exist = await PixivisionArticle(aid=aid).exist()
    return aid, exist


async def _check_pixivision_new_article() -> list[int]:
    """检查 Pixivision 新特辑(数据库中没有的)"""
    articles_data = await Pixivision.query_illustration_list()
    check_tasks = [_check_pixivision_article_exist(aid=article.aid) for article in articles_data.illustrations]
    check_result = await semaphore_gather(tasks=check_tasks, semaphore_num=20)
    if error := [x for x in check_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    new_aid = [x[0] for x in check_result if not x[1]]
    return new_aid


async def _add_article_into_database(article: Pixivision) -> BoolResult:
    """在数据库中添加作品信息(仅新增不更新)"""
    article_data = await article.query_article()
    result = await PixivisionArticle(aid=article.aid).add_upgrade_unique_self(
        title=article_data.title_without_mark, description=article_data.description,
        tags=','.join(x.tag_name for x in article_data.tags_list),
        artworks_id=','.join(str(x.artwork_id) for x in article_data.artwork_list),
        url=article.url
    )
    return result


async def _msg_sender(entity: BaseInternalEntity, message: str | Message) -> int:
    """向 entity 发送消息"""
    try:
        msg_sender = MessageSender.init_from_bot_id(bot_id=entity.bot_id)
        sent_msg_id = await msg_sender.send_internal_entity_msg(entity=entity, message=message)
    except KeyError:
        logger.debug(f'PixivisionArticleUpdateMonitor | Bot({entity.bot_id}) not online, '
                     f'message to {entity.relation.relation_type.upper()}({entity.entity_id}) has be canceled')
        sent_msg_id = 0
    except ActionFailed as e:
        logger.warning(f'PixivisionArticleUpdateMonitor | Bot({entity.bot_id}) failed to send message to '
                       f'{entity.relation.relation_type.upper()}({entity.entity_id}) with ActionFailed, {e}')
        sent_msg_id = 0
    return sent_msg_id


async def send_pixivision_new_article() -> None:
    """向已订阅的用户或群发送 Pixivision 更新的特辑"""
    new_aids = await _check_pixivision_new_article()
    if new_aids:
        logger.info(f'PixivisionArticleUpdateMonitor | Confirmed pixivision '
                    f'new articles: {", ".join(str(x) for x in new_aids)}')
    else:
        logger.debug(f'PixivisionArticleUpdateMonitor | Pixivision has not new articles')
        return

    subscribed_entity = await _query_subscribed_entity_by_pixiv_user()
    # 获取新特辑消息内容
    message_prefix = f'【Pixivision】新的插画特辑!\n'
    preview_msg_tasks = [get_pixivision_article_preview(aid=aid, message_prefix=message_prefix) for aid in new_aids]
    send_messages = await semaphore_gather(tasks=preview_msg_tasks, semaphore_num=5)
    if error := [x for x in send_messages if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    # 数据库中插入新特辑信息
    add_artwork_tasks = [_add_article_into_database(article=Pixivision(aid=aid)) for aid in new_aids]
    add_result = await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=10)
    if error := [x for x in add_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    # 向订阅者发送新特辑信息
    send_tasks = [_msg_sender(entity=entity, message=send_message)
                  for entity in subscribed_entity for send_message in send_messages]
    sent_result = await semaphore_gather(tasks=send_tasks, semaphore_num=2)
    if error := [x for x in sent_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)


__all__ = [
    'get_pixivision_article_preview',
    'add_pixivision_sub',
    'delete_pixivision_sub',
    'send_pixivision_new_article'
]
