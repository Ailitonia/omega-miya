"""
@Author         : Ailitonia
@Date           : 2024/11/15 17:59:38
@FileName       : search.py
@Project        : omega-miya
@Description    : search models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, Optional, Union

from pydantic import Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseBilibiliModel, BaseBilibiliResponse


class ActivitySearchResult(BaseBilibiliModel):
    """站内活动搜索结果"""
    type: Literal['activity']
    id: int
    title: str
    desc: str
    cover: str
    corner: str
    pos: int
    url: str
    card_type: int
    card_value: str
    state: int
    status: int
    author: str
    position: int


class WebGameSearchResult(BaseBilibiliModel):
    """游戏(网页)搜索结果"""
    game_base_id: int
    game_name: str
    game_icon: str
    summary: str
    game_status: int
    game_link: str
    grade: float
    book_num: int
    download_num: int
    comment_num: int
    platform: str
    notice_title: str
    notice: str
    game_tags: str
    recommend_reason: str
    official_account: int


class VideoSearchResult(BaseBilibiliModel):
    """视频搜索结果"""
    type: Literal['video']
    id: int
    author: str
    mid: int
    typeid: str
    typename: str
    arcurl: str
    aid: int
    bvid: str
    title: str
    description: str
    pic: str
    play: int
    video_review: int
    favorites: int
    tag: str
    review: int
    pubdate: int
    senddate: int
    duration: str
    is_union_video: int
    rank_score: int
    hit_columns: list[str]


class _MediaScore(BaseBilibiliModel):
    user_count: int
    score: float


class _Ep(BaseBilibiliModel):
    id: int
    cover: AnyHttpUrl
    title: str
    url: AnyHttpUrl
    release_date: str
    index_title: str
    long_title: str


class MediaSearchResult(BaseBilibiliModel):
    """番剧&影视搜索结果"""
    type: Literal['media_bangumi', 'media_ft']
    media_id: int
    season_id: int
    title: str
    org_title: str
    cover: str
    media_type: int
    areas: str
    styles: str
    cv: str
    staff: str
    goto_url: AnyHttpUrl
    desc: str
    pubtime: int
    fix_pubtime_str: str
    pgc_season_id: int
    season_type: int
    season_type_name: str
    selection_style: str
    ep_size: int
    eps: list[_Ep]
    url: str
    is_follow: int
    media_score: _MediaScore
    hit_columns: list[str]
    hit_epids: str


class LiveRoomSearchResult(BaseBilibiliModel):
    """直播间搜索结果"""
    type: Literal['live_room']
    rank_offset: int
    uid: int
    roomid: int
    short_id: int
    tags: str
    live_time: str
    cate_name: str
    live_status: int
    uname: str
    uface: str
    user_cover: str
    area: int
    title: str
    cover: str
    online: int
    rank_index: int
    rank_score: int
    attentions: Optional[int] = Field(default=None)
    hit_columns: list[str]


class LiveUserSearchResult(BaseBilibiliModel):
    """主播搜索结果"""
    type: Literal['live_user']
    rank_offset: int
    uid: int
    roomid: int
    tags: str
    live_time: str
    live_status: int
    area: int
    is_live: bool
    uname: str
    uface: str
    rank_index: int
    rank_score: int
    attentions: int
    hit_columns: list[str]


class ArticleSearchResult(BaseBilibiliModel):
    """专栏搜索结果"""
    type: Literal['article']
    id: int
    category_name: str
    title: str
    mid: int
    desc: str
    image_urls: list[str]
    pub_time: int
    template_id: int
    category_id: int
    view: int
    like: int
    reply: int
    rank_offset: int
    rank_index: int
    rank_score: int


class TopicSearchResult(BaseBilibiliModel):
    """话题搜索结果"""
    type: Literal['topic']
    description: str
    pubdate: int
    title: str
    mid: int
    author: str
    arcurl: str
    keyword: str
    cover: str
    update: int
    favourite: int
    review: int
    tp_id: int
    tp_type: int
    rank_offset: int
    rank_index: int
    rank_score: int
    hit_columns: list[str]


class _Res(BaseBilibiliModel):
    aid: int
    bvid: str
    title: str
    pubdate: int
    arcurl: str
    pic: str
    play: str
    dm: int
    coin: int
    fav: int
    desc: str
    duration: str
    is_pay: Optional[int] = Field(default=None)
    is_union_video: int


class _OfficialVerify(BaseBilibiliModel):
    type: int
    desc: str


class UserSearchResult(BaseBilibiliModel):
    """用户搜索结果"""
    type: Literal['bili_user']
    mid: int
    uname: str
    usign: str
    fans: int
    videos: int
    upic: str
    level: int
    gender: int
    is_upuser: int
    is_live: int
    room_id: int
    res: list[_Res]
    official_verify: _OfficialVerify
    hit_columns: list[str]


class PhotoSearchResult(BaseBilibiliModel):
    """相簿搜索结果"""
    type: Literal['photo']
    id: int
    mid: int
    title: str
    cover: str
    uname: str
    count: int
    like: int
    view: int
    rank_index: int
    rank_score: int
    rank_offset: int
    hit_columns: list[str]


type SearchType = Literal[
    'video',
    'media_bangumi',
    'media_ft',
    'live',
    'live_room',
    'live_user',
    'article',
    'topic',
    'bili_user',
    'photo',
]

type AllSearchResultType = Union[
    ActivitySearchResult,
    WebGameSearchResult,
    VideoSearchResult,
    MediaSearchResult,
    LiveRoomSearchResult,
    LiveUserSearchResult,
    ArticleSearchResult,
    TopicSearchResult,
    UserSearchResult,
    PhotoSearchResult,
]


class _PageInfoCount(BaseBilibiliModel):
    num_results: int = Field(alias='numResults')
    total: int
    pages: int


class _PageInfo(BaseBilibiliModel):
    pgc: _PageInfoCount
    live_room: _PageInfoCount
    # photo: _PageInfoCount  # maybe deactivated
    topic: _PageInfoCount
    video: _PageInfoCount
    user: _PageInfoCount
    bili_user: _PageInfoCount
    media_ft: _PageInfoCount
    article: _PageInfoCount
    media_bangumi: _PageInfoCount
    special: _PageInfoCount
    operation_card: _PageInfoCount
    upuser: _PageInfoCount
    movie: _PageInfoCount
    live_all: _PageInfoCount
    tv: _PageInfoCount
    live: _PageInfoCount
    bangumi: _PageInfoCount
    activity: _PageInfoCount
    live_master: _PageInfoCount
    live_user: _PageInfoCount


class _TopTlist(BaseBilibiliModel):
    pgc: int
    live_room: int
    # photo: int  # maybe deactivated
    topic: int
    video: int
    user: int
    bili_user: int
    media_ft: int
    article: int
    media_bangumi: int
    card: int
    operation_card: int
    upuser: int
    movie: int
    # live_all: int  # maybe deactivated
    tv: int
    live: int
    special: int
    bangumi: int
    activity: int
    live_master: int
    live_user: int


class _SearchAllDataResult(BaseBilibiliModel):
    result_type: str
    data: list[AllSearchResultType]


class _SearchAllData(BaseBilibiliModel):
    seid: str
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    numResults: int = Field(default=1000)
    numPages: int = Field(default=50)
    suggest_keyword: str
    rqt_type: str
    pageinfo: _PageInfo
    top_tlist: _TopTlist
    show_column: int
    show_module_list: list[str]
    result: list[_SearchAllDataResult]


class SearchAllResult(BaseBilibiliResponse):
    """api.bilibili.com/x/web-interface/wbi/search/all/v2 返回值"""
    data: _SearchAllData

    @property
    def all_results(self) -> list[AllSearchResultType]:
        return [x for results in self.data.result for x in results.data]


class _SearchTypeData(BaseBilibiliModel):
    seid: str
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    numResults: int = Field(default=1000)
    numPages: int = Field(default=50)
    suggest_keyword: str
    rqt_type: str
    show_column: int
    result: list[AllSearchResultType]


class SearchTypeResult(BaseBilibiliResponse):
    """api.bilibili.com/x/web-interface/wbi/search/type 返回值"""
    data: _SearchTypeData

    @property
    def all_results(self) -> list[AllSearchResultType]:
        return [x for x in self.data.result]


__all__ = [
    'VideoSearchResult',
    'MediaSearchResult',
    'LiveRoomSearchResult',
    'LiveUserSearchResult',
    'ArticleSearchResult',
    'TopicSearchResult',
    'UserSearchResult',
    'PhotoSearchResult',
    'AllSearchResultType',
    'SearchAllResult',
    'SearchType',
    'SearchTypeResult',
]
