"""
@Author         : Ailitonia
@Date           : 2022/04/13 21:55
@FileName       : api.py
@Project        : nonebot2_miya
@Description    : go-cqhttp Api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import ujson as json
from typing import Literal
from pydantic import parse_obj_as
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

from omega_miya.database import (InternalOneBotV11Bot, InternalBotGroup, InternalBotUser,
                                 InternalBotGuild, DatabaseUpgradeError)
from omega_miya.utils.process_utils import semaphore_gather

from .._api import BaseOnebotApi
from ..exception import ApiNotSupport
from .model import (SentMessage, ReceiveMessage, ReceiveForwardMessage, StrangerInfo, LoginInfo, FriendInfo,
                    GroupInfo, GroupHonor, GroupUser, GroupSystemMessage, GroupFileSystemInfo, GroupRootFiles,
                    GroupFolderFiles, GroupFileResource, GroupAtAllRemain, GroupEssenceMessage, GroupMessageHistory,
                    Anonymous, QidianAccountUser, Cookies, CSRF, Credentials, VersionInfo, Status, OnlineClients,
                    UrlSafely, ImageFile, OcrImageResult, RecordFile, CanSendImage, CanSendRecord, DownloadedFile,
                    GuildServiceProfile, GuildInfo, GuildMeta, ChannelInfo, GuildMemberList, GuildMemberProfile,
                    SentGuildMessage, TopicChannelFeedInfo)


class GoCqhttpBot(BaseOnebotApi):
    """go-cqhttp api

    适配版本: go-cqhttp v1.0.0-rc1
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.self_id = bot.self_id if isinstance(bot.self_id, str) else str(bot.self_id)
        self._internal_bot = InternalOneBotV11Bot(bot_self_id=self.self_id, bot_type=self.bot.type)

    async def connecting_db_upgrade(self) -> None:
        """在 Bot 连接时更新数据库中 Bot 信息"""
        bot_version_info = await self.get_version_info()
        info = '||'.join([f'{k}:{v}' for (k, v) in bot_version_info.dict().items()])
        db_upgrade_result = await self._internal_bot.add_upgrade(bot_status=1, bot_info=info)
        if db_upgrade_result.error:
            raise DatabaseUpgradeError(f'Upgrade bot info error: {db_upgrade_result.info}')

        bot_login_info = await self.get_login_info()
        # 更新群组相关信息
        groups_result = await self.get_group_list()
        group_upgrade_tasks = [
            InternalBotGroup(bot_id=self.self_id, parent_id=self.self_id, entity_id=x.group_id).add_only(
                parent_entity_name=bot_login_info.nickname,
                entity_name=x.group_name,
                entity_info=x.group_memo,
                related_entity_name=x.group_name
            )
            for x in groups_result]
        # 更新用户相关信息
        users_result = await self.get_friend_list()
        user_upgrade_tasks = [
            InternalBotUser(bot_id=self.self_id, parent_id=self.self_id, entity_id=x.user_id).add_only(
                parent_entity_name=bot_login_info.nickname,
                entity_name=x.nickname,
                related_entity_name=x.remark
            )
            for x in users_result]
        # 更新频道相关信息
        guild_profile = await self.get_guild_service_profile()
        guild_data = await self.get_guild_list()
        guild_upgrade_tasks = [
            InternalBotGuild(bot_id=self.self_id, parent_id=guild_profile.tiny_id, entity_id=x.guild_id).add_only(
                parent_entity_name=guild_profile.nickname,
                entity_name=x.guild_name,
                related_entity_name=x.guild_name
            )
            for x in guild_data]

        upgrade_result = await semaphore_gather(
            tasks=[*group_upgrade_tasks, *user_upgrade_tasks, *guild_upgrade_tasks], semaphore_num=1)
        for result in upgrade_result:
            if isinstance(result, BaseException):
                raise DatabaseUpgradeError(f'Upgrade bot entity error: {repr(result)}')
            elif result.error:
                raise DatabaseUpgradeError(f'Upgrade bot entity error: {result.info}')

    async def disconnecting_db_upgrade(self) -> None:
        """在 Bot 断开连接时更新数据库中 Bot 信息"""
        db_upgrade_result = await self._internal_bot.add_upgrade(bot_status=0)
        if db_upgrade_result.error:
            raise DatabaseUpgradeError(f'Upgrade bot info error: {db_upgrade_result.info}')

    async def send_like(self, user_id: int | str, times: int | str) -> None:
        raise ApiNotSupport('go-cqhttp not support "send_like" api')

    async def send_private_msg(
            self,
            user_id: int | str,
            message: str | Message,
            auto_escape: bool = False
    ) -> SentMessage:
        message_result = await self.bot.send_private_msg(user_id=user_id, message=message, auto_escape=auto_escape)
        return SentMessage.parse_obj(message_result)

    async def send_stranger_msg(
            self,
            user_id: int | str,
            group_id: int | str,
            message: str | Message,
            auto_escape: bool = False
    ) -> SentMessage:
        """通过群组向发起临时会话

        :param user_id: 对方 QQ 号
        :param group_id: 主动发起临时会话群号(机器人本身必须是管理员/群主)
        :param message: 要发送的内容
        :param auto_escape: 消息内容是否作为纯文本发送 ( 即不解析 CQ 码 ) , 只在 message 字段是字符串时有效
        """
        message_result = await self.bot.call_api(
            'send_private_msg', user_id=user_id, group_id=group_id, message=message, auto_escape=auto_escape)
        return SentMessage.parse_obj(message_result)

    async def send_group_msg(
            self,
            group_id: int | str,
            message: str | Message,
            auto_escape: bool = False
    ) -> SentMessage:
        message_result = await self.bot.send_group_msg(group_id=group_id, message=message, auto_escape=auto_escape)
        return SentMessage.parse_obj(message_result)

    async def send_group_forward_msg(
            self,
            group_id: int | str,
            messages: list[str | Message | MessageSegment | dict]
    ) -> SentMessage:
        """发送合并转发 ( 群 )

        :param group_id: 群号
        :param messages: 自定义转发消息, 具体看 cq-http 文档的 CQcode
        """
        message_result = await self.bot.send_group_forward_msg(group_id=group_id, messages=messages)
        return SentMessage.parse_obj(message_result)

    async def send_msg(
            self,
            message_type: Literal['private', 'group'] | None = None,
            user_id: int | str | None = None,
            group_id: int | str | None = None,
            message: str | Message | None = None,
            auto_escape: bool = False
    ) -> SentMessage:
        if user_id and group_id:
            raise ValueError('"user_id" and "group_id" only need one')
        elif user_id and message_type != 'group':
            message_result = await self.bot.send_msg(
                message_type='private', user_id=user_id, message=message, auto_escape=auto_escape)
        elif group_id and message_type != 'private':
            message_result = await self.bot.send_msg(
                message_type='group', group_id=group_id, message=message, auto_escape=auto_escape)
        else:
            raise ValueError('illegal parameter combination ')
        return SentMessage.parse_obj(message_result)

    async def delete_msg(self, message_id: int) -> None:
        return await self.bot.delete_msg(message_id=message_id)

    async def get_msg(self, message_id: int) -> ReceiveMessage:
        message_result = await self.bot.get_msg(message_id=message_id)
        return ReceiveMessage.parse_obj(message_result)

    async def get_forward_msg(self, message_id: str) -> ReceiveForwardMessage:
        """获取合并转发消息(字段 message_id 对应合并转发中的 id 字段)

        :param message_id: 消息id
        """
        message_result = await self.bot.call_api('get_forward_msg', message_id=message_id)
        return ReceiveForwardMessage.parse_obj(message_result)

    async def get_image(self, file: str) -> ImageFile:
        """获取图片信息

        :param file: 图片缓存文件名
        """
        file_result = await self.bot.get_image(file=file)
        return ImageFile.parse_obj(file_result)

    async def set_group_kick(
            self,
            group_id: int | str,
            user_id: int | str,
            reject_add_request: bool = False
    ) -> None:
        return await self.bot.set_group_kick(group_id=group_id, user_id=user_id, reject_add_request=reject_add_request)

    async def set_group_ban(
            self,
            group_id: int | str,
            user_id: int | str,
            duration: int | str = 1800
    ) -> None:
        return await self.bot.set_group_ban(group_id=group_id, user_id=user_id, duration=duration)

    async def set_group_anonymous_ban(
            self,
            group_id: int | str,
            anonymous: Anonymous | dict | str | None = None,
            anonymous_flag: str | None = None,
            duration: int | str = 1800
    ) -> None:
        if isinstance(anonymous, Anonymous):
            _anonymous = anonymous.json()
        elif isinstance(anonymous, dict):
            _anonymous = json.dumps(anonymous)
        else:
            _anonymous = anonymous
        return await self.bot.set_group_anonymous_ban(
            group_id=group_id, anonymous=_anonymous, anonymous_flag=anonymous_flag, duration=duration)

    async def set_group_whole_ban(self, group_id: int | str, enable: bool = True) -> None:
        return await self.bot.set_group_whole_ban(group_id=group_id, enable=enable)

    async def set_group_admin(self, group_id: int | str, user_id: int | str, enable: bool = True) -> None:
        return await self.bot.set_group_admin(group_id=group_id, user_id=user_id, enable=enable)

    async def set_group_anonymous(self, group_id: int | str, enable: bool = True) -> None:
        """群组匿名(该 API 暂未被 go-cqhttp 支持, 您可以提交 pr 以使该 API 被支持 提交 pr)"""
        raise ApiNotSupport('go-cqhttp not support "set_group_anonymous" api')

    async def set_group_card(self, group_id: int | str, user_id: int | str, card: str = '') -> None:
        return await self.bot.set_group_card(group_id=group_id, user_id=user_id, card=card)

    async def set_group_name(self, group_id: int | str, group_name: str) -> None:
        return await self.bot.set_group_name(group_id=group_id, group_name=group_name)

    async def set_group_leave(self, group_id: int | str, is_dismiss: bool = False) -> None:
        return await self.bot.set_group_leave(group_id=group_id, is_dismiss=is_dismiss)

    async def set_group_special_title(
            self,
            group_id: int | str,
            user_id: int | str,
            special_title: str = '',
            duration: int | str = -1
    ) -> None:
        return await self.bot.set_group_special_title(
            group_id=group_id, user_id=user_id, special_title=special_title, duration=duration)

    async def set_friend_add_request(self, flag: str, approve: bool = True, remark: str = '') -> None:
        return await self.bot.set_friend_add_request(flag=flag, approve=approve, remark=remark)

    async def set_group_add_request(
            self,
            flag: str,
            sub_type: Literal['add', 'invite'],
            approve: bool = True,
            reason: str = '') -> None:
        return await self.bot.set_group_add_request(flag=flag, sub_type=sub_type, approve=approve, reason=reason)

    async def get_login_info(self) -> LoginInfo:
        login_info = await self.bot.get_login_info()
        return LoginInfo.parse_obj(login_info)

    async def qidian_get_account_info(self) -> QidianAccountUser:
        """获取企点账号信息(该API只有企点协议可用)"""
        login_info = await self.bot.call_api('qidian_get_account_info')
        return QidianAccountUser.parse_obj(login_info)

    async def get_stranger_info(self, user_id: int | str, no_cache: bool = False) -> StrangerInfo:
        stranger_info = await self.bot.get_stranger_info(user_id=user_id, no_cache=no_cache)
        return StrangerInfo.parse_obj(stranger_info)

    async def get_friend_list(self) -> list[FriendInfo]:
        friend_list = await self.bot.get_friend_list()
        return parse_obj_as(list[FriendInfo], friend_list)

    async def is_friend(self, user_id: int | str) -> bool:
        """检查用户是否是好友

        :param user_id: 用户 QQ 号
        """
        friend_list = await self.get_friend_list()
        if str(user_id) in (x.user_id for x in friend_list):
            return True
        else:
            return False

    async def delete_friend(self, friend_id: int | str) -> None:
        """删除好友

        :param friend_id: 好友 QQ 号
        """
        return await self.bot.call_api('delete_friend', friend_id=friend_id)

    async def get_group_info(self, group_id: int | str, *, no_cache: bool = False) -> GroupInfo:
        """获取群信息

        如果机器人尚未加入群, group_create_time, group_level, max_member_count 和 member_count 将会为0
        (提示: 这里提供了一个API用于获取群图片, group_id 为群号 https://p.qlogo.cn/gh/{group_id}/{group_id}/100)
        """
        group_info = await self.bot.get_group_info(group_id=group_id, no_cache=no_cache)
        return GroupInfo.parse_obj(group_info)

    async def get_group_list(self) -> list[GroupInfo]:
        groups_data = await self.bot.get_group_list()
        return parse_obj_as(list[GroupInfo], groups_data)

    async def get_group_member_info(self, group_id: int | str, user_id: int | str, no_cache: bool = False) -> GroupUser:
        user_info = await self.bot.get_group_member_info(group_id=group_id, user_id=user_id, no_cache=no_cache)
        return GroupUser.parse_obj(user_info)

    async def get_group_member_list(self, group_id: int | str) -> list[GroupUser]:
        users_data = await self.bot.get_group_member_list(group_id=group_id)
        return parse_obj_as(list[GroupUser], users_data)

    async def get_group_honor_info(
            self,
            group_id: int | str,
            type_: Literal['talkative', 'performer', 'legend', 'strong_newbie', 'emotion', 'all']
    ) -> GroupHonor:
        honor_result = await self.bot.get_group_honor_info(group_id=group_id, type=type_)
        return GroupHonor.parse_obj(honor_result)

    async def get_cookies(self, domain: str = '') -> Cookies:
        """获取 Cookies(该 API 暂未被 go-cqhttp 支持, 您可以提交 pr 以使该 API 被支持 提交 pr)"""
        raise ApiNotSupport('go-cqhttp not support "get_cookies" api')

    async def get_csrf_token(self) -> CSRF:
        """获取 CSRF Token(该 API 暂未被 go-cqhttp 支持, 您可以提交 pr 以使该 API 被支持 提交 pr)"""
        raise ApiNotSupport('go-cqhttp not support "get_csrf_token" api')

    async def get_credentials(self, domain: str = '') -> Credentials:
        """获取 QQ 相关接口凭证(该 API 暂未被 go-cqhttp 支持, 您可以提交 pr 以使该 API 被支持 提交 pr)"""
        raise ApiNotSupport('go-cqhttp not support "get_credentials" api')

    async def get_record(
            self,
            file: str,
            out_format: Literal['mp3', 'amr', 'wma', 'm4a', 'spx', 'ogg', 'wav', 'flac']
    ) -> RecordFile:
        """获取语音(该 API 暂未被 go-cqhttp 支持, 您可以提交 pr 以使该 API 被支持 提交 pr)"""
        raise ApiNotSupport('go-cqhttp not support "get_record" api')

    async def can_send_image(self) -> CanSendImage:
        result = await self.bot.can_send_image()
        return CanSendImage.parse_obj(result)

    async def can_send_record(self) -> CanSendRecord:
        result = await self.bot.can_send_record()
        return CanSendRecord.parse_obj(result)

    async def get_version_info(self) -> VersionInfo:
        version_result = await self.bot.get_version_info()
        return VersionInfo.parse_obj(version_result)

    async def set_restart(self, delay: int = 0) -> None:
        """重启 go-cqhttp(实测 go-cqhttp 并不支持)"""
        raise ApiNotSupport('go-cqhttp not support "set_restart" api')

    async def clean_cache(self) -> None:
        """清理缓存(该 API 暂未被 go-cqhttp 支持, 您可以提交 pr 以使该 API 被支持 提交 pr)"""
        raise ApiNotSupport('go-cqhttp not support "clean_cache" api')

    async def set_group_portrait(self, group_id: int | str, file: str, cache: int = 1) -> None:
        r"""设置群头像

        - file 参数支持以下几种格式：
            - 绝对路径, 例如 file:///C:\\Users\Richard\Pictures\1.png, 格式使用 file URI
            - 网络 URL, 例如 https://i1.piimg.com/567571/fdd6e7b6d93f1ef0.jpg
            - Base64 编码, 例如 base64://iVBORw0KGgoAAAANSUhEUgAAABQAAAAVCAIAAADJt1n/AAAAKElEQVQ4EWPk5+RmIBcwkasRpG9UM4mhNxpgowFGMARGEwnBIEJVAAAdBgBNAZf+QAAAAABJRU5ErkJggg==
        - cache参数: 通过网络 URL 发送时有效, 1 表示使用缓存, 0 关闭关闭缓存, 默认为 1
        - 目前这个API在登录一段时间后因cookie失效而失效, 请考虑后使用

        :param group_id: 群号
        :param file: 图片文件名
        :param cache: 表示是否使用已缓存的文件
        """
        return await self.bot.call_api('set_group_portrait', group_id=group_id, file=file, cache=cache)

    async def ocr_image(self, image: str) -> OcrImageResult:
        """图片 OCR

        目前图片OCR接口仅支持接受的图片

        :param image: 图片ID
        """
        ocr_result = await self.bot.call_api('ocr_image', image=image)
        return OcrImageResult.parse_obj(ocr_result)

    async def get_group_system_msg(self) -> GroupSystemMessage:
        """获取群系统消息"""
        system_mes_result = await self.bot.call_api('get_group_system_msg')
        return GroupSystemMessage.parse_obj(system_mes_result)

    async def upload_group_file(self, group_id: int | str, file: str, name: str, folder: str | None = None) -> None:
        """上传群文件

        在不提供 folder 参数的情况下默认上传到根目录
        只能上传本地文件, 需要上传 http 文件的话请先调用 download_file API下载

        :param group_id: 群号
        :param file: 本地文件路径
        :param name: 储存名称
        :param folder: 父目录ID
        """
        return await self.bot.call_api('upload_group_file', group_id=group_id, file=file, name=name, folder=folder)

    async def get_group_file_system_info(self, group_id: int | str) -> GroupFileSystemInfo:
        system_info_result = await self.bot.call_api('get_group_file_system_info', group_id=group_id)
        return GroupFileSystemInfo.parse_obj(system_info_result)

    async def get_group_root_files(self, group_id: int | str) -> GroupRootFiles:
        """获取群根目录文件列表

        :param group_id: 群号
        """
        root_file_result = await self.bot.call_api('get_group_root_files', group_id=group_id)
        return GroupRootFiles.parse_obj(root_file_result)

    async def get_group_files_by_folder(self, group_id: int | str, folder_id: str) -> GroupFolderFiles:
        """获取群子目录文件列表

        :param group_id: 群号
        :param folder_id: 文件夹ID 参考 Folder 对象
        """
        file_result = await self.bot.call_api('get_group_files_by_folder', group_id=group_id, folder_id=folder_id)
        return GroupFolderFiles.parse_obj(file_result)

    async def get_group_file_url(self, group_id: int | str, file_id: str, busid: int) -> GroupFileResource:
        """获取群文件资源链接

        :param group_id: 群号
        :param file_id: 文件ID 参考 File 对象
        :param busid: 文件类型 参考 File 对象
        """
        file_result = await self.bot.call_api('get_group_file_url', group_id=group_id, file_id=file_id, busid=busid)
        return GroupFileResource.parse_obj(file_result)

    async def get_status(self) -> Status:
        status_result = await self.bot.get_status()
        return Status.parse_obj(status_result)

    async def get_group_at_all_remain(self, group_id: int | str) -> GroupAtAllRemain:
        """获取群 @全体成员 剩余次数

        :param group_id: 群号
        """
        result = await self.bot.call_api('get_group_at_all_remain', group_id=group_id)
        return GroupAtAllRemain.parse_obj(result)

    async def send_group_notice(self, group_id: int | str, content: str, image: str | None = None) -> None:
        """发送群公告

        :param group_id: 群号
        :param content: 公告内容
        :param image: 图片路径（可选）
        """
        if image is None:
            await self.bot.call_api('_send_group_notice', group_id=group_id, content=content)
        else:
            await self.bot.call_api('_send_group_notice', group_id=group_id, content=content, image=image)

    async def reload_event_filter(self, file: str) -> None:
        """重载事件过滤器

        :param file: 事件过滤器文件
        """
        return await self.bot.call_api('reload_event_filter', file=file)

    async def download_file(self, url: str, thread_count: int, headers: str | list[str]) -> DownloadedFile:
        """下载文件到缓存目录

        通过这个API下载的文件能直接放入CQ码作为图片或语音发送
        调用后会阻塞直到下载完成后才会返回数据，请注意下载大文件时的超时

        :param url: 链接地址
        :param thread_count: 下载线程数
        :param headers: 自定义请求头
        """
        file_result = await self.bot.call_api('download_file', url=url, thread_count=thread_count, headers=headers)
        return DownloadedFile.parse_obj(file_result)

    async def get_online_clients(self, no_cache: bool = False) -> OnlineClients:
        """获取当前账号在线客户端列表

        :param no_cache: 是否无视缓存
        """
        client_result = await self.bot.call_api('get_online_clients', no_cache=no_cache)
        return OnlineClients.parse_obj(client_result)

    async def get_group_msg_history(self, group_id: int | str, message_seq: int | None = None) -> GroupMessageHistory:
        """获取群消息历史记录

        :param group_id: 群号
        :param message_seq: 起始消息序号, 可通过 get_msg 获得, 不提供起始序号将默认获取最新的消息
        """
        message_result = await self.bot.call_api('get_group_msg_history', group_id=group_id, message_seq=message_seq)
        return GroupMessageHistory.parse_obj(message_result)

    async def set_essence_msg(self, message_id: int) -> None:
        """设置精华消息

        :param message_id: 消息ID
        """
        return await self.bot.call_api('set_essence_msg', message_id=message_id)

    async def delete_essence_msg(self, message_id: int) -> None:
        """移出精华消息

        :param message_id: 消息ID
        """
        return await self.bot.call_api('delete_essence_msg', message_id=message_id)

    async def get_essence_msg_list(self, group_id: int | str) -> list[GroupEssenceMessage]:
        """获取精华消息列表

        :param group_id: 群号
        """
        messages_result = await self.bot.call_api('get_essence_msg_list', group_id=group_id)
        return parse_obj_as(list[GroupEssenceMessage], messages_result)

    async def check_url_safely(self, url: str) -> UrlSafely:
        """检查链接安全性

        :param url: 需要检查的链接
        :return: level, int: 安全等级, 1: 安全 2: 未知 3: 危险
        """
        result = await self.bot.call_api('check_url_safely', url=url)
        return UrlSafely.parse_obj(result)

    async def get_guild_service_profile(self) -> GuildServiceProfile:
        """获取频道系统内BOT的资料"""
        result_data = await self.bot.call_api(api='get_guild_service_profile')
        return GuildServiceProfile.parse_obj(result_data)

    async def get_guild_list(self) -> list[GuildInfo]:
        """获取频道列表"""
        result_data = await self.bot.call_api(api='get_guild_list')
        return parse_obj_as(list[GuildInfo], result_data)

    async def get_guild_meta_by_guest(self, guild_id: int | str) -> GuildMeta:
        """通过访客获取频道元数据

        :param guild_id: 频道ID
        """
        meta_result = await self.bot.call_api('get_guild_meta_by_guest', guild_id=guild_id)
        return GuildMeta.parse_obj(meta_result)

    async def get_guild_channel_list(self, guild_id: int | str, no_cache: bool = False) -> list[ChannelInfo]:
        """获取子频道列表

        :param guild_id: 频道ID
        :param no_cache: 是否无视缓存
        """
        channel_result = await self.bot.call_api('get_guild_channel_list', guild_id=guild_id, no_cache=no_cache)
        return parse_obj_as(list[ChannelInfo], channel_result)

    async def get_guild_member_list(self, guild_id: int | str, next_token: str | None = None) -> GuildMemberList:
        """获取频道成员列表

        next_token 为空的情况下, 将返回第一页的数据, 并在返回值附带下一页的 token

        默认情况下频道管理员的权限组ID为 2, 部分频道可能会另行创建, 需手动判断
        此接口仅展现最新的权限组, 获取用户加入的所有权限组请使用 get_guild_member_profile 接口

        由于频道人数较多(数万), 请尽量不要全量拉取成员列表, 这将会导致严重的性能问题, 尽量使用 get_guild_member_profile 接口代替全量拉取

        :param guild_id: 频道ID
        :param next_token: 翻页Token
        """
        member_result = await self.bot.call_api('get_guild_member_list', guild_id=guild_id, next_token=next_token)
        return GuildMemberList.parse_obj(member_result)

    async def get_guild_member_profile(self, guild_id: int | str, user_id: int | str) -> GuildMemberProfile:
        """单独获取频道成员信息

        :param guild_id: 频道ID
        :param user_id: 用户ID
        """
        member_result = await self.bot.call_api('get_guild_member_profile', guild_id=guild_id, user_id=user_id)
        return GuildMemberProfile.parse_obj(member_result)

    async def send_guild_channel_msg(
            self, guild_id: int | str, channel_id: int | str, message: str | Message
    ) -> SentGuildMessage:
        """发送信息到子频道

        :param guild_id: 频道ID
        :param channel_id: 子频道ID
        :param message: 消息, 与原有消息类型相同
        """
        message_result = await self.bot.call_api(
            'send_guild_channel_msg', guild_id=guild_id, channel_id=channel_id, message=message)
        return SentGuildMessage.parse_obj(message_result)

    async def get_topic_channel_feeds(self, guild_id: int | str, channel_id: int | str) -> list[TopicChannelFeedInfo]:
        """获取话题频道帖子

        :param guild_id: 频道ID
        :param channel_id: 子频道ID
        """
        feeds_result = await self.bot.call_api('get_topic_channel_feeds', guild_id=guild_id, channel_id=channel_id)
        return parse_obj_as(list[TopicChannelFeedInfo], feeds_result)


__all__ = [
    'GoCqhttpBot'
]
