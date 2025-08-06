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
from .message import MessageContent


class Choice(BaseOpenAIModel):
    index: int
    message: MessageContent
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


class PromptTokensDetails(BaseOpenAIModel):
    cached_tokens: int


class CompletionTokensDetails(BaseOpenAIModel):
    reasoning_tokens: int = -1
    accepted_prediction_tokens: int = -1
    rejected_prediction_tokens: int = -1


class Usage(BaseOpenAIModel):
    prompt_tokens: int = -1
    completion_tokens: int = -1
    total_tokens: int = -1
    prompt_tokens_details: PromptTokensDetails | None = None
    completion_tokens_details: CompletionTokensDetails | None = None


class ChatCompletion(BaseOpenAIModel):
    id: str
    object: Literal['chat.completion']
    created: int
    model: str
    choices: list[Choice]
    usage: Usage
    service_tier: str | None = None
    system_fingerprint: str | None = None


__all__ = [
    'ChatCompletion',
]
