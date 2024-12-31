"""
@Author         : Ailitonia
@Date           : 2024/11/28 10:56:47
@FileName       : dynamic.py
@Project        : omega-miya
@Description    : dynamic models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from enum import StrEnum, unique
from typing import Any

from pydantic import Field, Json

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseBilibiliModel, BaseBilibiliResponse


@unique
class DynamicType(StrEnum):
    """动态类型"""
    none = 'DYNAMIC_TYPE_NONE'  # 无效动态
    forward = 'DYNAMIC_TYPE_FORWARD'  # 动态转发
    av = 'DYNAMIC_TYPE_AV'  # 投稿视频
    pgc = 'DYNAMIC_TYPE_PGC'  # 剧集（番剧、电影、纪录片）
    pgc_union = 'DYNAMIC_TYPE_PGC_UNION'
    courses = 'DYNAMIC_TYPE_COURSES'
    word = 'DYNAMIC_TYPE_WORD'  # 纯文字动态
    draw = 'DYNAMIC_TYPE_DRAW'  # 带图动态
    article = 'DYNAMIC_TYPE_ARTICLE'  # 投稿专栏
    music = 'DYNAMIC_TYPE_MUSIC'  # 音乐
    common_square = 'DYNAMIC_TYPE_COMMON_SQUARE'  # 装扮/剧集点评/普通分享
    common_vertical = 'DYNAMIC_TYPE_COMMON_VERTICAL'
    live = 'DYNAMIC_TYPE_LIVE'  # 直播间分享
    medialist = 'DYNAMIC_TYPE_MEDIALIST'  # 收藏夹
    courses_season = 'DYNAMIC_TYPE_COURSES_SEASON'  # 课程
    courses_batch = 'DYNAMIC_TYPE_COURSES_BATCH'
    ad = 'DYNAMIC_TYPE_AD'
    applet = 'DYNAMIC_TYPE_APPLET'
    subscription = 'DYNAMIC_TYPE_SUBSCRIPTION'
    live_rcmd = 'DYNAMIC_TYPE_LIVE_RCMD'  # 直播开播
    banner = 'DYNAMIC_TYPE_BANNER'
    ugc_season = 'DYNAMIC_TYPE_UGC_SEASON'  # 合集更新
    subscription_new = 'DYNAMIC_TYPE_SUBSCRIPTION_NEW'


@unique
class RichTextNodeType(StrEnum):
    """富文本节点类型"""
    none = 'RICH_TEXT_NODE_TYPE_NONE'
    text = 'RICH_TEXT_NODE_TYPE_TEXT'  # 文字节点
    at = 'RICH_TEXT_NODE_TYPE_AT'  # @用户
    lottery = 'RICH_TEXT_NODE_TYPE_LOTTERY'  # 互动抽奖
    vote = 'RICH_TEXT_NODE_TYPE_VOTE'  # 投票
    topic = 'RICH_TEXT_NODE_TYPE_TOPIC'  # 话题
    goods = 'RICH_TEXT_NODE_TYPE_GOODS'  # 商品链接
    bv = 'RICH_TEXT_NODE_TYPE_BV'  # 视频链接
    av = 'RICH_TEXT_NODE_TYPE_AV'
    emoji = 'RICH_TEXT_NODE_TYPE_EMOJI'  # 表情
    user = 'RICH_TEXT_NODE_TYPE_USER'
    cv = 'RICH_TEXT_NODE_TYPE_CV'
    vc = 'RICH_TEXT_NODE_TYPE_VC'
    web = 'RICH_TEXT_NODE_TYPE_WEB'  # 网页链接
    taobao = 'RICH_TEXT_NODE_TYPE_TAOBAO'
    mail = 'RICH_TEXT_NODE_TYPE_MAIL'  # 邮箱地址
    ogv_season = 'RICH_TEXT_NODE_TYPE_OGV_SEASON'  # 剧集信息
    ogv_ep = 'RICH_TEXT_NODE_TYPE_OGV_EP'
    search_word = 'RICH_TEXT_NODE_TYPE_SEARCH_WORD'
    view_picture = 'RICH_TEXT_NODE_TYPE_VIEW_PICTURE'


@unique
class AuthorType(StrEnum):
    """作者类型"""
    none = 'AUTHOR_TYPE_NONE'
    normal = 'AUTHOR_TYPE_NORMAL'  # 普通更新
    pgc = 'AUTHOR_TYPE_PGC'  # 剧集更新
    ugc_season = 'AUTHOR_TYPE_UGC_SEASON'  # 合集更新


@unique
class EmojiType(StrEnum):
    """表情类型"""
    none = 'EMOJI_TYPE_NONE'
    old = 'EMOJI_TYPE_OLD'
    new = 'EMOJI_TYPE_NEW'
    vip = 'EMOJI_TYPE_VIP'


@unique
class AdditionalType(StrEnum):
    """相关内容卡片类型"""
    none = 'ADDITIONAL_TYPE_NONE'
    pgc = 'ADDITIONAL_TYPE_PGC'
    goods = 'ADDITIONAL_TYPE_GOODS'  # 商品信息
    vote = 'ADDITIONAL_TYPE_VOTE'  # 投票
    common = 'ADDITIONAL_TYPE_COMMON'  # 一般类型
    match = 'ADDITIONAL_TYPE_MATCH'
    up_rcmd = 'ADDITIONAL_TYPE_UP_RCMD'
    ugc = 'ADDITIONAL_TYPE_UGC'  # 视频跳转
    reserve = 'ADDITIONAL_TYPE_RESERVE'


@unique
class AdditionalButtonType(StrEnum):
    """相关内容卡片类型 (BUTTON)"""
    none = 'ADDITIONAL_BUTTON_TYPE_NONE'
    jump = 'ADDITIONAL_BUTTON_TYPE_JUMP'
    button = 'ADDITIONAL_BUTTON_TYPE_BUTTON'


@unique
class AdditionalButtonStatus(StrEnum):
    """相关内容卡片类型 (BUTTON_STATUS)"""
    none = 'ADDITIONAL_BUTTON_STATUS_NONE'
    uncheck = 'ADDITIONAL_BUTTON_STATUS_UNCHECK'
    check = 'ADDITIONAL_BUTTON_STATUS_CHECK'


@unique
class AddButtonClickType(StrEnum):
    """相关内容卡片类型 (ADD_BUTTON_CLICK)"""
    none = 'ADD_BUTTON_CLICK_TYPE_NONE'
    reserve = 'ADD_BUTTON_CLICK_TYPE_RESERVE'


@unique
class DisableState(StrEnum):
    """相关内容卡片类型 (DISABLE_STATE)"""
    highlight = 'DISABLE_STATE_HIGHLIGHT'
    gray = 'DISABLE_STATE_GRAY'


@unique
class AddButtonBgStyle(StrEnum):
    """相关内容卡片类型 (ADD_BUTTON_BG_STYLE)"""
    fill = 'ADD_BUTTON_BG_STYLE_FILL'
    stroke = 'ADD_BUTTON_BG_STYLE_STROKE'
    gray = 'ADD_BUTTON_BG_STYLE_GRAY'


@unique
class HighlightTextStyleType(StrEnum):
    """相关内容卡片类型 (HIGHLIGHT_TEXT_STYLE)"""
    none = 'HIGHLIGHT_TEXT_STYLE_TYPE_NONE'
    active = 'HIGHLIGHT_TEXT_STYLE_TYPE_ACTIVE'


@unique
class MajorType(StrEnum):
    """动态主体类型"""
    none = 'MAJOR_TYPE_NONE'  # 动态失效/转发动态
    opus = 'MAJOR_TYPE_OPUS'  # 图文动态
    archive = 'MAJOR_TYPE_ARCHIVE'  # 视频
    pgc = 'MAJOR_TYPE_PGC'  # 剧集更新
    courses = 'MAJOR_TYPE_COURSES'
    draw = 'MAJOR_TYPE_DRAW'  # 带图动态
    article = 'MAJOR_TYPE_ARTICLE'
    music = 'MAJOR_TYPE_MUSIC'  # 音频更新
    common = 'MAJOR_TYPE_COMMON'  # 一般类型
    live = 'MAJOR_TYPE_LIVE'  # 直播间分享
    medialist = 'MAJOR_TYPE_MEDIALIST'
    applet = 'MAJOR_TYPE_APPLET'
    subscription = 'MAJOR_TYPE_SUBSCRIPTION'
    live_rcmd = 'MAJOR_TYPE_LIVE_RCMD'  # 直播状态
    ugc_season = 'MAJOR_TYPE_UGC_SEASON'  # 合计更新
    subscription_new = 'MAJOR_TYPE_SUBSCRIPTION_NEW'


@unique
class MediaType(StrEnum):
    """动态主体类型 (MEDIA)"""
    none = 'MEDIA_TYPE_NONE'
    ugc = 'MEDIA_TYPE_UGC'
    pgc = 'MEDIA_TYPE_PGC'
    live = 'MEDIA_TYPE_LIVE'


@unique
class PgcSubType(StrEnum):
    """动态主体类型 (PGC_SUB)"""
    none = 'PGC_SUB_TYPE_NONE'
    bangumi = 'PGC_SUB_TYPE_BANGUMI'
    movie = 'PGC_SUB_TYPE_MOVIE'
    documentary = 'PGC_SUB_TYPE_DOCUMENTARY'
    domestic = 'PGC_SUB_TYPE_DOMESTIC'
    tv = 'PGC_SUB_TYPE_TV'


@unique
class DrawTagType(StrEnum):
    """动态主体类型 (DRAW_TAG)"""
    none = 'DRAW_TAG_TYPE_NONE'
    common = 'DRAW_TAG_TYPE_COMMON'
    goods = 'DRAW_TAG_TYPE_GOODS'
    user = 'DRAW_TAG_TYPE_USER'
    topic = 'DRAW_TAG_TYPE_TOPIC'
    lbs = 'DRAW_TAG_TYPE_LBS'


@unique
class MajorCommonStyleType(StrEnum):
    """动态主体类型 (MAJOR_COMMON_STYLE)"""
    none = 'MAJOR_COMMON_STYLE_TYPE_NONE'
    square = 'MAJOR_COMMON_STYLE_TYPE_SQUARE'
    vertical = 'MAJOR_COMMON_STYLE_TYPE_VERTICAL'


@unique
class ReserveType(StrEnum):
    """动态主体类型 (RESERVE)"""
    none = 'RESERVE_TYPE_NONE'
    recall = 'RESERVE_TYPE_RECALL'


@unique
class LiveStateType(StrEnum):
    """动态主体类型 (LIVE_STATE)"""
    none = 'LIVE_STATE_TYPE_NONE'
    live = 'LIVE_STATE_TYPE_LIVE'
    rotation = 'LIVE_STATE_TYPE_ROTATION'


@unique
class SubscriptionNewStyleType(StrEnum):
    """动态主体类型 (SUBSCRIPTION_NEW_STYLE)"""
    none = 'SUBSCRIPTION_NEW_STYLE_TYPE_NONE'
    draw = 'SUBSCRIPTION_NEW_STYLE_TYPE_DRAW'
    live = 'SUBSCRIPTION_NEW_STYLE_TYPE_LIVE'


@unique
class ThreePointType(StrEnum):
    """动态主体类型 (THREE_POINT)"""
    delete = 'THREE_POINT_DELETE'  # 删除
    report = 'THREE_POINT_REPORT'  # 举报
    following = 'THREE_POINT_FOLLOWING'  # 关注/取消关注
    top = 'THREE_POINT_TOP'  # 置顶/取消置顶
    unfav = 'THREE_POINT_UNFAV'
    unsubs = 'THREE_POINT_UNSUBS'
    topic_report = 'THREE_POINT_TOPIC_REPORT'
    topic_irrelevant = 'THREE_POINT_TOPIC_IRRELEVANT'
    rcmd_resource = 'THREE_POINT_RCMD_RESOURCE'
    rcmd_feedback = 'THREE_POINT_RCMD_FEEDBACK'


@unique
class FoldType(StrEnum):
    """动态主体类型 (FOLD)"""
    none = 'FOLD_TYPE_NONE'
    publish = 'FOLD_TYPE_PUBLISH'
    frequent = 'FOLD_TYPE_FREQUENT'
    unite = 'FOLD_TYPE_UNITE'
    limit = 'FOLD_TYPE_LIMIT'


@unique
class DynStatusType(StrEnum):
    """动态主体类型 (DYN_STATUS)"""
    none = 'DYN_STATUS_TYPE_NONE'
    normal = 'DYN_STATUS_TYPE_NORMAL'
    auditing = 'DYN_STATUS_TYPE_AUDITING'
    self_visible = 'DYN_STATUS_TYPE_SELF_VISIBLE'
    deleted = 'DYN_STATUS_TYPE_DELETED'


@unique
class SceneType(StrEnum):
    """动态主体类型 (SCENE)"""
    detail = 'SCENE_DETAIL'
    hot = 'SCENE_HOT'
    general = 'SCENE_GENERAL'
    space = 'SCENE_SPACE'
    topic = 'SCENE_TOPIC'


class DynItemModuleAuthor(BaseBilibiliModel):
    """UP 主信息"""
    # avatar: dict[str, Any]
    face: AnyHttpUrl
    face_nft: bool
    following: bool | None = Field(False)
    jump_url: str
    label: str
    mid: str
    name: str
    # official_verify: dict[str, Any]
    # pendant: dict[str, Any]
    pub_action: str = Field('')
    pub_location_text: str = Field('')
    pub_time: str = Field('')
    pub_ts: int
    type: AuthorType
    # vip: dict[str, Any]


class BaseAdditionalItemDesc(BaseBilibiliModel):
    style: int
    text: str


class AdditionalNoneItem(BaseBilibiliModel):
    """动态失效/转发动态"""


class AdditionalPgcItem(BaseBilibiliModel):
    """剧集类型"""


class AdditionalGoodsItem(BaseBilibiliModel):
    """商品内容"""
    head_icon: str = Field('')
    head_text: str
    items: list[dict[str, Any]]
    jump_url: str = Field('')


class AdditionalVoteItem(BaseBilibiliModel):
    """投票信息"""
    choice_cnt: int
    default_share: int
    desc: str
    end_time: int
    join_num: int
    status: int
    # type: Any | None
    uid: str
    vote_id: str


class AdditionalCommonItem(BaseBilibiliModel):
    """一般类型"""
    # button: dict[str, Any]
    cover: str
    desc1: str
    desc2: str
    head_text: str
    id_str: str
    jump_url: str
    style: int
    sub_type: str
    title: str


class AdditionalMatchItem(BaseBilibiliModel):
    """ADDITIONAL_TYPE_MATCH"""


class AdditionalUpRcmdItem(BaseBilibiliModel):
    """直播状态更新"""


class AdditionalUgcItem(BaseBilibiliModel):
    """视频信息"""
    cover: str
    desc_second: str
    duration: str
    head_text: str = Field('')
    id_str: str
    jump_url: str
    multi_line: bool
    title: str


class AdditionalReserveItem(BaseBilibiliModel):
    """预约信息"""
    # button: dict[str, Any]
    desc1: BaseAdditionalItemDesc
    desc2: BaseAdditionalItemDesc
    # desc3: BaseAdditionalItemDesc
    jump_url: str
    reserve_total: int
    rid: str
    state: int
    stype: int
    title: str
    up_mid: str



class BaseModuleDynamicAdditional(BaseBilibiliModel):
    """相关内容卡片信息"""
    type: AdditionalType


class ModuleDynamicAdditionalNone(BaseModuleDynamicAdditional):
    """一般类型"""
    none: AdditionalNoneItem


class ModuleDynamicAdditionalPgc(BaseModuleDynamicAdditional):
    """一般类型"""
    pgc: AdditionalPgcItem


class ModuleDynamicAdditionalGoods(BaseModuleDynamicAdditional):
    """商品内容"""
    goods: AdditionalGoodsItem


class ModuleDynamicAdditionalVote(BaseModuleDynamicAdditional):
    """投票信息"""
    vote: AdditionalVoteItem


class ModuleDynamicAdditionalCommon(BaseModuleDynamicAdditional):
    """一般类型"""
    common: AdditionalCommonItem


class ModuleDynamicAdditionalMatch(BaseModuleDynamicAdditional):
    """一般类型"""
    match: AdditionalMatchItem


class ModuleDynamicAdditionalUpRcmd(BaseModuleDynamicAdditional):
    """一般类型"""
    up_rcmd: AdditionalUpRcmdItem


class ModuleDynamicAdditionalUgc(BaseModuleDynamicAdditional):
    """视频信息"""
    ugc: AdditionalUgcItem


class ModuleDynamicAdditionalReserve(BaseModuleDynamicAdditional):
    """预约信息"""
    reserve: AdditionalReserveItem


type ModuleDynamicAdditional = (
        ModuleDynamicAdditionalNone
        | ModuleDynamicAdditionalPgc
        | ModuleDynamicAdditionalGoods
        | ModuleDynamicAdditionalVote
        | ModuleDynamicAdditionalCommon
        | ModuleDynamicAdditionalMatch
        | ModuleDynamicAdditionalUpRcmd
        | ModuleDynamicAdditionalReserve
        | ModuleDynamicAdditionalUgc
        | BaseModuleDynamicAdditional
)


class DescRichTextNodeEmoji(BaseBilibiliModel):
    icon_url: str
    size: int
    text: str
    type: int


class DescRichTextNode(BaseBilibiliModel):
    orig_text: str
    text: str
    type: RichTextNodeType
    emoji: DescRichTextNodeEmoji | None = Field(None)
    jump_url: str | None = Field(None)
    rid: str | None = Field(None)


class ModuleDynamicDesc(BaseBilibiliModel):
    """动态文字内容"""
    rich_text_nodes: list[DescRichTextNode]
    text: str


class MajorNoneItem(BaseBilibiliModel):
    """动态失效/转发动态"""
    tips: str = Field('动态已失效或已被删除')


class MajorOpusItem(BaseBilibiliModel):
    """图文动态"""

    class _Pic(BaseBilibiliModel):
        height: int
        width: int
        size: str
        url: str
        live_url: str | None = Field(None)

    fold_action: list[str]
    jump_url: str
    pics: list[_Pic]
    summary: ModuleDynamicDesc
    title: str | None = Field(None)


class MajorArchiveItem(BaseBilibiliModel):
    """视频信息"""
    aid: str
    # badge: dict[str, Any]
    bvid: str
    cover: str
    desc: str
    disable_preview: int
    duration_text: str
    jump_url: str
    stat: dict[str, Any]
    title: str
    type: int


class MajorPgcItem(BaseBilibiliModel):
    """剧集信息"""
    # badge: dict[str, Any]
    cover: str
    epid: str
    jump_url: str
    season_id: str
    stat: dict[str, Any]
    sub_type: int
    title: str
    type: int = Field(2)


class MajorCoursesItem(BaseBilibiliModel):
    """课程信息"""
    # badge: dict[str, Any]
    cover: str
    desc: str
    id: str
    jump_url: str
    sub_title: str
    title: str


class MajorDrawItem(BaseBilibiliModel):
    """带图动态"""

    class _Item(BaseBilibiliModel):
        height: int
        width: int
        size: str
        src: str
        tags: list[str]

    id: str
    items: list[_Item]


class MajorArticleItem(BaseBilibiliModel):
    """专栏类型"""
    covers: list[str]
    desc: str
    id: str
    jump_url: str
    label: str
    title: str


class MajorMusicItem(BaseBilibiliModel):
    """音频信息"""
    cover: str
    id: str
    jump_url: str
    label: str
    title: str


class MajorCommonItem(BaseBilibiliModel):
    """一般类型"""
    # badge: dict[str, Any]
    biz_type: int = Field(0)
    cover: str
    desc: str
    id: str
    jump_url: str
    label: str = Field('')
    sketch_id: str
    style: int = Field(1)
    title: str


class MajorLiveItem(BaseBilibiliModel):
    """直播间分享"""
    # badge: dict[str, Any]
    cover: str
    desc_first: str  # 直播主分区名称
    desc_second: str  # 观看人数
    id: str
    jump_url: str
    live_state: int
    reserve_type: int = Field(0)
    title: str


class MajorLiveRcmdItem(BaseBilibiliModel):
    """直播状态"""
    class _Content(BaseBilibiliModel):
        class _LivePlayInfo(BaseBilibiliModel):
            area_id: int
            area_name: str
            parent_area_id: int
            parent_area_name: str
            live_start_time: int
            room_id: int
            room_type: int
            room_paid_type: int
            play_type: int
            cover: str
            uid: int
            online: int
            link: str
            live_id: str
            live_screen_type: int
            live_status: int
            title: str

        type: int
        live_play_info: _LivePlayInfo

    content: Json[_Content]
    reserve_type: str


class MajorMedialistItem(BaseBilibiliModel):
    """合集信息"""


class MajorAppletItem(BaseBilibiliModel):
    """小程序信息"""


class MajorSubscriptionItem(BaseBilibiliModel):
    """订阅信息"""


class MajorSubscriptionNewItem(BaseBilibiliModel):
    """订阅信息"""


class MajorUgcSeasonItem(BaseBilibiliModel):
    """合集信息"""
    aid: str
    # badge: dict[str, Any]
    cover: str
    desc: str
    disable_preview: int
    duration_text: str
    jump_url: str
    stat: dict[str, Any]
    title: str


class BaseModuleDynamicMajor(BaseBilibiliModel):
    """动态主体对象"""
    type: MajorType

    def get_major_image_urls(self) -> list[str]:
        """获取图片链接"""
        return []

    def get_major_text(self) -> str:
        """获取文本内容"""
        return ''


class ModuleDynamicMajorNone(BaseModuleDynamicMajor):
    """动态失效/转发动态"""
    none: MajorNoneItem

    def get_major_text(self) -> str:
        return self.none.tips



class ModuleDynamicMajorOpus(BaseModuleDynamicMajor):
    """图文动态"""
    opus: MajorOpusItem

    def get_major_image_urls(self) -> list[str]:
        return [x.url for x in self.opus.pics]

    def get_major_text(self) -> str:
        return self.opus.summary.text


class ModuleDynamicMajorArchive(BaseModuleDynamicMajor):
    """视频信息"""
    archive: MajorArchiveItem

    def get_major_image_urls(self) -> list[str]:
        return [self.archive.cover]

    def get_major_text(self) -> str:
        return (
            f'《{self.archive.title}》\n{self.archive.desc}\n'
            f'视频传送门: https://{self.archive.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorPgc(BaseModuleDynamicMajor):
    """剧集信息"""
    pgc: MajorPgcItem

    def get_major_image_urls(self) -> list[str]:
        return [self.pgc.cover]

    def get_major_text(self) -> str:
        return (
            f'《{self.pgc.title}》\n'
            f'剧集传送门: {self.pgc.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorCourses(BaseModuleDynamicMajor):
    """课程信息"""
    courses: MajorCoursesItem

    def get_major_image_urls(self) -> list[str]:
        return [self.courses.cover]

    def get_major_text(self) -> str:
        return (
            f'《{self.courses.title}》\n{self.courses.desc}\n'
            f'课程传送门: https://{self.courses.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorDraw(BaseModuleDynamicMajor):
    """带图动态"""
    draw: MajorDrawItem

    def get_major_image_urls(self) -> list[str]:
        return [x.src for x in self.draw.items]

    def get_major_text(self) -> str:
        return ''


class ModuleDynamicMajorArticle(BaseModuleDynamicMajor):
    """专栏类型"""
    article: MajorArticleItem

    def get_major_image_urls(self) -> list[str]:
        return self.article.covers

    def get_major_text(self) -> str:
        return (
            f'《{self.article.title}》\n{self.article.desc}\n'
            f'专栏传送门: https://{self.article.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorMusic(BaseModuleDynamicMajor):
    """音频信息"""
    music: MajorMusicItem

    def get_major_image_urls(self) -> list[str]:
        return [self.music.cover]

    def get_major_text(self) -> str:
        return (
            f'《{self.music.title}》\n'
            f'音频传送门: https://{self.music.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorCommon(BaseModuleDynamicMajor):
    """一般类型"""
    common: MajorCommonItem

    def get_major_image_urls(self) -> list[str]:
        return [self.common.cover]

    def get_major_text(self) -> str:
        return f'{self.common.title}\n{self.common.desc}'


class ModuleDynamicMajorLive(BaseModuleDynamicMajor):
    """直播间分享"""
    live: MajorLiveItem

    def get_major_image_urls(self) -> list[str]:
        return [self.live.cover]

    def get_major_text(self) -> str:
        return (
            f'{self.live.title}\n'
            f'直播间传送门: https://{self.live.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorLiveRcmd(BaseModuleDynamicMajor):
    """直播状态"""
    live_rcmd: MajorLiveRcmdItem

    def get_major_image_urls(self) -> list[str]:
        return [self.live_rcmd.content.live_play_info.cover]

    def get_major_text(self) -> str:
        return self.live_rcmd.content.live_play_info.title


class ModuleDynamicMajorMedialist(BaseModuleDynamicMajor):
    """合集信息"""
    medialist: MajorMedialistItem


class ModuleDynamicMajorApplet(BaseModuleDynamicMajor):
    """小程序信息"""
    applet: MajorAppletItem


class ModuleDynamicMajorSubscription(BaseModuleDynamicMajor):
    """订阅信息"""
    subscription: MajorSubscriptionItem


class ModuleDynamicMajorSubscriptionNew(BaseModuleDynamicMajor):
    """订阅信息"""
    subscription_new: MajorSubscriptionNewItem


class ModuleDynamicMajorUgcSeason(BaseModuleDynamicMajor):
    """合集信息"""
    ugc_season: MajorUgcSeasonItem

    def get_major_image_urls(self) -> list[str]:
        return [self.ugc_season.cover]

    def get_major_text(self) -> str:
        return (
            f'《{self.ugc_season.title}》\n{self.ugc_season.desc}\n'
            f'合集传送门: https://{self.ugc_season.jump_url.removeprefix("//")}'
        )


type ModuleDynamicMajor = (
        ModuleDynamicMajorNone
        | ModuleDynamicMajorOpus
        | ModuleDynamicMajorArchive
        | ModuleDynamicMajorPgc
        | ModuleDynamicMajorCourses
        | ModuleDynamicMajorDraw
        | ModuleDynamicMajorArticle
        | ModuleDynamicMajorMusic
        | ModuleDynamicMajorCommon
        | ModuleDynamicMajorLive
        | ModuleDynamicMajorLiveRcmd
        | ModuleDynamicMajorMedialist
        | ModuleDynamicMajorApplet
        | ModuleDynamicMajorSubscription
        | ModuleDynamicMajorSubscriptionNew
        | ModuleDynamicMajorUgcSeason
        | BaseModuleDynamicMajor
)


class ModuleDynamicTopic(BaseBilibiliModel):
    """话题信息"""
    id: str
    jump_url: str
    name: str


class DynItemModuleDynamic(BaseBilibiliModel):
    """动态内容信息"""
    additional: ModuleDynamicAdditional | None = Field(None)  # 相关内容卡片信息
    desc: ModuleDynamicDesc | None = Field(None)  # 动态文字内容
    major: ModuleDynamicMajor | None = Field(None)  # 动态主体对象
    topic: ModuleDynamicTopic | None = Field(None)  # 话题信息


class DynItemModuleMore(BaseBilibiliModel):
    """动态右上角三点菜单"""
    three_point_items: list[dict[str, Any]]


class DynItemModuleStat(BaseBilibiliModel):
    """动态统计数据"""
    comment: dict[str, Any]
    forward: dict[str, Any]
    like: dict[str, Any]


class DynItemModuleInteraction(BaseBilibiliModel):
    """热度评论"""
    items: list[dict[str, Any]]


class DynItemModuleFold(BaseBilibiliModel):
    """动态折叠信息"""
    ids: list[str]
    statement: str
    type: int = Field(1)
    users: list[str] = Field(default_factory=list)


class DynItemModuleDispute(BaseBilibiliModel):
    """争议小黄条"""
    desc: str
    jump_url: str
    title: str


class DynItemModuleTag(BaseBilibiliModel):
    """置顶信息"""
    text: str


class DynItemModules(BaseBilibiliModel):
    """动态信息"""
    module_author: DynItemModuleAuthor
    module_dynamic: DynItemModuleDynamic
    # module_more: DynItemModuleMore | None = Field(None)
    # module_stat: DynItemModuleStat | None = Field(None)
    # module_interaction: DynItemModuleInteraction | None = Field(None)
    # module_fold: DynItemModuleFold | None = Field(None)
    # module_dispute: DynItemModuleDispute | None = Field(None)
    # module_tag: DynItemModuleTag | None = Field(None)

    @property
    def uname(self) -> str:
        return self.module_author.name

    @property
    def pub_text(self) -> str:
        """动态发布说明文本"""
        return (
            f'{self.uname}{f" {pub_time} " if (pub_time := self.module_author.pub_time) else ""}'
            f'{pub_action if (pub_action := self.module_author.pub_action) else "发布了新动态"}'
        )

    @property
    def desc_text(self) -> str:
        """动态内容文本"""
        return desc.text if (desc := self.module_dynamic.desc) is not None else ''

    @property
    def major_text(self) -> str:
        """动态主体内容文本"""
        return major.get_major_text() if (major := self.module_dynamic.major) is not None else ''

    @property
    def dyn_text(self) -> str:
        """格式化动态内容文本"""
        return (
            f'{self.pub_text}'
            f'{f"\n\n“{self.desc_text}”" if self.desc_text else ""}'
            f'{f"\n\n{self.major_text}" if self.major_text else ""}'
        )

    @property
    def dyn_image_urls(self) -> list[str]:
        """动态图片链接列表"""
        return self.module_dynamic.major.get_major_image_urls() if self.module_dynamic.major is not None else []


class DynItemBasic(BaseBilibiliModel):
    comment_id_str: str
    comment_type: str
    rid_str: str


class DynCommonItem(BaseBilibiliModel):
    basic: DynItemBasic
    id_str: str
    modules: DynItemModules
    type: DynamicType
    visible: bool

    @property
    def dyn_text(self) -> str:
        """动态内容文本"""
        return self.modules.dyn_text

    @property
    def dyn_image_urls(self) -> list[str]:
        """动态图片链接列表"""
        return self.modules.dyn_image_urls


class DynForwardItem(DynCommonItem):
    orig: DynCommonItem

    @property
    def dyn_text(self) -> str:
        """动态内容文本"""
        return (
            f'{self.modules.dyn_text}'
            f'{f"\n{"=" * 8}转发动态{"=" * 8}\n{self.orig.dyn_text}" if self.orig.dyn_text else ""}'
        )

    @property
    def dyn_image_urls(self) -> list[str]:
        """动态图片链接列表"""
        return self.modules.dyn_image_urls + self.orig.dyn_image_urls


type DynItem = DynForwardItem | DynCommonItem


class DynData(BaseBilibiliModel):
    has_more: bool
    items: list[DynItem]
    offset: str
    update_baseline: str
    update_num: int


class Dynamics(BaseBilibiliResponse):
    """获取动态列表结果"""
    data: DynData


class DynDetail(BaseBilibiliResponse):
    """获取单条动态详情结果"""
    class _Item(BaseBilibiliModel):
        item: DynItem

    data: _Item


__all__ = [
    'BaseModuleDynamicMajor',
    'Dynamics',
    'DynamicType',
    'DynDetail',
    'DynData',
    'DynItem',
    'DynCommonItem',
    'DynForwardItem',
    'DynItemModules',
    'ModuleDynamicMajor',
    'ModuleDynamicMajorNone',
    'ModuleDynamicMajorOpus',
    'ModuleDynamicMajorArchive',
    'ModuleDynamicMajorPgc',
    'ModuleDynamicMajorCourses',
    'ModuleDynamicMajorDraw',
    'ModuleDynamicMajorArticle',
    'ModuleDynamicMajorMusic',
    'ModuleDynamicMajorCommon',
    'ModuleDynamicMajorLive',
    'ModuleDynamicMajorLiveRcmd',
    'ModuleDynamicMajorMedialist',
    'ModuleDynamicMajorApplet',
    'ModuleDynamicMajorSubscription',
    'ModuleDynamicMajorSubscriptionNew',
    'ModuleDynamicMajorUgcSeason',
]
