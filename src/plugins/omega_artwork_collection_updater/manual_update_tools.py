"""
@Author         : Ailitonia
@Date           : 2024/8/17 下午7:56
@FileName       : manual_update_tools
@Project        : nonebot2_miya
@Description    : 数据库手动导入/更新工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from asyncio import sleep as async_sleep
from typing import Annotated

from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command
from nonebot.rule import to_me
from pydantic import BaseModel, ConfigDict

from src.compat import parse_json_as
from src.database import ArtworkCollectionDAL
from src.exception import WebSourceException
from src.params.handler import get_command_str_single_arg_parser_handler
from src.resource import TemporaryResource
from src.service import enable_processor_state
from src.service.artwork_collection import ALLOW_ARTWORK_ORIGIN, get_artwork_collection_type
from src.utils.process_utils import semaphore_gather


class CustomImportArtwork(BaseModel):
    """手动导入/更新作品信息"""
    origin: ALLOW_ARTWORK_ORIGIN
    aid: str
    classification: int = 3
    rating: int

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


async def _get_custom_import_artworks_data_from_file() -> list[CustomImportArtwork]:
    """获取需要导入图库的作品"""
    async with TemporaryResource('custom_import_collected_artworks.json').async_open('r', encoding='utf-8') as af:
        data = await af.read()
    return parse_json_as(list[CustomImportArtwork], data)


async def _import_artwork_into_database(import_data: CustomImportArtwork, log_index: int = -1) -> None:
    collected_artwork = get_artwork_collection_type(origin=import_data.origin)(artwork_id=import_data.aid)

    try:
        artwork_data = await collected_artwork.artwork_proxy.query()
        classification = 1 if artwork_data.classification.value == 1 else import_data.classification
        rating = 3 if artwork_data.rating.value == 3 else import_data.rating

        await collected_artwork.add_and_upgrade_artwork_into_database(
            classification=classification, rating=rating, force_update_mark=True
        )
    except WebSourceException as e:
        # 网络问题有可能是风控/限流, 小概率是作品已经被删除
        if e.status_code == 404:
            raise e

        logger.warning(
            f'ImportCustomCollectedArtworks | 获取作品 {collected_artwork} 信息时发生异常, {e!r}, 60秒后重试'
        )
        await async_sleep(60)

        artwork_data = await collected_artwork.artwork_proxy.query()
        classification = 1 if artwork_data.classification.value == 1 else import_data.classification
        rating = 3 if artwork_data.rating.value == 3 else import_data.rating

        await collected_artwork.add_and_upgrade_artwork_into_database(
            classification=classification, rating=rating, force_update_mark=True
        )

    if log_index % 10 == 0:
        logger.info(f'ImportCustomCollectedArtworks | 已导入作品 {collected_artwork}, index: {log_index}')
    else:
        logger.debug(f'ImportCustomCollectedArtworks | 已导入作品 {collected_artwork}, index: {log_index}')


@on_command(
    '导入图库',
    rule=to_me(),
    aliases={'图库导入'},
    permission=SUPERUSER,
    priority=10,
    block=True,
    state=enable_processor_state(name='ImportCustomCollectedArtworks', enable_processor=False),
).handle()
async def handle_import_collected_artworks(matcher: Matcher) -> None:
    try:
        artworks_data = await _get_custom_import_artworks_data_from_file()
        logger.info(f'ImportCustomCollectedArtworks | 解析导入数据完成, 总计: {len(artworks_data)}')
        await matcher.send(f'已读取待导入作品, 总计: {len(artworks_data)}, 开始获取作品信息')
    except Exception as e:
        logger.error(f'ImportCustomCollectedArtworks | 从文件中读取导入数据失败, {e}')
        await matcher.finish('解析导入数据失败, 或导入文件不存在, 已取消操作, 详情请查看日志')

    import_tasks = [
        _import_artwork_into_database(import_data=x, log_index=index)
        for index, x in enumerate(artworks_data)
    ]
    await semaphore_gather(tasks=import_tasks, semaphore_num=8, return_exceptions=True)

    logger.success(f'ImportCustomCollectedArtworks | 导入作品已完成, 总计: {len(artworks_data)}')
    await matcher.finish(f'导入作品已完成, 总计: {len(artworks_data)}')


@on_command(
    '图库统计',
    rule=to_me(),
    aliases={'图库查询', '查询图库'},
    permission=SUPERUSER,
    handlers=[get_command_str_single_arg_parser_handler('origins', ensure_key=True)],
    priority=10,
    block=True,
    state=enable_processor_state(name='ArtworkCollectionStatistics', enable_processor=False),
).got('origins')
async def handle_artwork_collection_statistics(
        matcher: Matcher,
        dal: Annotated[ArtworkCollectionDAL, Depends(ArtworkCollectionDAL.dal_dependence)],
        origins: Annotated[str | None, ArgStr('origins')],
) -> None:
    if origins is None:
        query_origin = None
        query_keywords = None
    elif len(split_origins := origins.strip().split(maxsplit=1)) == 1:
        query_origin = split_origins[0]
        query_keywords = None
    elif len(split_origins := origins.strip().split(maxsplit=1)) > 1:
        query_origin = split_origins[0]
        query_keywords = split_origins[1:]
    else:
        query_origin = None
        query_keywords = None

    try:
        classification_statistic = await dal.query_classification_statistic(query_origin, query_keywords)
        rating_statistic = await dal.query_rating_statistic(query_origin, query_keywords)
    except Exception as e:
        logger.error(f'ArtworkCollectionStatistics | 查询数据库作品{origins!r}统计信息失败, {e!r}')
        await matcher.finish(f'查询数据库作品{origins!r}统计信息失败, 详情请查看日志')

    prefix_text = f'本地数据库{origins if origins is not None else "全量"!r}统计信息:'
    classification_text = (
        f'-- Classification --\n'
        f'Unknown: {classification_statistic.unknown}\n'
        f'Unclassified: {classification_statistic.unclassified}\n'
        f'AIGenerated: {classification_statistic.ai_generated}\n'
        f'Automatic: {classification_statistic.automatic}\n'
        f'Confirmed: {classification_statistic.confirmed}'
    )
    rating_text = (
        f'-- Rating --\n'
        f'Unknown: {rating_statistic.unknown}\n'
        f'General: {rating_statistic.general}\n'
        f'Sensitive: {rating_statistic.sensitive}\n'
        f'Questionable: {rating_statistic.questionable}\n'
        f'Explicit: {rating_statistic.explicit}'
    )
    send_message = f'{prefix_text}\n\n{classification_text}\n\n{rating_text}'

    await matcher.finish(send_message)


__all__ = []
