"""
@Author         : Ailitonia
@Date           : 2022/05/1 17:48
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Moe Plugin Utils
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
from nonebot.adapters.onebot.v11 import MessageSegment, Message

from omega_miya.database import InternalBotUser, InternalBotGroup, InternalPixiv, InternalSubscriptionSource
from omega_miya.database.internal.entity import BaseInternalEntity
from omega_miya.result import BoolResult
from omega_miya.local_resource import TmpResource
from omega_miya.web_resource.pixiv import PixivArtwork, PixivUser
from omega_miya.utils.process_utils import run_async_catching_exception, run_sync, semaphore_gather
from omega_miya.utils.image_utils import ImageUtils
from omega_miya.utils.message_tools import MessageSender

from .config import moe_plugin_config, moe_plugin_resource_config


_ALLOW_R18_NODE = moe_plugin_config.moe_plugin_allow_r18_node
"""允许预览 r18 作品的权限节点"""
_Import_pids_file: TmpResource


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
async def prepare_send_image(
        pid: int,
        *,
        enable_flash_mode: bool = moe_plugin_config.moe_plugin_enable_flash_mode
) -> (MessageSegment, bool):
    """预处理待发送图片

    :param pid: 作品 PID
    :param enable_flash_mode: 是否启用闪照模式
    :return: 发送的消息, 消息是否需要撤回
    """

    async def _handle_noise(image: TmpResource) -> TmpResource:
        """噪点处理图片"""
        _image = await run_sync(ImageUtils.init_from_file)(file=image)
        await run_sync(_image.gaussian_noise)(sigma=16)
        await run_sync(_image.mark)(text=f'Pixiv | {pid}')
        return await _image.save(file_name=f'{image.path.name}_noise_sigma16_marked.jpg')

    async def _handle_mark(image: TmpResource) -> TmpResource:
        """标记水印"""
        _image = await run_sync(ImageUtils.init_from_file)(file=image)
        await run_sync(_image.mark)(text=f'Pixiv | {pid}')
        return await _image.save(file_name=f'{image.path.name}_marked.jpg')

    internal_artwork = InternalPixiv(pid=pid)
    database_artwork_data = await internal_artwork.get_artwork_model()
    need_recall = False if database_artwork_data.nsfw_tag == 0 else True

    # 获取并处理作品图片
    artwork = PixivArtwork(pid=pid)
    artwork_image = await artwork.get_page_file()
    if need_recall:
        artwork_image = await _handle_noise(image=artwork_image)
    else:
        artwork_image = await _handle_mark(image=artwork_image)

    if enable_flash_mode:
        send_msg = MessageSegment.image(file=artwork_image.file_uri, type_='flash')
    else:
        send_msg = MessageSegment.image(file=artwork_image.file_uri)
    return send_msg, need_recall


def get_query_argument_parser() -> ArgumentParser:
    """查询图库的 shell command argument parser"""
    parser = ArgumentParser(prog='图库查询命令参数解析', description='Parse searching arguments')
    parser.add_argument('-s', '--nsfw-tag', type=int, default=0)
    parser.add_argument('-i', '--classified', type=int, default=1)
    parser.add_argument('-o', '--order', type=str, default='random',
                        choices=['random', 'pid', 'pid_desc', 'create_time', 'create_time_desc'])
    parser.add_argument('-n', '--num', type=int, default=moe_plugin_config.moe_plugin_query_image_num)
    parser.add_argument('-a', '--acc-mode', type=bool, default=moe_plugin_config.moe_plugin_enable_acc_mode)
    parser.add_argument('-nf', '--no-flash', action='store_true',
                        default=(not moe_plugin_config.moe_plugin_enable_flash_mode))
    parser.add_argument('word', nargs='*')
    return parser


class QueryArguments(BaseModel):
    """查询图库命令 argument parser 的解析结果 Model"""
    nsfw_tag: int
    classified: int
    order: Literal['random', 'pid', 'pid_desc', 'create_time', 'create_time_desc']
    num: int
    acc_mode: bool
    no_flash: bool
    word: list[str]

    class Config:
        orm_mode = True


def parse_from_query_parser(args: Namespace) -> QueryArguments:
    """解析查询命令参数"""
    return QueryArguments.from_orm(args)


async def add_artwork_into_database(
        artwork: PixivArtwork,
        nsfw_tag: int,
        *,
        upgrade_pages: bool = True,
        add_only: bool = True
) -> BoolResult:
    """在数据库中添加作品信息"""
    artwork_data = await artwork.get_artwork_model()
    nsfw_tag = 2 if artwork_data.is_r18 else nsfw_tag
    if add_only:
        result = await InternalPixiv(pid=artwork.pid).add_only(artwork_data=artwork_data, nsfw_tag=nsfw_tag,
                                                               classified=1, upgrade_pages=upgrade_pages)
    else:
        result = await InternalPixiv(pid=artwork.pid).add_upgrade(artwork_data=artwork_data, nsfw_tag=nsfw_tag,
                                                                  classified=1, upgrade_pages=upgrade_pages)
    return result


@run_async_catching_exception
async def _get_database_import_pids() -> list[int]:
    """从本地文件中读取需要导入数据库的图片 PID"""
    async with moe_plugin_resource_config.default_database_import_file.async_open('r', encoding='utf-8') as af:
        pids = [int(x.strip()) for x in await af.readlines() if x.strip().isdigit()]
    return pids


async def get_database_import_pids() -> list[int]:
    pids = await _get_database_import_pids()
    if isinstance(pids, Exception):
        logger.error(f'MoeDatabaseImport | 从文件中读取导入文件列表失败, {pids}, '
                     f'请确认导入文件{moe_plugin_resource_config.default_database_import_file.resolve_path}存在')
        pids = []
    return pids


__all__ = [
    'has_allow_r18_node',
    'prepare_send_image',
    'get_query_argument_parser',
    'parse_from_query_parser',
    'add_artwork_into_database',
    'get_database_import_pids'
]
