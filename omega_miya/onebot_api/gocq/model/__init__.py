"""
@Author         : Ailitonia
@Date           : 2022/04/14 21:40
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .file import ImageFile, OcrImageResult, DownloadedFile, VersionInfo, Status, OnlineClients, UrlSafely
from .group import (GroupSystemMessage, GroupFileSystemInfo, GroupRootFiles, GroupFolderFiles, GroupFileResource,
                    GroupAtAllRemain, GroupEssenceMessage)
from .guild import (GuildServiceProfile, GuildInfo, GuildMeta, ChannelInfo, GuildMemberList, GuildMemberProfile,
                    SentGuildMessage, TopicChannelFeedInfo)
from .message import ReceiveMessage, GroupMessageHistory, ReceiveForwardMessage
from .user import StrangerInfo, GroupUser, Anonymous, QidianAccountUser


__all__ = [
    'ImageFile',
    'OcrImageResult',
    'DownloadedFile',
    'VersionInfo',
    'Status',
    'OnlineClients',
    'UrlSafely',
    'GroupSystemMessage',
    'GroupFileSystemInfo',
    'GroupRootFiles',
    'GroupFolderFiles',
    'GroupFileResource',
    'GroupAtAllRemain',
    'GroupEssenceMessage',
    'ReceiveMessage',
    'GroupMessageHistory',
    'ReceiveForwardMessage',
    'GuildServiceProfile',
    'GuildInfo',
    'GuildMeta',
    'ChannelInfo',
    'GuildMemberList',
    'GuildMemberProfile',
    'SentGuildMessage',
    'TopicChannelFeedInfo',
    'StrangerInfo',
    'GroupUser',
    'Anonymous',
    'QidianAccountUser'
]
