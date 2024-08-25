"""
@Author         : Ailitonia
@Date           : 2022/04/30 18:11
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Pixivision 特辑作品图片预处理及插件工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Sequence

from nonebot import logger
from nonebot.exception import ActionFailed
from sqlalchemy.exc import NoResultFound

from src.database import PixivisionArticleDAL, begin_db_session
from src.resource import TemporaryResource
from src.service import (
    OmegaMatcherInterface as OmMI,
    OmegaEntityInterface as OmEI,
    OmegaEntity,
    OmegaMessage,
    OmegaMessageSegment,
)
from src.service.artwork_collection import PixivArtworkCollection
from src.service.artwork_proxy import PixivArtworkProxy
from src.service.omega_base.internal import OmegaPixivisionSubSource
from src.utils.pixiv_api import Pixivision
from src.utils.process_utils import semaphore_gather

if TYPE_CHECKING:
    from src.database.internal.entity import Entity
    from src.database.internal.subscription_source import SubscriptionSource
    from src.utils.pixiv_api.model.pixivision import PixivisionArticle, PixivisionIllustration

_TMP_FOLDER: TemporaryResource = TemporaryResource('pixivision')
"""图片缓存文件夹"""


async def _query_pixivision_sub_source() -> "SubscriptionSource":
    """从数据库查询 Pixivision 订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaPixivisionSubSource(session=session).query_subscription_source()
    return source_res


async def _check_new_article(articles: Sequence["PixivisionIllustration"]) -> list["PixivisionIllustration"]:
    """检查新的 pixivision 特辑文章(数据库中没有的)"""
    async with begin_db_session() as session:
        new_aids = await PixivisionArticleDAL(session=session).query_not_exists_ids(aids=[x.aid for x in articles])
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


async def _add_new_pixivision_article(articles: Sequence["PixivisionIllustration"]) -> None:
    """向数据库中写入 Pixivision 的特辑文章(仅新增不更新)"""
    tasks = [_add_upgrade_article_content(article=Pixivision(aid=article.aid)) for article in articles]
    await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)


async def _add_pixivision_article_artworks_into_database(article_data: "PixivisionArticle") -> None:
    """向数据库中写入 Pixivision 特辑文章中的作品"""
    add_artwork_tasks = [
        PixivArtworkCollection(x.artwork_id).add_artwork_into_database_ignore_exists()
        for x in article_data.artwork_list
    ]
    await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=8, return_exceptions=False)


async def _add_pixivision_sub_source() -> "SubscriptionSource":
    """在数据库中新增 Pixivision 订阅源"""
    async with begin_db_session() as session:
        sub_source = OmegaPixivisionSubSource(session=session)
        await sub_source.add_upgrade()
        source_res = await sub_source.query_subscription_source()
    return source_res


async def add_pixivision_sub(interface: OmMI) -> None:
    """目标对象添加 Pixivision 订阅"""
    source_res = await _add_pixivision_sub_source()
    await interface.entity.add_subscription(subscription_source=source_res, sub_info=f'Pixivision特辑订阅')


async def delete_pixivision_sub(interface: OmMI) -> None:
    """为目标对象删除 Pixivision 订阅"""
    source_res = await _query_pixivision_sub_source()
    await interface.entity.delete_subscription(subscription_source=source_res)


async def _query_subscribed_entity() -> list["Entity"]:
    """查询已经订阅了 Pixivision 的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaPixivisionSubSource(session=session)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def generate_pixivision_illustration_list_preview(page: int = 1) -> "TemporaryResource":
    """根据 Pixivision Illustration 导览页面内容生成预览图"""
    illustration_result = await Pixivision.query_illustration_list(page=page)
    title = f'Pixivision Illustration - Page {page}'

    return await PixivArtworkProxy.generate_any_images_preview(
        preview_name=title,
        image_data=[
            (x.thumbnail, f'ArticleID: {x.aid}\n{x.split_title_without_mark}')
            for x in illustration_result.illustrations
        ],
        preview_size=(480, 270),
        hold_ratio=True,
        num_of_line=4,
    )


async def _generate_pixivision_article_preview(title: str, article_data: "PixivisionArticle") -> "TemporaryResource":
    """根据 Pixivision 特辑内容生成预览图"""
    return await PixivArtworkProxy.generate_artworks_preview(
        preview_name=title,
        artworks=[PixivArtworkProxy(x.artwork_id) for x in article_data.artwork_list],
        preview_size=(512, 512),
        num_of_line=4,
    )


async def format_pixivision_article_message(article: Pixivision, msg_prefix: str | None = None) -> str | OmegaMessage:
    """处理 Pixivision 特辑更新为消息"""
    article_data = await article.query_article()

    send_message = f'《{article_data.title}》\n'
    try:
        if article_data.eyecatch_image is None:
            raise ValueError('article eyecatch image not found')
        eyecatch_image = await article.download_resource(
            url=article_data.eyecatch_image, save_folder=_TMP_FOLDER('eyecatch')
        )
        send_message += OmegaMessageSegment.image(url=eyecatch_image.path)
    except Exception as e:
        logger.warning(f'PixivisionArticleMonitor | Query {article} eye-catch image failed, {e!r}')

    send_message += f'\n{article_data.description}\n'

    try:
        title = f'Pixivision - {article_data.title_without_mark}'
        preview_image = await _generate_pixivision_article_preview(title=title, article_data=article_data)

        # Pixivision 特辑作品自动存入数据库
        await _add_pixivision_article_artworks_into_database(article_data=article_data)

        send_message += OmegaMessageSegment.image(url=preview_image.path)
    except Exception as e:
        logger.warning(f'PixivisionArticleMonitor | Query {article} preview image failed, {e!r}')
    send_message += f'\n传送门: {article.url}'

    if msg_prefix is not None:
        send_message = msg_prefix + send_message
    return send_message


async def _msg_sender(entity: "Entity", message: str | OmegaMessage) -> None:
    """向 entity 发送消息"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            interface = OmEI(entity=internal_entity)
            await interface.send_entity_message(message=message)
    except ActionFailed as e:
        logger.warning(f'PixivisionArticleMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'PixivisionArticleMonitor | Sending message to {entity} failed, {e!r}')


async def pixivision_monitor_main() -> None:
    """向已订阅的用户或群发送 Pixivision 更新的特辑"""
    articles_data = await Pixivision.query_illustration_list()
    new_articles = await _check_new_article(articles=articles_data.illustrations)

    if new_articles:
        logger.info(
            f'PixivisionArticleMonitor | Confirmed new articles: {", ".join(str(x.aid) for x in new_articles)}'
        )
    else:
        logger.debug(f'PixivisionArticleMonitor | No new pixivision article found')
        return

    # 获取特辑文章消息内容
    format_msg_tasks = [
        format_pixivision_article_message(
            article=Pixivision(aid=article.aid),
            msg_prefix='【Pixivision】新的插画特辑!\n'
        )
        for article in new_articles
    ]
    send_messages = await semaphore_gather(tasks=format_msg_tasks, semaphore_num=3, return_exceptions=False)

    # 数据库中插入新动态信息
    await _add_new_pixivision_article(articles=new_articles)

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
    'format_pixivision_article_message',
    'generate_pixivision_illustration_list_preview',
    'pixivision_monitor_main',
]
