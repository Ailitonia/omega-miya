"""
@Author         : Ailitonia
@Date           : 2022/04/14 20:14
@FileName       : _api.py
@Project        : nonebot2_miya 
@Description    : OneBot Api 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import Literal
from nonebot.adapters import Message

from .model import (GroupInfo, GroupHonor, SentMessage, ReceiveMessage, CustomNodeMessage,
                    LoginInfo, FriendInfo, StrangerInfo, GroupUser,
                    ImageFile, RecordFile, CanSendImage, CanSendRecord, Cookies, CSRF, Credentials, Status, VersionInfo)


class BaseOneBotApi(abc.ABC):
    """OneBot Api 基类"""

    @abc.abstractmethod
    async def send_private_msg(
            self,
            user_id: int | str,
            message: str | Message,
            auto_escape: bool = False
    ) -> SentMessage:
        """发送私聊消息

        :param user_id: 对方 QQ 号
        :param message: 要发送的内容
        :param auto_escape: 消息内容是否作为纯文本发送（即不解析 CQ 码），只在 message 字段是字符串时有效
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def send_group_msg(
            self,
            group_id: int | str,
            message: str | Message,
            auto_escape: bool = False
    ) -> SentMessage:
        """发送群消息

        :param group_id: 群号
        :param message: 要发送的内容
        :param auto_escape: 消息内容是否作为纯文本发送（即不解析 CQ 码），只在 message 字段是字符串时有效
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def send_msg(
            self,
            message_type: Literal['private', 'group'] | None = None,
            user_id: int | str | None = None,
            group_id: int | str | None = None,
            message: str | Message | None = None,
            auto_escape: bool = False
    ) -> SentMessage:
        """发送消息

        :param message_type: 消息类型，支持 private、group，分别对应私聊、群组，如不传入，则根据传入的 *_id 参数判断
        :param user_id: 对方 QQ 号（消息类型为 private 时需要）
        :param group_id: 群号（消息类型为 group 时需要）
        :param message: 要发送的内容
        :param auto_escape: 消息内容是否作为纯文本发送（即不解析 CQ 码），只在 message 字段是字符串时有效
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_msg(self, message_id: int) -> None:
        """撤回消息

        :param message_id: 消息 ID
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_msg(self, message_id: int) -> ReceiveMessage:
        """获取消息

        :param message_id: 消息 ID
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_forward_msg(self, id_: str) -> CustomNodeMessage:
        """获取合并转发消息

        :param id_: 合并转发 ID
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def send_like(self, user_id: int | str, times: int | str) -> None:
        """发送好友赞

        :param user_id: 对方 QQ 号
        :param times: 赞的次数，每个好友每天最多 10 次
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_kick(
            self,
            group_id: int | str,
            user_id: int | str,
            reject_add_request: bool = False
    ) -> None:
        """群组踢人

        :param group_id: 群号
        :param user_id: 要踢的 QQ 号
        :param reject_add_request: 拒绝此人的加群请求
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_ban(
            self,
            group_id: int | str,
            user_id: int | str,
            duration: int | str = 1800
    ) -> None:
        """群组单人禁言

        :param group_id: 群号
        :param user_id: 要禁言的 QQ 号
        :param duration: 禁言时长，单位秒，0 表示取消禁言
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_anonymous_ban(
            self,
            group_id: int | str,
            anonymous: dict | None = None,
            anonymous_flag: str | None = None,
            duration: int | str = 1800
    ) -> None:
        """群组匿名用户禁言

        :param group_id: 群号
        :param anonymous: 可选，要禁言的匿名用户对象（群消息上报的 anonymous 字段）
        :param anonymous_flag: 可选，要禁言的匿名用户的 flag（需从群消息上报的数据中获得）
        :param duration: 禁言时长，单位秒，无法取消匿名用户禁言
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_whole_ban(self, group_id: int | str, enable: bool = True) -> None:
        """群组全员禁言

        :param group_id: 群号
        :param enable: 是否禁言
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_admin(self, group_id: int | str, user_id: int | str, enable: bool = True) -> None:
        """群组设置管理员

        :param group_id: 群号
        :param user_id: 要设置管理员的 QQ 号
        :param enable: true 为设置，false 为取消
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_anonymous(self, group_id: int | str, enable: bool = True) -> None:
        """群组匿名

        :param group_id: 群号
        :param enable: 是否允许匿名聊天
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_card(self, group_id: int | str, user_id: int | str, card: str = '') -> None:
        """设置群名片（群备注）

        :param group_id: 群号
        :param user_id: 要设置的 QQ 号
        :param card: 群名片内容，不填或空字符串表示删除群名片
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_name(self, group_id: int | str, group_name: str) -> None:
        """设置群名

        :param group_id: 群号
        :param group_name: 新群名
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_leave(self, group_id: int | str, is_dismiss: bool = False) -> None:
        """退出群组

        :param group_id: 群号
        :param is_dismiss: 是否解散，如果登录号是群主，则仅在此项为 true 时能够解散
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_special_title(
            self,
            group_id: int | str,
            user_id: int | str,
            special_title: str = '',
            duration: int | str = -1
    ) -> None:
        """设置群组专属头衔

        :param group_id: 群号
        :param user_id: 要设置的 QQ 号
        :param special_title: 专属头衔，不填或空字符串表示删除专属头衔
        :param duration: 专属头衔有效期，单位秒，-1 表示永久，不过此项似乎没有效果，可能是只有某些特殊的时间长度有效，有待测试
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_friend_add_request(self, flag: str, approve: bool = True, remark: str = '') -> None:
        """处理加好友请求

        :param flag: 加好友请求的 flag（需从上报的数据中获得）
        :param approve: 是否同意请求
        :param remark: 添加后的好友备注（仅在同意时有效）
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_group_add_request(
            self,
            flag: str,
            sub_type: Literal['add', 'invite'],
            approve: bool = True,
            reason: str = '') -> None:
        """处理加群请求／邀请

        :param flag: 加群请求的 flag（需从上报的数据中获得）
        :param sub_type: add 或 invite，请求类型（需要和上报消息中的 sub_type 字段相符）
        :param approve: 是否同意请求／邀请
        :param reason: 拒绝理由（仅在拒绝时有效）
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_login_info(self) -> LoginInfo:
        """获取登录号信息"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_stranger_info(self, user_id: int | str, no_cache: bool = False) -> StrangerInfo:
        """获取陌生人信息

        :param user_id: QQ 号
        :param no_cache: 是否不使用缓存（使用缓存可能更新不及时，但响应更快）
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_friend_list(self) -> list[FriendInfo]:
        """获取好友列表"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_group_info(self, group_id: int | str, no_cache: bool = False) -> GroupInfo:
        """获取群信息"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_group_list(self) -> list[GroupInfo]:
        """获取群列表"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_group_member_info(self, group_id: int | str, user_id: int | str, no_cache: bool = False) -> GroupUser:
        """获取群成员信息

        :param group_id: 群号
        :param user_id: QQ 号
        :param no_cache: 是否不使用缓存（使用缓存可能更新不及时，但响应更快）
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_group_member_list(self, group_id: int | str) -> list[GroupUser]:
        """获取群成员列表

        :param group_id: 群号
        :return: 响应内容为 JSON 数组，每个元素的内容和上面的 get_group_member_info 接口相同，但对于同一个群组的同一个成员，
        获取列表时和获取单独的成员信息时，某些字段可能有所不同，例如 area、title 等字段在获取列表时无法获得，具体应以单独的成员信息为准。
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_group_honor_info(
            self,
            group_id: int | str,
            type_: Literal['talkative', 'performer', 'legend', 'strong_newbie', 'emotion', 'all']
    ) -> GroupHonor:
        """获取群荣誉信息

        :param group_id: 群号
        :param type_: 要获取的群荣誉类型，可传入 talkative performer legend strong_newbie emotion 以分别获取单个类型的群荣誉数据，或传入 all 获取所有数据
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_cookies(self, domain: str = '') -> Cookies:
        """获取 Cookies

        :param domain: 需要获取 cookies 的域名
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_csrf_token(self) -> CSRF:
        """获取 CSRF Token"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_credentials(self, domain: str = '') -> Credentials:
        """获取 QQ 相关接口凭证

        :param domain: 需要获取 cookies 的域名
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_record(
            self,
            file: str,
            out_format: Literal['mp3', 'amr', 'wma', 'm4a', 'spx', 'ogg', 'wav', 'flac']
    ) -> RecordFile:
        """获取语音(要使用此接口，通常需要安装 ffmpeg，请参考 OneBot 实现的相关说明)

        :param file: 收到的语音文件名（消息段的 file 参数），如 0B38145AA44505000B38145AA4450500.silk
        :param out_format: 要转换到的格式，目前支持 mp3、amr、wma、m4a、spx、ogg、wav、flac
        :return: file: 转换后的语音文件路径，如 /home/somebody/cqhttp/data/record/0B38145AA44505000B38145AA4450500.mp3
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_image(self, file: str) -> ImageFile:
        """获取图片

        :param file: 收到的图片文件名（消息段的 file 参数），如 6B4DE3DFD1BD271E3297859D41C530F5.jpg
        :return: file: 下载后的图片文件路径，如 /home/somebody/cqhttp/data/image/6B4DE3DFD1BD271E3297859D41C530F5.jpg
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def can_send_image(self) -> CanSendImage:
        """检查是否可以发送图片"""
        raise NotImplementedError

    @abc.abstractmethod
    async def can_send_record(self) -> CanSendRecord:
        """检查是否可以发送语音"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_status(self) -> Status:
        """获取运行状态"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_version_info(self) -> VersionInfo:
        """获取运行状态"""
        raise NotImplementedError

    @abc.abstractmethod
    async def set_restart(self, delay: int = 0) -> None:
        """重启 OneBot 实现(由于重启 OneBot 实现同时需要重启 API 服务，这意味着当前的 API 请求会被中断，因此需要异步地重启，接口返回的 status 是 async)

        :param delay: 要延迟的毫秒数，如果默认情况下无法重启，可以尝试设置延迟为 2000 左右
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def clean_cache(self) -> None:
        """清理缓存"""
        raise NotImplementedError


__all__ = [
    'BaseOneBotApi'
]
