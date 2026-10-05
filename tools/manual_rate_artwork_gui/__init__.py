"""
@Author         : Ailitonia
@Date           : 2024/9/8 17:05
@FileName       : __init__.py
@Project        : omega-miya
@Description    : ArtworkCollection 作品人工评级工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
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
        raise ValueError('source_type param is acquired but not')
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
