"""
@Author         : Ailitonia
@Date           : 2026/9/8 19:35
@FileName       : utils
@Project        : omega-miya
@Description    : nonebug 测试工具集
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Iterable, Mapping
from types import ModuleType, SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from nonebot.adapters import Event, Message, MessageSegment
from pydantic import create_model


def unique_test_id(prefix: str) -> str:
    """生成带唯一后缀的测试 ID"""
    return f'{prefix}_{uuid4().hex[:8]}'


def rebind_module_namespace(
        monkeypatch: pytest.MonkeyPatch,
        module: ModuleType,
        name: str,
        **overrides: Any,
) -> SimpleNamespace:
    """以 SimpleNamespace 重绑定目标模块命名空间内的名字(继承原对象全部属性, 仅覆盖指定项)

    目标模块内 `import asyncio`/`import time` 之类的名字指向进程共享的全局模块对象,
    直接 patch 其属性会在共享 session 事件循环上殃及常驻组件(如 uvicorn Server.main_loop);
    此处仅替换目标模块内的名字绑定本身, 返回替换后的命名空间以便取用注入的替身
    """
    source = getattr(module, name)
    namespace = SimpleNamespace(**{**vars(source), **overrides})
    monkeypatch.setattr(module, name, namespace)
    return namespace


def escape_text(s: str, *, escape_comma: bool = True) -> str:
    s = s.replace('&', '&amp;').replace('[', '&#91;').replace(']', '&#93;')
    if escape_comma:
        s = s.replace(',', '&#44;')
    return s


def make_fake_message():
    class FakeMessageSegment(MessageSegment):
        @classmethod
        def get_message_class(cls):
            return FakeMessage

        def __str__(self) -> str:
            return self.data['text'] if self.type == 'text' else f'[fake:{self.type}]'

        @classmethod
        def text(cls, text: str):
            return cls('text', {'text': text})

        @staticmethod
        def image(url: str):
            return FakeMessageSegment('image', {'url': url})

        @staticmethod
        def nested(content: 'FakeMessage'):
            return FakeMessageSegment('node', {'content': content})

        def is_text(self) -> bool:
            return self.type == 'text'

    class FakeMessage(Message):
        @classmethod
        def get_segment_class(cls):
            return FakeMessageSegment

        @staticmethod
        def _construct(msg: str | Iterable[Mapping]):
            if isinstance(msg, str):
                yield FakeMessageSegment.text(msg)
            else:
                for seg in msg:
                    yield FakeMessageSegment(**seg)
            return

        def __add__(self, other):
            other = escape_text(other) if isinstance(other, str) else other
            return super().__add__(other)

    return FakeMessage


def make_fake_event(
        _base: type[Event] | None = None,
        _type: str = 'message',
        _name: str = 'test',
        _description: str = 'test',
        _user_id: str | None = 'test',
        _session_id: str | None = 'test',
        _message: Message | None = None,
        _to_me: bool = True,
        **fields,
) -> type[Event]:
    _Fake = create_model('_Fake', __base__=_base or Event, **fields)

    class FakeEvent(_Fake):
        model_config = {'extra': 'forbid'}  # noqa: RUF012

        def get_type(self) -> str:
            return _type

        def get_event_name(self) -> str:
            return _name

        def get_event_description(self) -> str:
            return _description

        def get_user_id(self) -> str:
            if _user_id is not None:
                return _user_id
            raise NotImplementedError

        def get_session_id(self) -> str:
            if _session_id is not None:
                return _session_id
            raise NotImplementedError

        def get_message(self) -> 'Message':
            if _message is not None:
                return _message
            raise NotImplementedError

        def is_tome(self) -> bool:
            return _to_me

    return FakeEvent
