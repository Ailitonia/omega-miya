"""
@Author         : Ailitonia
@Date           : 2023/2/3 23:08
@FileName       : model
@Project        : nonebot2_miya
@Description    : Weibo model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from lxml import etree
from pydantic import BaseModel, Extra, AnyUrl, validator
from typing import Optional, Literal


class WeiboBaseModel(BaseModel):
    """微博基类"""
    class Config:
        extra = Extra.ignore


class WeiboUserBase(WeiboBaseModel):
    """微博用户基础数据"""
    id: int
    screen_name: str
    profile_image_url: AnyUrl
    profile_url: AnyUrl
    statuses_count: int
    verified: bool
    verified_type: int
    close_blue_v: bool
    description: str
    gender: str
    mbtype: int
    svip: int
    urank: int
    mbrank: int
    follow_me: bool
    following: bool
    follow_count: int
    followers_count: str
    followers_count_str: str
    cover_image_phone: AnyUrl
    avatar_hd: AnyUrl
    like: bool
    like_me: bool


class _UserData(WeiboBaseModel):
    """user info data model"""
    fans_scheme: AnyUrl
    follow_scheme: AnyUrl
    isStarStyle: int
    profile_ext: str
    scheme: AnyUrl
    showAppTips: int
    tabsInfo: Optional[dict]
    userInfo: WeiboUserBase


class WeiboUserInfo(WeiboBaseModel):
    """微博用户信息"""
    ok: int
    data: _UserData


class _MbLogVisible(WeiboBaseModel):
    """mbLog.visible model"""
    type: int
    list_id: int


class _PicGeo(WeiboBaseModel):
    """pic.geo model"""
    width: int
    height: int
    croped: bool


class _PicLarge(WeiboBaseModel):
    """pic.large model"""
    size: Literal['large']
    url: AnyUrl
    geo: _PicGeo


class _MblogPic(WeiboBaseModel):
    """mblog.pic model"""
    pid: str
    url: AnyUrl
    size: str
    geo: _PicGeo
    large: _PicLarge


class _WeiboCardMbLog(WeiboBaseModel):
    """card.mblog model"""
    visible: _MbLogVisible
    created_at: str
    id: int
    mid: str
    can_edit: bool
    show_additional_indication: int
    text: str
    textLength: Optional[int]
    source: str
    favorited: bool
    pic_ids: list[str]
    thumbnail_pic: Optional[AnyUrl]
    bmiddle_pic: Optional[AnyUrl]
    original_pic: Optional[AnyUrl]
    is_paid: bool
    mblog_vip_type: int
    user: WeiboUserBase
    retweeted_status: Optional["_WeiboCardMbLog"]
    reposts_count: int
    comments_count: int
    reprint_cmt_count: int
    attitudes_count: int
    pending_approval_count: int
    isLongText: bool
    mlevel: int
    show_mlevel: int
    darwin_tags: Optional[list]
    hot_page: Optional[dict]
    mblogtype: Optional[int]
    rid: Optional[str]
    extern_safe: Optional[int]
    number_display_strategy: Optional[dict]
    content_auth: Optional[int]
    comment_manage_info: Optional[dict]
    pic_num: int
    new_comment_style: Optional[int]
    region_name: str
    region_opt: int
    edit_config: Optional[dict]
    pics: Optional[list[_MblogPic]]
    bid: str

    @validator('text')
    def _remove_text_html_tags(cls, v):
        text_html = etree.HTML(v)
        text = ''.join(text for x in text_html.xpath('/html/*') for text in x.itertext()).strip()
        return text

    @property
    def created_datetime(self) -> datetime:
        return datetime.strptime(self.created_at, '%a %b %d %H:%M:%S %z %Y')

    @property
    def format_created_at(self) -> str:
        return self.created_datetime.strftime('%m-%d %H:%M')

    @property
    def is_retweeted(self) -> bool:
        return self.retweeted_status is not None


class WeiboCardStatus(WeiboBaseModel):
    """微博status页面解析后的单条微博内容"""
    hotScheme: AnyUrl
    appScheme: AnyUrl
    callUinversalLink: bool
    callWeibo: bool
    schemeOrigin: bool
    appLink: AnyUrl
    xianzhi_scheme: AnyUrl
    third_scheme: AnyUrl
    status: _WeiboCardMbLog
    call: int


class WeiboCard(WeiboBaseModel):
    """单条微博内容(data.cards.card model)"""
    card_type: str
    itemid: str
    mblog: _WeiboCardMbLog
    profile_type_id: str
    scheme: str


class _CardListInfo(WeiboBaseModel):
    """weibo cards data.cardlistInfo model"""
    containerid: str
    v_p: int
    show_style: int
    total: int
    autoLoadMoreIndex: int
    since_id: int


class _CardsData(WeiboBaseModel):
    """weibo cards data model"""
    cardlistInfo: _CardListInfo
    cards: list[WeiboCard]
    scheme: AnyUrl
    showAppTips: int


class WeiboCards(WeiboBaseModel):
    """页面微博内容"""
    ok: int
    data: _CardsData


class _HotCardlistInfo(WeiboBaseModel):
    """realtime hot data.cardlistInfo"""
    starttime: int
    can_shared: int
    cardlist_menus: Optional[list]
    config: dict
    page_type: str
    cardlist_head_cards: list[dict]
    enable_load_imge_scrolling: Optional[int]
    nick: str
    page_title: str
    search_request_id: str
    v_p: str
    containerid: str
    refresh_configs: dict
    headbg_animation: Optional[str]
    total: int
    page_size: int
    select_id: str
    title_top: str
    show_style: int
    page: Optional[int]


class _HotCardGroup(WeiboBaseModel):
    """realtime hot data.cards.card_group"""
    card_type: int
    icon: Optional[AnyUrl]
    icon_height: Optional[int]
    icon_width: Optional[int]
    itemid: Optional[str]
    pic: Optional[AnyUrl]
    desc: Optional[str]
    desc_extr: Optional[str]
    actionlog: Optional[dict]
    scheme: AnyUrl
    display_arrow: Optional[int]
    is_show_arrow: Optional[int]
    left_tag_img: Optional[AnyUrl]
    title: Optional[str]
    title_sub: Optional[str]
    sub_title: Optional[str]


class WeiboRealtimeHotCard(WeiboBaseModel):
    """realtime hot data.cards"""
    itemid: Optional[str]
    card_group: list[_HotCardGroup]
    show_type: int
    card_type: int
    title: Optional[str]


class _RealtimeHotData(WeiboBaseModel):
    """realtime hot data"""
    cardlistInfo: _HotCardlistInfo
    cards: list[WeiboRealtimeHotCard]


class WeiboRealtimeHot(WeiboBaseModel):
    """微博实时热搜"""
    ok: int
    data: _RealtimeHotData


__all__ = [
    'WeiboCard',
    'WeiboCards',
    'WeiboCardStatus',
    'WeiboUserBase',
    'WeiboUserInfo',
    'WeiboRealtimeHotCard',
    'WeiboRealtimeHot'
]
