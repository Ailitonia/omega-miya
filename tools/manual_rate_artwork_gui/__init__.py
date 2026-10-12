"""
@Author         : Ailitonia
@Date           : 2024/9/8 17:05
@FileName       : __init__.py
@Project        : omega-miya
@Description    : ArtworkCollection 作品人工评级工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

用法 (GUI 入口, 弹出 Tk 窗口对作品逐张人工评级):
    python bot.py --tool-execute manual_rate_artwork_gui:run_pixiv_local_artwork_file_rating
    python bot.py --tool-execute manual_rate_artwork_gui:run_pixiv_related_artwork_rating
    python bot.py --tool-execute manual_rate_artwork_gui:run_pixiv_search_popular_artwork_rating
    python bot.py --tool-execute manual_rate_artwork_gui:run_pixiv_top_recommend_artwork_rating
    python bot.py --tool-execute manual_rate_artwork_gui:run_db_non_rating_artwork_rating [origin_name]
    python bot.py --tool-execute manual_rate_artwork_gui:run_db_review_record_artwork_rating [origin_name]

用法 (导入入口, 将 GUI 评级结果写入图库数据库):
    python bot.py --tool-execute manual_rate_artwork_gui:run_import_artwork_rating_into_database <source_type>

说明:
    - GUI 入口按数据源拉取待评级作品, 评级结果按会话时间戳缓存到临时资源目录
      omega_tools_manual_rate_artwork/<source_type>/output/ 下
    - origin_name 为图库站点名, 缺省为 pixiv
    - 导入入口读取指定 source_type 目录下全部历史会话的评级数据 (同一作品以最新一次会话为准),
      与站点评级取较大值幂等合并后写入图库数据库
    - source_type 取值须与 GUI 入口对应:
      local_pixiv_image / pixiv_related_artwork / pixiv_search_popular_artwork / pixiv_top_recommend /
      database_non_rating_artwork / database_non_review_record_artwork
"""

from .data_source import ArtworkRatingImportTool
from .sources import (
    DatabaseNonRatingArtworkSource,
    DatabaseNonReviewRecordArtworkSource,
    PixivLocalArtworkFileSource,
    PixivRelatedArtworkSource,
    PixivSearchPopularArtworkSource,
    PixivTopRecommendArtworkSource,
)
from .ui_main import ManualRatingArtworkMain


async def run_import_artwork_rating_into_database(*args: str) -> None:
    if not (source_type := args[0] if args else None):
        raise ValueError('source_type param is required but not provided')
    await ArtworkRatingImportTool(source_type).import_artwork_rating_into_database()


def run_pixiv_local_artwork_file_rating():
    main = ManualRatingArtworkMain(PixivLocalArtworkFileSource())
    main.run()


def run_pixiv_related_artwork_rating():
    main = ManualRatingArtworkMain(PixivRelatedArtworkSource())
    main.run()


def run_pixiv_search_popular_artwork_rating():
    main = ManualRatingArtworkMain(PixivSearchPopularArtworkSource())
    main.run()


def run_pixiv_top_recommend_artwork_rating():
    main = ManualRatingArtworkMain(PixivTopRecommendArtworkSource())
    main.run()


def run_db_non_rating_artwork_rating(*args: str):
    origin_name = args[0] if args else 'pixiv'
    main = ManualRatingArtworkMain(DatabaseNonRatingArtworkSource(origin_name))
    main.run()


def run_db_review_record_artwork_rating(*args: str):
    origin_name = args[0] if args else 'pixiv'
    main = ManualRatingArtworkMain(DatabaseNonReviewRecordArtworkSource(origin_name))
    main.run()


__all__ = [
    'run_db_non_rating_artwork_rating',
    'run_db_review_record_artwork_rating',
    'run_import_artwork_rating_into_database',
    'run_pixiv_local_artwork_file_rating',
    'run_pixiv_related_artwork_rating',
    'run_pixiv_search_popular_artwork_rating',
    'run_pixiv_top_recommend_artwork_rating',
]
