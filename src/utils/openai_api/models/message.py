"""
@Author         : Ailitonia
@Date           : 2025/2/11 13:56:10
@FileName       : message.py
@Project        : omega-miya
@Description    : openai message
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from enum import StrEnum, unique
from typing import Any, Iterable, Literal, Self

from pydantic import Field

from .base import BaseOpenAIModel


class BaseMessageContent[T](BaseOpenAIModel):
    """openai 消息内容基类"""
    type: T


class AudioContent(BaseOpenAIModel):
    data: str
    format: str


class ImageContent(BaseOpenAIModel):
    url: str
    detail: str | None = None


class AudioMessageContent(BaseMessageContent[Literal['input_audio']]):
    input_audio: AudioContent


class ImageMessageContent(BaseMessageContent[Literal['image_url']]):
    image_url: ImageContent


class TextMessageContent(BaseMessageContent[Literal['text']]):
    text: str


type MessageContentType = AudioMessageContent | ImageMessageContent | TextMessageContent


@unique
class MessageRole(StrEnum):
    developer = 'developer'
    system = 'system'
    user = 'user'
    assistant = 'assistant'
    tool = 'tool'
    function = 'function'


class Function(BaseOpenAIModel):
    name: str
    arguments: str


class ToolCalls(BaseOpenAIModel):
    id: str
    type: Literal['function']
    function: Function


class Audio(BaseOpenAIModel):
    id: str
    expires_at: int
    data: str
    transcript: str


class MessageContent(BaseOpenAIModel):
    """openai 消息内容"""
    role: MessageRole
    content: list[MessageContentType] | str = Field(default_factory=list)
    name: str | None = Field(default=None)
    refusal: str | None = Field(default=None)
    audio: Audio | None = Field(default=None)
    tool_calls: ToolCalls | None = Field(default=None)
    tool_call_id: str | None = Field(default=None)
    function_call: Function | None = Field(default=None)

    @classmethod
    def developer(cls, name: str | None = None) -> Self:
        return cls(role=MessageRole.developer, name=name)

    @classmethod
    def system(cls, name: str | None = None) -> Self:
        return cls(role=MessageRole.system, name=name)

    @classmethod
    def user(cls, name: str | None = None) -> Self:
        return cls(role=MessageRole.user, name=name)

    @classmethod
    def assistant(cls, name: str | None = None) -> Self:
        return cls(role=MessageRole.assistant, name=name)

    @classmethod
    def tool(cls, name: str | None = None) -> Self:
        return cls(role=MessageRole.tool, name=name)

    @classmethod
    def function(cls, name: str | None = None) -> Self:
        return cls(role=MessageRole.function, name=name)

    @property
    def plain_text(self) -> str:
        """提取消息内纯文本消息"""
        if isinstance(self.content, list):
            return '\n'.join(x.text for x in self.content if isinstance(x, TextMessageContent))
        else:
            return self.content

    def add_audio(self, data: str, format_: str) -> Self:
        if isinstance(self.content, str):
            self.content = [TextMessageContent.model_validate({'type': 'text', 'text': self.content})]

        self.content.append(AudioMessageContent.model_validate({
            'type': 'input_audio',
            'input_audio': {
                'data': data,
                'format': format_
            },
        }))
        return self

    def add_image_url(self, image_url: str, *, detail: str | None = None) -> Self:
        if isinstance(self.content, str):
            self.content = [TextMessageContent.model_validate({'type': 'text', 'text': self.content})]

        self.content.append(ImageMessageContent.model_validate({
            'type': 'image_url',
            'image_url': {
                'url': image_url,
                'detail': detail
            },
        }))
        return self

    def add_text(self, text: str) -> Self:
        if isinstance(self.content, str):
            self.content = [TextMessageContent.model_validate({'type': 'text', 'text': self.content})]

        self.content.append(TextMessageContent.model_validate({'type': 'text', 'text': text}))
        return self

    def set_plain_text(self, text: str) -> Self:
        self.content = text
        return self

    @property
    def messages(self) -> dict[str, Any]:
        """导出 messages 数据"""
        return self.model_dump(exclude_none=True)


class Message(BaseOpenAIModel):
    """openai 消息"""
    messages: list[MessageContent] = Field(default_factory=list)

    def add_content(self, content: MessageContent) -> Self:
        self.messages.append(content)
        return self

    def extend_content(self, contents: Iterable[MessageContent]) -> Self:
        self.messages.extend(contents)
        return self


__all__ = [
    'Message',
    'MessageContent',
    'MessageRole',
]
