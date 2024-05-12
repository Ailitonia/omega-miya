"""
@Author         : Ailitonia
@Date           : 2022/04/13 22:02
@FileName       : guild.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp guild model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from pydantic import AnyHttpUrl
from nonebot.adapters.onebot.v11.message import Message

from ...model.base_model import BaseOnebotModel


T_GUILD_ID = str


class GuildServiceProfile(BaseOnebotModel):
    """Api /get_guild_service_profile 频道系统内BOT的资料 返回值

    - nickname: 昵称
    - tiny_id: 自身的ID
    - avatar_url: 头像链接
    """
    nickname: str
    tiny_id: T_GUILD_ID
    avatar_url: AnyHttpUrl


class GuildInfo(BaseOnebotModel):
    """Api /get_guild_list 频道列表
    正常情况下响应 GuildInfo 数组, 未加入任何频道响应 null

    - guild_id, 频道ID
    - guild_name, 频道名称
    - guild_display_id, 频道显示ID, 公测后可能作为搜索ID使用
    """
    guild_id: T_GUILD_ID
    guild_name: str
    guild_display_id: int


class GuildMeta(BaseOnebotModel):
    """Api /get_guild_meta_by_guest 访客获取的频道元数据

    - guild_id: 频道ID
    - guild_name: 频道名称
    - guild_profile: 频道简介
    - create_time: 创建时间
    - max_member_count: 频道人数上限
    - max_robot_count: 频道BOT数上限
    - max_admin_count: 频道管理员人数上限
    - member_count: 已加入人数
    - owner_id: 创建者ID
    """
    guild_id: str
    guild_name: str
    guild_profile: str
    create_time: int
    max_member_count: int
    max_robot_count: int
    max_admin_count: int
    member_count: int
    owner_id: str


class ChannelInfo(BaseOnebotModel):
    """Api /get_guild_channel_list 子频道信息

    - owner_guild_id: 所属频道ID
    - channel_id: 子频道ID
    - channel_type: 子频道类型
    - channel_name: 子频道名称
    - create_time: 创建时间
    - creator_tiny_id: 创建者ID
    - talk_permission: 发言权限类型
    - visible_type: 可视性类型
    - current_slow_mode: 当前启用的慢速模式Key
    - slow_modes: 频道内可用慢速模式类型列表

    已知子频道类型列表
        - 1: 文字频道
        - 2: 语音频道
        - 5: 直播频道
        - 7: 主题频道

    """

    class _SlowModeInfo(BaseOnebotModel):
        """慢速模式信息

        - slow_mode_key: 慢速模式Key
        - slow_mode_text: 慢速模式说明
        - speak_frequency: 周期内发言频率限制
        - slow_mode_circle: 单位周期时间, 单位秒
        """
        slow_mode_key: int
        slow_mode_text: str
        speak_frequency: int
        slow_mode_circle: int

    owner_guild_id: str
    channel_id: str
    channel_type: int
    channel_name: str
    create_time: int
    creator_tiny_id: str
    talk_permission: int
    visible_type: int
    current_slow_mode: int
    slow_modes: list[_SlowModeInfo]


class GuildMemberInfo(BaseOnebotModel):
    """Api /get_guild_member_list 频道成员信息

    - tiny_id: 成员ID
    - title: 成员头衔
    - nickname: 成员昵称
    - role_id: 所在权限组ID
    - role_name: 所在权限组名称
    """
    tiny_id: str
    title: str
    nickname: str
    role_id: str
    role_name: str


class GuildMemberList(BaseOnebotModel):
    """Api /get_guild_member_list 频道成员列表

    - members: 成员列表
    - finished: 是否最终页
    - next_token: 翻页Token
    """
    members: list[GuildMemberInfo]
    finished: bool
    next_token: Optional[str]


class GuildMemberProfile(BaseOnebotModel):
    """Api /get_guild_member_profile 单独获取频道成员信息

    - tiny_id: 用户ID
    - nickname: 用户昵称
    - avatar_url: 头像地址
    - join_time: 加入时间
    - roles: 加入的所有权限组
    """

    class _RoleInfo(BaseOnebotModel):
        """权限组信息

        - role_id: 权限组ID
        - role_name: 权限组名称
        """
        role_id: str
        role_name: str

    tiny_id: str
    nickname: str
    avatar_url: AnyHttpUrl
    join_time: int
    roles: list[_RoleInfo]


class GuildRoles(BaseOnebotModel):
    """Api /get_guild_roles 获取频道角色(身份组)列表

    - role_id: 频道角色(身份组)ID
    - role_name: 频道角色(身份组)名称
    - argb_color: 频道角色(身份组)标签颜色
    - independent: 是否独立角色(身份组)
    - member_count: 频道角色(身份组)用户数
    - max_count: 频道角色(身份组)最大用户数
    - owned:
    - disabled:
    """
    role_id: int
    role_name: str
    argb_color: int
    independent: bool
    member_count: int
    max_count: int
    owned: bool
    disabled: bool


class CreatedGuildRoles(BaseOnebotModel):
    """Api /create_guild_role 创建频道角色(身份组)

    - role_id: 频道角色(身份组)ID
    """
    role_id: int


class SentGuildMessage(BaseOnebotModel):
    """频道消息"""
    message_id: str


class ReceiveGuildMessage(BaseOnebotModel):
    """收到的频道消息

    - message_id: 消息id
    - real_id: 消息真实id
    - sender: 发送者
    - time: 发送时间
    - message: 消息内容
    """
    class _GuildSender(BaseOnebotModel):
        user_id: int
        nickname: str

    guild_id: int
    channel_id: int
    message_id: str
    message_source: str
    message_seq: int
    message: Message
    reactions: list[int]
    sender: _GuildSender
    time: int


class TopicChannelFeedInfo(BaseOnebotModel):
    """Api /get_topic_channel_feeds 话题频道帖子信息

    - id: 帖子ID
    - channel_id: 子频道ID
    - guild_id: 频道ID
    - create_time: 发帖时间
    - title: 帖子标题
    - sub_title: 帖子副标题
    - poster_info: 发帖人信息
    - resource: 媒体资源信息
    - resource.images: 帖子附带的图片列表
    - resource.videos: 帖子附带的视频列表
    - contents: 帖子内容
    """

    class _PosterInfo(BaseOnebotModel):
        """发帖人信息

        - tiny_id: 发帖人ID
        - nickname: 发帖人昵称
        - icon_url: 发帖人头像链接
        """
        tiny_id: str
        nickname: str
        icon_url: AnyHttpUrl

    class _FeedMedia(BaseOnebotModel):
        """帖子附带的媒体列表

        - images: 帖子附带的图片列表
        - videos: 帖子附带的视频列表
        """

        class _FeedMediaResource(BaseOnebotModel):
            """帖子附带的媒体列表内容

            - file_id: 媒体ID
            - pattern_id: 控件ID?(不确定)
            - url: 媒体链接
            - height: 媒体高度
            - width: 媒体宽度
            """
            file_id: str
            pattern_id: str
            url: AnyHttpUrl
            height: int
            width: int

        images: list[_FeedMediaResource]
        videos: list[_FeedMediaResource]

    class _FeedContent(BaseOnebotModel):
        """帖子内容

        - type: 内容类型
        - data: 内容数据

        内容类型列表
            - text: 文本
            - face: 表情
            - at: At
            - url_quote: 链接引用
            - channel_quote: 子频道引用
        """

        class _TextData(BaseOnebotModel):
            """文本

            - text: 文本内容
            """
            text: str

        class _FaceData(BaseOnebotModel):
            """表情

            - id: 表情ID
            """
            id: str

        class _AtData(BaseOnebotModel):
            """At

            - id: 目标ID
            - qq: 目标ID, 为确保和 array message 的一致性保留
            """
            id: str
            qq: str

        class _UrlQuoteData(BaseOnebotModel):
            """链接引用

            - display_text: 显示文本
            - url: 链接
            """
            display_text: str
            url: AnyHttpUrl

        class _ChannelQuoteData(BaseOnebotModel):
            """子频道引用

            - display_text: 显示文本
            - guild_id: 频道ID
            - channel_id: 子频道ID
            """
            display_text: str
            guild_id: str
            channel_id: str

        type: str
        data: Optional[_TextData | _FaceData | _AtData | _UrlQuoteData | _ChannelQuoteData]

    id: str
    channel_id: str
    guild_id: str
    create_time: int
    title: str
    sub_title: str
    poster_info: _PosterInfo
    resource: _FeedMedia
    contents: list[_FeedContent]


__all__ = [
    'GuildServiceProfile',
    'GuildInfo',
    'GuildMeta',
    'ChannelInfo',
    'GuildMemberList',
    'GuildMemberProfile',
    'GuildRoles',
    'CreatedGuildRoles',
    'SentGuildMessage',
    'ReceiveGuildMessage',
    'TopicChannelFeedInfo'
]
