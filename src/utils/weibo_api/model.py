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
from typing import Literal, Optional

from lxml import etree
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.compat import AnyUrlStr as AnyUrl


class WeiboBaseModel(BaseModel):
    """微博基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True)


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
    tabsInfo: dict | None = None
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


class _PagePic(WeiboBaseModel):
    """page_info.page_pic model"""
    url: AnyUrl
    pid: str | None = None
    source: int | None = None
    is_self_cover: int | None = None
    type: int | None = None
    width: int | str | None = None
    height: int | str | None = None


class _PageInfo(WeiboBaseModel):
    """page_info model"""
    type: str
    object_type: str | None = None
    page_pic: _PagePic
    page_url: AnyUrl | None = None
    page_title: str | None = None
    title: str | None = None
    content1: str | None = None
    content2: str | None = None
    url_ori: AnyUrl | None = None
    object_id: str | None = None

    @property
    def pic_url(self) -> AnyUrl:
        return self.page_pic.url


class _WeiboCardMbLog(WeiboBaseModel):
    """card.mblog model"""
    visible: _MbLogVisible
    created_at: str
    id: int
    mid: str
    can_edit: bool
    show_additional_indication: int | None = None
    text: str
    textLength: int | None = None
    source: str
    favorited: bool
    pic_ids: list[str]
    thumbnail_pic: AnyUrl | None = None
    bmiddle_pic: AnyUrl | None = None
    original_pic: AnyUrl | None = None
    is_paid: bool
    mblog_vip_type: int
    user: WeiboUserBase
    retweeted_status: Optional['_WeiboCardMbLog'] = None
    reposts_count: int
    comments_count: int
    reprint_cmt_count: int
    attitudes_count: int
    pending_approval_count: int
    isLongText: bool
    mlevel: int
    show_mlevel: int
    darwin_tags: list | None = None
    hot_page: dict | None = None
    mblogtype: int | None = None
    rid: str | None = None
    extern_safe: int | None = None
    number_display_strategy: dict | None = None
    content_auth: int | None = None
    comment_manage_info: dict | None = None
    pic_num: int
    new_comment_style: int | None = None
    region_name: str | None = None
    region_opt: int | None = None
    page_info: _PageInfo | None = None
    edit_config: dict | None = None
    pics: list[_MblogPic] | None = None
    bid: str

    @field_validator('text')
    @classmethod
    def _remove_text_html_tags(cls, text: str):
        if not text.strip():
            return text

        text_html = etree.HTML(text)
        text = ''.join(text for x in text_html.xpath('/html/*') for text in x.itertext()).strip()
        return text

    @field_validator('retweeted_status', mode='before')
    @classmethod
    def _check_retweeted_status(cls, v):
        # 排除转发了由于作者设置导致没有查看权限的微博
        if v.get('user', None) is None:
            return None
        return v

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
    mblog: _WeiboCardMbLog
    itemid: str | None = None
    profile_type_id: str | None = None
    scheme: str | None = None


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

    @model_validator(mode='before')
    @classmethod
    def exclude_null_card(cls, values):
        """排除所有无内容的微博"""
        if isinstance(values, dict):
            cards = filter(lambda x: (isinstance(x, dict) and x.get('mblog') is not None), values.get('cards', []))
            values['cards'] = cards
        return values


class WeiboCards(WeiboBaseModel):
    """页面微博内容"""
    ok: int
    data: _CardsData


class _WeiboExtendData(WeiboBaseModel):
    """weibo extend data model"""
    ok: int
    longTextContent: str
    reposts_count: int
    comments_count: int
    attitudes_count: int

    @field_validator('longTextContent')
    @classmethod
    def _remove_text_html_tags(cls, v):
        text_html = etree.HTML(v)
        text = ''.join(text for x in text_html.xpath('/html/*') for text in x.itertext()).strip()
        return text


class WeiboExtend(WeiboBaseModel):
    """获取微博全文内容"""
    ok: int
    data: _WeiboExtendData


class _HotCardlistInfo(WeiboBaseModel):
    """realtime hot data.cardlistInfo"""
    starttime: int
    can_shared: int
    cardlist_menus: list | None = None
    config: dict
    page_type: str
    cardlist_head_cards: list[dict]
    enable_load_imge_scrolling: int | None = None
    nick: str
    page_title: str
    search_request_id: str
    v_p: str
    containerid: str
    refresh_configs: dict
    headbg_animation: str | None = None
    total: int
    page_size: int
    select_id: str
    title_top: str
    show_style: int
    page: int | None = None


class _HotCardGroup(WeiboBaseModel):
    """realtime hot data.cards.card_group"""
    card_type: int
    icon: AnyUrl | None = None
    icon_height: int | None = None
    icon_width: int | None = None
    itemid: str | None = None
    pic: AnyUrl | None = None
    desc: str | None = None
    desc_extr: str | None = None
    actionlog: dict | None = None
    scheme: AnyUrl
    display_arrow: int | None = None
    is_show_arrow: int | None = None
    left_tag_img: AnyUrl | None = None
    title: str | None = None
    title_sub: str | None = None
    sub_title: str | None = None


class WeiboRealtimeHotCard(WeiboBaseModel):
    """realtime hot data.cards"""
    itemid: str | None = None
    card_group: list[_HotCardGroup]
    show_type: int
    card_type: int
    title: str | None = None


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
    'WeiboExtend',
    'WeiboRealtimeHotCard',
    'WeiboRealtimeHot',
    'WeiboUserBase',
    'WeiboUserInfo',
]
