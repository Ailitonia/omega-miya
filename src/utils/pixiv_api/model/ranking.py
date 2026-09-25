"""
@Author         : Ailitonia
@Date           : 2022/04/05 23:15
@FileName       : ranking.py
@Project        : nonebot2_miya
@Description    : Pixiv Ranking Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BasePixivModel


class _IllustContentType(BasePixivModel):
    sexual: int
    lo: bool
    grotesque: bool
    violent: bool
    homosexual: bool
    drug: bool
    thoughts: bool
    antisocial: bool
    religion: bool
    original: bool
    furry: bool
    bl: bool
    yuri: bool


class _IllustSery(BasePixivModel):
    illust_series_id: str
    illust_series_user_id: str
    illust_series_title: str
    illust_series_caption: str
    illust_series_content_count: str
    illust_series_create_datetime: str
    illust_series_content_illust_id: str
    illust_series_content_order: str
    page_url: str


class _Content(BasePixivModel):
    """Pixiv 排行榜内容"""
    title: str
    date: str
    tags: list[str]
    url: AnyHttpUrl
    illust_id: str
    illust_type: str
    illust_book_style: str
    illust_page_count: str
    illust_content_type: _IllustContentType | None = Field(default=None)
    illust_series: bool | _IllustSery | None = Field(default=None)
    width: int
    height: int
    user_id: str
    user_name: str
    profile_img: str
    rank: int
    yes_rank: int
    rating_count: int
    view_count: int
    illust_upload_timestamp: int
    attr: str
    is_masked: bool
    is_bookmarked: bool
    bookmarkable: bool


class _MetaOgp(BasePixivModel):
    description: str
    image: str
    title: str


class _TwitterCard(BasePixivModel):
    card: str
    site: str
    description: str
    image: str
    title: str


class _Meta(BasePixivModel):
    h_title: str
    meta_ogp: _MetaOgp | None = Field(default=None)
    twitter_card: _TwitterCard | None = Field(default=None)
    h_canonical: str
    title: str


class PixivRanking(BasePixivModel):
    """Pixiv 排行榜数据"""
    content: str
    contents: list[_Content]
    mode: str
    page: int
    date: str
    date_range_text: str
    prev: bool | int
    prev_date: bool | str
    next: bool | int
    next_date: bool | str
    rank_total: int
    meta: _Meta | None = Field(default=None)

    def get_ranking(self, rank_num: int) -> _Content:
        # 以页内首条目的 rank 为基准定位, 兼容末页不足整页的情况
        offset = rank_num - self.contents[0].rank if self.contents else -1
        if not 0 <= offset < len(self.contents):
            raise ValueError(f'Ranking num not in this page, maybe in page {int((rank_num - 1) // 50 + 1)}')
        return self.contents[offset]


__all__ = [
    'PixivRanking',
]
