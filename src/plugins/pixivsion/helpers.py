"""
@Author         : Ailitonia
@Date           : 2022/04/30 18:11
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Pixiv Plugin Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from sqlalchemy.exc import NoResultFound
from typing import Iterable

from nonebot import logger
from nonebot.adapters import Message
from nonebot.exception import ActionFailed

from src.database import PixivisionArticleDAL, begin_db_session
from src.database.internal.entity import Entity
from src.database.internal.subscription_source import SubscriptionSource
from src.service import EntityInterface, OmegaEntity, OmegaMessageSegment
from src.service.omega_base.internal import OmegaPixivisionSubSource
from src.utils.pixiv_api import Pixivision
from src.utils.pixiv_api.model.pixivision import PixivisionIllustration
from src.utils.process_utils import semaphore_gather


async def _query_pixivision_sub_source() -> SubscriptionSource:
    """从数据库查询动态订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaPixivisionSubSource(session=session).query_subscription_source()
    return source_res


async def _check_new_article(articles: Iterable[PixivisionIllustration]) -> list[PixivisionIllustration]:
    """检查新的 pixivision 特辑文章(数据库中没有的)"""
    async with begin_db_session() as session:
        all_aids = [x.aid for x in articles]
        new_aids = await PixivisionArticleDAL(session=session).query_not_exists_ids(aids=all_aids)
    return [x for x in articles if x.aid in new_aids]


async def _add_upgrade_article_content(article: Pixivision) -> None:
    """在数据库中添加特辑文章信息(仅新增不更新)"""
    article_data = await article.query_article()

    async with begin_db_session() as session:
        dal = PixivisionArticleDAL(session=session)
        try:
            await dal.query_unique(aid=article.aid)
        except NoResultFound:
            await dal.add(
                aid=article.aid,
                title=article_data.title_without_mark,
                description=article_data.description,
                tags=','.join(x.tag_name for x in article_data.tags_list),
                artworks_id=','.join(str(x.artwork_id) for x in article_data.artwork_list),
                url=article.url
            )


async def _add_new_pixivision_article(articles: Iterable[PixivisionIllustration]) -> None:
    """在数据库中更新 Pixivision 的特辑文章(仅新增不更新)"""
    new_article_data = await _check_new_article(articles=articles)

    tasks = [_add_upgrade_article_content(article=Pixivision(aid=article.aid)) for article in new_article_data]
    await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)


async def _add_pixivision_sub_source() -> SubscriptionSource:
    """在数据库中新增 Pixivision 订阅源"""
    async with begin_db_session() as session:
        sub_source = OmegaPixivisionSubSource(session=session)
        await sub_source.add_upgrade()
        source_res = await sub_source.query_subscription_source()
    return source_res


async def add_pixivision_sub(entity_interface: EntityInterface) -> None:
    """目标对象添加 Pixivision 订阅"""
    source_res = await _add_pixivision_sub_source()
    await entity_interface.entity.add_subscription(subscription_source=source_res,
                                                   sub_info=f'Pixivision特辑订阅')


async def delete_pixivision_sub(entity_interface: EntityInterface) -> None:
    """为目标对象删除 Pixivision 订阅"""
    source_res = await _query_pixivision_sub_source()
    await entity_interface.entity.delete_subscription(subscription_source=source_res)


async def _query_subscribed_entity() -> list[Entity]:
    """查询已经订阅了 Pixivision 的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaPixivisionSubSource(session=session)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def format_pixivision_update_message(article: Pixivision, message_prefix: str | None = None) -> str | Message:
    """处理 Pixivision 特辑更新为消息"""
    pixivision_data = await article.query_article()

    send_message = f'《{pixivision_data.title}》\n'
    try:
        eyecatch_image = await article.query_eyecatch_image()
        send_message += OmegaMessageSegment.image(url=eyecatch_image.path)
    except Exception as e:
        logger.warning(f'PixivisionArticleMonitor | Query {article} eye-catch image failed, {e!r}')
    send_message += f'\n{pixivision_data.description}\n'
    try:
        preview_image = await article.query_article_with_preview()
        send_message += OmegaMessageSegment.image(url=preview_image.path)
    except Exception as e:
        logger.warning(f'PixivisionArticleMonitor | Query {article} preview image failed, {e!r}')
    send_message += f'\n传送门: {article.url}'

    if message_prefix is not None:
        send_message = message_prefix + send_message
    return send_message


async def _msg_sender(entity: Entity, message: str | Message) -> None:
    """向 entity 发送消息"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            entity_interface = EntityInterface(entity=internal_entity)
            await entity_interface.send_msg(message=message)
    except ActionFailed as e:
        logger.warning(f'PixivisionArticleMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'PixivisionArticleMonitor | Sending message to {entity} failed, {e!r}')


async def pixivision_monitor_main() -> None:
    """向已订阅的用户或群发送 Pixivision 更新的特辑"""

    articles_data = await Pixivision.query_illustration_list()

    new_articles = await _check_new_article(articles=articles_data.illustrations)
    if new_articles:
        logger.info(f'PixivisionArticleMonitor | Confirmed '
                    f'new articles: {", ".join(str(x.aid) for x in new_articles)}')
    else:
        logger.debug(f'PixivisionArticleMonitor | No new pixivision article found')
        return

    # 获取特辑文章消息内容
    format_msg_tasks = [
        format_pixivision_update_message(
            article=Pixivision(aid=article.aid),
            message_prefix='【Pixivision】新的插画特辑!\n'
        )
        for article in new_articles
    ]
    send_messages = await semaphore_gather(tasks=format_msg_tasks, semaphore_num=3, return_exceptions=False)

    # 数据库中插入新动态信息
    add_artwork_tasks = [_add_upgrade_article_content(article=Pixivision(aid=article.aid)) for article in new_articles]
    await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=10, return_exceptions=False)

    # 向订阅者发送新动态信息
    subscribed_entity = await _query_subscribed_entity()
    send_tasks = [
        _msg_sender(entity=entity, message=send_msg)
        for entity in subscribed_entity for send_msg in send_messages
    ]
    await semaphore_gather(tasks=send_tasks, semaphore_num=2)


__all__ = [
    'add_pixivision_sub',
    'delete_pixivision_sub',
    'format_pixivision_update_message',
    'pixivision_monitor_main'
]
