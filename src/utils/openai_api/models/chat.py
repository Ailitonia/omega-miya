"""
@Author         : Ailitonia
@Date           : 2025/2/12 11:00:26
@FileName       : chat.py
@Project        : omega-miya
@Description    : openai chat model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any, Literal

from pydantic import Field, field_validator

from .base import BaseOpenAIModel
from .message import MessageContent, MessageContentType, MessageRole


class TopLogprob(BaseOpenAIModel):
    token: str
    bytes: list[int] | None = None
    logprob: float


class TokenLogprob(TopLogprob):
    top_logprobs: list[TopLogprob] = Field(default_factory=list)


class ChoiceLogprobs(BaseOpenAIModel):
    content: list[TokenLogprob] | None = None
    refusal: list[TokenLogprob] | None = None


class Choice(BaseOpenAIModel):
    index: int
    message: MessageContent
    logprobs: ChoiceLogprobs | None = None
    finish_reason: Literal[
        'stop',
        'eos',
        'length',
        'content_filter',
        'tool_calls',
        'function_call',
        'insufficient_system_resource',
        'not_provided',
    ] = Field(default='not_provided')

    @field_validator('finish_reason', mode='before')
    @classmethod
    def _enforce_no_null_finish_reason(cls, value: Any) -> Any:
        if value is None:
            return 'not_provided'
        else:
            return value


class ChunkChoice(BaseOpenAIModel):
    index: int
    delta: MessageContent
    logprobs: ChoiceLogprobs | None = None
    finish_reason: Literal[
        'stop',
        'eos',
        'length',
        'content_filter',
        'tool_calls',
        'function_call',
        'insufficient_system_resource',
        'not_provided',
    ] = Field(default='not_provided')

    @field_validator('delta', mode='before')
    @classmethod
    def _complement_delta_role(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        # 如果 role 键不存在或者值为 None，则设置为 assistant
        if value.get('role', None) is None:
            value['role'] = MessageRole.assistant

        return value

    @field_validator('finish_reason', mode='before')
    @classmethod
    def _enforce_no_null_finish_reason(cls, value: Any) -> Any:
        if value is None:
            return 'not_provided'
        else:
            return value


class PromptTokensDetails(BaseOpenAIModel):
    cached_tokens: int = -1
    audio_tokens: int | None = None
    cache_write_tokens: int | None = None
    image_tokens: int | None = None
    text_tokens: int | None = None


class CompletionTokensDetails(BaseOpenAIModel):
    reasoning_tokens: int = -1
    accepted_prediction_tokens: int = -1
    rejected_prediction_tokens: int = -1
    audio_tokens: int | None = None
    text_tokens: int | None = None


class Usage(BaseOpenAIModel):
    prompt_tokens: int = -1
    completion_tokens: int = -1
    total_tokens: int = -1
    cached_tokens: int | None = None
    prompt_cache_hit_tokens: int | None = None
    prompt_cache_miss_tokens: int | None = None
    prompt_tokens_details: PromptTokensDetails | None = None
    completion_tokens_details: CompletionTokensDetails | None = None


class ChatCompletion(BaseOpenAIModel):
    id: str
    object: Literal['chat.completion']
    created: int
    model: str
    choices: list[Choice]
    usage: Usage | None = None
    service_tier: str | None = None
    system_fingerprint: str | None = None
    metadata: dict[str, str] | None = None


class ChatCompletionChunk(BaseOpenAIModel):
    id: str
    object: Literal['chat.completion.chunk']
    created: int
    model: str
    choices: list[ChunkChoice]
    usage: Usage | None = None
    service_tier: str | None = None
    system_fingerprint: str | None = None


class ChatCompletionDeleted(BaseOpenAIModel):
    id: str
    object: Literal['chat.completion.deleted']
    deleted: bool


class ChatCompletionStoreMessage(MessageContent):
    id: str
    content_parts: list[MessageContentType] | None = Field(default=None)


class ChatCompletionList(BaseOpenAIModel):
    object: Literal['list']
    data: list[ChatCompletion]
    first_id: str | None = None
    last_id: str | None = None
    has_more: bool = False


class ChatCompletionMessageList(BaseOpenAIModel):
    object: Literal['list']
    data: list[ChatCompletionStoreMessage]
    first_id: str | None = None
    last_id: str | None = None
    has_more: bool = False


__all__ = [
    'ChatCompletion',
    'ChatCompletionChunk',
    'ChatCompletionDeleted',
    'ChatCompletionList',
    'ChatCompletionMessageList',
    'ChatCompletionStoreMessage',
]
