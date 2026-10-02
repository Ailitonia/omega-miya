"""
@Author         : Ailitonia
@Date           : 2026/9/19 16:06
@FileName       : test_005_openai_api
@Project        : omega-miya
@Description    : openai api 单元测试(主体经合成载荷/mock 覆盖; TestRealAPI 为 OPENAI_API_REAL_TEST 门禁的真实 API 验证)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
import json
from contextlib import contextmanager
from io import BytesIO
from typing import TYPE_CHECKING, Any

import pytest
from PIL import Image
from pydantic import BaseModel

from tests.test_003_web.helpers import require_env_flag

if TYPE_CHECKING:
    from pathlib import Path

    from src.utils.openai_api import OpenAIClient

_SERVICE_NAME = 'test_service'
_SERVICE_KEY = 'sk-test-key'
_SERVICE_BASE = 'https://api.test.local/v1'
_SERVICE_MODELS = ['test-model', 'test-model-mini']

_CHAT_COMPLETION_PAYLOAD: dict[str, Any] = {
    'id': 'chatcmpl-test',
    'object': 'chat.completion',
    'created': 1694268190,
    'model': 'test-model',
    'choices': [
        {
            'index': 0,
            'message': {'role': 'assistant', 'content': 'hello', 'refusal': None},
            'logprobs': None,
            'finish_reason': 'stop',
        }
    ],
    'usage': {'prompt_tokens': 9, 'completion_tokens': 2, 'total_tokens': 11},
}


def _chunk(delta: dict[str, Any], index: int = 0, finish_reason: str | None = None) -> dict[str, Any]:
    return {
        'id': 'chatcmpl-test',
        'object': 'chat.completion.chunk',
        'created': 1694268190,
        'model': 'test-model',
        'choices': [{'index': index, 'delta': delta, 'logprobs': None, 'finish_reason': finish_reason}],
    }


def _sse_lines(chunks: list[dict[str, Any]]) -> list[str]:
    lines = ['data: ' + json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
    lines.insert(1, '')
    return lines + ['data: [DONE]']


async def _make_chat_call(client: 'OpenAIClient', **kwargs):
    """以罐头入参(固定模型与单条 user 消息)发起聚合补全调用"""
    return await client.create_chat_completion(
        model='test-model', message=[{'role': 'user', 'content': 'hi'}], **kwargs
    )


@pytest.fixture(scope='module')
def openai_api():
    from src.utils.openai_api import api as api_module

    return api_module


@pytest.fixture
def configured_service(monkeypatch: pytest.MonkeyPatch):
    """向 openai 服务配置注入两个合成服务(覆盖多服务/多模型展开与默认项回退)"""
    from src.utils.openai_api.config import Service, openai_service_config

    services = [
        Service(
            name=_SERVICE_NAME,
            api_key=_SERVICE_KEY,
            base_url=_SERVICE_BASE,
            available_models=_SERVICE_MODELS,
        ),
        Service(
            name='second_service',
            api_key='sk-second-key',
            base_url='https://second.test.local/v1',
            available_models=['other-model'],
        ),
    ]
    monkeypatch.setattr(openai_service_config, 'openai_service_config', services)
    return openai_service_config


@pytest.fixture
def client(configured_service, openai_api) -> 'OpenAIClient':
    return openai_api.OpenAIClient(api_key=_SERVICE_KEY, base_url=_SERVICE_BASE)


@pytest.fixture
def capture_post(monkeypatch: pytest.MonkeyPatch, openai_api) -> dict[str, Any]:
    """mock _post_acquire_as_json, 捕获请求参数并返回罐头 ChatCompletion"""
    captured: dict[str, Any] = {}

    async def fake_post(self_, url, params=None, payload=None, **kwargs):
        captured.update({'url': url, 'params': params, 'kwargs': kwargs})
        return captured.get('response', _CHAT_COMPLETION_PAYLOAD)

    monkeypatch.setattr(openai_api.OpenAIClient, '_post_acquire_as_json', fake_post)
    return captured


@pytest.fixture
def capture_get(monkeypatch: pytest.MonkeyPatch, openai_api) -> dict[str, Any]:
    """mock _get_resource_as_json, 捕获请求参数并按 url 返回罐头 JSON"""
    captured: dict[str, Any] = {}

    async def fake_get(self_, url, params=None, **kwargs):
        captured.update({'url': url, 'params': params, 'kwargs': kwargs})
        if url.endswith('/models'):
            return {'object': 'list', 'data': [{'id': 'test-model', 'object': 'model', 'owned_by': 'test'}]}
        if url.endswith('/files'):
            return {'object': 'list', 'data': [{
                'id': 'file-1', 'object': 'file', 'bytes': 12, 'created_at': 1,
                'filename': 'a.txt', 'purpose': 'user_data',
            }]}
        if url.endswith('/files/file-1/content'):
            return {'content': 'abc', 'file_type': 'text/plain', 'filename': 'a.txt', 'title': 'a', 'type': 'file'}
        if url.endswith('/files/file-1'):
            return {'id': 'file-1', 'object': 'file', 'bytes': 12, 'created_at': 1,
                    'filename': 'a.txt', 'purpose': 'user_data'}
        if url.endswith('/chat/completions/chatcmpl-1/messages'):
            return {'object': 'list', 'data': [
                {'id': 'chatcmpl-1-0', 'role': 'user', 'content': 'hi', 'name': None, 'content_parts': None},
            ], 'first_id': 'chatcmpl-1-0', 'last_id': 'chatcmpl-1-0', 'has_more': False}
        if url.endswith('/chat/completions/chatcmpl-1'):
            return _CHAT_COMPLETION_PAYLOAD
        if url.endswith('/chat/completions'):
            return {
                'object': 'list',
                'data': [_CHAT_COMPLETION_PAYLOAD],
                'first_id': 'chatcmpl-test',
                'last_id': 'chatcmpl-test',
                'has_more': False,
            }
        return {'ok': True}

    monkeypatch.setattr(openai_api.OpenAIClient, '_get_resource_as_json', fake_get)
    return captured


@pytest.fixture
def capture_delete(monkeypatch: pytest.MonkeyPatch, openai_api) -> dict[str, Any]:
    """mock _request_delete, 捕获请求参数并返回按 'payload' 键构造的合成 Response"""
    from nonebot.drivers import Response

    captured: dict[str, Any] = {}

    async def fake_delete(self_, url, params=None, **kwargs):
        captured.update({'url': url, 'kwargs': kwargs})
        return Response(200, content=json.dumps(captured['payload']).encode())

    monkeypatch.setattr(openai_api.OpenAIClient, '_request_delete', fake_delete)
    return captured


@pytest.fixture
def stream_lines_factory(monkeypatch: pytest.MonkeyPatch, openai_api):
    """mock _stream_post_acquire_iter_lines 为同步产出预置 SSE 行的异步生成器"""

    def _install(lines: list[str]) -> dict[str, Any]:
        captured: dict[str, Any] = {}

        def fake_stream(self_, url, params=None, **kwargs):
            captured.update({'url': url, 'kwargs': kwargs})

            async def _gen():
                for line in lines:
                    yield line

            return _gen()

        monkeypatch.setattr(openai_api.OpenAIClient, '_stream_post_acquire_iter_lines', fake_stream)
        return captured

    return _install


class TestClientInit:

    def test_get_available_services(self, configured_service, openai_api):
        assert openai_api.OpenAIClient.get_available_services() == [
            (_SERVICE_NAME, 'test-model'),
            (_SERVICE_NAME, 'test-model-mini'),
            ('second_service', 'other-model'),
        ]

    def test_init_from_config(self, configured_service, openai_api):
        client = openai_api.OpenAIClient.init_from_config(service_name=_SERVICE_NAME, model_name='test-model')
        assert client.base_url == _SERVICE_BASE

    def test_init_from_config_with_unknown_service(self, configured_service, openai_api):
        with pytest.raises(ValueError, match='not config'):
            openai_api.OpenAIClient.init_from_config(service_name='no_such', model_name='test-model')

    def test_init_from_config_with_unavailable_model(self, configured_service, openai_api):
        with pytest.raises(ValueError, match='not provide model'):
            openai_api.OpenAIClient.init_from_config(service_name=_SERVICE_NAME, model_name='gpt-4o')

    def test_init_default_from_config_without_service(self, monkeypatch: pytest.MonkeyPatch, openai_api):
        from src.utils.openai_api.config import openai_service_config

        monkeypatch.setattr(openai_service_config, 'openai_service_config', [])
        with pytest.raises(RuntimeError, match='no openai service'):
            openai_api.OpenAIClient.init_default_from_config()

    def test_request_headers(self, client: 'OpenAIClient'):
        headers = client.request_headers
        assert headers['Authorization'] == f'Bearer {_SERVICE_KEY}'
        assert headers['Content-Type'] == 'application/json'


class TestCreateChatCompletion:

    async def test_normal_payload_and_parse(self, client: 'OpenAIClient', capture_post: dict[str, Any]):
        from src.utils.openai_api.models import ChatCompletion, MessageContent

        result = await client.create_chat_completion_normal(
            model='test-model',
            message=MessageContent.user().set_plain_text('hi'),
            temperature=0.5,
        )

        assert isinstance(result, ChatCompletion)
        assert result.choices[0].message.content == 'hello'
        assert capture_post['url'] == f'{_SERVICE_BASE}/chat/completions'
        payload = capture_post['kwargs']['json']
        assert payload['model'] == 'test-model'
        assert payload['stream'] is False
        assert payload['temperature'] == 0.5
        assert payload['messages'] == [{'role': 'user', 'content': 'hi'}]

    async def test_normal_strips_stream_kwarg(self, client: 'OpenAIClient', capture_post: dict[str, Any]):
        from src.utils.openai_api.models import MessageContent

        await client.create_chat_completion_normal(
            model='test-model',
            message=[MessageContent.user().set_plain_text('hi')],
            stream=True,
        )
        # 外部误传 stream 参数时应被剥离, 始终以非流式请求
        assert capture_post['kwargs']['json']['stream'] is False

    async def test_normal_with_message_object(self, client: 'OpenAIClient', capture_post: dict[str, Any]):
        from src.utils.openai_api.models import Message, MessageContent

        message = Message()
        message.set_prefix_content('you are helpful')
        message.add_content(MessageContent.user().set_plain_text('hi'))

        await client.create_chat_completion_normal(model='test-model', message=message)
        messages = capture_post['kwargs']['json']['messages']
        assert [x['role'] for x in messages] == ['system', 'user']
        # reasoning_content 为扩展字段, 请求序列化时应被排除
        assert all('reasoning_content' not in x for x in messages)

    async def test_stream_sse_parsing(self, client: 'OpenAIClient', stream_lines_factory):
        captured = stream_lines_factory(_sse_lines([
            _chunk({'role': 'assistant', 'content': ''}),
            _chunk({'content': '你好'}),
            _chunk({'content': ' world'}, finish_reason='stop'),
        ]))

        chunks = [chunk async for chunk in client.create_chat_completion_using_stream(
            model='test-model', message=[{'role': 'user', 'content': 'hi'}]
        )]

        assert captured['url'] == f'{_SERVICE_BASE}/chat/completions'
        assert len(chunks) == 3
        assert chunks[1].choices[0].delta.content == '你好'
        assert chunks[2].choices[0].finish_reason == 'stop'
        assert chunks[0].object == 'chat.completion.chunk'

    async def test_stream_sse_data_prefix_without_space(self, client: 'OpenAIClient', stream_lines_factory):
        # 兼容不带空格前缀的 data: 行(部分第三方兼容服务), data:[DONE] 同样不带空格
        lines = ['data:' + json.dumps(_chunk({'content': 'x'}), ensure_ascii=False), 'data:[DONE]']
        stream_lines_factory(lines)

        chunks = [chunk async for chunk in client.create_chat_completion_using_stream(
            model='test-model', message=[{'role': 'user', 'content': 'hi'}]
        )]
        assert len(chunks) == 1
        assert chunks[0].choices[0].delta.content == 'x'

    async def test_stream_malformed_data_line_raises(self, client: 'OpenAIClient', stream_lines_factory):
        # 流中无法解析的 data 行(如供应商返回的错误体)应抛出带原文上下文的 RuntimeError
        stream_lines_factory(['data: {"error": {"message": "bad request"}}'])

        with pytest.raises(RuntimeError, match='failed to parse chat completion stream line'):
            async for _ in client.create_chat_completion_using_stream(
                    model='test-model', message=[{'role': 'user', 'content': 'hi'}]
            ):
                pass

    async def test_stream_with_usage_only_tail_chunk(self, client: 'OpenAIClient', stream_lines_factory):
        # stream_options.include_usage 的末片 choices 为空数组
        lines = _sse_lines([_chunk({'content': 'x'})])[:-1]
        lines.append('data: ' + json.dumps({
            'id': 'chatcmpl-test', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'test-model',
            'choices': [], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
        }))
        lines.append('data: [DONE]')
        stream_lines_factory(lines)

        chunks = [chunk async for chunk in client.create_chat_completion_using_stream(
            model='test-model', message=[{'role': 'user', 'content': 'hi'}]
        )]
        assert len(chunks) == 2
        assert chunks[-1].usage is not None
        assert chunks[-1].usage.total_tokens == 2

    async def test_aggregate_content_and_reasoning(self, client: 'OpenAIClient', stream_lines_factory):
        captured = stream_lines_factory(_sse_lines([
            _chunk({'role': 'assistant', 'content': ''}, finish_reason=None),
            _chunk({'reasoning_content': 'let me '}),
            _chunk({'reasoning_content': 'think'}),
            _chunk({'content': 'Hello'}),
            _chunk({'content': ' world'}, finish_reason='stop'),
        ]))

        result = await _make_chat_call(client)

        assert captured['kwargs']['json']['stream'] is True
        assert len(result) == 1
        assert result[0].role == 'assistant'
        assert result[0].content == 'Hello world'
        assert result[0].reasoning_content == 'let me think'

    async def test_aggregate_refusal_and_audio_annotations(
            self,
            client: 'OpenAIClient',
            stream_lines_factory,
    ):
        audio_tail = {'id': 'audio-2', 'expires_at': 2, 'data': 'd2', 'transcript': 't2'}
        stream_lines_factory(_sse_lines([
            _chunk({'role': 'assistant', 'content': ''}),
            _chunk({'refusal': 'cannot '}),
            _chunk({'refusal': 'help'}),
            _chunk({'audio': {'id': 'audio-1', 'expires_at': 1, 'data': 'd1', 'transcript': 't1'}}),
            _chunk({'audio': audio_tail}),
            _chunk({
                'annotations': [{'type': 'url_citation',
                                 'url_citation': {'end_index': 3, 'start_index': 0, 'title': 't',
                                                  'url': 'https://e.c'}}]
            }, finish_reason='stop'),
        ]))

        result = await _make_chat_call(client)

        assert result[0].refusal == 'cannot help'
        # audio/annotations 取末个非空分片
        assert result[0].audio is not None
        assert result[0].audio.id == 'audio-2'
        assert result[0].annotations is not None
        assert result[0].annotations[0].url_citation.title == 't'

    async def test_aggregate_tool_calls_fragments(self, client: 'OpenAIClient', stream_lines_factory):
        stream_lines_factory(_sse_lines([
            _chunk({'role': 'assistant', 'content': ''}),
            _chunk({'tool_calls': [{'index': 0, 'id': 'call_1', 'type': 'function',
                                    'function': {'name': 'get_weather', 'arguments': ''}}]}),
            _chunk({'tool_calls': [{'index': 0, 'function': {'arguments': '{"city":'}}]}),
            _chunk({'tool_calls': [{'index': 0, 'function': {'arguments': ' "SF"}'}}]}, finish_reason='tool_calls'),
        ]))

        result = await _make_chat_call(client)

        tool_calls = result[0].tool_calls
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].id == 'call_1'
        assert tool_calls[0].function is not None
        assert tool_calls[0].function.name == 'get_weather'
        assert json.loads(tool_calls[0].function.arguments or '') == {'city': 'SF'}

    async def test_aggregate_parallel_tool_calls(self, client: 'OpenAIClient', stream_lines_factory):
        stream_lines_factory(_sse_lines([
            _chunk({'role': 'assistant', 'content': ''}),
            _chunk({'tool_calls': [{'index': 0, 'id': 'c0', 'type': 'function',
                                    'function': {'name': 'f0', 'arguments': '{"i":'}}]}),
            _chunk({'tool_calls': [{'index': 1, 'id': 'c1', 'type': 'function',
                                    'function': {'name': 'f1', 'arguments': ''}}]}),
            _chunk({'tool_calls': [
                {'index': 0, 'function': {'arguments': ' 0}'}},
                {'index': 1, 'function': {'arguments': '{"j": 1}'}},
            ]}, finish_reason='tool_calls'),
        ]))

        result = await _make_chat_call(client)

        tool_calls = sorted(result[0].tool_calls or [], key=lambda x: x.index or 0)
        assert len(tool_calls) == 2
        assert tool_calls[0].id == 'c0'
        assert json.loads(tool_calls[0].function.arguments or '') == {'i': 0}
        assert tool_calls[1].id == 'c1'
        assert json.loads(tool_calls[1].function.arguments or '') == {'j': 1}

    async def test_aggregate_tool_calls_without_index(self, client: 'OpenAIClient', stream_lines_factory):
        # 部分第三方服务分片不带 index, 应回退为按出现顺序合并
        stream_lines_factory(_sse_lines([
            _chunk({'role': 'assistant', 'content': ''}),
            _chunk({'tool_calls': [{'id': 'cx', 'type': 'function',
                                    'function': {'name': 'fx', 'arguments': '{"a":'}}]}),
            _chunk({'tool_calls': [{'function': {'arguments': ' 1}'}}]}, finish_reason='tool_calls'),
        ]))

        result = await _make_chat_call(client)

        tool_calls = result[0].tool_calls
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].id == 'cx'
        assert json.loads(tool_calls[0].function.arguments or '') == {'a': 1}

    async def test_aggregate_custom_tool_calls_fragments(self, client: 'OpenAIClient', stream_lines_factory):
        # custom 类型 tool call 的 custom.input 分片同样需要跨分片拼接
        stream_lines_factory(_sse_lines([
            _chunk({'role': 'assistant', 'content': ''}),
            _chunk({'tool_calls': [{'index': 0, 'id': 'call_c1', 'type': 'custom',
                                    'custom': {'name': 'run_sql', 'input': 'SELECT'}}]}),
            _chunk({'tool_calls': [{'index': 0, 'custom': {'input': ' * FROM t'}}]}, finish_reason='tool_calls'),
        ]))

        result = await _make_chat_call(client)

        tool_calls = result[0].tool_calls
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].id == 'call_c1'
        assert tool_calls[0].type == 'custom'
        assert tool_calls[0].custom is not None
        assert tool_calls[0].custom.name == 'run_sql'
        assert tool_calls[0].custom.input == 'SELECT * FROM t'

    async def test_aggregate_multiple_choices(self, client: 'OpenAIClient', stream_lines_factory):
        stream_lines_factory(_sse_lines([
            _chunk({'role': 'assistant', 'content': 'first'}, index=0),
            _chunk({'role': 'assistant', 'content': 'second'}, index=1),
            _chunk({'content': ' /more'}, index=0, finish_reason='stop'),
            _chunk({}, index=1, finish_reason='stop'),
        ]))

        result = await _make_chat_call(client)

        assert len(result) == 2
        assert result[0].content == 'first /more'
        assert result[1].content == 'second'

    async def test_aggregate_empty_stream_raises(self, client: 'OpenAIClient', stream_lines_factory):
        # 空响应体的错误响应在流式请求中不产生任何分块, 聚合层应抛出带上下文的异常而非静默返回空列表
        stream_lines_factory([])
        with pytest.raises(RuntimeError, match='no chunks'):
            await _make_chat_call(client)

    async def test_non_stream_returns_choice_messages(self, client: 'OpenAIClient', capture_post: dict[str, Any]):
        result = await _make_chat_call(client, stream=False)
        assert len(result) == 1
        assert result[0].content == 'hello'
        assert capture_post['kwargs']['json']['stream'] is False


class TestOtherEndpoints:

    async def test_create_embeddings(self, client: 'OpenAIClient', capture_post: dict[str, Any]):
        from src.utils.openai_api.models import Embeddings

        capture_post['response'] = {
            'object': 'list', 'model': 'embedding-model',
            'data': [{'object': 'embedding', 'embedding': [0.1, 0.2], 'index': 0}],
            'usage': {'prompt_tokens': 1, 'completion_tokens': 0, 'total_tokens': 1},
        }
        result = await client.create_embeddings(input_=['a', 'b'], model='embedding-model')

        assert isinstance(result, Embeddings)
        assert capture_post['url'] == f'{_SERVICE_BASE}/embeddings'
        payload = capture_post['kwargs']['json']
        assert payload['input'] == ['a', 'b']
        assert payload['model'] == 'embedding-model'
        assert payload['encoding_format'] == 'float'

    async def test_list_models(self, client: 'OpenAIClient', capture_get: dict[str, Any]):
        from src.utils.openai_api.models import ModelList

        result = await client.list_models()

        assert isinstance(result, ModelList)
        assert result.data[0].id == 'test-model'
        assert capture_get['url'] == f'{_SERVICE_BASE}/models'

    async def test_list_files_with_params(self, client: 'OpenAIClient', capture_get: dict[str, Any]):
        from src.utils.openai_api.models import FileList

        result = await client.list_files(purpose='user_data', limit=10, order='desc', after='file-0')

        assert isinstance(result, FileList)
        assert capture_get['url'] == f'{_SERVICE_BASE}/files'
        assert capture_get['params'] == {'purpose': 'user_data', 'limit': 10, 'order': 'desc', 'after': 'file-0'}

    async def test_list_files_without_params(self, client: 'OpenAIClient', capture_get: dict[str, Any]):
        await client.list_files()
        assert capture_get['params'] == {}

    async def test_retrieve_file_and_content(self, client: 'OpenAIClient', capture_get: dict[str, Any]):
        await client.retrieve_file('file-1')
        assert capture_get['url'] == f'{_SERVICE_BASE}/files/file-1'

        await client.retrieve_file_content('file-1')
        assert capture_get['url'] == f'{_SERVICE_BASE}/files/file-1/content'

    async def test_delete_file(self, client: 'OpenAIClient', capture_delete: dict[str, Any]):
        from src.utils.openai_api.models import FileDeleted

        capture_delete['payload'] = {'id': 'file-1', 'object': 'file.deleted', 'deleted': True}

        result = await client.delete_file('file-1')

        assert isinstance(result, FileDeleted)
        assert result.deleted is True
        assert capture_delete['url'] == f'{_SERVICE_BASE}/files/file-1'

    async def test_upload_file(self, tmp_path: 'Path', client: 'OpenAIClient', capture_post: dict[str, Any]):
        from src.resource import AnyResource
        from src.utils.openai_api.models import File

        capture_post['response'] = {'id': 'file-1', 'object': 'file', 'bytes': 3, 'created_at': 1,
                                    'filename': 'a.txt', 'purpose': 'user_data'}

        resource_file = tmp_path / 'a.txt'
        resource_file.write_bytes(b'abc')
        result = await client.upload_file(file=AnyResource(tmp_path, 'a.txt'), purpose='user_data')

        assert isinstance(result, File)
        assert result.id == 'file-1'
        assert capture_post['url'] == f'{_SERVICE_BASE}/files'
        files = capture_post['kwargs']['files']
        assert files['purpose'] == (None, 'user_data', 'text/plain')
        assert files['file'][0] == 'a.txt'

    async def test_get_chat_completion(self, client: 'OpenAIClient', capture_get: dict[str, Any]):
        from src.utils.openai_api.models import ChatCompletion

        result = await client.get_chat_completion('chatcmpl-1')
        assert isinstance(result, ChatCompletion)
        assert capture_get['url'] == f'{_SERVICE_BASE}/chat/completions/chatcmpl-1'

    async def test_update_chat_completion(self, client: 'OpenAIClient', capture_post: dict[str, Any]):
        await client.update_chat_completion('chatcmpl-1', metadata={'k': 'v'})
        assert capture_post['url'] == f'{_SERVICE_BASE}/chat/completions/chatcmpl-1'
        assert capture_post['kwargs']['json'] == {'metadata': {'k': 'v'}}

    async def test_delete_chat_completion(self, client: 'OpenAIClient', capture_delete: dict[str, Any]):
        from src.utils.openai_api.models import ChatCompletionDeleted

        capture_delete['payload'] = {'id': 'chatcmpl-1', 'object': 'chat.completion.deleted', 'deleted': True}

        result = await client.delete_chat_completion('chatcmpl-1')
        assert isinstance(result, ChatCompletionDeleted)
        assert result.deleted is True

    async def test_list_chat_completions(self, client: 'OpenAIClient', capture_get: dict[str, Any]):
        from src.utils.openai_api.models import ChatCompletionList

        result = await client.list_chat_completions(
            after='chatcmpl-0', limit=5, metadata={'k': 'v'}, model='test-model', order='desc'
        )
        assert isinstance(result, ChatCompletionList)
        assert result.has_more is False
        assert capture_get['url'] == f'{_SERVICE_BASE}/chat/completions'
        assert capture_get['params'] == {
            'after': 'chatcmpl-0', 'limit': 5, 'metadata[k]': 'v', 'model': 'test-model', 'order': 'desc',
        }

    async def test_get_chat_completion_messages(self, client: 'OpenAIClient', capture_get: dict[str, Any]):
        from src.utils.openai_api.models import ChatCompletionMessageList

        result = await client.get_chat_completion_messages('chatcmpl-1', after='m-0', limit=10, order='asc')

        assert isinstance(result, ChatCompletionMessageList)
        assert capture_get['url'] == f'{_SERVICE_BASE}/chat/completions/chatcmpl-1/messages'
        assert capture_get['params'] == {'after': 'm-0', 'limit': 10, 'order': 'asc'}


class TestModels:

    def test_message_content_role_factories(self):
        from src.utils.openai_api.models import MessageContent, MessageRole

        for factory, role in [
            (MessageContent.developer, MessageRole.developer),
            (MessageContent.system, MessageRole.system),
            (MessageContent.user, MessageRole.user),
            (MessageContent.assistant, MessageRole.assistant),
            (MessageContent.tool, MessageRole.tool),
            (MessageContent.function, MessageRole.function),
        ]:
            assert factory().role is role

    def test_message_content_null_content_converts_to_empty_str(self):
        from src.utils.openai_api.models import MessageContent

        content = MessageContent.model_validate({'role': 'assistant', 'content': None, 'refusal': None})
        assert content.content == ''

    def test_message_content_plain_text(self):
        from src.utils.openai_api.models import MessageContent
        from src.utils.openai_api.models.message import TextMessageContent

        assert MessageContent.user().set_plain_text('a').plain_text == 'a'
        message = MessageContent.user()
        message.add_text('a')
        message.add_image('https://img', detail='low')
        message.add_text('b')
        assert message.plain_text == 'a\nb'
        assert isinstance(message.content, list)
        assert all(not isinstance(x, TextMessageContent) or x.text for x in message.content)

    def test_message_content_add_methods_upgrade_str_content(self):
        from src.utils.openai_api.models import MessageContent

        message = MessageContent.user().set_plain_text('text')
        message.add_audio('audio-data', format_='wav')
        message.add_file(file_data='file-data')
        assert isinstance(message.content, list)
        assert [x.type for x in message.content] == ['text', 'input_audio', 'file']

    def test_message_content_add_file_without_any_param(self):
        from src.utils.openai_api.models import MessageContent

        with pytest.raises(ValueError, match='None of any'):
            MessageContent.user().add_file()

    def test_message_content_dump_excludes_reasoning_content_and_none(self):
        from src.utils.openai_api.models import MessageContent

        dumped = MessageContent.user().set_plain_text('hi').model_dump(mode='json', exclude_none=True)
        assert dumped == {'role': 'user', 'content': 'hi'}
        assert 'reasoning_content' not in dumped
        assert 'name' not in dumped

    @pytest.mark.parametrize(
        ('added', 'expected'),
        [
            pytest.param(['m0', 'm1', 'm2'], ['m1', 'm2'], id='trim_over_limit'),
            pytest.param(['m0', 'm1'], ['m0', 'm1'], id='keep_exactly_limit'),
        ],
    )
    def test_message_trim_chat_messages(self, added: list[str], expected: list[str]):
        from src.utils.openai_api.models import Message, MessageContent

        message = Message(max_messages=2)
        for text in added:
            message.add_content(MessageContent.user().set_plain_text(text))

        assert [x.content for x in message.messages] == expected

    def test_message_prefix_content(self):
        from src.utils.openai_api.models import Message, MessageRole

        message = Message()
        message.set_prefix_content('sys', assistant_text='hi', use_developer=True)
        roles = [x.role for x in message.prefix_messages]
        assert roles == [MessageRole.developer, MessageRole.assistant]

    def test_chat_completion_full_payload(self):
        from src.utils.openai_api.models import ChatCompletion

        completion = ChatCompletion.model_validate({
            'id': 'c1', 'object': 'chat.completion', 'created': 1, 'model': 'm',
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant', 'content': 'ok', 'refusal': None,
                    'annotations': [{'type': 'url_citation', 'url_citation': {
                        'end_index': 2, 'start_index': 0, 'title': 't', 'url': 'https://e.c'}}],
                    'tool_calls': [{'id': 'call-1', 'type': 'function',
                                    'function': {'name': 'f', 'arguments': '{}'}}],
                },
                'logprobs': {'content': [{'token': 'ok', 'bytes': [111, 107], 'logprob': -0.1,
                                          'top_logprobs': [{'token': 'ok', 'bytes': None, 'logprob': -0.1}]}],
                             'refusal': None},
                'finish_reason': 'tool_calls',
            }],
            'usage': {
                'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2,
                'prompt_tokens_details': {'cached_tokens': 0, 'text_tokens': 1},
                'completion_tokens_details': {'reasoning_tokens': 0, 'audio_tokens': 0},
            },
        })

        choice = completion.choices[0]
        assert choice.message.tool_calls is not None
        assert choice.message.tool_calls[0].id == 'call-1'
        assert choice.logprobs is not None
        assert choice.logprobs.content[0].token == 'ok'
        assert completion.usage is not None
        assert completion.usage.prompt_tokens_details is not None
        assert completion.usage.prompt_tokens_details.text_tokens == 1

    def test_chat_completion_without_usage(self):
        from src.utils.openai_api.models import ChatCompletion

        payload = {k: v for k, v in _CHAT_COMPLETION_PAYLOAD.items() if k != 'usage'}
        completion = ChatCompletion.model_validate(payload)
        assert completion.usage is None

    def test_chat_completion_null_finish_reason(self):
        from src.utils.openai_api.models import ChatCompletion

        payload = {k: v for k, v in _CHAT_COMPLETION_PAYLOAD.items() if k != 'choices'}
        payload['choices'] = [{**_CHAT_COMPLETION_PAYLOAD['choices'][0], 'finish_reason': None}]
        completion = ChatCompletion.model_validate(payload)
        assert completion.choices[0].finish_reason == 'not_provided'

    def test_chat_completion_custom_tool_call(self):
        from src.utils.openai_api.models import ChatCompletion

        completion = ChatCompletion.model_validate({
            'id': 'c1', 'object': 'chat.completion', 'created': 1, 'model': 'm',
            'choices': [{
                'index': 0,
                'message': {'role': 'assistant', 'content': None,
                            'tool_calls': [{'id': 'call-2', 'type': 'custom',
                                            'custom': {'name': 'ct', 'input': 'raw'}}]},
                'finish_reason': 'tool_calls',
            }],
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
        })

        tool_call = completion.choices[0].message.tool_calls[0]
        assert tool_call.type == 'custom'
        assert tool_call.custom is not None
        assert tool_call.custom.name == 'ct'

    @pytest.mark.parametrize(
        ('delta', 'extra_fields', 'expected_content'),
        [
            pytest.param({}, {}, '', id='complements_empty_delta_role'),
            # 未建模的额外字段(如 obfuscation)应被忽略
            pytest.param({'content': 'x'}, {'obfuscation': 'r4N7vQ2m'}, 'x', id='ignores_extra_fields'),
            pytest.param({'content': 'x'}, {}, 'x', id='null_finish_reason'),
        ],
    )
    def test_chunk_field_defaults(
            self,
            delta: dict[str, Any],
            extra_fields: dict[str, Any],
            expected_content: str,
    ):
        from src.utils.openai_api.models import ChatCompletionChunk

        payload = _chunk(delta)
        payload.update(extra_fields)
        chunk = ChatCompletionChunk.model_validate(payload)

        choice = chunk.choices[0]
        assert choice.delta.role == 'assistant'
        assert choice.delta.content == expected_content
        assert choice.finish_reason == 'not_provided'

    def test_stored_completion_models(self):
        from src.utils.openai_api.models import (
            ChatCompletionDeleted,
            ChatCompletionList,
            ChatCompletionMessageList,
        )

        deleted = ChatCompletionDeleted.model_validate(
            {'id': 'c1', 'object': 'chat.completion.deleted', 'deleted': True}
        )
        assert deleted.deleted is True

        completion_list = ChatCompletionList.model_validate({
            'object': 'list', 'data': [_CHAT_COMPLETION_PAYLOAD], 'first_id': 'c', 'last_id': 'c', 'has_more': True,
        })
        assert completion_list.has_more is True
        assert completion_list.data[0].id == 'chatcmpl-test'

        message_list = ChatCompletionMessageList.model_validate({
            'object': 'list',
            'data': [
                {'id': 'c1-0', 'role': 'user', 'content': 'write', 'name': None, 'content_parts': None},
                {'id': 'c1-1', 'role': 'assistant', 'content': None, 'refusal': None,
                 'content_parts': [{'text': 't', 'type': 'text'}]},
            ],
            'first_id': 'c1-0', 'last_id': 'c1-1', 'has_more': False,
        })
        assert message_list.data[0].content == 'write'
        assert message_list.data[1].content == ''
        assert message_list.data[1].content_parts is not None

    def test_embeddings_and_file_model_list_models(self):
        from src.utils.openai_api.models import Embeddings, FileList, ModelList

        embeddings = Embeddings.model_validate({
            'object': 'list', 'model': 'e-model',
            'data': [{'object': 'embedding', 'embedding': [0.1, 0.2], 'index': 0}],
            'usage': {'prompt_tokens': 1, 'total_tokens': 1},
        })
        assert embeddings.data[0].embedding == [0.1, 0.2]

        file_list = FileList.model_validate({'object': 'list', 'data': [
            {'id': 'f', 'object': 'file', 'bytes': 1, 'created_at': 1, 'filename': 'a', 'purpose': 'user_data'}]})
        assert file_list.data[0].id == 'f'

        model_list = ModelList.model_validate(
            {'object': 'list', 'data': [{'id': 'm', 'object': 'model', 'owned_by': 'o'}]}
        )
        assert model_list.data[0].id == 'm'


def _make_png_bytes() -> bytes:
    image = Image.new('RGB', (4, 4), color=(255, 0, 0))
    with BytesIO() as buffer:
        image.save(buffer, format='PNG')
        return buffer.getvalue()


class TestHelpers:

    async def test_encode_bytes_image(self):
        from src.utils.openai_api.helpers import encode_bytes_image

        data_url = await encode_bytes_image(_make_png_bytes())

        assert data_url.startswith('data:image/webp;base64,')
        with Image.open(BytesIO(base64.b64decode(data_url.split(',', 1)[1]))) as decoded:
            assert decoded.format == 'WEBP'
            assert decoded.size == (4, 4)

    @pytest.mark.parametrize(
        ('convert_format', 'expected_prefix'),
        [
            pytest.param(None, 'data:image/png;base64,', id='default_format'),
            pytest.param('webp', 'data:image/webp;base64,', id='convert_webp'),
        ],
    )
    async def test_encode_local_image(self, tmp_path: 'Path', convert_format: str | None, expected_prefix: str):
        from src.resource import AnyResource
        from src.utils.openai_api.helpers import encode_local_image

        (tmp_path / 'img.png').write_bytes(_make_png_bytes())
        kwargs = {} if convert_format is None else {'convert_format': convert_format}
        data_url = await encode_local_image(AnyResource(tmp_path, 'img.png'), **kwargs)
        assert data_url.startswith(expected_prefix)

    async def test_encode_local_file_and_audio(self, tmp_path: 'Path'):
        from src.resource import AnyResource
        from src.utils.openai_api.helpers import encode_local_audio, encode_local_file

        (tmp_path / 'a.txt').write_bytes(b'hello')
        encoded = await encode_local_file(AnyResource(tmp_path, 'a.txt'))
        assert base64.b64decode(encoded) == b'hello'

        (tmp_path / 's.wav').write_bytes(b'wave-bytes')
        audio_data, audio_format = await encode_local_audio(AnyResource(tmp_path, 's.wav'))
        assert base64.b64decode(audio_data) == b'wave-bytes'
        assert audio_format == 'wav'

    @pytest.mark.parametrize(
        ('raw', 'expected'),
        [
            pytest.param('{"a": 1, "b": [1, 2]}', {'a': 1, 'b': [1, 2]}, id='valid_passthrough'),
            # 仅缺闭合符时不应截断尾部字段
            pytest.param('{"a": "x", "b": "y"', {'a': 'x', 'b': 'y'}, id='only_missing_closers_keeps_fields'),
            pytest.param('{"a": 1, "b":', {'a': 1}, id='truncated_tail_value'),
            # 尾部字段完整时仅补闭合符, 不丢失 "c"
            pytest.param('{"a": 1, "b": 2, "c": 3', {'a': 1, 'b': 2, 'c': 3},
                         id='truncated_trailing_field_kept_when_closable'),
            pytest.param('{"a": [1, {"b": 2', {'a': [1, {'b': 2}]}, id='nested_unclosed'),
            pytest.param('{"a": "has } brace and , comma"', {'a': 'has } brace and , comma'},
                         id='ignores_braces_inside_strings'),
            pytest.param('{"a": "quote \\" inside"', {'a': 'quote " inside'}, id='escaped_quotes'),
            pytest.param('{"a":\n "line1\\nline2"\n', {'a': 'line1\nline2'}, id='removes_external_newlines_only'),
        ],
    )
    def test_fix_broken_generated_json(self, raw: str, expected: dict):
        """修复破损生成 JSON 的两级策略: 先整体解析, 失败时补全闭合符, 再失败时截断尾部残缺字段"""
        from src.utils.openai_api.helpers import fix_broken_generated_json

        assert json.loads(fix_broken_generated_json(raw)) == expected


class _ReplyModel(BaseModel):
    value: str


@pytest.fixture
def chat_session(configured_service):
    from src.utils.openai_api import ChatSession

    session = ChatSession(
        service_name=_SERVICE_NAME,
        model_name='test-model',
        default_user_name='tester',
        init_system_message='you are helpful',
    )
    return session


def _mock_session_reply(monkeypatch: pytest.MonkeyPatch, session, contents: list[str]) -> dict[str, Any]:
    """mock session.client.create_chat_completion 返回合成 assistant 回复并捕获请求参数"""
    from src.utils.openai_api.models import MessageContent

    captured: dict[str, Any] = {}

    async def fake_create_chat_completion(model, message, stream=True, **kwargs):
        captured.update({'model': model, 'message': message, 'stream': stream, 'kwargs': kwargs})
        return [MessageContent.assistant().set_plain_text(contents[0])]

    monkeypatch.setattr(session.client, 'create_chat_completion', fake_create_chat_completion)
    return captured


class TestChatSession:

    def test_init_with_prefix_messages(self, chat_session):
        from src.utils.openai_api.models import MessageRole

        prefix = chat_session.message.prefix_messages
        assert len(prefix) == 1
        assert prefix[0].role is MessageRole.system
        assert prefix[0].content == 'you are helpful'

    def test_init_with_developer_prefix(self, configured_service):
        from src.utils.openai_api import ChatSession
        from src.utils.openai_api.models import MessageRole

        session = ChatSession(
            service_name=_SERVICE_NAME,
            model_name='test-model',
            init_system_message='sys',
            init_assistant_message='hello',
            use_developer_message=True,
        )
        roles = [x.role for x in session.message.prefix_messages]
        assert roles == [MessageRole.developer, MessageRole.assistant]

    async def test_chat_appends_history_and_default_user_name(
            self,
            monkeypatch: pytest.MonkeyPatch,
            chat_session,
    ):
        captured = _mock_session_reply(monkeypatch, chat_session, ['hi there'])

        reply = await chat_session.chat('ping')

        assert reply == 'hi there'
        assert captured['model'] == 'test-model'
        assert captured['message'] is chat_session.message
        # user(ping) + assistant(reply), default_user_name 回填 user 消息
        assert [x.name for x in chat_session.message.chat_messages if x.role == 'user'] == ['tester']

    async def test_simple_chat_with_empty_choices_raises(self, monkeypatch: pytest.MonkeyPatch, chat_session):
        async def fake_create_chat_completion(model, message, stream=True, **kwargs):
            return []

        monkeypatch.setattr(chat_session.client, 'create_chat_completion', fake_create_chat_completion)
        with pytest.raises(RuntimeError, match='no choices'):
            await chat_session.simple_chat()

    async def test_chat_query_json(self, monkeypatch: pytest.MonkeyPatch, chat_session):
        captured = _mock_session_reply(
            monkeypatch, chat_session, ['```json\n{"value": "ok"}\n```'],
        )

        reply = await chat_session.chat_query_json('extract', _ReplyModel)

        assert isinstance(reply, _ReplyModel)
        assert reply.value == 'ok'
        assert captured['kwargs']['response_format'] == {'type': 'json_object'}

        # advance_chat 的 json_object 与仅 model_type 两个分支分别委派 chat_query_json / chat 后解析
        reply_json = await chat_session.advance_chat('extract', response_format='json_object', model_type=_ReplyModel)
        assert reply_json.value == 'ok'
        reply_model = await chat_session.advance_chat('extract', model_type=_ReplyModel)
        assert reply_model.value == 'ok'

    async def test_chat_query_json_without_model_type(self, monkeypatch: pytest.MonkeyPatch, chat_session):
        _mock_session_reply(monkeypatch, chat_session, ['{"raw": 1}'])

        reply = await chat_session.chat_query_json('extract')

        assert reply == {'raw': 1}

        # advance_chat 无 response_format/model_type 时透传纯文本响应
        reply_text = await chat_session.advance_chat('extract')
        assert reply_text == '{"raw": 1}'

    async def test_chat_query_schema(self, monkeypatch: pytest.MonkeyPatch, chat_session):
        captured = _mock_session_reply(monkeypatch, chat_session, ['{"value": "ok"}'])

        reply = await chat_session.chat_query_schema('extract', _ReplyModel)

        assert isinstance(reply, _ReplyModel)
        response_format = captured['kwargs']['response_format']
        assert response_format['type'] == 'json_schema'
        assert response_format['json_schema']['name'] == '_ReplyModel'
        assert response_format['json_schema']['strict'] is True
        assert 'properties' in response_format['json_schema']['schema']

        # advance_chat 的 json_schema 分支委派 chat_query_schema
        reply_schema = await chat_session.advance_chat('extract', response_format='json_schema', model_type=_ReplyModel)
        assert reply_schema.value == 'ok'

    async def test_add_chat_file_requires_any_param(self, chat_session):
        with pytest.raises(ValueError, match='None of any'):
            await chat_session.add_chat_file()

    async def test_add_chat_file_with_file_id_uses_user_role(self, chat_session):
        await chat_session.add_chat_file(file_id='file-1', filename='a.txt', user_name='tester')

        added = chat_session.message.chat_messages[-1]
        assert added.role.value == 'user'
        assert added.content[0].type == 'file'
        assert added.content[0].file.file_id == 'file-1'
        assert added.content[0].file.filename == 'a.txt'

    async def test_add_chat_image_url_passthrough(self, chat_session):
        await chat_session.add_chat_image('https://img.test/x.png', encoding_web_image=False)

        added = chat_session.message.chat_messages[-1]
        assert added.content[0].type == 'image_url'
        assert added.content[0].image_url.url == 'https://img.test/x.png'

    async def test_add_chat_local_image(self, tmp_path: 'Path', chat_session):
        from src.resource import AnyResource

        (tmp_path / 'img.png').write_bytes(_make_png_bytes())
        await chat_session.add_chat_image(AnyResource(tmp_path, 'img.png'))

        added = chat_session.message.chat_messages[-1]
        assert added.content[0].image_url.url.startswith('data:image/png;base64,')

    async def test_chat_session_trim_history(
            self,
            configured_service,
            monkeypatch: pytest.MonkeyPatch,
    ):
        from src.utils.openai_api import ChatSession

        session = ChatSession(service_name=_SERVICE_NAME, model_name='test-model', max_messages=2)
        _mock_session_reply(monkeypatch, session, ['ok'])

        await session.chat('a')
        await session.chat('b')

        # 每轮 user+assistant 各占一条, 上限 2 时仅保留最后一轮
        assert len(session.message.chat_messages) == 2
        assert [x.content for x in session.message.chat_messages] == ['b', 'ok']

    def test_fix_md_json_variants(self):
        from src.utils.openai_api import ChatSession

        assert ChatSession.fix_md_json('```json\n{"a": 1}\n```') == '{"a": 1}'
        assert ChatSession.fix_md_json('  {"a": 1}  ') == '{"a": 1}'
        assert ChatSession.fix_md_json('```json\n{"text": "```nested```"}\n```') == '{"text": "```nested```"}'
        # 裸代码围栏(无 json 标注)
        assert ChatSession.fix_md_json('```\n{"a": 1}\n```') == '{"a": 1}'


# 真实 API 验证: 常规运行整体跳过, 手动执行 OPENAI_API_REAL_TEST=1 pytest ... -k TestRealAPI

_REAL_API_ENV = 'OPENAI_API_REAL_TEST'

requires_live = require_env_flag(_REAL_API_ENV)
"""真实请求验证类门禁: 日常运行(含全量套件)一律跳过, 由用户手动设置 OPENAI_API_REAL_TEST=1 后发起"""

_REAL_API_TOOLS = [{
    'type': 'function',
    'function': {
        'name': 'get_current_weather',
        'description': 'Get the current weather in a given location',
        'parameters': {
            'type': 'object',
            'properties': {
                'location': {'type': 'string', 'description': 'The city and state, e.g. San Francisco, CA'},
            },
            'required': ['location'],
        },
    },
}]

# 已知无需建模的响应元数据字段(请求追踪/内部标识等, 非业务数据)
_REAL_API_IGNORABLE_KEYS = {'request_id', 'obfuscation', 'prompt_filter_results'}


def _skip_if_unsupported(exc: Exception) -> None:
    """提供商不支持对应端点(4xx)时跳过用例, 保留完整断言供支持的提供商复用"""
    from src.exception import WebSourceException

    if isinstance(exc, WebSourceException) and 400 <= exc.status_code < 500:
        pytest.skip(f'提供商不支持该端点({exc.status_code}): {exc.message[:200]}')
    raise exc


def _fail_with_response(exc: Exception) -> None:
    """将 WebSourceException 的响应体内容带出, 便于定位 4xx 具体原因"""
    from src.exception import WebSourceException

    if isinstance(exc, WebSourceException):
        body = bytes(exc.content or b'').decode('utf-8', 'replace')[:500]
        pytest.fail(f'请求失败({exc.status_code}): {body}')
    raise exc


def _skip_on_provider_error(exc: Exception, raw_capture: list[Any]) -> None:
    """提供商不支持该子端点时跳过

    兼容两类表示: 4xx WebSourceException, 以及 HTTP 200 + 业务错误体
    (如 GLM 的 {'msg': ..., 'code': ...}) 导致的 ValidationError
    """
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        raw = raw_capture[-1] if raw_capture else None
        if isinstance(raw, dict) and 'msg' in raw and 'code' in raw:
            pytest.skip(f'提供商不支持该子端点: {raw}')
    _skip_if_unsupported(exc)


@contextmanager
def real_endpoint_guard(raw_capture: list[Any]):
    """文件子端点请求守卫: 提供商不支持该子端点时跳过用例(_skip_on_provider_error 的 with 包装)"""
    try:
        yield
    except Exception as e:
        _skip_on_provider_error(e, raw_capture)


@requires_live
class TestRealAPI:

    @pytest.fixture
    def real_model(self) -> str:
        from src.utils.openai_api.api import OpenAIClient

        services = OpenAIClient.get_available_services()
        assert services, '未配置任何 openai 服务(.env.test OPENAI_SERVICE_CONFIG)'
        return services[0][1]

    @pytest.fixture
    def real_client(self):
        from src.utils.openai_api.api import OpenAIClient

        return OpenAIClient.init_default_from_config()

    @pytest.fixture
    def raw_capture(self, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
        """包装原始请求方法并记录真实响应 JSON, 用于对比模型保留字段"""
        from src.utils.openai_api.api import OpenAIClient

        records: list[Any] = []
        original_post = OpenAIClient._post_acquire_as_json.__func__
        original_get = OpenAIClient._get_resource_as_json.__func__

        async def wrapped_post(cls, url, params=None, **kwargs):
            result = await original_post(cls, url, params=params, **kwargs)
            records.append(result)
            return result

        async def wrapped_get(cls, url, params=None, **kwargs):
            result = await original_get(cls, url, params=params, **kwargs)
            records.append(result)
            return result

        monkeypatch.setattr(OpenAIClient, '_post_acquire_as_json', classmethod(wrapped_post))
        monkeypatch.setattr(OpenAIClient, '_get_resource_as_json', classmethod(wrapped_get))
        return records

    def _assert_no_meaningful_drop(self, raw: dict[str, Any], model_dump: dict[str, Any], *, where: str = '') -> None:
        """对比原始响应与模型 dump, 顶层不应存在未建模的有意义字段"""
        for key in raw:
            if key in _REAL_API_IGNORABLE_KEYS or key in model_dump:
                continue
            pytest.fail(f'真实响应字段 {key!r}{where} 未被数据模型保留: raw_keys={sorted(raw)}')

    def _assert_usage_details_modeled(self, raw_completion: dict[str, Any], model_dump: dict[str, Any]) -> None:
        """对比 usage 及其嵌套明细字段是否被完整建模"""
        raw_usage = raw_completion.get('usage') or {}
        for key in raw_usage:
            if key in model_dump.get('usage') or {}:
                continue
            pytest.fail(f'真实响应 usage 字段 {key!r} 未被数据模型保留: raw_usage_keys={sorted(raw_usage)}')

        for detail_key in ('prompt_tokens_details', 'completion_tokens_details'):
            raw_detail = raw_usage.get(detail_key) or {}
            modeled_detail = ((model_dump.get('usage') or {}).get(detail_key)) or {}
            for key in raw_detail:
                if key in modeled_detail:
                    continue
                pytest.fail(
                    f'真实响应 usage.{detail_key} 字段 {key!r} 未被数据模型保留: raw_keys={sorted(raw_detail)}'
                )

    async def test_real_list_models(self, real_client, raw_capture: list[Any]):
        from src.utils.openai_api.models import ModelList

        result = await real_client.list_models()

        assert isinstance(result, ModelList)
        assert result.data
        raw = raw_capture[-1]
        assert isinstance(raw, dict)
        for raw_item, modeled in zip(raw['data'], result.data):
            self._assert_no_meaningful_drop(raw_item, modeled.model_dump(), where='(models.data[])')

    async def test_real_chat_completion_normal(self, real_client, real_model: str, raw_capture: list[Any]):
        from src.utils.openai_api.models import MessageContent

        completion = await real_client.create_chat_completion_normal(
            model=real_model,
            message=[MessageContent.user().set_plain_text('用一句话回答: 1+1 等于几?')],
            max_tokens=512,
        )

        assert completion.choices
        assert '2' in (completion.choices[0].message.content or '')
        assert completion.usage is not None
        assert completion.usage.total_tokens > 0

        raw = raw_capture[-1]
        assert isinstance(raw, dict)
        self._assert_no_meaningful_drop(raw, completion.model_dump())
        self._assert_usage_details_modeled(raw, completion.model_dump())

        raw_choice = raw['choices'][0]
        modeled_choice = completion.choices[0].model_dump()
        self._assert_no_meaningful_drop(raw_choice, modeled_choice, where='(choices[])')

    async def test_real_chat_completion_stream(self, real_client, real_model: str):
        from src.utils.openai_api.models import MessageRole

        contents = await real_client.create_chat_completion(
            model=real_model,
            message=[{'role': 'user', 'content': '用一句话回答: 1+1 等于几?'}],
            stream=True,
            max_tokens=512,
        )

        assert contents
        assert contents[0].role is MessageRole.assistant
        assert '2' in contents[0].content

    async def _request_tool_calls(self, real_client, *, stream: bool = False):
        """遍历配置模型请求工具调用

        thinking 模型不支持显式 tool_choice, 先尝试 required 再退回默认 auto;
        所有模型均无法发起工具调用时跳过用例
        """
        from src.exception import WebSourceException
        from src.utils.openai_api.api import OpenAIClient

        message = [{'role': 'user', 'content': '波士顿现在的天气怎么样? 请务必调用工具查询'}]
        for _, model in OpenAIClient.get_available_services():
            for tool_choice in ('required', None):
                kwargs: dict[str, Any] = {
                    'model': model, 'message': message, 'tools': _REAL_API_TOOLS, 'max_tokens': 512,
                }
                if tool_choice is not None:
                    kwargs['tool_choice'] = tool_choice
                try:
                    if stream:
                        return model, await real_client.create_chat_completion(stream=True, **kwargs)
                    return model, await real_client.create_chat_completion_normal(**kwargs)
                except WebSourceException as e:
                    body = bytes(e.content or b'').decode('utf-8', 'replace')
                    if e.status_code == 400 and 'tool_choice' in body:
                        continue
                    _fail_with_response(e)

        pytest.skip('配置的模型均不支持工具调用')

    async def test_real_chat_completion_normal_with_tools(self, real_client, raw_capture: list[Any]):
        _, completion = await self._request_tool_calls(real_client, stream=False)

        message = completion.choices[0].message
        assert message.tool_calls
        tool_call = message.tool_calls[0]
        assert tool_call.id
        assert tool_call.function is not None
        assert tool_call.function.name == 'get_current_weather'
        assert isinstance(json.loads(tool_call.function.arguments or ''), dict)

        raw_tool_call = raw_capture[-1]['choices'][0]['message']['tool_calls'][0]
        self._assert_no_meaningful_drop(raw_tool_call, tool_call.model_dump(), where='(message.tool_calls[])')

    async def test_real_chat_completion_stream_with_tools(self, real_client):
        _, contents = await self._request_tool_calls(real_client, stream=True)

        assert contents
        tool_calls = contents[0].tool_calls
        assert tool_calls
        assert tool_calls[0].id
        assert tool_calls[0].function is not None
        assert tool_calls[0].function.name == 'get_current_weather'
        assert isinstance(json.loads(tool_calls[0].function.arguments or ''), dict)

    async def test_real_chat_completion_reasoning_content(self, real_client, real_model: str):
        """reasoning 模型的 reasoning_content 流式拼接(扩展字段), 不强制存在"""
        contents = await real_client.create_chat_completion(
            model=real_model,
            message=[{'role': 'user', 'content': '用一句话回答: 1+1 等于几?'}],
            stream=True,
            max_tokens=2048,
        )

        assert contents
        assert contents[0].content
        assert isinstance(contents[0].reasoning_content, str)

    async def test_real_embeddings(self, real_client, real_model: str):
        from src.exception import WebSourceException
        from src.utils.openai_api.models import Embeddings

        result = None
        last_exception: Exception | None = None
        for model in (real_model, 'embedding-3', 'embedding-2', 'text-embedding-3-small'):
            try:
                result = await real_client.create_embeddings(input_='hello world', model=model)
                break
            except Exception as e:
                last_exception = e
                if not (isinstance(e, WebSourceException) and 400 <= e.status_code < 500):
                    raise
        if result is None:
            assert last_exception is not None
            _skip_if_unsupported(last_exception)

        assert isinstance(result, Embeddings)
        assert result.data
        assert result.data[0].embedding

    @pytest.fixture
    async def real_uploaded_file(self, real_client, tmp_path: 'Path'):
        """上传一个共享文件供各子端点用例复用, 结束后尽力清理"""
        from src.resource import AnyResource
        from src.utils.openai_api.models import File

        (tmp_path / 'real_check.txt').write_bytes(b'omega real api check')

        # 不同提供商支持的 purpose 不同(OpenAI: user_data 等, moonshot/GLM: file-extract 等), 逐一回退
        uploaded: File | None = None
        last_exception: Exception | None = None
        for purpose in ('user_data', 'file-extract', 'batch'):
            try:
                uploaded = await real_client.upload_file(file=AnyResource(tmp_path, 'real_check.txt'), purpose=purpose)
                break
            except Exception as e:
                last_exception = e
                from src.exception import WebSourceException

                if not (isinstance(e, WebSourceException) and 400 <= e.status_code < 500):
                    raise
        if uploaded is None:
            assert last_exception is not None
            _skip_if_unsupported(last_exception)

        yield uploaded

        try:
            await real_client.delete_file(uploaded.id)
        except Exception:  # noqa: S110
            pass

    async def test_real_files_upload_and_list(self, real_client, real_uploaded_file):
        from src.utils.openai_api.models import FileList

        # 部分提供商(如 GLM)的文件列表必须按 purpose 过滤才有返回
        listed_ids: set[str] = set()
        for list_kwargs in ({'purpose': real_uploaded_file.purpose}, {}):
            file_list = await real_client.list_files(**list_kwargs)
            assert isinstance(file_list, FileList)
            listed_ids.update(x.id for x in file_list.data)

        if not listed_ids:
            pytest.skip('提供商文件列表接口未返回任何文件')
        assert real_uploaded_file.id in listed_ids

    async def test_real_files_retrieve(self, real_client, real_uploaded_file, raw_capture: list[Any]):
        with real_endpoint_guard(raw_capture):
            retrieved = await real_client.retrieve_file(real_uploaded_file.id)
        assert retrieved.id == real_uploaded_file.id

    async def test_real_files_content(self, real_client, real_uploaded_file, raw_capture: list[Any]):
        from src.utils.openai_api.models import FileContent

        with real_endpoint_guard(raw_capture):
            content = await real_client.retrieve_file_content(real_uploaded_file.id)
        assert isinstance(content, FileContent)
        assert content.content
        self._assert_no_meaningful_drop(raw_capture[-1], content.model_dump(), where='(files/content)')

    async def test_real_files_delete(self, real_client, real_uploaded_file, raw_capture: list[Any]):
        from src.utils.openai_api.models import FileDeleted

        with real_endpoint_guard(raw_capture):
            deleted = await real_client.delete_file(real_uploaded_file.id)
        assert isinstance(deleted, FileDeleted)
        assert deleted.deleted is True

    async def test_real_stored_completions(self, real_client, real_model: str):
        from src.utils.openai_api.models import ChatCompletion

        try:
            created = await real_client.create_chat_completion_normal(
                model=real_model,
                message=[{'role': 'user', 'content': 'hi'}],
                store=True,
                max_tokens=16,
            )
        except Exception as e:
            _skip_if_unsupported(e)

        completion_id = created.id

        try:
            retrieved = await real_client.get_chat_completion(completion_id)
            assert isinstance(retrieved, ChatCompletion)

            updated = await real_client.update_chat_completion(completion_id, metadata={'origin': 'omega-test'})
            assert updated.id == completion_id

            listed = await real_client.list_chat_completions(limit=5)
            assert completion_id in {x.id for x in listed.data}

            messages = await real_client.get_chat_completion_messages(completion_id, limit=5)
            assert messages.data

            deleted = await real_client.delete_chat_completion(completion_id)
            assert deleted.deleted is True
        except Exception as e:
            _skip_if_unsupported(e)
