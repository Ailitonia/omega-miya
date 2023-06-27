"""
@Author         : Ailitonia
@Date           : 2022/04/05 23:15
@FileName       : ranking.py
@Project        : nonebot2_miya 
@Description    : Pixiv Ranking Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import AnyHttpUrl
from .base_model import BasePixivModel


class PixivRankingContentModel(BasePixivModel):
    """Pixiv 排行榜内容"""
    illust_id: int
    title: str
    user_name: str
    user_id: int
    width: int
    height: int
    url: AnyHttpUrl
    tags: list[str]


class PixivRankingModel(BasePixivModel):
    """Pixiv 排行榜 Model"""
    content: str
    contents: list[PixivRankingContentModel]
    date: str
    mode: str
    page: int
    next: int
    prev: int
    next_date: str
    prev_date: str
    rank_total: int

    def get_ranking(self, rank_num: int) -> PixivRankingContentModel:
        if not (self.page - 1) * len(self.contents) <= rank_num - 1 < self.page * len(self.contents):
            raise ValueError(f'Ranking num not in this page, maybe in page {int((rank_num - 1) // 50 + 1)}')
        return self.contents[rank_num - 1]


__all__ = [
    'PixivRankingModel'
]
