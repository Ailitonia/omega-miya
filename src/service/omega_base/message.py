"""
@Author         : Ailitonia
@Date           : 2023/5/27 13:59
@FileName       : message
@Project        : nonebot2_miya
@Description    : Omega Internal Message
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from enum import StrEnum, unique
from pathlib import Path
from typing import Iterable, Type, Union, override

import ujson as json
from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment


@unique
class MessageSegmentType(StrEnum):
    at = 'at'
    at_all = 'at_all'
    forward_id = 'forward_id'
    custom_node = 'custom_node'
    image = 'image'
    image_file = 'image_file'
    file = 'file'
    text = 'text'


class MessageSegment(BaseMessageSegment["Message"]):
    """Omega 中间件 MessageSegment 适配。具体方法参考协议消息段类型或源码。"""

    @classmethod
    @override
    def get_message_class(cls) -> Type["Message"]:
        return Message

    @override
    def __str__(self) -> str:
        if self.is_text():
            return self.data.get('text', '')
        return ''

    def __repr__(self) -> str:
        if self.is_text():
            return self.data.get('text', '')
        params = ', '.join([f'{k}={v}' for k, v in self.data.items() if v is not None])
        return f'[{self.type}{":" if params else ""}{params}]'

    @override
    def is_text(self) -> bool:
        return self.type == MessageSegmentType.text

    @staticmethod
    def at(user_id: int | str) -> "MessageSegment":
        return MessageSegment(type=MessageSegmentType.at, data={'user_id': str(user_id)})

    @staticmethod
    def at_all() -> "MessageSegment":
        return MessageSegment(type=MessageSegmentType.at_all, data={'at_all': True})

    @staticmethod
    def forward_id(id_: int | str) -> "MessageSegment":
        return MessageSegment(type=MessageSegmentType.forward_id, data={'id': str(id_)})

    @staticmethod
    def custom_node(user_id: int | str, nickname: str, content: str | BaseMessageSegment) -> "MessageSegment":
        return MessageSegment(
            type=MessageSegmentType.custom_node,
            data={
                'user_id': str(user_id),
                'nickname': str(nickname),
                'content': MessageSegment.text(content) if isinstance(content, str) else content
            }
        )

    @staticmethod
    def image(url: Union[str, Path]) -> "MessageSegment":
        return MessageSegment(
            type=MessageSegmentType.image,
            data={'url': str(url.resolve()) if isinstance(url, Path) else url}
        )

    @staticmethod
    def image_file(file: Path) -> "MessageSegment":
        return MessageSegment(
            type=MessageSegmentType.image_file,
            data={'file': str(file.resolve())}
        )

    @staticmethod
    def file(file: Path) -> "MessageSegment":
        return MessageSegment(
            type=MessageSegmentType.file,
            data={'file': str(file.resolve())}
        )

    @staticmethod
    def text(text: str) -> "MessageSegment":
        return MessageSegment(type=MessageSegmentType.text, data={'text': text})


class Message(BaseMessage[MessageSegment]):
    """Omega 中间件 Message 适配。"""

    @classmethod
    @override
    def get_segment_class(cls) -> Type[MessageSegment]:
        return MessageSegment

    def __repr__(self) -> str:
        return "".join(repr(seg) for seg in self)

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        yield MessageSegment.text(text=msg)

    @classmethod
    def loads(cls, message_data: str) -> "Message":
        """将导出的消息 json 字符串转化为 Message 对象"""
        message = cls(MessageSegment(**seg) for seg in json.loads(message_data))
        return message

    def dumps(self) -> str:
        """将 Message 转化为 json 字符串导出"""
        message_data = json.dumps([{'type': seg.type, 'data': seg.data} for seg in self], ensure_ascii=False)
        return message_data

    def extract_image_urls(self) -> list[str]:
        """提取消息中的图片链接"""
        return [
            segment.data['url']
            for segment in self
            if (segment.type == MessageSegmentType.image.value) and ('url' in segment.data)
        ]

    def filter(self, types: Iterable[str]) -> "Message":
        """过滤消息段类型"""
        return self.__class__(seg for seg in self.copy() if seg.type in types)


__all__ = [
    'Message',
    'MessageSegment',
    'MessageSegmentType',
]
