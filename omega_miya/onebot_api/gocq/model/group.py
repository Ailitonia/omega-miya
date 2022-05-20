"""
@Author         : Ailitonia
@Date           : 2022/04/16 15:52
@FileName       : group.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp Group Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from pydantic import AnyHttpUrl
from ...model import BaseOnebotModel
from ...model import GroupInfo as OnebotGroupInfo, GroupHonor as OnebotGroupHonor


class GroupInfo(OnebotGroupInfo):
    """群信息"""


class GroupHonor(OnebotGroupHonor):
    """群荣耀信息"""


class GroupInvitedRequest(BaseOnebotModel):
    """群邀请消息

    - request_id: 请求ID
    - invitor_uin: 邀请者
    - invitor_nick: 邀请者昵称
    - group_id: 群号
    - group_name: 群名
    - checked: 是否已被处理
    - actor: 处理者, 未处理为0
    """
    request_id: int
    invitor_uin: int
    invitor_nick: str
    group_id: int
    group_name: str
    checked: bool
    actor: int


class GroupJoinRequest(BaseOnebotModel):
    """进群消息

    - request_id: 请求ID
    - requester_uin: 请求者ID
    - requester_nick: 请求者昵称
    - message: 验证消息
    - group_id: 群号
    - group_name: 群名
    - checked: 是否已被处理
    - actor: 处理者, 未处理为0
    """
    request_id: int
    requester_uin: int
    requester_nick: str
    message: str
    group_id: int
    group_name: str
    checked: bool
    actor: int


class GroupSystemMessage(BaseOnebotModel):
    """群系统消息

    - invited_requests: 邀请消息列表
    - join_requests: 进群消息列表
    """
    invited_requests: Optional[list[GroupInvitedRequest]]
    join_requests: Optional[list[GroupJoinRequest]]


class GroupFileSystemInfo(BaseOnebotModel):
    """群文件系统信息

    - file_count: 文件总数
    - limit_count: 文件上限
    - used_space: 已使用空间
    - total_space: 空间上限
    """
    file_count: int
    limit_count: int
    used_space: int
    total_space: int


class GroupFile(BaseOnebotModel):
    """群文件

    - group_id: 群号
    - file_id: 文件ID
    - file_name: 文件名
    - busid: 文件类型
    - file_size: 文件大小
    - upload_time: 上传时间
    - dead_time: 过期时间,永久文件恒为0
    - modify_time: 最后修改时间
    - download_times: 下载次数
    - uploader: 上传者ID
    - uploader_name: 上传者名字
    """
    group_id: int
    file_id: str
    file_name: str
    busid: int
    file_size: int
    upload_time: int
    dead_time: int
    modify_time: int
    download_times: int
    uploader: int
    uploader_name: str


class GroupFolder(BaseOnebotModel):
    """群文件文件夹

    - group_id: 群号
    - folder_id: 文件夹ID
    - folder_name: 文件名
    - create_time: 创建时间
    - creator: 创建者
    - creator_name: 创建者名字
    - total_file_count: 子文件数量
    """
    group_id: int
    folder_id: str
    folder_name: str
    create_time: int
    creator: int
    creator_name: str
    total_file_count: int


class GroupRootFiles(BaseOnebotModel):
    """群根目录文件列表

    - files: 文件列表
    - folders: 文件夹列表
    """
    files: list[GroupFile]
    folders: Optional[list[GroupFolder]]


class GroupFolderFiles(GroupRootFiles):
    """群子目录文件列表

    - files: 文件列表
    - folders: 文件夹列表
    """


class GroupFileResource(BaseOnebotModel):
    """群文件资源链接"""
    url: AnyHttpUrl


class GroupAtAllRemain(BaseOnebotModel):
    """群 @全体成员 剩余次数

    - can_at_all: 是否可以 @全体成员
    - remain_at_all_count_for_group: 群内所有管理当天剩余 @全体成员 次数
    - remain_at_all_count_for_uin: Bot 当天剩余 @全体成员 次数
    """
    can_at_all: bool
    remain_at_all_count_for_group: int
    remain_at_all_count_for_uin: int


class GroupEssenceMessage(BaseOnebotModel):
    """群精华消息

    - sender_id: 发送者QQ 号
    - sender_nick: 发送者昵称
    - sender_time: 消息发送时间
    - operator_id: 操作者QQ 号
    - operator_nick: 操作者昵称
    - operator_time: 精华设置时间
    - message_id: 消息ID
    """
    sender_id: int
    sender_nick: str
    sender_time: int
    operator_id: int
    operator_nick: str
    operator_time: int
    message_id: int


__all__ = [
    'GroupInfo',
    'GroupHonor',
    'GroupSystemMessage',
    'GroupFileSystemInfo',
    'GroupRootFiles',
    'GroupFolderFiles',
    'GroupFileResource',
    'GroupAtAllRemain',
    'GroupEssenceMessage'
]
