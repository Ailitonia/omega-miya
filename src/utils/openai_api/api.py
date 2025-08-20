"""
@Author         : Ailitonia
@Date           : 2025/2/11 10:16:06
@FileName       : api.py
@Project        : omega-miya
@Description    : openai API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Literal, Self

from src.compat import dump_obj_as
from src.utils import BaseCommonAPI
from .config import openai_service_config
from .models import (
    ChatCompletion,
    ChatCompletionChunk,
    Embeddings,
    File,
    FileContent,
    FileDeleted,
    FileList,
    Message,
    MessageContent,
    ModelList,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.resource import BaseResource
    from src.utils.omega_requests.types import CookieTypes, HeaderTypes, QueryTypes, Timeout, TimeoutTypes

    type ChatMessage = Message | Iterable[MessageContent]


class BaseOpenAIClient(BaseCommonAPI):
    """openai API 客户端基类"""

    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url

    @staticmethod
    def get_available_services() -> list[tuple[str, str]]:
        """获取可用的已配置服务"""
        return [
            (service.name, model)
            for service in openai_service_config.openai_service_config
            for model in service.available_models
        ]

    @classmethod
    def init_from_config(cls, service_name: str, model_name: str) -> Self:
        """从配置文件中初始化"""
        if not (service_map := openai_service_config.service_map) or (service_name not in service_map):
            raise ValueError(f'openai service {service_name!r} not config')

        if model_name not in service_map[service_name].available_models:
            raise ValueError(f'openai service {service_name!r} not provide model {model_name!r}')

        return cls(
            api_key=service_map[service_name].api_key,
            base_url=service_map[service_name].base_url,
        )

    @classmethod
    def init_default_from_config(cls) -> Self:
        """从配置文件中初始化, 使用第一个可用配置项"""
        if not (available_services := cls.get_available_services()):
            raise RuntimeError('no openai service has been config')
        return cls.init_from_config(*available_services[0])

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
    def _get_default_headers(cls) -> dict[str, str]:
        return {'Content-Type': 'application/json'}

    @classmethod
    def _get_default_cookies(cls) -> dict[str, str]:
        return {}

    @classmethod
    def _get_default_timeout(cls) -> 'Timeout':
        timeout = cls._get_omega_requests_default_timeout()
        timeout.total = 300
        timeout.connect = 10
        timeout.read = 60
        return timeout

    @classmethod
    async def get_any_resource_as_bytes(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> bytes:
        """请求任意来源资源内容"""
        headers = cls._get_omega_requests_default_headers() if headers is None else headers
        cookies = {} if cookies is None else cookies

        return await cls._get_resource_as_bytes(
            url=url, params=params,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )

    async def create_chat_completion_normal(
            self,
            model: str,
            message: 'ChatMessage',
            **kwargs,
    ) -> 'ChatCompletion':
        """Creates a model response for the given chat conversation.

        Parameter support can differ depending on the model used to generate the response,
        particularly for newer reasoning models. Parameters that are only supported for
        reasoning models are noted below.

        :param model: ID of the model to use.
        :param message: A list of messages comprising the conversation so far.
        """
        kwargs.pop('stream', None)  # 移除流式会话参数
        url = f'{self.base_url}/chat/completions'
        data = {
            'model': model,
            'messages': dump_obj_as(
                list[MessageContent],
                message.messages if isinstance(message, Message) else message,
                mode='json',
                exclude_none=True,
            ),
            'stream': False,
            **kwargs,
        }
        response = await self._post_acquire_as_json(url=url, json=data, headers=self.request_headers)
        return ChatCompletion.model_validate(response)

    async def create_chat_completion_using_stream(
            self,
            model: str,
            message: 'ChatMessage',
            **kwargs,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Creates a model response for the given chat conversation. Using stream mode.

        Parameter support can differ depending on the model used to generate the response,
        particularly for newer reasoning models. Parameters that are only supported for
        reasoning models are noted below.

        :param model: ID of the model to use.
        :param message: A list of messages comprising the conversation so far.
        """
        kwargs.pop('stream', None)  # 移除流式会话参数
        url = f'{self.base_url}/chat/completions'
        data = {
            'model': model,
            'messages': dump_obj_as(
                list[MessageContent],
                message.messages if isinstance(message, Message) else message,
                mode='json',
                exclude_none=True,
            ),
            'stream': True,
            **kwargs,
        }

        line_prefix = r'data: '
        eof_target = r'[DONE]'
        async for line in self._stream_post_acquire_iter_lines(
                url=url, json=data, headers=self.request_headers, chunk_size=256,
        ):
            if line and line.startswith(line_prefix):
                if (content := line.removeprefix(line_prefix).strip()) != eof_target:
                    yield ChatCompletionChunk.model_validate_json(content)

    async def create_chat_completion(
            self,
            model: str,
            message: 'ChatMessage',
            stream: bool = True,
            **kwargs,
    ) -> list[MessageContent]:
        """Creates a model response for the given chat conversation.

        Parameter support can differ depending on the model used to generate the response,
        particularly for newer reasoning models. Parameters that are only supported for
        reasoning models are noted below.

        :param model: ID of the model to use.
        :param message: A list of messages comprising the conversation so far.
        :param stream: Using stream mode.
        """
        if not stream:
            chat = await self.create_chat_completion_normal(model=model, message=message, **kwargs)
            return [x.message for x in chat.choices]

        content_map: dict[int, list[MessageContent]] = {}
        async for chunk in self.create_chat_completion_using_stream(model=model, message=message, **kwargs):
            for choice in chunk.choices:
                if choice.index not in content_map:
                    content_map[choice.index] = [choice.delta]
                else:
                    content_map[choice.index].append(choice.delta)

        return [
            MessageContent.model_validate({
                'role': x[0].role,
                'content': (
                        [i for c in x for i in c.content if isinstance(c.content, list)]
                        or ''.join(c.content for c in x if isinstance(c.content, str))
                ),
                'reasoning_content': ''.join(c.reasoning_content for c in x),
                'name': x[0].name,
                'refusal': x[0].refusal,
                'audio': x[0].audio,
                'tool_calls': x[0].tool_calls,
                'tool_call_id': x[0].tool_call_id,
                'function_call': x[0].function_call,
            })
            for x in content_map.values()
        ]

    async def create_embeddings(
            self,
            input_: str | list[str],
            model: str,
            *,
            encoding_format: Literal['float', 'base64'] = 'float',
            **kwargs,
    ) -> Embeddings:
        """Creates an embedding vector representing the input text."""
        url = f'{self.base_url}/embeddings'
        data = {
            'input': input_,
            'model': model,
            'encoding_format': encoding_format,
            **kwargs,
        }
        response = await self._post_acquire_as_json(url=url, json=data, headers=self.request_headers)
        return Embeddings.model_validate(response)

    async def list_models(self) -> ModelList:
        """Lists the currently available models, and provides basic information about each one."""
        url = f'{self.base_url}/models'
        response = await self._get_resource_as_json(url=url, headers=self.request_headers)
        return ModelList.model_validate(response)

    async def upload_file(
            self,
            file: 'BaseResource',
            purpose: str = 'user_data',
            *,
            timeout: 'TimeoutTypes' = 300,
    ) -> File:
        """Upload a file that can be used across various endpoints.

        :param file: The File to be uploaded
        :param purpose: The intended purpose of the uploaded file. One of:
            `assistants`: Used in the Assistants API.
            `batch`: Used in the Batch API.
            `fine-tune`: Used for fine-tuning.
            `vision`: Images used for vision fine-tuning.
            `user_data`: Flexible file type for any purpose.
            `evals`: Used for eval data sets.
            `file-extract`: moonshot/kimi only support this purpose.
        :param timeout: Timeout threshold.
        """
        url = f'{self.base_url}/files'
        headers = {'Authorization': f'Bearer {self._api_key}'}

        with file.open('rb') as f:
            files = {
                'file': (file.name, f, 'application/octet-stream'),
                'purpose': (None, purpose, 'text/plain')
            }
            response = await self._post_acquire_as_json(
                url=url,
                files=files,
                headers=headers,
                timeout=timeout,
            )
        return File.model_validate(response)

    async def list_files(
            self,
            purpose: str | None = None,
            limit: int | None = None,
            order: Literal['created_at', 'asc', 'desc'] | None = None,
            after: str | None = None,
    ) -> FileList:
        """Returns a list of files."""
        url = f'{self.base_url}/files'
        params = {}
        if purpose is not None:
            params['purpose'] = purpose
        if limit is not None:
            params['limit'] = limit
        if order is not None:
            params['order'] = order
        if after is not None:
            params['after'] = after

        response = await self._get_resource_as_json(url=url, params=params, headers=self.request_headers)
        return FileList.model_validate(response)

    async def retrieve_file(self, file_id: str) -> File:
        """Returns information about a specific file."""
        url = f'{self.base_url}/files/{file_id}'
        response = await self._get_resource_as_json(url=url, headers=self.request_headers)
        return File.model_validate(response)

    async def retrieve_file_content(self, file_id: str) -> FileContent:
        """Returns the contents of the specified file."""
        url = f'{self.base_url}/files/{file_id}/content'
        response = await self._get_resource_as_json(url=url, headers=self.request_headers)
        return FileContent.model_validate(response)

    async def delete_file(self, file_id: str) -> FileDeleted:
        """Delete a file."""
        url = f'{self.base_url}/files/{file_id}'
        response = await self._request_delete(url=url, headers=self.request_headers)
        return FileDeleted.model_validate(self._parse_content_as_json(response))


__all__ = [
    'BaseOpenAIClient',
]
