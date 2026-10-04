"""
@Author         : Ailitonia
@Date           : 2024/9/8 17:05
@FileName       : manual_rate_pixiv_artwork
@Project        : ailitonia-toolkit
@Description    : pixiv 作品人工评级工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .data_source import (
    ArtworkRecommendPixivArtworkSource,
    LocalPixivArtworkSource,
    NonRatingPixivArtworkSource,
    RecommendPixivArtworkSource,
    SearchPopularPixivArtworkSource,
)
from .ui_main import ManualRatingPixivArtworkMain


def run_local_artwork_rating():
    main = ManualRatingPixivArtworkMain(LocalPixivArtworkSource())
    main.run()


def run_db_non_rating_artwork_rating():
    main = ManualRatingPixivArtworkMain(NonRatingPixivArtworkSource())
    main.run()


def run_top_recommend_artwork_rating():
    main = ManualRatingPixivArtworkMain(RecommendPixivArtworkSource())
    main.run()


def run_artwork_recommend_artwork_rating():
    main = ManualRatingPixivArtworkMain(ArtworkRecommendPixivArtworkSource())
    main.run()


def run_search_popular_artwork_rating():
    main = ManualRatingPixivArtworkMain(SearchPopularPixivArtworkSource())
    main.run()


__all__ = [
    'run_artwork_recommend_artwork_rating',
    'run_db_non_rating_artwork_rating',
    'run_local_artwork_rating',
    'run_top_recommend_artwork_rating',
    'run_search_popular_artwork_rating',
]
