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

from pydantic import ValidationError

from src.compat import dump_obj_as
from src.utils import BaseCommonAPI
from src.utils.omega_requests.types import Timeout
from .config import openai_service_config
from .models import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionDeleted,
    ChatCompletionList,
    ChatCompletionMessageList,
    Embeddings,
    File,
    FileContent,
    FileDeleted,
    FileList,
    Message,
    MessageContent,
    ModelList,
    ToolCalls,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.resource import BaseResource
    from src.utils.omega_requests.types import CookieTypes, HeaderTypes, QueryTypes, TimeoutTypes

    type ChatMessage = Message | Iterable[MessageContent]


class OpenAIClient(BaseCommonAPI):
    """openai API 客户端"""

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
        # 剥离尾部斜杠, 避免 URL 拼接产生双斜杠路径 (部分提供商网关无法路由)
        return self._base_url.rstrip('/')

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
        return Timeout(total=300, connect=10, read=60)

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

    @staticmethod
    def _parse_chat_message(message: 'ChatMessage') -> list[MessageContent]:
        """将 message 参数统一解析为 MessageContent 列表"""
        if isinstance(message, Message):
            return message.messages
        if isinstance(message, MessageContent):
            return [message]
        return list(message)

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
                self._parse_chat_message(message),
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
                self._parse_chat_message(message),
                mode='json',
                exclude_none=True,
            ),
            'stream': True,
            **kwargs,
        }

        line_prefix = 'data:'
        eof_target = '[DONE]'
        async for line in self._stream_post_acquire_iter_lines(
                url=url, json=data, headers=self.request_headers, chunk_size=256,
        ):
            if not line or not line.startswith(line_prefix):
                continue
            if not (content := line.removeprefix(line_prefix).strip()) or content == eof_target:
                continue
            try:
                yield ChatCompletionChunk.model_validate_json(content)
            except ValidationError as e:
                # 流中无法解析的 data 行通常是供应商返回的错误信息, 附带原文便于排障
                raise RuntimeError(f'failed to parse chat completion stream line: {content[:200]!r}') from e

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
        received_any_chunk = False
        async for chunk in self.create_chat_completion_using_stream(model=model, message=message, **kwargs):
            received_any_chunk = True
            for choice in chunk.choices:
                if choice.index not in content_map:
                    content_map[choice.index] = [choice.delta]
                else:
                    content_map[choice.index].append(choice.delta)

        if not received_any_chunk:
            # 空响应体的错误响应在流式请求中不产生任何分块, 此处显式抛出异常而非静默返回空列表
            raise RuntimeError('chat completion stream returned no chunks, possibly an empty-body error response')

        contents: list[MessageContent] = []
        for deltas in content_map.values():
            annotations = next((c.annotations for c in reversed(deltas) if c.annotations is not None), None)
            audio = next((c.audio for c in reversed(deltas) if c.audio is not None), None)
            contents.append(MessageContent.model_validate({
                'role': deltas[0].role,
                'content': (
                        [i for c in deltas for i in c.content if isinstance(c.content, list)]
                        or ''.join(c.content for c in deltas if isinstance(c.content, str))
                ),
                'reasoning_content': ''.join(c.reasoning_content for c in deltas),
                'name': deltas[0].name,
                'refusal': ''.join(c.refusal for c in deltas if c.refusal) or None,
                'annotations': annotations,
                'audio': audio,
                'tool_calls': self._merge_tool_calls_chunks(deltas),
                'tool_call_id': deltas[0].tool_call_id,
                'function_call': deltas[0].function_call,
            }))

        return contents

    @staticmethod
    def _merge_tool_calls_chunks(deltas: list[MessageContent]) -> list[ToolCalls] | None:
        """按 index 合并流式响应中的 tool_calls 分片

        流式响应中每个 tool call 的 `id` 与 `function.name` / `custom.name` 仅在首个分片出现,
        `function.arguments` / `custom.input` 按分片增量传输, 需要跨分片拼接还原完整调用
        """
        merged_calls: dict[int, ToolCalls] = {}
        for delta in deltas:
            for tool_call in (delta.tool_calls or []):
                if tool_call.index is not None:
                    index = tool_call.index
                else:
                    # 部分第三方服务分片不带 index, 并入最后一个已合并的调用
                    index = max(merged_calls) if merged_calls else 0

                if index not in merged_calls:
                    merged_calls[index] = tool_call.model_copy(deep=True)
                    continue

                merged = merged_calls[index]
                if tool_call.id is not None:
                    merged.id = tool_call.id
                if tool_call.function is not None:
                    if merged.function is None:
                        merged.function = tool_call.function.model_copy(deep=True)
                    else:
                        if tool_call.function.name is not None:
                            merged.function.name = tool_call.function.name
                        if tool_call.function.arguments is not None:
                            merged.function.arguments = (merged.function.arguments or '') + tool_call.function.arguments
                if tool_call.custom is not None:
                    if merged.custom is None:
                        merged.custom = tool_call.custom.model_copy(deep=True)
                    else:
                        if tool_call.custom.name is not None:
                            merged.custom.name = tool_call.custom.name
                        if tool_call.custom.input is not None:
                            merged.custom.input = (merged.custom.input or '') + tool_call.custom.input

        return list(merged_calls.values()) or None

    async def get_chat_completion(self, completion_id: str) -> ChatCompletion:
        """Get a stored chat completion.

        Only Chat Completions that have been created with the `store` parameter set to `true` will be returned.

        :param completion_id: The ID of the chat completion.
        """
        url = f'{self.base_url}/chat/completions/{completion_id}'
        response = await self._get_resource_as_json(url=url, headers=self.request_headers)
        return ChatCompletion.model_validate(response)

    async def update_chat_completion(
            self,
            completion_id: str,
            metadata: dict[str, str] | None = None,
    ) -> ChatCompletion:
        """Modify a stored chat completion.

        Only Chat Completions that have been created with the `store` parameter set to `true` can be modified.
        Currently, the only supported modification is to update the `metadata` field.

        :param completion_id: The ID of the chat completion.
        :param metadata: Set of 16 key-value pairs that can be attached to an object.
        """
        url = f'{self.base_url}/chat/completions/{completion_id}'
        data = {'metadata': metadata}
        response = await self._post_acquire_as_json(url=url, json=data, headers=self.request_headers)
        return ChatCompletion.model_validate(response)

    async def delete_chat_completion(self, completion_id: str) -> ChatCompletionDeleted:
        """Delete a stored chat completion.

        Only Chat Completions that have been created with the `store` parameter set to `true` can be deleted.

        :param completion_id: The ID of the chat completion to delete.
        """
        url = f'{self.base_url}/chat/completions/{completion_id}'
        response = await self._request_delete(url=url, headers=self.request_headers)
        return ChatCompletionDeleted.model_validate(self._parse_content_as_json(response))

    async def list_chat_completions(
            self,
            *,
            after: str | None = None,
            limit: int | None = None,
            metadata: dict[str, str] | None = None,
            model: str | None = None,
            order: Literal['asc', 'desc'] | None = None,
    ) -> ChatCompletionList:
        """List stored Chat Completions.

        Only Chat Completions that have been stored with the `store` parameter set to `true` will be returned.

        :param after: Identifier for the last chat completion from the previous pagination request.
        :param limit: Number of Chat Completions to retrieve.
        :param metadata: A list of metadata keys to filter the Chat Completions by.
        :param model: The model used to generate the Chat Completions.
        :param order: Sort order for Chat Completions by timestamp. Defaults to `asc`.
        """
        url = f'{self.base_url}/chat/completions'
        params = {}
        if after is not None:
            params['after'] = after
        if limit is not None:
            params['limit'] = limit
        if metadata is not None:
            params.update({f'metadata[{key}]': value for key, value in metadata.items()})
        if model is not None:
            params['model'] = model
        if order is not None:
            params['order'] = order

        response = await self._get_resource_as_json(url=url, params=params, headers=self.request_headers)
        return ChatCompletionList.model_validate(response)

    async def get_chat_completion_messages(
            self,
            completion_id: str,
            *,
            after: str | None = None,
            limit: int | None = None,
            order: Literal['asc', 'desc'] | None = None,
    ) -> ChatCompletionMessageList:
        """Get the messages in a stored chat completion.

        Only Chat Completions that have been created with the `store` parameter set to `true` will be returned.

        :param completion_id: The ID of the chat completion.
        :param after: Identifier for the last message from the previous pagination request.
        :param limit: Number of messages to retrieve.
        :param order: Sort order for messages by timestamp. Defaults to `asc`.
        """
        url = f'{self.base_url}/chat/completions/{completion_id}/messages'
        params = {}
        if after is not None:
            params['after'] = after
        if limit is not None:
            params['limit'] = limit
        if order is not None:
            params['order'] = order

        response = await self._get_resource_as_json(url=url, params=params, headers=self.request_headers)
        return ChatCompletionMessageList.model_validate(response)

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
    'OpenAIClient',
]
