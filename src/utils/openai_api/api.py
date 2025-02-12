"""
@Author         : Ailitonia
@Date           : 2025/2/11 10:16:06
@FileName       : api.py
@Project        : omega-miya
@Description    : openai API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Iterable

from src.compat import dump_obj_as
from src.utils import BaseCommonAPI
from .models import ChatCompletion, Message, MessageContent


class BaseOpenAIClient(BaseCommonAPI):
    """openai API 客户端基类"""

    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def request_headers(self) -> dict[str, str]:
        headers = self._get_default_headers()
        headers['Authorization'] = f'Bearer {self._api_key}'
        return headers

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        raise NotImplementedError

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        raise NotImplementedError

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> dict[str, str]:
        return {'Content-Type': 'application/json'}

    @classmethod
    def _get_default_cookies(cls) -> dict[str, str]:
        return {}

    async def create_chat_completion(
            self,
            model: str,
            message: 'Message' | Iterable['MessageContent'],
            **kwargs,
    ) -> 'ChatCompletion':
        """Creates a model response for the given chat conversation.

        Parameter support can differ depending on the model used to generate the response,
        particularly for newer reasoning models. Parameters that are only supported for
        reasoning models are noted below.

        :param model: ID of the model to use.
        :param message: A list of messages comprising the conversation so far.
        """
        url = f'{self.base_url}/chat/completions'
        data = {
            'model': model,
            'messages': dump_obj_as(
                list[MessageContent],
                message.messages if isinstance(message, Message) else message,
                mode='json',
                exclude_none=True,
            ),
            **kwargs,
        }
        response = await self._post_json(url=url, json=data, headers=self.request_headers)
        return ChatCompletion.model_validate(response)


__all__ = [
    'BaseOpenAIClient',
]
