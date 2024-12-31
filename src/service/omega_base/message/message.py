"""
@Author         : Ailitonia
@Date           : 2023/5/27 13:59
@FileName       : message
@Project        : nonebot2_miya
@Description    : Omega Internal Message
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from collections.abc import Iterable, Sequence
from enum import StrEnum, unique
from pathlib import Path
from typing import Any, Union, override

import ujson as json
from nonebot.internal.adapter import Message as BaseMessage
from nonebot.internal.adapter import MessageSegment as BaseMessageSegment


@unique
class MessageSegmentType(StrEnum):
    at = 'at'
    at_all = 'at_all'
    emoji = 'emoji'

    audio = 'audio'
    file = 'file'
    image = 'image'
    image_file = 'image_file'
    video = 'video'
    voice = 'voice'

    reply = 'reply'
    ref_node = 'ref_node'
    custom_node = 'custom_node'

    json_hyper = 'json_hyper'
    xml_hyper = 'xml_hyper'

    text = 'text'
    other = 'other'


class MessageSegment(BaseMessageSegment['Message']):
    """Omega 中间件 MessageSegment 适配。具体方法参考协议消息段类型或源码。"""

    @classmethod
    @override
    def get_message_class(cls) -> type['Message']:
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
    def at(user_id: int | str) -> 'MessageSegment':
        """At 消息段, 表示一类提醒某用户的消息段类型

        - type: at
        - data_map: {user_id: str}
        """
        return MessageSegment(type=MessageSegmentType.at, data={'user_id': str(user_id)})

    @staticmethod
    def at_all() -> 'MessageSegment':
        """AtAll 消息段, 表示一类提醒所有人的消息段类型

        - type: at_all
        - data_map: {at_all: bool}
        """
        return MessageSegment(type=MessageSegmentType.at_all, data={'at_all': True})

    @staticmethod
    def emoji(id_: str, *, name: str | None = None) -> 'MessageSegment':
        """Emoji 消息段, 表示一类表情元素消息段类型

        - type: emoji
        - data_map: {id: str, name: Optional[str]}
        """
        return MessageSegment(type=MessageSegmentType.emoji, data={'id': id_, 'name': name})

    @staticmethod
    def audio(url: str | Path) -> 'MessageSegment':
        """Audio 消息段, 表示一类音频消息段类型

        - type: audio
        - data_map: {url: str}
        """
        return MessageSegment(
            type=MessageSegmentType.audio,
            data={'url': url.resolve().as_posix() if isinstance(url, Path) else url}
        )

    @staticmethod
    def file(file: Path) -> 'MessageSegment':
        """File 消息段, 表示一类文件消息段类型

        - type: file
        - data_map: {file: str}
        """
        return MessageSegment(
            type=MessageSegmentType.file,
            data={'file': file.resolve().as_posix()}
        )

    @staticmethod
    def image(url: str | Path) -> 'MessageSegment':
        """Image 消息段, 表示一类图片消息段类型

        - type: image
        - data_map: {url: str}
        """
        return MessageSegment(
            type=MessageSegmentType.image,
            data={'url': url.resolve().as_posix() if isinstance(url, Path) else url}
        )

    @staticmethod
    def image_file(file: Path) -> 'MessageSegment':
        """ImageFile 消息段, 表示一类以文件发送的图片消息段类型

        - type: image_file
        - data_map: {file: str}
        """
        return MessageSegment(
            type=MessageSegmentType.image_file,
            data={'file': file.resolve().as_posix()}
        )

    @staticmethod
    def video(url: str | Path) -> 'MessageSegment':
        """Video 消息段, 表示一类视频消息段类型

        - type: video
        - data_map: {url: str}
        """
        return MessageSegment(
            type=MessageSegmentType.video,
            data={'url': url.resolve().as_posix() if isinstance(url, Path) else url}
        )

    @staticmethod
    def voice(url: str | Path) -> 'MessageSegment':
        """Voice 消息段, 表示一类语音消息段类型

        - type: voice
        - data_map: {url: str}
        """
        return MessageSegment(
            type=MessageSegmentType.voice,
            data={'url': url.resolve().as_posix() if isinstance(url, Path) else url}
        )

    @staticmethod
    def reply(id_: int | str) -> 'MessageSegment':
        """Reply 消息段, 表示一类回复消息段类型

        - type: reply
        - data_map: {id: str}
        """
        return MessageSegment(type=MessageSegmentType.reply, data={'id': str(id_)})

    @staticmethod
    def ref_node(id_: int | str) -> 'MessageSegment':
        """ReferenceNode 消息段, 表示转发消息的引用消息段类型

        - type: ref_node
        - data_map: {id: str}
        """
        return MessageSegment(type=MessageSegmentType.ref_node, data={'id': str(id_)})

    @staticmethod
    def custom_node(
            user_id: int | str,
            nickname: str,
            content: Sequence[Union[str, 'MessageSegment']],
    ) -> 'MessageSegment':
        """CustomNode 消息段, 表示转发消息的自定义消息段类型

        - type: custom_node
        - data_map: {user_id: str, nickname: str, content: list[MessageSegment]}
        """
        return MessageSegment(
            type=MessageSegmentType.custom_node,
            data={
                'user_id': str(user_id),
                'nickname': str(nickname),
                'content': [MessageSegment.text(x) if isinstance(x, str) else x for x in content]
            }
        )

    @staticmethod
    def json_hyper(raw: str) -> 'MessageSegment':
        """JSON Hyper 消息段, 表示一类以 JSON 传输的超文本消息内容, 如卡片消息、ark消息、小程序等消息段类型

        - type: json_hyper
        - data_map: {raw: str}
        """
        return MessageSegment(type=MessageSegmentType.json_hyper, data={'raw': raw})

    @staticmethod
    def xml_hyper(raw: str) -> 'MessageSegment':
        """XML Hyper 消息段, 表示一类以 XML 传输的超文本消息内容, 如卡片消息、ark消息、小程序等消息段类型

        - type: xml_hyper
        - data_map: {raw: str}
        """
        return MessageSegment(type=MessageSegmentType.xml_hyper, data={'raw': raw})

    @staticmethod
    def text(text: str) -> 'MessageSegment':
        """纯文本消息段类型

        - type: text
        - data_map: {text: str}
        """
        return MessageSegment(type=MessageSegmentType.text, data={'text': text})

    @staticmethod
    def other(type_: str, data: dict[str, Any]) -> 'MessageSegment':
        """其他消息段类型

        - type: other
        - data_map: {type: str, data: dict[str, Any]}
        """
        return MessageSegment(type=MessageSegmentType.other, data={'type': type_, 'data': data})


class Message(BaseMessage[MessageSegment]):
    """Omega 中间件 Message 适配。"""

    @classmethod
    @override
    def get_segment_class(cls) -> type[MessageSegment]:
        return MessageSegment

    def __repr__(self) -> str:
        return ''.join(repr(seg) for seg in self)

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        yield MessageSegment.text(text=msg)

    @classmethod
    def loads(cls, message_data: str) -> 'Message':
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
            if (segment.type == MessageSegmentType.image) and ('url' in segment.data)
        ]

    def filter(self, types: Iterable[str]) -> 'Message':
        """过滤消息段类型"""
        return self.__class__(seg for seg in self.copy() if seg.type in types)


__all__ = [
    'Message',
    'MessageSegment',
    'MessageSegmentType',
]
