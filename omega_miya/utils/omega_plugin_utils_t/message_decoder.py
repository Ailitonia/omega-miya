"""
@Author         : Ailitonia
@Date           : 2021/08/14 19:42
@FileName       : message_decoder.py
@Project        : nonebot2_miya 
@Description    : 消息解析工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List
from nonebot.adapters.cqhttp.message import Message


class MessageDecoder(object):
    def __init__(self, message: Message):
        self.__message = message

    def get_all_img_url(self) -> List[str]:
        return [msg_seg.data.get('url') for msg_seg in self.__message if msg_seg.type == 'image']

    def get_all_at_qq(self) -> List[int]:
        return [msg_seg.data.get('qq') for msg_seg in self.__message if msg_seg.type == 'at']


__all__ = [
    'MessageDecoder'
]
