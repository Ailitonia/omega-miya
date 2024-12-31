"""
@Author         : Ailitonia
@Date           : 2022/05/1 17:48
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Moe Plugin Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from nonebot.log import logger
from nonebot.rule import ArgumentParser, Namespace
from pydantic import BaseModel, ConfigDict

from src.service import OmegaMessageSegment
from src.service.artwork_collection import get_artwork_collection, get_artwork_collection_type
from src.service.artwork_proxy.add_ons.image_ops import ImageOpsMixin
from .config import moe_plugin_config
from .consts import ALL_MOE_PLUGIN_ARTWORK_ORIGIN, ALLOW_MOE_PLUGIN_ARTWORK_ORIGIN, ALLOW_R18_NODE

if TYPE_CHECKING:
    from src.service import OmegaMatcherInterface
    from src.service.artwork_collection.typing import CollectedArtwork


async def _has_allow_r18_node(interface: 'OmegaMatcherInterface') -> bool:
    """判断当前 entity 主体是否具有允许预览 r18 作品的权限"""
    if interface.matcher.plugin is None:
        return False

    return (
            await interface.entity.check_global_permission() and
            await interface.entity.check_auth_setting(
                module=interface.matcher.plugin.module_name,
                plugin=interface.matcher.plugin.name,
                node=ALLOW_R18_NODE
            )
    )


async def has_allow_r18_node(interface: 'OmegaMatcherInterface') -> bool:
    """判断当前 entity 主体是否具有允许预览 r18 作品的权限"""
    try:
        allow_r18 = await _has_allow_r18_node(interface=interface)
    except Exception as e:
        logger.warning(f'Checking {interface.entity} r18 node failed, {e!r}')
        allow_r18 = False
    return allow_r18


def get_query_argument_parser() -> ArgumentParser:
    """查询图库的 shell command argument parser"""
    parser = ArgumentParser(prog='图库查询命令参数解析', description='Parse searching arguments')
    parser.add_argument('-o', '--origin', type=str, default=None)
    parser.add_argument('-a', '--all-origin', action='store_true')
    parser.add_argument('-r', '--r18', action='store_true')
    parser.add_argument('-l', '--latest', action='store_true')
    parser.add_argument('-m', '--ratio', type=int, default=None)
    parser.add_argument('-n', '--num', type=int, default=0)
    parser.add_argument('keywords', nargs='*')
    return parser


class QueryArguments(BaseModel):
    """查询图库命令 argument parser 的解析结果 Model"""
    origin: ALLOW_MOE_PLUGIN_ARTWORK_ORIGIN | None
    all_origin: bool
    r18: bool
    latest: bool
    ratio: int | None
    num: int
    keywords: list[str]

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True)


def parse_from_query_parser(args: Namespace) -> QueryArguments:
    """解析查询命令参数"""
    return QueryArguments.model_validate(args)


async def query_artworks_from_database(
        keywords: Sequence[str],
        origin: ALLOW_MOE_PLUGIN_ARTWORK_ORIGIN | None = None,
        all_origin: bool = False,
        allow_rating_range: tuple[int, int] = (0, 0),
        latest: bool = False,
        ratio: int | None = None,
        num: int = 0,
) -> list['CollectedArtwork']:
    """从数据库查询收藏作品, 特别的: 当参数 `origin` 值为 `none` 时代表从所有的来源随机获取"""
    if all_origin:
        query_origin = ALL_MOE_PLUGIN_ARTWORK_ORIGIN
    elif origin is None:
        query_origin = moe_plugin_config.moe_plugin_default_origin
    else:
        query_origin = origin

    query_num = min(
        max(num, moe_plugin_config.moe_plugin_query_image_num),
        moe_plugin_config.moe_plugin_query_image_limit
    )

    order_mode: Literal['latest', 'random'] = 'latest' if latest else 'random'

    random_artworks = await get_artwork_collection_type().query_any_origin_by_condition(
        keywords=keywords, origin=query_origin, num=query_num,
        allow_classification_range=(2, 3), allow_rating_range=allow_rating_range, ratio=ratio, order_mode=order_mode,
    )

    return [get_artwork_collection(artwork=artwork) for artwork in random_artworks]


async def prepare_send_image(collected_artwork: 'CollectedArtwork') -> OmegaMessageSegment:
    """预处理待发送图片"""
    if not isinstance(collected_artwork.artwork_proxy, ImageOpsMixin):
        raise RuntimeError(f'{collected_artwork} is not compatible with the image processing method')

    output_file = await collected_artwork.artwork_proxy.get_proceed_page_file(no_blur_rating=3)

    return OmegaMessageSegment.image(url=output_file.path)


__all__ = [
    'has_allow_r18_node',
    'get_query_argument_parser',
    'parse_from_query_parser',
    'prepare_send_image',
    'query_artworks_from_database',
]
