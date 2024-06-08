"""
@Author         : Ailitonia
@Date           : 2023/5/27 13:59
@FileName       : message
@Project        : nonebot2_miya
@Description    : Omega Internal Message
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import ujson as json
from enum import Enum, unique
from pathlib import Path
from typing import Iterable, Literal, Type, Union

from nonebot.typing import overrides

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment


@unique
class MessageSegmentType(Enum):
    at: Literal['at'] = 'at'
    at_all: Literal['at_all'] = 'at_all'
    forward_id: Literal['forward_id'] = 'forward_id'
    custom_node: Literal['custom_node'] = 'custom_node'
    image: Literal['image'] = 'image'
    image_file: Literal['image_file'] = 'image_file'
    file: Literal['file'] = 'file'
    text: Literal['text'] = 'text'


class MessageSegment(BaseMessageSegment):
    """Omega 中间件 MessageSegment 适配。具体方法参考协议消息段类型或源码。"""

    @classmethod
    @overrides(BaseMessageSegment)
    def get_message_class(cls) -> Type["Message"]:
        return Message

    @overrides(BaseMessageSegment)
    def __str__(self) -> str:
        if self.is_text():
            return self.data.get('text', '')
        return ''

    def __repr__(self) -> str:
        if self.is_text():
            return self.data.get('text', '')
        params = ', '.join([f'{k}={v}' for k, v in self.data.items() if v is not None])
        return f'[{self.type}{":" if params else ""}{params}]'

    @overrides(BaseMessageSegment)
    def is_text(self) -> bool:
        return self.type == MessageSegmentType.text.value

    @staticmethod
    def at(user_id: int | str) -> "MessageSegment":
        return MessageSegment(MessageSegmentType.at.value, {'user_id': str(user_id)})

    @staticmethod
    def at_all() -> "MessageSegment":
        return MessageSegment(MessageSegmentType.at_all.value, {'at_all': True})

    @staticmethod
    def forward_id(id_: int | str) -> "MessageSegment":
        return MessageSegment(MessageSegmentType.forward_id.value, {'id': str(id_)})

    @staticmethod
    def custom_node(user_id: int | str, nickname: str, content: str | BaseMessageSegment) -> "MessageSegment":
        return MessageSegment(
            MessageSegmentType.custom_node.value,
            {
                'user_id': str(user_id),
                'nickname': str(nickname),
                'content': MessageSegment.text(content) if isinstance(content, str) else content
            }
        )

    @staticmethod
    def image(url: Union[str, Path]) -> "MessageSegment":
        return MessageSegment(
            MessageSegmentType.image.value,
            {
                'url': str(url.resolve()) if isinstance(url, Path) else url
            }
        )

    @staticmethod
    def image_file(file: Path) -> "MessageSegment":
        return MessageSegment(
            MessageSegmentType.image_file.value,
            {
                'file': str(file.resolve())
            }
        )

    @staticmethod
    def file(file: Path) -> "MessageSegment":
        return MessageSegment(
            MessageSegmentType.file.value,
            {
                'file': str(file.resolve())
            }
        )

    @staticmethod
    def text(text: str) -> "MessageSegment":
        return MessageSegment(MessageSegmentType.text.value, {'text': text})


class Message(BaseMessage[MessageSegment]):
    """Omega 中间件 Message 适配。"""

    @classmethod
    @overrides(BaseMessage)
    def get_segment_class(cls) -> Type[MessageSegment]:
        return MessageSegment

    def __repr__(self) -> str:
        return "".join(repr(seg) for seg in self)

    @staticmethod
    @overrides(BaseMessage)
    def _construct(text: str) -> Iterable[MessageSegment]:
        yield MessageSegment.text(text=text)

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
    'MessageSegmentType'
]
