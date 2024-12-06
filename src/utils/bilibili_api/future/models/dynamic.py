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


@unique
class DynamicType(StrEnum):
    """动态类型"""
    none = "DYNAMIC_TYPE_NONE"  # 无效动态
    forward = "DYNAMIC_TYPE_FORWARD"  # 动态转发
    av = "DYNAMIC_TYPE_AV"  # 投稿视频
    pgc = "DYNAMIC_TYPE_PGC"  # 剧集（番剧、电影、纪录片）
    courses = "DYNAMIC_TYPE_COURSES"
    word = "DYNAMIC_TYPE_WORD"  # 纯文字动态
    draw = "DYNAMIC_TYPE_DRAW"  # 带图动态
    article = "DYNAMIC_TYPE_ARTICLE"  # 投稿专栏
    music = "DYNAMIC_TYPE_MUSIC"  # 音乐
    common_square = "DYNAMIC_TYPE_COMMON_SQUARE"  # 装扮/剧集点评/普通分享
    common_vertical = "DYNAMIC_TYPE_COMMON_VERTICAL"
    live = "DYNAMIC_TYPE_LIVE"  # 直播间分享
    medialist = "DYNAMIC_TYPE_MEDIALIST"  # 收藏夹
    courses_season = "DYNAMIC_TYPE_COURSES_SEASON"  # 课程
    courses_batch = "DYNAMIC_TYPE_COURSES_BATCH"
    ad = "DYNAMIC_TYPE_AD"
    applet = "DYNAMIC_TYPE_APPLET"
    subscription = "DYNAMIC_TYPE_SUBSCRIPTION"
    live_rcmd = "DYNAMIC_TYPE_LIVE_RCMD"  # 直播开播
    banner = "DYNAMIC_TYPE_BANNER"
    ugc_season = "DYNAMIC_TYPE_UGC_SEASON"  # 合集更新
    subscription_new = "DYNAMIC_TYPE_SUBSCRIPTION_NEW"


@unique
class RichTextNodeType(StrEnum):
    """富文本节点类型"""
    none = "RICH_TEXT_NODE_TYPE_NONE"
    text = "RICH_TEXT_NODE_TYPE_TEXT"  # 文字节点
    at = "RICH_TEXT_NODE_TYPE_AT"  # @用户
    lottery = "RICH_TEXT_NODE_TYPE_LOTTERY"  # 互动抽奖
    vote = "RICH_TEXT_NODE_TYPE_VOTE"  # 投票
    topic = "RICH_TEXT_NODE_TYPE_TOPIC"  # 话题
    goods = "RICH_TEXT_NODE_TYPE_GOODS"  # 商品链接
    bv = "RICH_TEXT_NODE_TYPE_BV"  # 视频链接
    av = "RICH_TEXT_NODE_TYPE_AV"
    emoji = "RICH_TEXT_NODE_TYPE_EMOJI"  # 表情
    user = "RICH_TEXT_NODE_TYPE_USER"
    cv = "RICH_TEXT_NODE_TYPE_CV"
    vc = "RICH_TEXT_NODE_TYPE_VC"
    web = "RICH_TEXT_NODE_TYPE_WEB"  # 网页链接
    taobao = "RICH_TEXT_NODE_TYPE_TAOBAO"
    mail = "RICH_TEXT_NODE_TYPE_MAIL"  # 邮箱地址
    ogv_season = "RICH_TEXT_NODE_TYPE_OGV_SEASON"  # 剧集信息
    ogv_ep = "RICH_TEXT_NODE_TYPE_OGV_EP"
    search_word = "RICH_TEXT_NODE_TYPE_SEARCH_WORD"


@unique
class AuthorType(StrEnum):
    """作者类型"""
    none = "AUTHOR_TYPE_NONE"
    normal = "AUTHOR_TYPE_NORMAL"  # 普通更新
    pgc = "AUTHOR_TYPE_PGC"  # 剧集更新
    ugc_season = "AUTHOR_TYPE_UGC_SEASON"  # 合集更新


@unique
class EmojiType(StrEnum):
    """表情类型"""
    none = "EMOJI_TYPE_NONE"
    old = "EMOJI_TYPE_OLD"
    new = "EMOJI_TYPE_NEW"
    vip = "EMOJI_TYPE_VIP"


@unique
class AdditionalType(StrEnum):
    """相关内容卡片类型"""
    none = "ADDITIONAL_TYPE_NONE"
    pgc = "ADDITIONAL_TYPE_PGC"
    goods = "ADDITIONAL_TYPE_GOODS"  # 商品信息
    vote = "ADDITIONAL_TYPE_VOTE"  # 投票
    common = "ADDITIONAL_TYPE_COMMON"  # 一般类型
    match = "ADDITIONAL_TYPE_MATCH"
    up_rcmd = "ADDITIONAL_TYPE_UP_RCMD"
    ugc = "ADDITIONAL_TYPE_UGC"  # 视频跳转
    reserve = "ADDITIONAL_TYPE_RESERVE"


@unique
class AdditionalButtonType(StrEnum):
    """相关内容卡片类型 (BUTTON)"""
    none = "ADDITIONAL_BUTTON_TYPE_NONE"
    jump = "ADDITIONAL_BUTTON_TYPE_JUMP"
    button = "ADDITIONAL_BUTTON_TYPE_BUTTON"


@unique
class AdditionalButtonStatus(StrEnum):
    """相关内容卡片类型 (BUTTON_STATUS)"""
    none = "ADDITIONAL_BUTTON_STATUS_NONE"
    uncheck = "ADDITIONAL_BUTTON_STATUS_UNCHECK"
    check = "ADDITIONAL_BUTTON_STATUS_CHECK"


@unique
class AddButtonClickType(StrEnum):
    """相关内容卡片类型 (ADD_BUTTON_CLICK)"""
    none = "ADD_BUTTON_CLICK_TYPE_NONE"
    reserve = "ADD_BUTTON_CLICK_TYPE_RESERVE"


@unique
class DisableState(StrEnum):
    """相关内容卡片类型 (DISABLE_STATE)"""
    highlight = "DISABLE_STATE_HIGHLIGHT"
    gray = "DISABLE_STATE_GRAY"


@unique
class AddButtonBgStyle(StrEnum):
    """相关内容卡片类型 (ADD_BUTTON_BG_STYLE)"""
    fill = "ADD_BUTTON_BG_STYLE_FILL"
    stroke = "ADD_BUTTON_BG_STYLE_STROKE"
    gray = "ADD_BUTTON_BG_STYLE_GRAY"


@unique
class HighlightTextStyleType(StrEnum):
    """相关内容卡片类型 (HIGHLIGHT_TEXT_STYLE)"""
    none = "HIGHLIGHT_TEXT_STYLE_TYPE_NONE"
    active = "HIGHLIGHT_TEXT_STYLE_TYPE_ACTIVE"


@unique
class MajorType(StrEnum):
    """动态主体类型"""
    none = "MAJOR_TYPE_NONE"  # 动态失效/转发动态
    opus = "MAJOR_TYPE_OPUS"  # 图文动态
    archive = "MAJOR_TYPE_ARCHIVE"  # 视频
    pgc = "MAJOR_TYPE_PGC"  # 剧集更新
    courses = "MAJOR_TYPE_COURSES"
    draw = "MAJOR_TYPE_DRAW"  # 带图动态
    article = "MAJOR_TYPE_ARTICLE"
    music = "MAJOR_TYPE_MUSIC"  # 音频更新
    common = "MAJOR_TYPE_COMMON"  # 一般类型
    live = "MAJOR_TYPE_LIVE"  # 直播间分享
    medialist = "MAJOR_TYPE_MEDIALIST"
    applet = "MAJOR_TYPE_APPLET"
    subscription = "MAJOR_TYPE_SUBSCRIPTION"
    live_rcmd = "MAJOR_TYPE_LIVE_RCMD"  # 直播状态
    ugc_season = "MAJOR_TYPE_UGC_SEASON"  # 合计更新
    subscription_new = "MAJOR_TYPE_SUBSCRIPTION_NEW"


@unique
class MediaType(StrEnum):
    """动态主体类型 (MEDIA)"""
    none = "MEDIA_TYPE_NONE"
    ugc = "MEDIA_TYPE_UGC"
    pgc = "MEDIA_TYPE_PGC"
    live = "MEDIA_TYPE_LIVE"


@unique
class PgcSubType(StrEnum):
    """动态主体类型 (PGC_SUB)"""
    none = "PGC_SUB_TYPE_NONE"
    bangumi = "PGC_SUB_TYPE_BANGUMI"
    movie = "PGC_SUB_TYPE_MOVIE"
    documentary = "PGC_SUB_TYPE_DOCUMENTARY"
    domestic = "PGC_SUB_TYPE_DOMESTIC"
    tv = "PGC_SUB_TYPE_TV"


@unique
class DrawTagType(StrEnum):
    """动态主体类型 (DRAW_TAG)"""
    none = "DRAW_TAG_TYPE_NONE"
    common = "DRAW_TAG_TYPE_COMMON"
    goods = "DRAW_TAG_TYPE_GOODS"
    user = "DRAW_TAG_TYPE_USER"
    topic = "DRAW_TAG_TYPE_TOPIC"
    lbs = "DRAW_TAG_TYPE_LBS"


@unique
class MajorCommonStyleType(StrEnum):
    """动态主体类型 (MAJOR_COMMON_STYLE)"""
    none = "MAJOR_COMMON_STYLE_TYPE_NONE"
    square = "MAJOR_COMMON_STYLE_TYPE_SQUARE"
    vertical = "MAJOR_COMMON_STYLE_TYPE_VERTICAL"


@unique
class ReserveType(StrEnum):
    """动态主体类型 (RESERVE)"""
    none = "RESERVE_TYPE_NONE"
    recall = "RESERVE_TYPE_RECALL"


@unique
class LiveStateType(StrEnum):
    """动态主体类型 (LIVE_STATE)"""
    none = "LIVE_STATE_TYPE_NONE"
    live = "LIVE_STATE_TYPE_LIVE"
    rotation = "LIVE_STATE_TYPE_ROTATION"


@unique
class SubscriptionNewStyleType(StrEnum):
    """动态主体类型 (SUBSCRIPTION_NEW_STYLE)"""
    none = "SUBSCRIPTION_NEW_STYLE_TYPE_NONE"
    draw = "SUBSCRIPTION_NEW_STYLE_TYPE_DRAW"
    live = "SUBSCRIPTION_NEW_STYLE_TYPE_LIVE"


@unique
class ThreePointType(StrEnum):
    """动态主体类型 (THREE_POINT)"""
    delete = "THREE_POINT_DELETE"  # 删除
    report = "THREE_POINT_REPORT"  # 举报
    following = "THREE_POINT_FOLLOWING"  # 关注/取消关注
    top = "THREE_POINT_TOP"  # 置顶/取消置顶
    unfav = "THREE_POINT_UNFAV"
    unsubs = "THREE_POINT_UNSUBS"
    topic_report = "THREE_POINT_TOPIC_REPORT"
    topic_irrelevant = "THREE_POINT_TOPIC_IRRELEVANT"
    rcmd_resource = "THREE_POINT_RCMD_RESOURCE"
    rcmd_feedback = "THREE_POINT_RCMD_FEEDBACK"


@unique
class FoldType(StrEnum):
    """动态主体类型 (FOLD)"""
    none = "FOLD_TYPE_NONE"
    publish = "FOLD_TYPE_PUBLISH"
    frequent = "FOLD_TYPE_FREQUENT"
    unite = "FOLD_TYPE_UNITE"
    limit = "FOLD_TYPE_LIMIT"


@unique
class DynStatusType(StrEnum):
    """动态主体类型 (DYN_STATUS)"""
    none = "DYN_STATUS_TYPE_NONE"
    normal = "DYN_STATUS_TYPE_NORMAL"
    auditing = "DYN_STATUS_TYPE_AUDITING"
    self_visible = "DYN_STATUS_TYPE_SELF_VISIBLE"
    deleted = "DYN_STATUS_TYPE_DELETED"


@unique
class SceneType(StrEnum):
    """动态主体类型 (SCENE)"""
    detail = "SCENE_DETAIL"
    hot = "SCENE_HOT"
    general = "SCENE_GENERAL"
    space = "SCENE_SPACE"
    topic = "SCENE_TOPIC"
