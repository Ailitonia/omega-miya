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
from pydantic import BaseModel, ConfigDict
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import ArgumentParser, Namespace
from nonebot.utils import run_sync

from src.database import begin_db_session
from src.service.omega_base import OmegaInterface, OmegaMessageSegment
from src.service.omega_base.internal import OmegaPixivArtwork
from src.resource import TemporaryResource
from src.utils.pixiv_api import PixivArtwork
from src.utils.image_utils import ImageUtils

from .config import moe_plugin_config, moe_plugin_resource_config
from .consts import ALLOW_R18_NODE


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


async def prepare_send_image(pid: int) -> OmegaMessageSegment:
    """预处理待发送图片

    :param pid: 作品 PID
    :return: 发送的消息
    """

    def _handle_noise(image: bytes) -> ImageUtils:
        """噪点处理图片"""
        image = ImageUtils.init_from_bytes(image=image)
        image.gaussian_noise(sigma=16)
        image.mark(text=f'Pixiv | {pid}')
        return image

    def _handle_mark(image: bytes) -> ImageUtils:
        """标记水印"""
        image = ImageUtils.init_from_bytes(image=image)
        image.mark(text=f'Pixiv | {pid}')
        return image

    async def _handle_image(image_: bytes, need_noise_: bool, output_file_: TemporaryResource) -> TemporaryResource:
        """异步处理图片"""
        if need_noise_:
            image = await run_sync(_handle_noise)(image=image_)
        else:
            image = await run_sync(_handle_mark)(image=image_)

        return await image.save(file=output_file_)

    async with begin_db_session() as session:
        internal_artwork = OmegaPixivArtwork(session=session, pid=pid)
        artwork_data = await internal_artwork.query_artwork()

    if artwork_data.nsfw_tag != 0:
        need_noise = True
        file_name = f'{pid}_p0_noise_sigma16_marked.jpg'
    else:
        need_noise = False
        file_name = f'{pid}_p0_marked.jpg'
    output_file = moe_plugin_resource_config.default_processed_image_folder(file_name)

    # 获取并处理作品图片
    artwork = PixivArtwork(pid=pid)
    artwork_image = await artwork.get_page_bytes()
    image_file = await _handle_image(image_=artwork_image, need_noise_=need_noise, output_file_=output_file)

    return OmegaMessageSegment.image(url=image_file.path)


def get_query_argument_parser() -> ArgumentParser:
    """查询图库的 shell command argument parser"""
    parser = ArgumentParser(prog='图库查询命令参数解析', description='Parse searching arguments')
    parser.add_argument('-s', '--nsfw-tag', type=int, default=0)
    parser.add_argument('-c', '--classified', type=int, default=1)
    parser.add_argument('-o', '--order', type=str, default='random',
                        choices=['random', 'pid', 'pid_desc', 'create_time', 'create_time_desc'])
    parser.add_argument('-n', '--num', type=int, default=moe_plugin_config.moe_plugin_query_image_num)
    parser.add_argument('-a', '--acc-mode', type=bool, default=moe_plugin_config.moe_plugin_enable_acc_mode)
    parser.add_argument('word', nargs='*')
    return parser


class QueryArguments(BaseModel):
    """查询图库命令 argument parser 的解析结果 Model"""
    nsfw_tag: int
    classified: int
    order: Literal['random', 'pid', 'pid_desc', 'create_time', 'create_time_desc']
    num: int
    acc_mode: bool
    word: list[str]
    model_config = ConfigDict(extra='ignore', from_attributes=True)


def parse_from_query_parser(args: Namespace) -> QueryArguments:
    """解析查询命令参数"""
    return QueryArguments.model_validate(args)


async def add_artwork_into_database(
        artwork: PixivArtwork,
        nsfw_tag: int,
        *,
        add_ignored_exists: bool = True,
        ignore_mark: bool = False
) -> None:
    """在数据库中添加作品信息"""
    artwork_data = await artwork.query_artwork()
    # 作品信息写入数据库
    async with begin_db_session() as session:
        db_artwork = OmegaPixivArtwork(session=session, pid=artwork.pid)

        nsfw_tag = 2 if artwork_data.is_r18 else nsfw_tag
        classified = 2 if artwork_data.is_ai else 1

        if add_ignored_exists:
            await db_artwork.add_ignore_exists(
                uid=artwork_data.uid, title=artwork_data.title, uname=artwork_data.uname,
                classified=classified, nsfw_tag=nsfw_tag,
                width=artwork_data.width, height=artwork_data.height, tags=','.join(artwork_data.tags),
                url=artwork_data.url
            )
            for index, url in artwork_data.all_page.items():
                await db_artwork.add_page_ignore_exists(
                    page=index, original=url.original, regular=url.regular,
                    small=url.small, thumb_mini=url.thumb_mini
                )
        else:
            await db_artwork.add_upgrade(
                uid=artwork_data.uid, title=artwork_data.title, uname=artwork_data.uname,
                classified=classified, nsfw_tag=nsfw_tag,
                width=artwork_data.width, height=artwork_data.height, tags=','.join(artwork_data.tags),
                url=artwork_data.url,
                ignore_mark=ignore_mark
            )
            for index, url in artwork_data.all_page.items():
                await db_artwork.add_upgrade_page(
                    page=index, original=url.original, regular=url.regular,
                    small=url.small, thumb_mini=url.thumb_mini
                )


async def _get_database_import_pids() -> list[int]:
    """从本地文件中读取需要导入数据库的图片 PID"""
    async with moe_plugin_resource_config.default_database_import_file.async_open('r', encoding='utf-8') as af:
        pids = [int(x.strip()) for x in await af.readlines() if x.strip().isdigit()]
    return pids


async def get_database_import_pids() -> list[int]:
    """从本地文件中读取需要导入数据库的图片 PID"""
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
