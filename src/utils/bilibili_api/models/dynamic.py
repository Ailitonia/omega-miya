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
from typing import Any, Literal

from pydantic import Field, Json

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseBilibiliModel, BaseBilibiliResponse


# ------------------------------------------------------------------ #
# 动态类型及富文本节点类型枚举值
# ------------------------------------------------------------------ #


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
    view_picture = 'RICH_TEXT_NODE_TYPE_VIEW_PICTURE'
    web = 'RICH_TEXT_NODE_TYPE_WEB'  # 网页链接
    taobao = 'RICH_TEXT_NODE_TYPE_TAOBAO'
    mail = 'RICH_TEXT_NODE_TYPE_MAIL'  # 邮箱地址
    ogv_season = 'RICH_TEXT_NODE_TYPE_OGV_SEASON'  # 剧集信息
    ogv_ep = 'RICH_TEXT_NODE_TYPE_OGV_EP'
    search_word = 'RICH_TEXT_NODE_TYPE_SEARCH_WORD'


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
    none = 'ADDITIONAL_TYPE_NONE'  # 无附加类型
    pgc = 'ADDITIONAL_TYPE_PGC'  # 番剧影视
    goods = 'ADDITIONAL_TYPE_GOODS'  # 商品信息
    vote = 'ADDITIONAL_TYPE_VOTE'  # 投票
    common = 'ADDITIONAL_TYPE_COMMON'  # 一般类型
    match = 'ADDITIONAL_TYPE_MATCH'  # 比赛
    up_rcmd = 'ADDITIONAL_TYPE_UP_RCMD'  # UP主推荐
    ugc = 'ADDITIONAL_TYPE_UGC'  # 视频跳转
    reserve = 'ADDITIONAL_TYPE_RESERVE'  # 直播预约
    upower_lottery = 'ADDITIONAL_TYPE_UPOWER_LOTTERY'  # 动态充电互动抽奖


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
    upower_common = 'MAJOR_TYPE_UPOWER_COMMON'  # 充电相关


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
    """动态右上角三点菜单 (THREE_POINT)"""
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
    """动态右上角三点菜单 (FOLD)"""
    none = 'FOLD_TYPE_NONE'
    publish = 'FOLD_TYPE_PUBLISH'
    frequent = 'FOLD_TYPE_FREQUENT'
    unite = 'FOLD_TYPE_UNITE'
    limit = 'FOLD_TYPE_LIMIT'


@unique
class DynStatusType(StrEnum):
    """动态右上角三点菜单 (DYN_STATUS)"""
    none = 'DYN_STATUS_TYPE_NONE'
    normal = 'DYN_STATUS_TYPE_NORMAL'
    auditing = 'DYN_STATUS_TYPE_AUDITING'
    self_visible = 'DYN_STATUS_TYPE_SELF_VISIBLE'
    deleted = 'DYN_STATUS_TYPE_DELETED'


@unique
class SceneType(StrEnum):
    """动态右上角三点菜单 (SCENE)"""
    detail = 'SCENE_DETAIL'
    hot = 'SCENE_HOT'
    general = 'SCENE_GENERAL'
    space = 'SCENE_SPACE'
    topic = 'SCENE_TOPIC'


@unique
class OpusModuleType(StrEnum):
    """动态新版 opus 功能模块类型"""
    title = 'MODULE_TYPE_TITLE'
    author = 'MODULE_TYPE_AUTHOR'
    stat = 'MODULE_TYPE_STAT'
    content = 'MODULE_TYPE_CONTENT'
    topic = 'MODULE_TYPE_TOPIC'
    collection = 'MODULE_TYPE_COLLECTION'
    extend = 'MODULE_TYPE_EXTEND'
    bottom = 'MODULE_TYPE_BOTTOM'


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块基类
# ------------------------------------------------------------------ #


class _BaseDynOpusItemModule(BaseBilibiliModel):
    """模块信息"""
    module_type: OpusModuleType


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleTitle
# ------------------------------------------------------------------ #

class _DynItemModuleTitleItem(BaseBilibiliModel):
    """标题内容"""
    text: str


class DynOpusItemModuleTitle(_BaseDynOpusItemModule):
    """标题信息"""
    module_title: _DynItemModuleTitleItem
    module_type: Literal[OpusModuleType.title]


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleMore, 兼容 DynItem.modules.module_more 三点更多按钮部分
# ------------------------------------------------------------------ #


class _DynItemModuleMoreThreePointItemParams(BaseBilibiliModel):
    dyn_id_str: str = Field(default_factory=str)
    dyn_type: str = Field(default_factory=str)
    rid_str: str = Field(default_factory=str)


class _DynItemModuleMoreThreePointItemModal(BaseBilibiliModel):
    cancel: str = Field(default_factory=str)
    confirm: str = Field(default_factory=str)
    content: str = Field(default_factory=str)
    title: str = Field(default_factory=str)


class _DynItemModuleMoreThreePointItem(BaseBilibiliModel):
    label: str = Field(default_factory=str)
    modal: _DynItemModuleMoreThreePointItemModal | None = Field(default=None)
    params: _DynItemModuleMoreThreePointItemParams | None = Field(default=None)
    type: str = Field(default_factory=str)


class _DynItemModuleMoreItem(BaseBilibiliModel):
    three_point_items: list[_DynItemModuleMoreThreePointItem] = Field(default_factory=list)


class DynOpusItemModuleMore(BaseBilibiliModel):
    """三点更多按钮模块"""
    module_more: _DynItemModuleMoreItem = Field(default_factory=_DynItemModuleMoreItem)


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleAuthor, 兼容 DynItem.modules.module_author 动态用户信息部分
# ------------------------------------------------------------------ #


class _DynItemModuleAuthor(BaseBilibiliModel):
    """用户信息"""
    # avatar: Any  # 头像信息, 主要用于网页渲染, 忽略
    # decorate: Any  # 装扮, 仅当动态接口且无 decorationCard 时存在, 忽略
    # decorate_card: Any  # 装扮, 仅当图文接口时存在, 忽略
    # decoration_card: Any    # 装扮, 仅当动态接口且有 decorationCard 时存在, 同 decorate_card, 忽略
    face: AnyHttpUrl
    face_nft: bool
    following: bool | int | None = Field(default=False)
    jump_url: str
    label: str  # 名称前标签 (合集, 电视剧, 番剧, etc.)
    mid: str  # UP 主 UID, 剧集 SeasonId
    name: str
    views_text: str = Field(default_factory=str)
    # official: Any  # UP 主认证信息, 仅图文接口, 忽略
    # official_verify: Any  # UP 主认证信息, 仅动态接口, 忽略
    # pendant: Any  # UP 主头像框, 忽略
    pub_action: str = Field(default_factory=str)  # 更新动作描述, 仅动态接口 (投稿了视频, 直播了, etc.)
    pub_location_text: str = Field(default_factory=str)
    pub_time: str = Field(default_factory=str)  # 更新时间 (x分钟前, x小时前, 昨天, etc.)
    pub_ts: int  # 更新时间戳, UNIX 秒级时间戳
    type: AuthorType  # 作者类型
    # vip: Any  # UP 主大会员信息, 忽略
    more: DynOpusItemModuleMore | None = Field(default=None)  # 三点按钮中的项目, 仅图文接口有, 其他为 null


class DynOpusItemModuleAuthor(_BaseDynOpusItemModule):
    """用户信息"""
    module_author: _DynItemModuleAuthor
    module_type: Literal[OpusModuleType.author]


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleStat, 兼容 DynItem.modules.module_stat 动态统计信息部分
# ------------------------------------------------------------------ #

class _DynItemModuleStatItemContent(BaseBilibiliModel):
    count: int = Field(default=0)
    forbidden: bool = Field(default=False)  # 是否屏蔽
    hidden: bool = Field(default=False)  # 是否隐藏
    status: bool = Field(default=False)  # 当前状态 (是否已进行该操作)


class _DynItemModuleStatItem(BaseBilibiliModel):
    coin: _DynItemModuleStatItemContent | None = Field(default=None)
    comment: _DynItemModuleStatItemContent | None = Field(default=None)
    favorite: _DynItemModuleStatItemContent | None = Field(default=None)
    forward: _DynItemModuleStatItemContent | None = Field(default=None)
    like: _DynItemModuleStatItemContent | None = Field(default=None)


class DynOpusItemModuleStat(_BaseDynOpusItemModule):
    """统计信息"""
    module_stat: _DynItemModuleStatItem
    module_type: Literal[OpusModuleType.stat]


# ------------------------------------------------------------------ #
# 动态新版 opus RichTextNode 富文本节点, 兼容 DynItemModules.module_dynamic 动态内容中 OpusItem 动态图文部分
# ------------------------------------------------------------------ #


class RichTextNodeTypeBase(BaseBilibiliModel):
    """RichTextNodeType"""
    orig_text: str
    text: str
    type: RichTextNodeType


class RichTextNodeTypeText(RichTextNodeTypeBase):
    """RichTextNodeType.text"""
    type: Literal[RichTextNodeType.text]


class RichTextNodeTypeAt(RichTextNodeTypeBase):
    """RichTextNodeType.at"""
    rid: str  # 用户 mid (UID)
    type: Literal[RichTextNodeType.at]


class RichTextNodeTypeLottery(RichTextNodeTypeBase):
    """RichTextNodeType.lottery"""
    rid: str  # 抽奖 id
    type: Literal[RichTextNodeType.lottery]


class RichTextNodeTypeVote(RichTextNodeTypeBase):
    """RichTextNodeType.vote"""
    rid: str  # 抽奖 id
    type: Literal[RichTextNodeType.vote]


class RichTextNodeTypeTopic(RichTextNodeTypeBase):
    """RichTextNodeType.topic"""
    jump_url: str  # 跳转 URL, 无协议头
    type: Literal[RichTextNodeType.topic]


class RichTextNodeTypeGoodsItem(BaseBilibiliModel):
    """RichTextNodeTypeGoods.goods 商品信息"""
    jump_url: str
    type: int


class RichTextNodeTypeGoods(RichTextNodeTypeBase):
    """RichTextNodeType.goods"""
    goods: RichTextNodeTypeGoodsItem  # 商品信息
    icon_name: str  # 图标名称 (shop, taobao, etc.)
    jump_url: str  # 跳转 URL
    rid: str
    type: Literal[RichTextNodeType.goods]


class RichTextNodeTypeBV(RichTextNodeTypeBase):
    """RichTextNodeType.bv"""
    jump_url: str  # 跳转 URL
    rid: str  # 视频 bvid
    type: Literal[RichTextNodeType.bv]


class RichTextNodeTypeAV(RichTextNodeTypeBase):
    """RichTextNodeType.av"""
    jump_url: str  # 跳转 URL
    rid: str  # 视频 av 号
    type: Literal[RichTextNodeType.av]


class RichTextNodeTypeEmojiItem(BaseBilibiliModel):
    """RichTextNodeTypeEmoji.emoji 表情信息"""
    icon_url: str
    size: int  # 表情尺寸, 1: small, 2: middle
    text: str  # 表情的文字代码, 一般与根对象的 text 一致
    type: int


class RichTextNodeTypeEmoji(RichTextNodeTypeBase):
    """RichTextNodeType.emoji"""
    emoji: RichTextNodeTypeEmojiItem  # 表情信息
    type: Literal[RichTextNodeType.emoji]


class RichTextNodeTypeCV(RichTextNodeTypeBase):
    """RichTextNodeType.cv"""
    jump_url: str  # 跳转 URL
    rid: str  # 专栏 CV 号
    type: Literal[RichTextNodeType.cv]


class RichTextNodeTypeViewPicturePicsItem(BaseBilibiliModel):
    """RichTextNodeTypeViewPicture.pics 图片信息"""
    src: str
    size: int
    height: int
    width: int


class RichTextNodeTypeViewPicture(RichTextNodeTypeBase):
    """RichTextNodeType.view_picture"""
    jump_url: str
    pics: list[RichTextNodeTypeViewPicturePicsItem]  # 图片信息
    rid: str  # 本条动态 id
    type: Literal[RichTextNodeType.view_picture]


class RichTextNodeTypeWebStyleItem(BaseBilibiliModel):
    """RichTextNodeTypeWeb.style 样式信息"""
    font_level: str
    font_size: int


class RichTextNodeTypeWeb(RichTextNodeTypeBase):
    """RichTextNodeType.web"""
    jump_url: str
    style: RichTextNodeTypeWebStyleItem | None = Field(default=None)
    type: Literal[RichTextNodeType.web]


class RichTextNodeTypeOgvSeason(RichTextNodeTypeBase):
    """RichTextNodeType.ogv_season"""
    jump_url: str
    rid: str
    type: Literal[RichTextNodeType.ogv_season]


class RichTextNodeTypeOgvEP(RichTextNodeTypeBase):
    """RichTextNodeType.ogv_ep"""
    jump_url: str
    rid: str
    type: Literal[RichTextNodeType.ogv_ep]


type RichTextNodes = (
        RichTextNodeTypeOgvEP
        | RichTextNodeTypeOgvSeason
        | RichTextNodeTypeWeb
        | RichTextNodeTypeViewPicture
        | RichTextNodeTypeCV
        | RichTextNodeTypeEmoji
        | RichTextNodeTypeAV
        | RichTextNodeTypeBV
        | RichTextNodeTypeGoods
        | RichTextNodeTypeTopic
        | RichTextNodeTypeVote
        | RichTextNodeTypeLottery
        | RichTextNodeTypeAt
        | RichTextNodeTypeText
        | RichTextNodeTypeBase
)


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleContent
# ------------------------------------------------------------------ #


class BaseDynItemModuleContentItemParagraph(BaseBilibiliModel):
    align: int  # 对齐方式, 0: 左对齐 (默认), 1: 居中, 2: 右对齐
    para_type: int  # 段落类型, 1: 文本, 2: 图片, 3: 分割线, 4: 块引用, 5: 列表, 6: 链接卡片, 7: 代码


class _FormulaNode(BaseBilibiliModel):
    class _Formula(BaseBilibiliModel):
        latex_content: str

    type: Literal['TEXT_NODE_TYPE_FORMULA']
    formula: _Formula


class _WordNode(BaseBilibiliModel):
    class _Word(BaseBilibiliModel):
        # font_size: Any  # 字体大小, 用于控制文本所用标签名 (如 h1 h2 p) 及行高
        # style: Any  # 补充样式
        words: str

    type: Literal['TEXT_NODE_TYPE_WORD']
    word: _Word


class _RichNode(BaseBilibiliModel):
    type: Literal['TEXT_NODE_TYPE_RICH']
    rich: RichTextNodes


class _TextParagraphNodes(BaseBilibiliModel):
    nodes: list[_RichNode | _WordNode | _FormulaNode]


class TextParagraph(BaseDynItemModuleContentItemParagraph):
    """文本/块引用"""
    para_type: Literal[1, 4]
    text: _TextParagraphNodes


class _PicsParagraphPicItem(BaseBilibiliModel):
    height: int
    width: int
    url: str
    live_url: str | None = Field(default=None)
    size: int | None = Field(default=None)


class _PicsParagraphPic(BaseBilibiliModel):
    style: int  # 样式, 1: isAlbum
    pics: list[_PicsParagraphPicItem]


class PicsParagraph(BaseDynItemModuleContentItemParagraph):
    """图片"""
    para_type: Literal[2]
    pic: _PicsParagraphPic


class _LineParagraphLinePic(BaseBilibiliModel):
    height: int
    url: str


class _LineParagraphLine(BaseBilibiliModel):
    pic: _LineParagraphLinePic


class LineParagraph(BaseDynItemModuleContentItemParagraph):
    """分割线"""
    para_type: Literal[3]
    line: _LineParagraphLine


class _ListParagraphListItem(BaseBilibiliModel):
    level: int
    nodes: list[_RichNode | _WordNode | _FormulaNode]
    order: int


class _ListParagraphList(BaseBilibiliModel):
    style: int  # 样式, 1: 有序列表, 2: 无序列表
    items: list[_ListParagraphListItem]


class ListParagraph(BaseDynItemModuleContentItemParagraph):
    """列表"""
    para_type: Literal[5]
    list: _ListParagraphList


class _BaseLinkCard(BaseBilibiliModel):
    oid: str | None = Field(default=None, description='关联id')
    type: str


class _CommonLinkCard(_BaseLinkCard):
    type: Literal[AdditionalType.common]
    common: 'AdditionalCommonItem'


class _GoodsLinkCard(_BaseLinkCard):
    type: Literal[AdditionalType.goods]
    goods: 'AdditionalGoodsItem'


class _MatchLinkCard(_BaseLinkCard):
    type: Literal[AdditionalType.match]
    match: 'AdditionalMatchItem'


class _VoteLinkCard(_BaseLinkCard):
    type: Literal[AdditionalType.vote]
    vote: 'AdditionalVoteItem'


class _UgcLinkCard(_BaseLinkCard):
    type: Literal[AdditionalType.ugc]
    ugc: 'AdditionalUgcItem'


class _ReserveLinkCard(_BaseLinkCard):
    type: Literal[AdditionalType.reserve]
    reserve: 'AdditionalReserveItem'


class _UpowerLotteryLinkCard(_BaseLinkCard):
    type: Literal[AdditionalType.upower_lottery]
    upower_lottery: 'AdditionalUpowerLotteryItem'


class _OpusLinkCardItemAuthor(BaseBilibiliModel):
    name: str


class _OpusLinkCardItemStat(BaseBilibiliModel):
    view: int


class _OpusLinkCardItem(BaseBilibiliModel):
    title: str
    author: _OpusLinkCardItemAuthor
    cover: str
    jump_url: str
    stat: _OpusLinkCardItemStat


class _OpusLinkCard(_BaseLinkCard):
    type: Literal['LINK_CARD_TYPE_OPUS']
    opus: _OpusLinkCardItem


class _MusicLinkCard(_BaseLinkCard):
    type: Literal['LINK_CARD_TYPE_MUSIC']
    music: 'MajorMusicItem'


class _LiveLinkCard(_BaseLinkCard):
    type: Literal['LINK_CARD_TYPE_LIVE']
    live: 'MajorLiveItem'


class _NullLinkCardItem(BaseBilibiliModel):
    text: str


class _NullLinkCard(_BaseLinkCard):
    type: Literal['LINK_CARD_TYPE_ITEM_NULL']
    item_null: _NullLinkCardItem


type LinkCardTypes = (
        _NullLinkCard
        | _LiveLinkCard
        | _MusicLinkCard
        | _OpusLinkCard
        | _UpowerLotteryLinkCard
        | _ReserveLinkCard
        | _UgcLinkCard
        | _VoteLinkCard
        | _MatchLinkCard
        | _GoodsLinkCard
        | _CommonLinkCard
        | _BaseLinkCard
)


class _LinkCardParagraphCard(BaseBilibiliModel):
    card: LinkCardTypes


class LinkCardParagraph(BaseDynItemModuleContentItemParagraph):
    """链接卡片"""
    para_type: Literal[6]
    link_card: _LinkCardParagraphCard


class _CodeParagraphCode(BaseBilibiliModel):
    content: str
    lang: str


class CodeParagraph(BaseDynItemModuleContentItemParagraph):
    """代码"""
    para_type: Literal[7]
    code: _CodeParagraphCode


type DynItemModuleContentItemParagraphTypes = (
        CodeParagraph
        | LinkCardParagraph
        | ListParagraph
        | LineParagraph
        | PicsParagraph
        | TextParagraph
        | BaseDynItemModuleContentItemParagraph
)


class _DynItemModuleContentItem(BaseBilibiliModel):
    paragraphs: list[DynItemModuleContentItemParagraphTypes] = Field(default_factory=list)


class DynOpusItemModuleContent(_BaseDynOpusItemModule):
    """动态内容"""
    module_content: _DynItemModuleContentItem
    module_type: Literal[OpusModuleType.content]


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleTopic, 兼容 DynItem.modules.module_dynamic.topic 话题信息部分
# ------------------------------------------------------------------ #


class _DynItemModuleTopicItem(BaseBilibiliModel):
    id: int
    name: str = Field(default_factory=str)
    jump_url: str = Field(default_factory=str)


class DynOpusItemModuleTopic(_BaseDynOpusItemModule):
    """话题"""
    module_topic: _DynItemModuleTopicItem
    module_type: Literal[OpusModuleType.topic]


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleCollection
# ------------------------------------------------------------------ #


class _DynItemModuleCollectionItem(BaseBilibiliModel):
    id: int
    name: str
    title: str
    count: str


class DynOpusItemModuleCollection(_BaseDynOpusItemModule):
    """文集"""
    module_collection: _DynItemModuleCollectionItem
    module_type: Literal[OpusModuleType.collection]


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleExtend
# ------------------------------------------------------------------ #

class _DynItemModuleExtendExtendItem(BaseBilibiliModel):
    text: str
    jump_url: str
    icon: str | None = Field(default=None)
    icon_svg: str | None = Field(default=None)


class _DynItemModuleExtendExtend(BaseBilibiliModel):
    items: list[_DynItemModuleExtendExtendItem]


class DynOpusItemModuleExtend(_BaseDynOpusItemModule):
    """扩展模块"""
    module_extend: _DynItemModuleExtendExtend
    module_type: Literal[OpusModuleType.extend]


# ------------------------------------------------------------------ #
# 动态新版 opus 功能模块 ModuleBottom
# ------------------------------------------------------------------ #

class _DynItemModuleBottomItemShareInfo(BaseBilibiliModel):
    title: str
    summary: str
    pic: str


class _DynItemModuleBottomItem(BaseBilibiliModel):
    share_info: _DynItemModuleBottomItemShareInfo


class DynOpusItemModuleBottom(_BaseDynOpusItemModule):
    """底部模块"""
    module_bottom: _DynItemModuleBottomItem
    module_type: Literal[OpusModuleType.bottom]


# ------------------------------------------------------------------ #
# 动态主体内容模型, DynItem.modules.module_dynamic -> 动态接口
# data.items[n].modules.module_dynamic / data.item.modules.module_dynamic 对象
# additional 对象部分, 动态相关内容卡片信息
# 与 opus 功能模块 ModuleContent 的 LinkCard 兼容
# ------------------------------------------------------------------ #


class BaseAdditionalItemDesc(BaseBilibiliModel):
    """相关内容卡片描述信息字段"""
    style: int = Field(default=-1)
    text: str = Field(default_factory=str)
    jump_url: str = Field(default_factory=str)
    visible: bool = Field(default=True)


class AdditionalNoneItem(BaseBilibiliModel):
    """动态失效/转发动态"""


class AdditionalPgcItem(BaseBilibiliModel):
    """剧集类型"""


class AdditionalGoodsItemItem(BaseBilibiliModel):
    id: str
    name: str
    brief: str
    cover: str
    price: str
    jump_desc: str
    jump_url: str


class AdditionalGoodsItem(BaseBilibiliModel):
    """商品内容"""
    head_icon: str = Field(default_factory=str)
    head_text: str = Field(default_factory=str)
    items: list[AdditionalGoodsItemItem] = Field(default_factory=list)
    jump_url: str = Field(default_factory=str)


class AdditionalVoteItem(BaseBilibiliModel):
    """投票信息"""
    choice_cnt: int
    default_share: int
    desc: str
    end_time: int
    join_num: int
    status: int
    type: Any = Field(default=None)
    uid: str
    vote_id: str


class AdditionalCommonItem(BaseBilibiliModel):
    """一般类型"""
    # button: Any  # 按钮内容, 忽略
    cover: str  # 左侧封面图
    desc1: str
    desc2: str
    head_text: str  # 卡片头文本
    id_str: str  # 相关id
    jump_url: str
    style: int
    sub_type: str  # 子类型 (game, decoration, ogv, etc.)
    title: str


class AdditionalMatchItemMatchTeam(BaseBilibiliModel):
    name: str
    pic: str


class AdditionalMatchItemMatchInfo(BaseBilibiliModel):
    center_bottom: str
    center_top: list[str]
    left_team: AdditionalMatchItemMatchTeam
    right_team: AdditionalMatchItemMatchTeam
    status: int
    title: str
    sub_title: str


class AdditionalMatchItem(BaseBilibiliModel):
    """赛事信息"""
    id_str: str
    match_info: AdditionalMatchItemMatchInfo
    jump_url: str


class AdditionalUpRcmdItem(BaseBilibiliModel):
    """直播状态更新"""


class AdditionalUgcItem(BaseBilibiliModel):
    """视频信息"""
    cover: str
    desc_second: str
    duration: str
    head_text: str = Field(default_factory=str)
    id_str: str  # 视频AV号
    jump_url: str
    multi_line: bool = Field(default=True)
    title: str


class AdditionalReserveItem(BaseBilibiliModel):
    """预约信息"""
    # button: Any  # 按钮内容, 忽略
    desc1: BaseAdditionalItemDesc
    desc2: BaseAdditionalItemDesc
    # desc3: BaseAdditionalItemDesc  # 预约有奖信息, 疑似已弃用, 忽略
    jump_url: str
    reserve_total: int
    rid: str
    state: int
    stype: int
    title: str
    up_mid: str


class AdditionalUpowerLotteryItem(BaseBilibiliModel):
    """动态充电互动抽奖"""
    desc: BaseAdditionalItemDesc
    hint: BaseAdditionalItemDesc
    jump_url: str
    rid: str
    state: int
    title: str
    up_mid: str
    upower_action_state: int
    upower_level: int


class BaseModuleDynamicAdditional(BaseBilibiliModel):
    """相关内容卡片信息"""
    type: AdditionalType


class ModuleDynamicAdditionalNone(BaseModuleDynamicAdditional):
    """无附加类型"""
    type: Literal[AdditionalType.none]
    none: AdditionalNoneItem


class ModuleDynamicAdditionalPgc(BaseModuleDynamicAdditional):
    """番剧影视"""
    type: Literal[AdditionalType.pgc]
    pgc: AdditionalPgcItem


class ModuleDynamicAdditionalGoods(BaseModuleDynamicAdditional):
    """商品内容"""
    type: Literal[AdditionalType.goods]
    goods: AdditionalGoodsItem


class ModuleDynamicAdditionalVote(BaseModuleDynamicAdditional):
    """投票信息"""
    type: Literal[AdditionalType.vote]
    vote: AdditionalVoteItem


class ModuleDynamicAdditionalCommon(BaseModuleDynamicAdditional):
    """一般类型"""
    type: Literal[AdditionalType.common]
    common: AdditionalCommonItem


class ModuleDynamicAdditionalMatch(BaseModuleDynamicAdditional):
    """比赛"""
    type: Literal[AdditionalType.match]
    match: AdditionalMatchItem


class ModuleDynamicAdditionalUpRcmd(BaseModuleDynamicAdditional):
    """UP主推荐"""
    type: Literal[AdditionalType.up_rcmd]
    up_rcmd: AdditionalUpRcmdItem


class ModuleDynamicAdditionalUgc(BaseModuleDynamicAdditional):
    """视频跳转"""
    type: Literal[AdditionalType.ugc]
    ugc: AdditionalUgcItem


class ModuleDynamicAdditionalReserve(BaseModuleDynamicAdditional):
    """直播预约"""
    type: Literal[AdditionalType.reserve]
    reserve: AdditionalReserveItem


class ModuleDynamicUpowerLottery(BaseModuleDynamicAdditional):
    """动态充电互动抽奖"""
    type: Literal[AdditionalType.upower_lottery]
    upower_lottery: AdditionalUpowerLotteryItem


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
        | ModuleDynamicUpowerLottery
        | BaseModuleDynamicAdditional
)


# ------------------------------------------------------------------ #
# 动态主体内容模型, DynItem.modules.module_dynamic -> 动态接口
# data.items[n].modules.module_dynamic / data.item.modules.module_dynamic 对象
# desc 对象部分, 动态文字内容信息
# ------------------------------------------------------------------ #


class _ModuleDynamicDesc(BaseBilibiliModel):
    """动态文字内容"""
    rich_text_nodes: list[RichTextNodes] = Field(default_factory=list)
    text: str = Field(default_factory=str)


# ------------------------------------------------------------------ #
# 动态主体内容模型, DynItem.modules.module_dynamic -> 动态接口
# data.items[n].modules.module_dynamic / data.item.modules.module_dynamic 对象
# major 对象部分, 动态主体对象信息
# ------------------------------------------------------------------ #


class MajorNoneItem(BaseBilibiliModel):
    """动态失效/转发动态"""
    tips: str = Field(default='动态已失效或已被删除')


class MajorOpusItem(BaseBilibiliModel):
    """图文动态"""

    class _Pic(BaseBilibiliModel):
        height: int
        width: int
        size: str
        url: str
        live_url: str | None = Field(default=None)

    fold_action: list[str]
    jump_url: str
    pics: list[_Pic]
    summary: _ModuleDynamicDesc
    title: str | None = Field(default=None)


class MajorArchiveItem(BaseBilibiliModel):
    """视频信息"""
    aid: str
    # badge: Any  # 角标信息, 忽略
    bvid: str
    cover: str
    desc: str
    disable_preview: int = Field(default=0)
    duration_text: str
    jump_url: str
    # stat: Any  # 统计信息, 忽略
    title: str
    type: int = Field(default=1)


class MajorPgcItem(BaseBilibiliModel):
    """剧集信息"""
    # badge: Any  # 角标信息, 忽略
    cover: str
    epid: str
    jump_url: str
    season_id: str
    # stat: Any  # 统计信息, 忽略
    sub_type: int  # 剧集类型, 1: 番剧, 2: 电影, 3: 纪录片, 4: 国创, 5: 电视剧, 6: 漫画, 7: 综艺
    title: str
    type: int = Field(default=2)


class MajorCoursesItem(BaseBilibiliModel):
    """课程信息"""
    # badge: Any  # 角标信息, 忽略
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

    id: str  # 对应相簿id
    items: list[_Item] = Field(default_factory=list)


class MajorArticleItem(BaseBilibiliModel):
    """专栏类型"""
    covers: list[str] = Field(default_factory=list)
    desc: str
    id: str  # 文章CV号
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
    # badge: Any  # 角标信息, 忽略
    biz_type: int = Field(default=0)
    cover: str
    desc: str
    id: str
    jump_url: str
    label: str = Field(default_factory=str)
    sketch_id: str
    style: int = Field(default=1)
    title: str


class MajorLiveItem(BaseBilibiliModel):
    """直播间分享"""
    # badge: Any  # 角标信息, 忽略
    cover: str
    desc_first: str  # 直播主分区名称
    desc_second: str  # 观看人数
    id: str
    jump_url: str
    live_state: int  # 直播状态, 0: 直播结束, 1: 正在直播
    reserve_type: int = Field(default=0)
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
    reserve_type: int = Field(default=0)


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
    # badge: Any  # 角标信息, 忽略
    cover: str
    desc: str
    disable_preview: int = Field(default=0)
    duration_text: str
    jump_url: str
    # stat: Any  # 统计信息, 忽略
    title: str


class MajorUpowerCommonItem(BaseBilibiliModel):
    """充电信息"""
    # background: Any  # 背景, 忽略
    # button: Any  # 按钮, 忽略
    # icon: Any  # 图标, 忽略
    rid: str  # 关联 id
    title: str
    title_prefix: str
    type: int
    up_mid: int  # UP 主 mid (UID)
    upower_action_state: int
    upower_level: int
    jump_url: str


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
    type: Literal[MajorType.none]

    def get_major_text(self) -> str:
        return self.none.tips


class ModuleDynamicMajorOpus(BaseModuleDynamicMajor):
    """图文动态"""
    opus: MajorOpusItem
    type: Literal[MajorType.opus]

    def get_major_image_urls(self) -> list[str]:
        return [x.url for x in self.opus.pics]

    def get_major_text(self) -> str:
        if self.opus.title:
            return f'「{self.opus.title}」\n{self.opus.summary.text}'
        return self.opus.summary.text


class ModuleDynamicMajorArchive(BaseModuleDynamicMajor):
    """视频信息"""
    archive: MajorArchiveItem
    type: Literal[MajorType.archive]

    def get_major_image_urls(self) -> list[str]:
        return [self.archive.cover]

    def get_major_text(self) -> str:
        return (
            f'「{self.archive.title}」\n{self.archive.desc}\n'
            f'视频传送门: https://{self.archive.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorPgc(BaseModuleDynamicMajor):
    """剧集信息"""
    pgc: MajorPgcItem
    type: Literal[MajorType.pgc]

    def get_major_image_urls(self) -> list[str]:
        return [self.pgc.cover]

    def get_major_text(self) -> str:
        return (
            f'「{self.pgc.title}」\n'
            f'剧集传送门: {self.pgc.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorCourses(BaseModuleDynamicMajor):
    """课程信息"""
    courses: MajorCoursesItem
    type: Literal[MajorType.courses]

    def get_major_image_urls(self) -> list[str]:
        return [self.courses.cover]

    def get_major_text(self) -> str:
        return (
            f'「{self.courses.title}」\n{self.courses.desc}\n'
            f'课程传送门: https://{self.courses.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorDraw(BaseModuleDynamicMajor):
    """带图动态"""
    draw: MajorDrawItem
    type: Literal[MajorType.draw]

    def get_major_image_urls(self) -> list[str]:
        return [x.src for x in self.draw.items]


class ModuleDynamicMajorArticle(BaseModuleDynamicMajor):
    """专栏类型"""
    article: MajorArticleItem
    type: Literal[MajorType.article]

    def get_major_image_urls(self) -> list[str]:
        return self.article.covers

    def get_major_text(self) -> str:
        return (
            f'「{self.article.title}」\n{self.article.desc}\n'
            f'专栏传送门: https://{self.article.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorMusic(BaseModuleDynamicMajor):
    """音频信息"""
    music: MajorMusicItem
    type: Literal[MajorType.music]

    def get_major_image_urls(self) -> list[str]:
        return [self.music.cover]

    def get_major_text(self) -> str:
        return (
            f'「{self.music.title}」\n'
            f'音频传送门: https://{self.music.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorCommon(BaseModuleDynamicMajor):
    """一般类型"""
    common: MajorCommonItem
    type: Literal[MajorType.common]

    def get_major_image_urls(self) -> list[str]:
        return [self.common.cover]

    def get_major_text(self) -> str:
        return f'{self.common.title}\n{self.common.desc}'


class ModuleDynamicMajorLive(BaseModuleDynamicMajor):
    """直播间分享"""
    live: MajorLiveItem
    type: Literal[MajorType.live]

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
    type: Literal[MajorType.live_rcmd]

    def get_major_image_urls(self) -> list[str]:
        return [self.live_rcmd.content.live_play_info.cover]

    def get_major_text(self) -> str:
        return self.live_rcmd.content.live_play_info.title


class ModuleDynamicMajorMedialist(BaseModuleDynamicMajor):
    """合集信息"""
    medialist: MajorMedialistItem
    type: Literal[MajorType.medialist]


class ModuleDynamicMajorApplet(BaseModuleDynamicMajor):
    """小程序信息"""
    applet: MajorAppletItem
    type: Literal[MajorType.applet]


class ModuleDynamicMajorSubscription(BaseModuleDynamicMajor):
    """订阅信息"""
    subscription: MajorSubscriptionItem
    type: Literal[MajorType.subscription]


class ModuleDynamicMajorSubscriptionNew(BaseModuleDynamicMajor):
    """订阅信息"""
    subscription_new: MajorSubscriptionNewItem
    type: Literal[MajorType.subscription_new]


class ModuleDynamicMajorUgcSeason(BaseModuleDynamicMajor):
    """合集信息"""
    ugc_season: MajorUgcSeasonItem
    type: Literal[MajorType.ugc_season]

    def get_major_image_urls(self) -> list[str]:
        return [self.ugc_season.cover]

    def get_major_text(self) -> str:
        return (
            f'「{self.ugc_season.title}」\n{self.ugc_season.desc}\n'
            f'合集传送门: https://{self.ugc_season.jump_url.removeprefix("//")}'
        )


class ModuleDynamicMajorUpowerCommon(BaseModuleDynamicMajor):
    """充电相关"""
    upower_common: MajorUpowerCommonItem
    type: Literal[MajorType.upower_common]

    def get_major_text(self) -> str:
        return (
            f'{self.upower_common.title_prefix}【{self.upower_common.title}】\n'
            f'传送门: https://{self.upower_common.jump_url.removeprefix("//")}'
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
        | ModuleDynamicMajorUpowerCommon
        | BaseModuleDynamicMajor
)


# ------------------------------------------------------------------ #
# 动态内容数据模型, DynItem.modules -> 动态接口 data.items[n].modules / data.item.modules 对象
# ------------------------------------------------------------------ #


class _DynItemModuleDynamic(BaseBilibiliModel):
    """动态内容信息"""
    additional: ModuleDynamicAdditional | None = Field(default=None)  # 相关内容卡片信息, 可能为 null
    desc: _ModuleDynamicDesc | None = Field(default=None)  # 动态文字内容, 其他动态时为 null
    major: ModuleDynamicMajor | None = Field(default=None)  # 动态主体对象, 转发动态时为 null
    topic: _DynItemModuleTopicItem | None = Field(default=None)  # 话题信息, 可能为 null


class _DynItemModuleInteractionItemDesc(BaseBilibiliModel):
    rich_text_nodes: list[RichTextNodes] = Field(default_factory=list)
    text: str = Field(default_factory=str)


class _DynItemModuleInteractionItem(BaseBilibiliModel):
    desc: _DynItemModuleInteractionItemDesc = Field(default_factory=_DynItemModuleInteractionItemDesc)
    type: int = Field(default=-1)  # 类型, 0: 点赞信息, 1: 评论信息


class _DynItemModuleInteraction(BaseBilibiliModel):
    """热度评论"""
    items: list[_DynItemModuleInteractionItem] = Field(default_factory=list)


class _DynItemModuleFold(BaseBilibiliModel):
    """动态折叠信息"""
    ids: list[str] = Field(default_factory=list)  # 被折叠的动态id列表
    statement: str = Field(default_factory=str)  # 显示文案, 如: 展开x条相关动态
    type: int = Field(default=1)
    users: list[str] = Field(default_factory=list)


class _DynItemModuleDispute(BaseBilibiliModel):
    """争议小黄条"""
    desc: str = Field(default_factory=str)
    jump_url: str = Field(default_factory=str)
    title: str = Field(default_factory=str)  # 提醒文案, 如: 视频内含有危险行为，请勿模仿


class _DynItemModuleTag(BaseBilibiliModel):
    """置顶信息"""
    text: str = Field(default_factory=str)  # 置顶动态出现这个对象，否则没有


class DynItemModules(BaseBilibiliModel):
    """动态信息"""
    module_author: _DynItemModuleAuthor  # 动态用户信息, 必须解析
    module_dynamic: _DynItemModuleDynamic  # 动态主体内容, 必须解析
    module_more: _DynItemModuleMoreItem | None = Field(default=None)
    module_stat: _DynItemModuleStatItem | None = Field(default=None)
    module_interaction: _DynItemModuleInteraction | None = Field(default=None)
    module_fold: _DynItemModuleFold | None = Field(default=None)
    module_dispute: _DynItemModuleDispute | None = Field(default=None)
    module_tag: _DynItemModuleTag | None = Field(default=None)

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


# ------------------------------------------------------------------ #
# 动态内容数据模型, DynItem -> 动态接口 data.items[n] / data.item 对象
# ------------------------------------------------------------------ #


class _DynItemBasicLikeIcon(BaseBilibiliModel):
    id: int = Field(default=0)
    action_url: str = Field(default_factory=str)
    start_url: str = Field(default_factory=str)
    end_url: str = Field(default_factory=str)


class _DynItemBasic(BaseBilibiliModel):
    comment_id_str: str = Field(default_factory=str)
    comment_type: str = Field(default_factory=str)
    rid_str: str = Field(default_factory=str)
    like_icon: _DynItemBasicLikeIcon
    title: str = Field(default_factory=str)
    uid: int = Field(default=-1)


class DynCommonItem(BaseBilibiliModel):
    basic: _DynItemBasic
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
    orig: DynCommonItem | None
    type: Literal[DynamicType.forward]

    @property
    def dyn_text(self) -> str:
        """动态内容文本"""
        return (
            f'{self.modules.dyn_text}'
            f'{f"\n{'=' * 8}转发动态{'=' * 8}\n@{self.orig.dyn_text}" if self.orig and self.orig.dyn_text else ""}'
        )

    @property
    def dyn_image_urls(self) -> list[str]:
        """动态图片链接列表"""
        orig_image_urls = [] if self.orig is None else self.orig.dyn_image_urls
        return self.modules.dyn_image_urls + orig_image_urls


type DynItem = DynForwardItem | DynCommonItem


class DynData(BaseBilibiliModel):
    """动态列表数据"""
    has_more: bool
    items: list[DynItem]
    offset: str
    update_baseline: str
    update_num: int


class DynDataSingle(BaseBilibiliModel):
    """单条动态数据"""
    item: DynItem


# ------------------------------------------------------------------ #
# 动态图文详细信息数据模型, 动态新版 opus 功能模块组成 -> 动态接口 data.item 对象
# ------------------------------------------------------------------ #


type OpusModuleTypes = (
        DynOpusItemModuleTitle
        | DynOpusItemModuleAuthor
        | DynOpusItemModuleStat
        | DynOpusItemModuleContent
        | DynOpusItemModuleTopic
        | DynOpusItemModuleCollection
        | DynOpusItemModuleExtend
        | DynOpusItemModuleBottom
        | _BaseDynOpusItemModule
)


class _DynOpusItem(BaseBilibiliModel):
    basic: _DynItemBasic
    id_str: str
    modules: list[OpusModuleTypes]
    type: int
    fallback: int | None = Field(default=None)


class DynOpusDataSingle(BaseBilibiliModel):
    """单条动态图文详细信息"""
    item: _DynOpusItem


# ------------------------------------------------------------------ #
# 调用 API 返回的最终数据模型
# ------------------------------------------------------------------ #


class Dynamics(BaseBilibiliResponse):
    """获取动态列表结果"""
    data: DynData


class DynamicDetail(BaseBilibiliResponse):
    """获取单条动态详情结果"""
    data: DynDataSingle


class DynamicOpusDetail(BaseBilibiliResponse):
    """获取单条动态图文详细信息结果"""
    data: DynOpusDataSingle


__all__ = [
    'Dynamics',
    'DynamicType',
    'DynamicDetail',
    'DynamicOpusDetail',
    'DynItem',
]
