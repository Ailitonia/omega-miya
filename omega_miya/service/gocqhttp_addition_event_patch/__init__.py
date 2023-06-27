"""
@Author         : Ailitonia
@Date           : 2023/3/18 3:15
@FileName       : gocqhttp_addition_event_patch
@Project        : nonebot2_miya
@Description    : Go-cqhttp 事件补丁
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .model import GroupCardNoticeEvent, OfflineFileNoticeEvent, ClientStatusNoticeEvent, EssenceNoticeEvent


__all__ = [
    'GroupCardNoticeEvent',
    'OfflineFileNoticeEvent',
    'ClientStatusNoticeEvent',
    'EssenceNoticeEvent'
]
