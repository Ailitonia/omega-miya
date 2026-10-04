"""
@Author         : Ailitonia
@Date           : 2025/5/18 16:17
@FileName       : __init__.py
@Project        : omega-miya
@Description    : osu! 曲包下载链接批量获取工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from itertools import count

from nonebot.log import logger

from src.exception import WebSourceException
from .config import osu_web_config
from .main import BeatmapsPacksType, OsuWeb
from .model import BeatmapsPack


async def _query_beatmaps_packs_info_output_to_meta_file(type_: 'BeatmapsPacksType' = 'standard') -> None:
    """根据类型获取并导出曲包信息"""

    for page in count(1):
        try:
            packs_ids = await OsuWeb.query_beatmaps_packs_list(type_=type_, page=page)
            if not packs_ids:
                logger.info(f'None pack in {type_} page {page}, stop parsing')
                break

            logger.info(f'get {type_} beatmaps packs in page {page}: {packs_ids}')
        except WebSourceException as e:
            if e.status_code == 404:
                logger.info(f'End of {type_} page {page}, stop parsing')
                break
            else:
                logger.error(f'query beatmaps packs list error: {e}, ignore {type_} page {page}')
                continue

        for pack_id in packs_ids:
            try:
                beatmap_meta_file = osu_web_config.meta_dir(type_, f'{pack_id}.json')
                if beatmap_meta_file.is_file:
                    logger.debug(f'beatmaps pack {pack_id!r} meta file exists, ignore')
                    continue
                pack_info = await OsuWeb.query_beatmap_pack(pack_id)
                async with beatmap_meta_file.async_open('w', encoding='utf-8') as af:
                    await af.write(pack_info.model_dump_json())
                logger.success(f'get beatmaps pack {pack_id!r} info completed')
            except Exception as e:
                logger.error(f'query beatmaps pack {pack_id!r} info error: {e}')
                continue

    logger.info(f'query {type_} beatmaps packs info completed')


async def _gen_download_url_from_meta_file(type_: 'BeatmapsPacksType' = 'standard') -> None:
    """根据已导出的元数据批量生成下载链接"""
    meta_folder = osu_web_config.meta_dir(type_)

    download_urls: list[str] = []
    for file in meta_folder.iter_current_files():
        async with file.async_open('r', encoding='utf-8') as af:
            pack_info = BeatmapsPack.model_validate_json(await af.read())
            download_urls.append(f'{pack_info.download_url}\n')

    output_file = osu_web_config.urls_dir(f'{type_}_beatmaps_packs_download_urls.txt')
    async with output_file.async_open('w', encoding='utf-8') as af:
        await af.writelines(download_urls)

    logger.info(f'generated {type_} beatmaps packs download urls')


async def _query_packs_download_urls(type_: 'BeatmapsPacksType' = 'standard') -> None:
    await _query_beatmaps_packs_info_output_to_meta_file(type_)
    await _gen_download_url_from_meta_file(type_)


async def query_packs_download_urls(*args: 'BeatmapsPacksType') -> None:
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


__all__ = [
    'query_all_type_packs_download_urls',
    'query_packs_download_urls',
]
