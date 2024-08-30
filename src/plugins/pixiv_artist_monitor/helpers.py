"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : helpers.py
@Project        : nonebot2_miya 
@Description    : 作品图片预处理及插件流程控制工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Literal, Optional, Sequence

from nonebot.exception import ActionFailed
from nonebot.log import logger

from src.database import begin_db_session
from src.service import (
    OmegaMatcherInterface as OmMI,
    OmegaEntityInterface as OmEI,
    OmegaEntity,
    OmegaMessage,
    OmegaMessageSegment,
)
from src.service.artwork_collection import PixivArtworkCollection
from src.service.artwork_proxy import PixivArtworkProxy
from src.service.omega_base.internal import OmegaPixivUserSubSource
from src.utils.pixiv_api import PixivUser
from src.utils.process_utils import semaphore_gather
from .consts import PIXIV_USER_SUB_TYPE

if TYPE_CHECKING:
    from src.database.internal.entity import Entity
    from src.database.internal.subscription_source import SubscriptionSource
    from src.resource import TemporaryResource
    from src.utils.pixiv_api.model.ranking import PixivRankingModel


async def _query_pixiv_user_sub_source(uid: int) -> "SubscriptionSource":
    """从数据库查询 Pixiv 用户订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaPixivUserSubSource(session=session, uid=uid).query_subscription_source()
    return source_res


async def _check_pixiv_user_new_artworks(pixiv_user: "PixivUser") -> list[str]:
    """检查 Pixiv 用户的新作品(数据库中没有的)"""
    user_data = await pixiv_user.query_user_data()
    return await PixivArtworkCollection.query_not_exists_aids(aids=[str(pid) for pid in user_data.manga_illusts])


async def _add_pixiv_user_new_artworks(pixiv_user: "PixivUser") -> None:
    """在数据库中新增目标用户的全部作品(仅新增不更新)"""
    user_new_pids = await _check_pixiv_user_new_artworks(pixiv_user=pixiv_user)

    # 应对 pixiv 流控, 对获取作品信息进行分段处理
    handle_pids = user_new_pids[:20]
    remain_pids = user_new_pids[20:]
    fail_count = 0
    while handle_pids:

        tasks = [PixivArtworkCollection(pid).add_artwork_into_database_ignore_exists() for pid in handle_pids]
        await semaphore_gather(tasks=tasks, semaphore_num=10)

        handle_pids.clear()
        handle_pids = remain_pids[:20]
        remain_pids = remain_pids[20:]

        if remain_pids:
            logger.debug(f'PixivUserAdder | Adding user({pixiv_user.uid}) artworks, {len(remain_pids)} remaining')
            await asyncio.sleep(int((len(remain_pids) if len(remain_pids) < 20 else 20) * 1.5))

    logger.info(f'PixivUserAdder | Adding user({pixiv_user.uid}) artworks completed, failed: {fail_count}')


async def _add_upgrade_pixiv_user_sub_source(pixiv_user: "PixivUser") -> "SubscriptionSource":
    """在数据库中更新 Pixiv 用户订阅源"""
    user_data = await pixiv_user.query_user_data()

    await _add_pixiv_user_new_artworks(pixiv_user=pixiv_user)

    async with begin_db_session() as session:
        sub_source = OmegaPixivUserSubSource(session=session, uid=pixiv_user.uid)
        await sub_source.add_upgrade(sub_user_name=user_data.name, sub_info='Pixiv用户订阅')
        source_res = await sub_source.query_subscription_source()
    return source_res


async def add_pixiv_user_sub(interface: OmMI, pixiv_user: "PixivUser") -> None:
    """为目标对象添加 Pixiv 用户订阅"""
    source_res = await _add_upgrade_pixiv_user_sub_source(pixiv_user=pixiv_user)
    await interface.entity.add_subscription(subscription_source=source_res,
                                            sub_info=f'Pixiv用户订阅(uid={pixiv_user.uid})')


async def delete_pixiv_user_sub(interface: OmMI, uid: int) -> None:
    """为目标对象删除 Pixiv 用户订阅"""
    source_res = await _query_pixiv_user_sub_source(uid=uid)
    await interface.entity.delete_subscription(subscription_source=source_res)


async def query_entity_subscribed_pixiv_user_sub_source(interface: OmMI) -> dict[str, str]:
    """获取目标对象已订阅的 Pixiv 用户

    :return: {用户 UID: 用户昵称} 的字典"""
    subscribed_source = await interface.entity.query_subscribed_source(sub_type=PIXIV_USER_SUB_TYPE)
    return {x.sub_id: x.sub_user_name for x in subscribed_source}


async def query_all_subscribed_pixiv_user_sub_source() -> list[int]:
    """获取所有已添加的 Pixiv 用户订阅源

    :return: 用户 UID 列表
    """
    async with begin_db_session() as session:
        source_res = await OmegaPixivUserSubSource.query_type_all(session=session)
    return [int(x.sub_id) for x in source_res]


async def query_subscribed_entity_by_pixiv_user(pixiv_user: "PixivUser") -> list["Entity"]:
    """根据 Pixiv 用户查询已经订阅了这个用户的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaPixivUserSubSource(session=session, uid=pixiv_user.uid)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def _format_pixiv_user_new_artwork_message(
        pid: str,
        *,
        message_prefix: Optional[str] = None,
        show_page_limiting: int = 10,
) -> OmegaMessage:
    """预处理用户作品预览消息"""
    artwork_ap = PixivArtworkCollection(artwork_id=pid).artwork_proxy

    artwork_data = await artwork_ap.query()
    artwork_desc = await artwork_ap.get_std_desc()

    # 处理作品预览
    process_mode: Literal['mark', 'blur'] = 'mark' if artwork_data.rating <= 1 else 'blur'
    show_page_num = min(len(artwork_data.pages), show_page_limiting)
    if len(artwork_data.pages) > show_page_num:
        artwork_desc = f'({show_page_limiting} of {len(artwork_data.pages)} pages)\n{"-" * 16}\n{artwork_desc}'

    tasks = [
        artwork_ap.get_custom_proceed_page_file(page_index=page_index, process_mode=process_mode)
        for page_index in range(show_page_num)
    ]
    proceed_pages = await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)

    # 拼接待发送消息
    send_msg = OmegaMessage(OmegaMessageSegment.image(url=x.path) for x in proceed_pages)
    if message_prefix is not None:
        send_msg = message_prefix + send_msg + f'\n{artwork_desc}'
    else:
        send_msg = send_msg + f'\n{artwork_desc}'
    return send_msg


async def _msg_sender(entity: "Entity", message: OmegaMessage) -> None:
    """向 entity 发送消息"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            interface = OmEI(entity=internal_entity)
            await interface.send_entity_message(message=message)
    except ActionFailed as e:
        logger.warning(f'PixivUserSubscriptionMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'PixivUserSubscriptionMonitor | Sending message to {entity} failed, {e!r}')


async def pixiv_user_new_artworks_monitor_main(pixiv_user: "PixivUser") -> None:
    """向已订阅的用户或群发送 Pixiv 用户更新的作品"""
    logger.debug(f'PixivUserSubscriptionMonitor | Start checking pixiv {pixiv_user} new artworks')
    user_data = await pixiv_user.query_user_data()

    new_pids = await _check_pixiv_user_new_artworks(pixiv_user=pixiv_user)
    if new_pids:
        logger.info(
            f'PixivUserSubscriptionMonitor | Confirmed {pixiv_user} new artworks: {", ".join(str(x) for x in new_pids)}'
        )
    else:
        logger.debug(f'PixivUserSubscriptionMonitor | {pixiv_user} has not new artworks')
        return

    # 获取作品更新消息内容
    message_prefix = f'【Pixiv】{user_data.name}发布了新的作品!\n'
    format_msg_tasks = [
        _format_pixiv_user_new_artwork_message(pid=pid, message_prefix=message_prefix)
        for pid in new_pids
    ]
    send_messages = await semaphore_gather(tasks=format_msg_tasks, semaphore_num=3, return_exceptions=False)

    # 数据库中插入新作品信息
    add_artwork_tasks = [PixivArtworkCollection(pid).add_artwork_into_database_ignore_exists() for pid in new_pids]
    await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=8, return_exceptions=False)

    # 向订阅者发送新作品信息
    subscribed_entity = await query_subscribed_entity_by_pixiv_user(pixiv_user=pixiv_user)
    send_tasks = [
        _msg_sender(entity=entity, message=send_msg)
        for entity in subscribed_entity for send_msg in send_messages
    ]
    await semaphore_gather(tasks=send_tasks, semaphore_num=2)


"""作品预览图生成工具"""


async def generate_artworks_preview(title: str, pids: Sequence[int], *, no_blur_rating: int = 1) -> "TemporaryResource":
    """生成多个作品的预览图"""
    return await PixivArtworkProxy.generate_artworks_preview(
        preview_name=title,
        artworks=[PixivArtworkProxy(pid) for pid in pids],
        no_blur_rating=no_blur_rating,
        preview_size=(360, 360),
        num_of_line=6,
    )


async def _generate_ranking_preview(title: str, ranking_data: "PixivRankingModel") -> "TemporaryResource":
    """根据榜单数据生成预览图"""
    return await PixivArtworkProxy.generate_artworks_preview(
        preview_name=title,
        artworks=[PixivArtworkProxy(x.illust_id) for x in ranking_data.contents],
        preview_size=(512, 512),
        num_of_line=6,
    )


def get_ranking_preview_factory(
        mode: Literal['daily', 'weekly', 'monthly'],
) -> Callable[[int], Coroutine[Any, Any, "TemporaryResource"]]:
    """获取榜单预览图生成器"""

    async def _factor(page: int) -> "TemporaryResource":
        ranking_data = await PixivUser.query_ranking(mode=mode, page=page, content='illust')

        title = f'Pixiv {mode.title()} Ranking {datetime.now().strftime("%Y-%m-%d")}'
        return await _generate_ranking_preview(title=title, ranking_data=ranking_data)

    return _factor


async def handle_ranking_preview(
        interface: "OmMI",
        page: str,
        ranking_preview_factory: Callable[[int], Coroutine[Any, Any, "TemporaryResource"]]
) -> None:
    """生成并发送榜单预览图"""
    page = page.strip()
    if not page.isdigit():
        await interface.finish_reply('榜单页码应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在获取榜单作品~')

    try:
        ranking_img = await ranking_preview_factory(int(page))
        await interface.send_reply(OmegaMessageSegment.image(ranking_img.path))
    except Exception as e:
        logger.error(f'PixivRanking | 获取榜单内容(page={ranking_preview_factory!r})失败, {e}')
        await interface.send_reply('获取榜单内容失败了QAQ, 请稍后再试')


__all__ = [
    'add_pixiv_user_sub',
    'delete_pixiv_user_sub',
    'query_entity_subscribed_pixiv_user_sub_source',
    'query_all_subscribed_pixiv_user_sub_source',
    'pixiv_user_new_artworks_monitor_main',
    'generate_artworks_preview',
    'get_ranking_preview_factory',
    'handle_ranking_preview',
]
