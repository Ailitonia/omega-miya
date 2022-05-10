"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Pixiv Plugin Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from pydantic import BaseModel
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import ArgumentParser, Namespace
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment, Message

from omega_miya.database import InternalBotUser, InternalBotGroup, InternalPixiv, InternalSubscriptionSource
from omega_miya.database.internal.entity import BaseInternalEntity
from omega_miya.result import BoolResult
from omega_miya.local_resource import TmpResource
from omega_miya.web_resource.pixiv import PixivArtwork, PixivUser
from omega_miya.utils.process_utils import run_async_catching_exception, run_sync, semaphore_gather
from omega_miya.utils.image_utils import ImageUtils
from omega_miya.utils.message_tools import MessageSender

from .config import pixiv_plugin_config


_ALLOW_R18_NODE = pixiv_plugin_config.pixiv_plugin_allow_r18_node
"""允许预览 r18 作品的权限节点"""
_USER_SUB_TYPE = pixiv_plugin_config.pixiv_plugin_user_subscription_type
"""pixiv 画师订阅 SubscriptionSource 的 sub_type"""


def _get_event_entity(bot: Bot, event: MessageEvent) -> BaseInternalEntity:
    """根据 event 获取不同 entity 对象"""
    if isinstance(event, GroupMessageEvent):
        entity = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.group_id))
    else:
        entity = InternalBotUser(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.user_id))
    return entity


@run_async_catching_exception
async def _has_allow_r18_node(bot: Bot, event: MessageEvent, matcher: Matcher) -> bool:
    """判断当前 event 主体是否具有允许预览 r18 作品的权限"""
    entity = _get_event_entity(bot=bot, event=event)
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    check_result = await entity.check_auth_setting(module=module_name, plugin=plugin_name, node=_ALLOW_R18_NODE)
    return check_result


async def has_allow_r18_node(bot: Bot, event: MessageEvent, matcher: Matcher) -> bool:
    """判断当前 event 主体是否具有允许预览 r18 作品的权限"""
    allow_r18 = await _has_allow_r18_node(bot=bot, event=event, matcher=matcher)
    if isinstance(allow_r18, Exception):
        allow_r18 = False
    return allow_r18


@run_async_catching_exception
async def _get_artwork_preview(
        pid: int,
        message_prefix: str | None = None,
        *,
        allow_r18: bool = False,
        preview_page_limiting: int = pixiv_plugin_config.pixiv_plugin_artwork_preview_page_limiting,
        generate_gif: bool = pixiv_plugin_config.pixiv_plugin_enable_generate_gif
) -> (Message, bool):
    """获取单个作品预览

    :param pid: 作品 PID
    :param message_prefix: 消息前缀
    :param allow_r18: 是否允许预览 r18 作品
    :param preview_page_limiting: 单个作品发送预览图片数量限制
    :param generate_gif: 是否对动态作品生成动图
    :return: 发送的消息, 消息是否需要撤回
    """

    async def _handle_r18_blur(image: TmpResource) -> TmpResource:
        """模糊处理 r18 图"""
        _image = await run_sync(ImageUtils.init_from_file)(file=image)
        await run_sync(_image.gaussian_blur)()
        return await _image.save(file_name=f'{image.path.name}_blur.jpg')

    async def _handle_r18_noise(image: TmpResource) -> TmpResource:
        """噪点处理 r18 图"""
        _image = await run_sync(ImageUtils.init_from_file)(file=image)
        await run_sync(_image.gaussian_noise)(sigma=16)
        return await _image.save(file_name=f'{image.path.name}_noise_sigma16.jpg')

    artwork = PixivArtwork(pid=pid)
    artwork_data = await artwork.get_artwork_model()
    need_recall = artwork_data.is_r18
    artwork_desc = await artwork.format_desc_msg()

    if generate_gif and artwork_data.illust_type == 2 and (
            allow_r18 and artwork_data.is_r18 or not artwork_data.is_r18):
        # 启用了动图作品生成 gif
        artwork_gif = await artwork.generate_ugoira_gif(original=False)
        send_msg = MessageSegment.image(artwork_gif.file_uri)
    else:
        # 直接生成作品预览
        artwork_pages = await artwork.get_all_page_file(page_limit=preview_page_limiting)

        if not allow_r18 and artwork_data.is_r18:
            blur_tasks = [_handle_r18_blur(x) for x in artwork_pages]
            artwork_pages = await semaphore_gather(tasks=blur_tasks, semaphore_num=10, return_exceptions=False)
            need_recall = False
        elif allow_r18 and artwork_data.is_r18:
            noise_tasks = [_handle_r18_noise(x) for x in artwork_pages]
            artwork_pages = await semaphore_gather(tasks=noise_tasks, semaphore_num=10, return_exceptions=False)
        send_msg = Message(MessageSegment.image(file=x.file_uri) for x in artwork_pages)

    if message_prefix is not None:
        send_msg = message_prefix + send_msg + f'\n{artwork_desc}'
    else:
        send_msg += f'\n{artwork_desc}'
    return send_msg, need_recall


async def get_artwork_preview(
        pid: int,
        message_prefix: str | None = None,
        *,
        allow_r18: bool = False,
        preview_page_limiting: int = pixiv_plugin_config.pixiv_plugin_artwork_preview_page_limiting,
        generate_gif: bool = pixiv_plugin_config.pixiv_plugin_enable_generate_gif
) -> (str | Message, bool):
    """获取单个作品预览

    :param pid: 作品 PID
    :param message_prefix: 消息前缀
    :param allow_r18: 是否允许预览 r18 作品
    :param preview_page_limiting: 单个作品发送预览图片数量限制
    :param generate_gif: 是否对动态作品生成动图
    :return: 发送的消息, 消息是否需要撤回
    """
    result = await _get_artwork_preview(pid=pid, message_prefix=message_prefix, allow_r18=allow_r18,
                                        preview_page_limiting=preview_page_limiting, generate_gif=generate_gif)
    if isinstance(result, Exception):
        logger.error(f'Pixiv | 获取作品(pid={pid})预览失败, {result}')
        send_message = '获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试'
        need_recall = False
    else:
        send_message, need_recall = result
    return send_message, need_recall


def get_searching_argument_parser() -> ArgumentParser:
    """搜索命令的 shell command argument parser"""
    parser = ArgumentParser(prog='搜索命令参数解析', description='Parse searching arguments')
    parser.add_argument('-c', '--custom', action='store_true')
    parser.add_argument('-m', '--mode', type=str, default='artworks', choices=['artworks', 'illustrations', 'manga'])
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
    page: int
    order: Literal['date_d', 'popular_d']
    like: int
    from_days_ago: int
    safe_mode: Literal['safe', 'all', 'r18']
    word: list[str]

    class Config:
        orm_mode = True


def parse_from_searching_parser(args: Namespace) -> SearchingArguments:
    """解析搜索命令参数"""
    return SearchingArguments.from_orm(args)


async def add_artwork_into_database(artwork: PixivArtwork, *, upgrade_pages: bool = True) -> BoolResult:
    """在数据库中添加作品信息(仅新增不更新)"""
    artwork_data = await artwork.get_artwork_model()
    nsfw_tag = 2 if artwork_data.is_r18 else -1
    result = await InternalPixiv(pid=artwork.pid).add_only(artwork_data=artwork_data, nsfw_tag=nsfw_tag,
                                                           upgrade_pages=upgrade_pages)
    return result


async def _add_pixiv_user_artworks_to_database(pixiv_user: PixivUser) -> BoolResult:
    """在数据库中新增目标用户的全部作品(仅新增不更新)"""
    user_data = await pixiv_user.get_user_model()
    tasks = [add_artwork_into_database(artwork=PixivArtwork(pid=pid), upgrade_pages=False)
             for pid in user_data.manga_illusts]
    add_result = await semaphore_gather(tasks=tasks, semaphore_num=25)
    if error := [x for x in add_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)
    return BoolResult(error=False, info='Success', result=True)


async def _add_pixiv_user_sub_source(pixiv_user: PixivUser) -> BoolResult:
    """在数据库中新增目标用户订阅源"""
    sub_source = InternalSubscriptionSource(sub_type=_USER_SUB_TYPE, sub_id=str(pixiv_user.uid))
    # 订阅源已存在则直接返回
    if await sub_source.exist():
        return BoolResult(error=False, info='PixivUserSubscriptionSource exist', result=True)

    add_artworks_result = await _add_pixiv_user_artworks_to_database(pixiv_user=pixiv_user)
    if add_artworks_result.error:
        return add_artworks_result

    user_data = await pixiv_user.get_user_model()
    add_source_result = await sub_source.add_upgrade(sub_user_name=user_data.name, sub_info='Pixiv用户订阅')
    return add_source_result


@run_async_catching_exception
async def add_pixiv_user_sub(bot: Bot, event: MessageEvent, pixiv_user: PixivUser) -> BoolResult:
    """根据 event 为群或用户添加 Pixiv 用户订阅"""
    entity = _get_event_entity(bot=bot, event=event)
    add_source_result = await _add_pixiv_user_sub_source(pixiv_user=pixiv_user)
    if add_source_result.error:
        return add_source_result

    add_sub_result = await entity.add_subscription(sub_type=_USER_SUB_TYPE, sub_id=str(pixiv_user.uid),
                                                   sub_info=f'Pixiv用户订阅(uid={pixiv_user.uid})')
    return add_sub_result


@run_async_catching_exception
async def delete_pixiv_user_sub(bot: Bot, event: MessageEvent, user_id: str) -> BoolResult:
    """根据 event 为群或用户删除 Pixiv 用户订阅"""
    entity = _get_event_entity(bot=bot, event=event)
    add_sub_result = await entity.delete_subscription(sub_type=_USER_SUB_TYPE, sub_id=user_id)
    return add_sub_result


@run_async_catching_exception
async def query_subscribed_user_sub_source(bot: Bot, event: MessageEvent) -> list[tuple[str, str]]:
    """根据 event 获取群或用户已订阅的 Pixiv 用户

    :return: 用户 UID, 用户昵称 的列表"""
    entity = _get_event_entity(bot=bot, event=event)
    subscribed_source = await entity.query_all_subscribed_source(sub_type=_USER_SUB_TYPE)
    sub_id_result = [(x.sub_id, x.sub_user_name) for x in subscribed_source]
    return sub_id_result


async def query_all_pixiv_user_subscription_source() -> list[int]:
    """获取所有已添加的 Pixiv 用户订阅源

    :return: 用户 UID 列表
    """
    source_result = await InternalSubscriptionSource.query_all_by_sub_type(sub_type=_USER_SUB_TYPE)
    result = [int(x.sub_id) for x in source_result]
    return result


async def _query_subscribed_entity_by_pixiv_user(pixiv_user: PixivUser) -> list[BaseInternalEntity]:
    """根据 Pixiv 用户查询已经订阅了这个用户的内部 Entity 对象"""
    sub_source = InternalSubscriptionSource(sub_type=_USER_SUB_TYPE, sub_id=str(pixiv_user.uid))
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


async def _check_user_new_artworks(pixiv_user: PixivUser) -> list[int]:
    """检查 Pixiv 用户的新作品(数据库中没有的)"""
    user_data = await pixiv_user.get_user_model()
    check_tasks = [InternalPixiv(pid=pid).exist() for pid in user_data.manga_illusts]
    check_result = await semaphore_gather(tasks=check_tasks, semaphore_num=50)
    if error := [x for x in check_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    new_pid = [x[0] for x in check_result if not x[1]]
    return new_pid


async def _msg_sender(entity: BaseInternalEntity, message: str | Message) -> int:
    """向 entity 发送消息"""
    try:
        msg_sender = MessageSender.init_from_bot_id(bot_id=entity.bot_id)
        sent_msg_id = await msg_sender.send_internal_entity_msg(entity=entity, message=message)
    except KeyError:
        logger.debug(f'PixivUserSubscriptionMonitor | Bot({entity.bot_id}) not online, '
                     f'message to {entity.relation.relation_type.upper()}({entity.entity_id}) has be canceled')
        sent_msg_id = 0
    return sent_msg_id


@run_async_catching_exception
async def send_pixiv_user_new_artworks(pixiv_user: PixivUser) -> None:
    """向已订阅的用户或群发送 Pixiv 用户更新的作品"""
    logger.debug(f'PixivUserSubscriptionMonitor | Start checking pixiv user({pixiv_user.uid}) new artworks')
    user_data = await pixiv_user.get_user_model()
    new_pids = await _check_user_new_artworks(pixiv_user=pixiv_user)
    if new_pids:
        logger.info(f'PixivUserSubscriptionMonitor | Confirmed pixiv user({pixiv_user.uid}) '
                    f'new artworks: {", ".join(str(x) for x in new_pids)}')
    else:
        logger.debug(f'PixivUserSubscriptionMonitor | Pixiv user({pixiv_user.uid}) has not new artworks')
        return

    subscribed_entity = await _query_subscribed_entity_by_pixiv_user(pixiv_user=pixiv_user)
    # 获取作品更新消息内容
    message_prefix = f'【Pixiv】{user_data.name}发布了新的作品!\n'
    preview_msg_tasks = [get_artwork_preview(pid=pid, message_prefix=message_prefix) for pid in new_pids]
    send_messages = await semaphore_gather(tasks=preview_msg_tasks, semaphore_num=5)
    if error := [x for x in send_messages if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    # 数据库中插入新作品信息
    add_artwork_tasks = [add_artwork_into_database(artwork=PixivArtwork(pid=pid)) for pid in new_pids]
    add_result = await semaphore_gather(tasks=add_artwork_tasks, semaphore_num=10)
    if error := [x for x in add_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    # 向订阅者发送新作品信息
    send_tasks = [_msg_sender(entity=entity, message=send_message[0])
                  for entity in subscribed_entity for send_message in send_messages]
    sent_result = await semaphore_gather(tasks=send_tasks, semaphore_num=2)
    if error := [x for x in sent_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)


__all__ = [
    'has_allow_r18_node',
    'get_artwork_preview',
    'get_searching_argument_parser',
    'parse_from_searching_parser',
    'add_artwork_into_database',
    'add_pixiv_user_sub',
    'delete_pixiv_user_sub',
    'query_subscribed_user_sub_source',
    'query_all_pixiv_user_subscription_source',
    'send_pixiv_user_new_artworks'
]
