"""
@Author         : Ailitonia
@Date           : 2021/08/14 19:42
@FileName       : message_tools.py
@Project        : nonebot2_miya 
@Description    : 消息解析工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List
from nonebot.adapters.cqhttp.message import Message
from nonebot.adapters.cqhttp.event import Event
from omega_miya.database import Result
from .picture_encoder import PicEncoder


class MessageDecoder(object):
    def __init__(self, message: Message):
        self.__message = message

    def get_all_img_url(self) -> List[str]:
        return [msg_seg.data.get('url') for msg_seg in self.__message if msg_seg.type == 'image']

    def get_all_at_qq(self) -> List[int]:
        return [msg_seg.data.get('qq') for msg_seg in self.__message if msg_seg.type == 'at']


class MessageTools(object):
    def __init__(self, message: Message):
        self.__message = message

    def safe_message_filter(self, *args: str) -> Message:
        """过滤消息, 仅保留允许的类型
        :param args: 允许的消息段类型
        :return: 过滤后的 Message
        """
        filtered_msg_list = [msg_seg for msg_seg in self.__message if msg_seg.type in args]
        return Message(filtered_msg_list)


class EventTools(object):
    def __init__(self, event: Event):
        self.event = event

    async def get_user_head_img(self, *, head_img_size: int = 5) -> Result.TextResult:
        """
        :param head_img_size: 1: 40×40px, 2: 40 × 40px, 3: 100 × 100px, 4: 140 × 140px, 5: 640 × 640px,
                            40: 40 × 40px, 100: 100 × 100px
        :return: 图片消息
        """
        user_id = getattr(self.event, 'user_id', None)
        if user_id is None:
            raise ValueError(f'Event: {self.event.get_event_name()} has not user id')

        url = f'https://q1.qlogo.cn/g?b=qq&nk={user_id}&s={head_img_size}'
        url2 = f'https://q2.qlogo.cn/headimg_dl?dst_uin={user_id}&spec={head_img_size}'
        url_i = f'https://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={user_id}'

        return await PicEncoder(pic_url=url).get_file(folder_flag='qq_head_img')


__all__ = [
    'MessageDecoder',
    'MessageTools',
    'EventTools'
]
