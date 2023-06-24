"""
@Author         : Ailitonia
@Date           : 2023/6/10 4:19
@FileName       : telegram
@Project        : nonebot2_miya
@Description    : Telegram 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pathlib import Path
from typing import Tuple, Union, Iterable
from urllib.parse import urlparse

from nonebot.adapters.telegram.message import (
    Entity,
    File,
    Message as TelegramMessage,
    MessageSegment as TelegramMessageSegment
)

from ..const import SupportedPlatform
from ..message_tools import register_builder, register_extractor
from ..types import MessageBuilder
from ...message import MessageSegmentType, Message as OmegaMessage, MessageSegment as OmegaMessageSegment


@register_builder(adapter_name=SupportedPlatform.telegram.value)
class TelegramMessageBuilder(MessageBuilder):

    @staticmethod
    def _construct(message: OmegaMessage) -> Iterable[TelegramMessageSegment]:

        def _iter_message(msg: OmegaMessage) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case MessageSegmentType.at.value:
                    yield Entity.mention(text='@' + data.get('user_id'))
                case MessageSegmentType.image.value:
                    url = data.get('url')
                    if urlparse(url).scheme not in ['http', 'https']:
                        url = Path(url).as_posix()
                    yield File.photo(file=url)
                case MessageSegmentType.text.value:
                    yield Entity.text(text=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment]) -> TelegramMessage:
        _msg = TelegramMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return TelegramMessage(message)
        elif isinstance(message, OmegaMessageSegment):
            return TelegramMessage(self._construct(OmegaMessage(message)))
        elif isinstance(message, OmegaMessage):
            return TelegramMessage(self._construct(message))
        else:
            return TelegramMessage(message)


@register_extractor(adapter_name=SupportedPlatform.telegram.value)
class TelegramMessageExtractor(MessageBuilder):
    """Telegram 消息解析器"""

    @staticmethod
    def _construct(message: TelegramMessage) -> Iterable[OmegaMessageSegment]:

        def _iter_message(msg: TelegramMessage) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case 'mention':
                    yield OmegaMessageSegment.at(user_id=str(data.get('text')).removeprefix('@'))
                case 'photo':
                    yield OmegaMessageSegment.image(url=data.get('file'))
                case 'text':
                    yield OmegaMessageSegment.text(text=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, TelegramMessage, TelegramMessageSegment]) -> OmegaMessage:
        _msg = OmegaMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return OmegaMessage(message)
        elif isinstance(message, TelegramMessageSegment):
            return OmegaMessage(self._construct(TelegramMessage(message)))
        elif isinstance(message, TelegramMessage):
            return OmegaMessage(self._construct(message))
        else:
            return OmegaMessage(message)


__all__ = []
