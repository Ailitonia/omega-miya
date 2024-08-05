"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Pixiv Plugin Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
from copy import deepcopy
from typing import Literal

from nonebot.adapters import Message
from nonebot.exception import ActionFailed
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import ArgumentParser, Namespace
from nonebot.utils import run_sync
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import NoResultFound

from src.database import PixivArtworkDAL, begin_db_session
from src.database.internal.entity import Entity
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType
from src.resource import TemporaryResource
from src.service import OmegaInterface, OmegaEntity, OmegaMessage, OmegaMessageSegment
from src.service.artwork_collection import PixivArtworkCollection
from src.service.artwork_proxy import PixivArtworkProxy
from src.service.omega_base.internal import OmegaPixivUserSubSource
from src.utils.image_utils import ImageUtils
from src.utils.pixiv_api import PixivArtwork, PixivUser
from src.utils.process_utils import semaphore_gather
from .config import pixiv_plugin_config, pixiv_plugin_resource_config
from .consts import ALLOW_R18_NODE

PIXIV_USER_SUB_TYPE: str = SubscriptionSourceType.pixiv_user.value
"""Pixiv 用户订阅类型"""


async def _has_allow_r18_node(matcher: Matcher, interface: OmegaInterface) -> bool:
    """判断当前 entity 主体是否具有允许预览 r18 作品的权限"""
    return (
            await interface.entity.check_global_permission() and
            await interface.entity.check_auth_setting(
                module=matcher.plugin.module_name,
                plugin=matcher.plugin.name,
                node=ALLOW_R18_NODE
            )
    )


async def has_allow_r18_node(matcher: Matcher, interface: OmegaInterface) -> bool:
    """判断当前 entity 主体是否具有允许预览 r18 作品的权限"""
    try:
        allow_r18 = await _has_allow_r18_node(matcher=matcher, interface=interface)
    except Exception as e:
        logger.warning(f'Checking {interface.entity} r18 node failed, {e!r}')
        allow_r18 = False
    return allow_r18


async def _prepare_artwork_preview(
        artwork: PixivArtworkProxy,
        *,
        allow_r18: bool = False,
        message_prefix: str | None = None,
) -> Message:
    """预处理待发送的单个作品预览

    :param artwork: Pixiv 作品
    :param allow_r18: 是否允许预览 r18 作品
    :param message_prefix: 消息前缀
    :return: 发送的消息
    """

    @run_sync
    def _handle_noise(image: TemporaryResource) -> ImageUtils:
        """噪点处理图片"""
        image = ImageUtils.init_from_file(file=image)
        image.gaussian_noise(sigma=16)
        image.mark(text=f'Pixiv | {artwork.s_aid}')
        return image

    @run_sync
    def _handle_blur(image: TemporaryResource) -> ImageUtils:
        """模糊处理图片"""
        image = ImageUtils.init_from_file(file=image)
        image.gaussian_blur()
        image.mark(text=f'Pixiv | {artwork.s_aid}')
        return image

    @run_sync
    def _handle_mark(image: TemporaryResource) -> ImageUtils:
        """标记水印"""
        image = ImageUtils.init_from_file(file=image)
        image.mark(text=f'Pixiv | {artwork.s_aid}')
        return image

    async def _handle_image(
            image_: TemporaryResource,
            file_name_prefix: str
    ) -> TemporaryResource:
        """异步处理图片"""
        is_r18 = True if (await artwork.query()).rating.value >= 3 else False
        if is_r18 and allow_r18:
            image = await _handle_noise(image=image_)
            file_name = f'{file_name_prefix}_noise_sigma16_marked.jpg'
        elif is_r18 and not allow_r18:
            image = await _handle_blur(image=image_)
            file_name = f'{file_name_prefix}_blur_marked.jpg'
        else:
            image = await _handle_mark(image=image_)
            file_name = f'{file_name_prefix}_marked.jpg'

        output_file_ = pixiv_plugin_resource_config.default_processed_image_folder(file_name)
        return await image.save(file=output_file_)

    preview_page_limiting = pixiv_plugin_config.pixiv_plugin_artwork_preview_page_limiting

    artwork_data = await artwork.query()
    artwork_desc = await artwork.get_std_desc()

    # 生成作品预览
    artwork_pages = await artwork.get_all_pages_file(page_limit=preview_page_limiting)
    tasks = [_handle_image(x, file_name_prefix=x.path.name.removesuffix(x.path.suffix)) for x in artwork_pages]
    send_pages = await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)
    send_msg = OmegaMessage(OmegaMessageSegment.image(url=x.path) for x in send_pages)

    if len(artwork_data.pages) > preview_page_limiting:
        artwork_desc = f'({preview_page_limiting} of {len(artwork_data.pages)} pages)\n{"-" * 16}\n{artwork_desc}'

    if message_prefix is not None:
        send_msg = message_prefix + send_msg + f'\n{artwork_desc}'
    else:
        send_msg += f'\n{artwork_desc}'

    return send_msg


async def get_artwork_preview(
        artwork: PixivArtworkProxy,
        *,
        allow_r18: bool = False,
        message_prefix: str | None = None
) -> str | Message:
    """获取单个作品预览

    :param artwork: Pixiv 作品
    :param message_prefix: 消息前缀
    :param allow_r18: 是否允许预览 r18 作品
    :return: 发送的消息
    """
    try:
        message = await _prepare_artwork_preview(artwork=artwork, allow_r18=allow_r18, message_prefix=message_prefix)
    except Exception as e:
        logger.error(f'Pixiv | 获取作品 {artwork} 预览失败, {e}')
        message = '获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试'
    return message


def get_searching_argument_parser() -> ArgumentParser:
    """搜索命令的 shell command argument parser"""
    parser = ArgumentParser(prog='搜索命令参数解析', description='Parse searching arguments')
    parser.add_argument('-c', '--custom', action='store_true')
    parser.add_argument('-m', '--mode', type=str, default='artworks', choices=['artworks', 'illustrations', 'manga'])
    parser.add_argument('-a', '--ai-type', type=int, default=1)
    parser.add_argument('-p', '--page', type=int, default=1)
    parser.add_argument('-o', '--order', type=str, default='date_d', choices=['date_d', 'popular_d'])
    parser.add_argument('-l', '--like', type=int, default=0)
    parser.add_argument('-d', '--from-days-ago', type=int, default=0)
    parser.add_argument('-s', '--safe-mode', type=str, default='safe', choices=['safe', 'all', 'r18'])
    parser.add_argument('word', nargs='+')
    return parser


class SearchingArguments(BaseModel):
    """搜索命令 argument parser 的解析结果 Model"""
    custom: bool = False
    mode: Literal['artworks', 'illustrations', 'manga']
    ai_type: int
    page: int
    order: Literal['date_d', 'popular_d']
    like: int
    from_days_ago: int
    safe_mode: Literal['safe', 'all', 'r18']
    word: list[str]
    model_config = ConfigDict(extra='ignore', from_attributes=True)


def parse_from_searching_parser(args: Namespace) -> SearchingArguments:
    """解析搜索命令参数"""
    return SearchingArguments.model_validate(args)


async def _add_artwork_into_database(artwork: PixivArtwork) -> None:
    """在数据库中添加作品信息(仅新增不更新)"""
    artwork_data = await artwork.query_artwork()
    nsfw_tag = 2 if artwork_data.is_r18 else -1
    classified = 2 if artwork_data.is_ai else 0

    # 作品信息写入数据库
    pixiv_collection = PixivArtworkCollection(artwork_id=str(artwork.pid))
    await pixiv_collection.add_ignore_exists(
        uid=artwork_data.uid, title=artwork_data.title, uname=artwork_data.uname,
        classified=classified, nsfw_tag=nsfw_tag,
        width=artwork_data.width, height=artwork_data.height, tags=','.join(artwork_data.tags),
        url=artwork_data.url
    )
    for index, url in artwork_data.all_page.items():
        await pixiv_collection.add_page_ignore_exists(
            page=index, original=url.original, regular=url.regular,
            small=url.small, thumb_mini=url.thumb_mini
        )


async def _add_upgrade_pixiv_user_artworks(pixiv_user: PixivUser) -> None:
    """在数据库中新增目标用户的全部作品(仅新增不更新)"""
    user_data = await pixiv_user.query_user_data()

    # 应对 pixiv 流控, 对获取作品信息进行分段处理
    all_pids = deepcopy(user_data.manga_illusts)
    handle_pids = []
    fail_count = 0
    while all_pids:
        while len(handle_pids) < 20:
            try:
                handle_pids.append(all_pids.pop())
            except IndexError:
                break

        tasks = [_add_artwork_into_database(artwork=PixivArtwork(pid=pid)) for pid in handle_pids]
        handle_pids.clear()
        import_result = await semaphore_gather(tasks=tasks, semaphore_num=20)
        fail_count += len([x for x in import_result if isinstance(x, Exception)])

        if all_pids:
            logger.debug(f'PixivUserAdder | Adding user({user_data.user_id}) artworks, {len(all_pids)} remaining')
            await asyncio.sleep(int((len(all_pids) if len(all_pids) < 20 else 20) * 1.5))

    logger.info(f'PixivUserAdder | Adding user({user_data.user_id}) artworks completed, failed: {fail_count}')


async def _query_pixiv_user_sub_source(uid: int) -> SubscriptionSource:
    """从数据库查询 Pixiv 用户订阅源"""
    async with begin_db_session() as session:
        source_res = await OmegaPixivUserSubSource(session=session, uid=uid).query_subscription_source()
    return source_res


async def _add_upgrade_pixiv_user_sub_source(pixiv_user: PixivUser) -> SubscriptionSource:
    """在数据库中新增目标用户订阅源"""
    user_data = await pixiv_user.query_user_data()

    async with begin_db_session() as session:
        sub_source = OmegaPixivUserSubSource(session=session, uid=pixiv_user.uid)
        try:
            # 订阅源已存在则直接返回
            source_res = await sub_source.query_subscription_source()
        except NoResultFound:
            await _add_upgrade_pixiv_user_artworks(pixiv_user=pixiv_user)
            await sub_source.add_upgrade(sub_user_name=user_data.name, sub_info='Pixiv用户订阅')
            source_res = await sub_source.query_subscription_source()

    return source_res


async def add_pixiv_user_sub(interface: OmegaInterface, pixiv_user: PixivUser) -> None:
    """为目标对象添加 Pixiv 用户订阅"""
    source_res = await _add_upgrade_pixiv_user_sub_source(pixiv_user=pixiv_user)
    await interface.entity.add_subscription(subscription_source=source_res,
                                            sub_info=f'Pixiv用户订阅(uid={pixiv_user.uid})')


async def delete_pixiv_user_sub(interface: OmegaInterface, uid: int) -> None:
    """为目标对象删除 Pixiv 用户订阅"""
    source_res = await _query_pixiv_user_sub_source(uid=uid)
    await interface.entity.delete_subscription(subscription_source=source_res)


async def query_entity_subscribed_user_sub_source(interface: OmegaInterface) -> dict[str, str]:
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


async def query_subscribed_entity_by_pixiv_user(pixiv_user: PixivUser) -> list[Entity]:
    """根据 Pixiv 用户查询已经订阅了这个用户的内部 Entity 对象"""
    async with begin_db_session() as session:
        sub_source = OmegaPixivUserSubSource(session=session, uid=pixiv_user.uid)
        subscribed_entity = await sub_source.query_all_entity_subscribed()
    return subscribed_entity


async def _check_user_new_artworks(pixiv_user: PixivUser) -> list[int]:
    """检查 Pixiv 用户的新作品(数据库中没有的)"""
    user_data = await pixiv_user.query_user_data()
    async with begin_db_session() as session:
        new_pids = await PixivArtworkDAL(session=session).query_not_exists_ids(pids=user_data.manga_illusts)
    return new_pids


async def _msg_sender(entity: Entity, message: str | Message) -> None:
    """向 entity 发送消息"""
    try:
        async with begin_db_session() as session:
            internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)
            interface = OmegaInterface(entity=internal_entity)
            await interface.send_msg(message=message)
    except ActionFailed as e:
        logger.warning(f'PixivUserSubscriptionMonitor | Sending message to {entity} failed with ActionFailed, {e!r}')
    except Exception as e:
        logger.error(f'PixivUserSubscriptionMonitor | Sending message to {entity} failed, {e!r}')


async def pixiv_user_new_artworks_monitor_main(pixiv_user: PixivUser) -> None:
    """向已订阅的用户或群发送 Pixiv 用户更新的作品"""
    logger.debug(f'PixivUserSubscriptionMonitor | Start checking pixiv {pixiv_user} new artworks')
    user_data = await pixiv_user.query_user_data()

    new_pids = await _check_user_new_artworks(pixiv_user=pixiv_user)
    if new_pids:
        logger.info(f'PixivUserSubscriptionMonitor | Confirmed {pixiv_user} '
                    f'new artworks: {", ".join(str(x) for x in new_pids)}')
    else:
        logger.debug(f'PixivUserSubscriptionMonitor | {pixiv_user} has not new artworks')
        return

    # 获取作品更新消息内容
    message_prefix = f'【Pixiv】{user_data.name}发布了新的作品!\n'
    preview_msg_tasks = [get_artwork_preview(artwork=PixivArtworkProxy(p), message_prefix=message_prefix) for p in
                         new_pids]
    send_messages = await semaphore_gather(tasks=preview_msg_tasks, semaphore_num=3, return_exceptions=False)

    # 数据库中插入新作品信息
    add_artwork_tasks = [_add_artwork_into_database(artwork=PixivArtwork(pid=pid)) for pid in new_pids]
    await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=10, return_exceptions=False)

    # 向订阅者发送新作品信息
    subscribed_entity = await query_subscribed_entity_by_pixiv_user(pixiv_user=pixiv_user)
    send_tasks = [
        _msg_sender(entity=entity, message=send_msg)
        for entity in subscribed_entity for send_msg in send_messages
    ]
    await semaphore_gather(tasks=send_tasks, semaphore_num=2)


__all__ = [
    'has_allow_r18_node',
    'get_artwork_preview',
    'get_searching_argument_parser',
    'parse_from_searching_parser',
    'add_pixiv_user_sub',
    'delete_pixiv_user_sub',
    'query_entity_subscribed_user_sub_source',
    'query_all_subscribed_pixiv_user_sub_source',
    'pixiv_user_new_artworks_monitor_main'
]
