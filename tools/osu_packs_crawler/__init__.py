"""
@Author         : Ailitonia
@Date           : 2025/5/18 16:17
@FileName       : __init__.py
@Project        : omega-miya
@Description    : osu! 曲包下载链接批量获取工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from asyncio import sleep as async_sleep
from itertools import count
from typing import get_args

from nonebot.log import logger

from src.exception import WebSourceException
from .api import BeatmapsPacksType, OsuWeb
from .config import osu_web_config
from .model import BeatmapsPack

_VALID_PACKS_TYPES: tuple[str, ...] = get_args(BeatmapsPacksType.__value__)
"""全部合法的曲包类型"""


async def _query_beatmaps_packs_info_output_to_meta_file(type_: 'BeatmapsPacksType' = 'standard') -> None:
    """根据类型获取并导出曲包信息"""
    consecutive_failures = 0
    queried_packs = 0
    succeed_packs = 0
    failed_packs = 0

    for page in count(1):
        try:
            if page > 1:
                await async_sleep(osu_web_config.omega_tool_osu_request_interval)
            packs_ids = await OsuWeb.query_beatmaps_packs_list(type_=type_, page=page)
            if not packs_ids:
                logger.info(f'None pack in {type_} page {page}, stop parsing')
                break

            logger.info(f'Get {type_} beatmaps packs in page {page}: {packs_ids}')
        except WebSourceException as e:
            if e.status_code == 404:
                logger.info(f'End of {type_} page {page}, stop parsing')
                break
            consecutive_failures += 1
            logger.error(
                f'Query beatmaps packs list error: {e}, ignore {type_} page {page} '
                f'(consecutive failures: {consecutive_failures})'
            )
            if consecutive_failures >= osu_web_config.omega_tool_osu_max_consecutive_failures:
                logger.error(
                    f'Too many consecutive failures ({consecutive_failures}) when parsing {type_}, '
                    f'abort and skip to next type'
                )
                break
            continue
        else:
            consecutive_failures = 0

        for pack_id in packs_ids:
            try:
                beatmap_meta_file = osu_web_config.meta_dir(type_, f'{pack_id}.json')
                if beatmap_meta_file.is_file:
                    logger.debug(f'Beatmaps pack {pack_id!r} meta file exists, ignore')
                    continue
                queried_packs += 1
                await async_sleep(osu_web_config.omega_tool_osu_request_interval)

                pack_info = await OsuWeb.query_beatmap_pack(pack_id)
                await beatmap_meta_file.safe_write_text(pack_info.model_dump_json(), encoding='utf-8')
                succeed_packs += 1
                logger.success(f'Bet beatmaps pack {pack_id!r} info completed')
            except Exception as e:
                failed_packs += 1
                logger.error(f'Query beatmaps pack {pack_id!r} info error: {e}')
                continue

    logger.info(
        f'Query {type_} beatmaps packs info completed, '
        f'newly queried: {queried_packs}, succeed: {succeed_packs}, failed: {failed_packs}'
    )
    if queried_packs > 0 and succeed_packs == 0:
        logger.critical(
            f'All {queried_packs} newly queried beatmaps packs of {type_} failed, '
            f'the page structure may have changed, please check the parser'
        )


async def _gen_download_url_from_meta_file(type_: 'BeatmapsPacksType' = 'standard') -> None:
    """根据已导出的元数据批量生成下载链接"""
    meta_folder = osu_web_config.meta_dir(type_)

    download_urls: list[str] = []
    skipped_files = 0
    for file in meta_folder.iter_current_files():
        try:
            async with file.async_open('r', encoding='utf-8') as af:
                pack_info = BeatmapsPack.model_validate_json(await af.read())
        except Exception as e:
            skipped_files += 1
            logger.warning(f'parse beatmaps pack meta file {file.resolve_path!r} failed: {e}, ignored')
            continue
        download_urls.append(f'{pack_info.download_url}\n')

    output_file = osu_web_config.urls_dir(f'{type_}_beatmaps_packs_download_urls.txt')
    await output_file.safe_write_text_lines(download_urls, encoding='utf-8')

    logger.info(
        f'generated {type_} beatmaps packs download urls, '
        f'total: {len(download_urls)}, skipped invalid meta files: {skipped_files}'
    )


async def _query_packs_download_urls(type_: 'BeatmapsPacksType' = 'standard') -> None:
    await _query_beatmaps_packs_info_output_to_meta_file(type_)
    await _gen_download_url_from_meta_file(type_)


async def query_packs_download_urls(*args: str) -> None:
    """按指定类型获取曲包下载链接, 不传入参数时默认获取 standard 类型"""
    for type_ in args:
        if type_ not in _VALID_PACKS_TYPES:
            raise ValueError(f'invalid beatmaps packs type: {type_!r}, expected one of {_VALID_PACKS_TYPES}')

    if not args:
        await _query_packs_download_urls()
    else:
        for type_ in args:
            await _query_packs_download_urls(type_)


async def query_all_type_packs_download_urls() -> None:
    await _query_packs_download_urls('standard')
    await _query_packs_download_urls('featured')
    await _query_packs_download_urls('tournament')
    await _query_packs_download_urls('loved')
    await _query_packs_download_urls('chart')
    await _query_packs_download_urls('theme')
    await _query_packs_download_urls('artist')


async def main(*args: str) -> None:
    """CLI 默认入口: 无参数抓取全部类型, 有参数按指定类型抓取"""
    if not args:
        await query_all_type_packs_download_urls()
    else:
        await query_packs_download_urls(*args)


__all__ = [
    'main',
]
