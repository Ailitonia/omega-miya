"""
@Author         : Ailitonia
@Date           : 2026/9/3 19:20
@FileName       : test_001_compat
@Project        : omega-miya
@Description    : src.compat 模块单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, ValidationInfo, field_validator


class _SimpleModel(BaseModel):
    """parse 系列函数测试用简单模型"""

    x: int
    y: str = 'default'


class _DumpModel(BaseModel):
    """dump 系列函数测试用模型, 覆盖默认值/可选值/datetime/别名字段"""

    a: int
    b: str | None = None
    c: datetime = Field(default_factory=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    d: str = Field(default='x', alias='D_ALIAS')


class _ContextModel(BaseModel):
    """context 参数透传测试用模型"""

    v: str

    @field_validator('v')
    @classmethod
    def _append_context_tag(cls, value: str, info: ValidationInfo) -> str:
        return f'{value}:{(info.context or {}).get("tag", "none")}'


class TestModuleContract:
    """模块导出契约测试"""

    def test_all_exports(self):
        import src.compat

        assert src.compat.__all__ == [
            'AnyUrlStr',
            'AnyHttpUrlStr',
            'EmptyNoneStr',
            'parse_obj_as',
            'parse_json_as',
            'dump_obj_as',
            'dump_json_as',
        ]

    def test_global_url_adapters(self):
        from src.compat import ANY_HTTP_URL_ADAPTER, ANY_URL_ADAPTER

        assert isinstance(ANY_URL_ADAPTER, TypeAdapter)
        assert isinstance(ANY_HTTP_URL_ADAPTER, TypeAdapter)


class TestAnyUrlStr:
    """AnyUrlStr 类型测试"""

    def test_valid_url(self):
        from src.compat import AnyUrlStr

        # pydantic v2 URL 规范化: 空路径补 '/'
        assert TypeAdapter(AnyUrlStr).validate_python('https://example.com') == 'https://example.com/'

    def test_url_normalized(self):
        from src.compat import AnyUrlStr

        # scheme 与 host 规范化为小写, 路径大小写保留
        assert TypeAdapter(AnyUrlStr).validate_python('HTTPS://EXAMPLE.COM/Path') == 'https://example.com/Path'

    def test_url_components_preserved(self):
        from src.compat import AnyUrlStr

        assert TypeAdapter(AnyUrlStr).validate_python('https://user:pass@Example.COM:8080/p?q=1#frag') == (
            'https://user:pass@example.com:8080/p?q=1#frag'
        )

    @pytest.mark.parametrize('url', ['ftp://example.com/file', 'ws://example.com', 'file:///etc/passwd'])
    def test_non_http_schemes_allowed(self, url: str):
        from src.compat import AnyUrlStr

        assert TypeAdapter(AnyUrlStr).validate_python(url).startswith(url.split(':')[0])

    def test_bytes_input_accepted(self):
        from src.compat import AnyUrlStr

        assert TypeAdapter(AnyUrlStr).validate_python(b'https://example.com') == 'https://example.com/'

    def test_surrounding_whitespace_stripped(self):
        from src.compat import AnyUrlStr

        assert TypeAdapter(AnyUrlStr).validate_python('  https://example.com  ') == 'https://example.com/'

    def test_unicode_domain_punycode(self):
        from src.compat import AnyUrlStr

        assert TypeAdapter(AnyUrlStr).validate_python('https://例子.com') == 'https://xn--fsqu00a.com/'

    def test_result_type_is_str(self):
        from src.compat import AnyUrlStr

        assert type(TypeAdapter(AnyUrlStr).validate_python('https://example.com')) is str

    @pytest.mark.parametrize('invalid_input', ['', 'example.com', '/path', 'not a url', 123, None, True])
    def test_invalid_input_raises(self, invalid_input: Any):
        from src.compat import AnyUrlStr

        with pytest.raises(ValidationError):
            TypeAdapter(AnyUrlStr).validate_python(invalid_input)

    def test_model_field_integration(self):
        from src.compat import AnyUrlStr

        class _Model(BaseModel):
            url: AnyUrlStr

        model = _Model(url='https://example.com')
        assert type(model.url) is str
        assert model.model_dump() == {'url': 'https://example.com/'}
        assert _Model.model_validate_json(model.model_dump_json()).url == 'https://example.com/'


class TestAnyHttpUrlStr:
    """AnyHttpUrlStr 类型测试"""

    @pytest.mark.parametrize('url', ['http://example.com', 'https://example.com/path?q=1'])
    def test_http_schemes_allowed(self, url: str):
        from src.compat import AnyHttpUrlStr

        assert TypeAdapter(AnyHttpUrlStr).validate_python(url).startswith('http')

    @pytest.mark.parametrize('url', ['ftp://example.com', 'ws://example.com', 'file:///etc/passwd'])
    def test_non_http_schemes_rejected(self, url: str):
        from src.compat import AnyHttpUrlStr

        with pytest.raises(ValidationError):
            TypeAdapter(AnyHttpUrlStr).validate_python(url)

    def test_bytes_input_accepted(self):
        from src.compat import AnyHttpUrlStr

        assert TypeAdapter(AnyHttpUrlStr).validate_python(b'https://example.com') == 'https://example.com/'

    def test_url_normalized(self):
        from src.compat import AnyHttpUrlStr

        assert TypeAdapter(AnyHttpUrlStr).validate_python('HTTP://EXAMPLE.COM') == 'http://example.com/'

    @pytest.mark.parametrize('invalid_input', ['', 'example.com', '/path', 123, None, True])
    def test_invalid_input_raises(self, invalid_input: Any):
        from src.compat import AnyHttpUrlStr

        with pytest.raises(ValidationError):
            TypeAdapter(AnyHttpUrlStr).validate_python(invalid_input)

    def test_model_json_roundtrip(self):
        from src.compat import AnyHttpUrlStr

        class _Model(BaseModel):
            url: AnyHttpUrlStr

        model = _Model(url='https://example.com')
        assert _Model.model_validate_json(model.model_dump_json()) == model


class TestEmptyNoneStr:
    """EmptyNoneStr 类型测试"""

    def test_none_becomes_empty_str(self):
        from src.compat import EmptyNoneStr

        assert TypeAdapter(EmptyNoneStr).validate_python(None) == ''

    def test_empty_str_preserved(self):
        from src.compat import EmptyNoneStr

        assert TypeAdapter(EmptyNoneStr).validate_python('') == ''

    def test_str_passthrough(self):
        from src.compat import EmptyNoneStr

        assert TypeAdapter(EmptyNoneStr).validate_python('abc') == 'abc'

    def test_bytes_coerced_to_str(self):
        from src.compat import EmptyNoneStr

        assert TypeAdapter(EmptyNoneStr).validate_python(b'abc') == 'abc'

    @pytest.mark.parametrize('invalid_input', [0, 123, 1.5, True])
    def test_non_str_input_raises(self, invalid_input: Any):
        from src.compat import EmptyNoneStr

        # 仅 None 被转换, 其他 falsy 值(如 0)不会被吞掉, 走正常 str 校验报错
        with pytest.raises(ValidationError):
            TypeAdapter(EmptyNoneStr).validate_python(invalid_input)

    def test_model_field(self):
        from src.compat import EmptyNoneStr

        class _Model(BaseModel):
            v: EmptyNoneStr = 'default'

        assert _Model(v=None).v == ''
        assert _Model(v='text').v == 'text'
        assert _Model().v == 'default'


class TestParseObjAs:
    """parse_obj_as 函数测试"""

    def test_scalar_coercion(self):
        from src.compat import parse_obj_as

        assert parse_obj_as(int, '123') == 123

    def test_container_coercion(self):
        from src.compat import parse_obj_as

        assert parse_obj_as(list[int], ['1', 2]) == [1, 2]

    def test_model_from_dict(self):
        from src.compat import parse_obj_as

        assert parse_obj_as(_SimpleModel, {'x': '1'}) == _SimpleModel(x=1)

    def test_invalid_input_raises(self):
        from src.compat import parse_obj_as

        with pytest.raises(ValidationError):
            parse_obj_as(int, 'abc')

    def test_strict_rejects_coercion(self):
        from src.compat import parse_obj_as

        with pytest.raises(ValidationError):
            parse_obj_as(int, '123', strict=True)

    def test_strict_accepts_exact_type(self):
        from src.compat import parse_obj_as

        assert parse_obj_as(int, 123, strict=True) == 123

    def test_from_attributes(self):
        from src.compat import parse_obj_as

        obj = SimpleNamespace(x=1, y='attr')
        assert parse_obj_as(_SimpleModel, obj, from_attributes=True) == _SimpleModel(x=1, y='attr')

    def test_from_attributes_disabled_by_default(self):
        from src.compat import parse_obj_as

        with pytest.raises(ValidationError):
            parse_obj_as(_SimpleModel, SimpleNamespace(x=1))

    def test_context_passed_to_validators(self):
        from src.compat import parse_obj_as

        assert parse_obj_as(_ContextModel, {'v': 'a'}, context={'tag': 'X'}).v == 'a:X'


class TestParseJsonAs:
    """parse_json_as 函数测试"""

    def test_str_input(self):
        from src.compat import parse_json_as

        assert parse_json_as(list[int], '[1, "2"]') == [1, 2]

    def test_bytes_input_equal_to_str(self):
        from src.compat import parse_json_as

        assert parse_json_as(list[int], b'[1, "2"]') == parse_json_as(list[int], '[1, "2"]')

    def test_invalid_json_raises_validation_error(self):
        from src.compat import parse_json_as

        # pydantic v2 中非法 JSON 包装为 ValidationError 而非 json.JSONDecodeError
        with pytest.raises(ValidationError):
            parse_json_as(list[int], '{oops')

    def test_strict_rejects_coercion(self):
        from src.compat import parse_json_as

        with pytest.raises(ValidationError):
            parse_json_as(list[int], '["1"]', strict=True)

    def test_strict_accepts_exact_type(self):
        from src.compat import parse_json_as

        assert parse_json_as(list[int], '[1, 2]', strict=True) == [1, 2]

    def test_context_passed_to_validators(self):
        from src.compat import parse_json_as

        assert parse_json_as(_ContextModel, '{"v": "a"}', context={'tag': 'Y'}).v == 'a:Y'

    def test_model_from_json(self):
        from src.compat import parse_json_as

        assert parse_json_as(_SimpleModel, '{"x": 1}') == _SimpleModel(x=1)


class TestDumpObjAs:
    """dump_obj_as 函数测试"""

    def test_validate_then_dump_scalar(self):
        from src.compat import dump_obj_as

        assert dump_obj_as(int, '123') == 123

    def test_validate_then_dump_container(self):
        from src.compat import dump_obj_as

        assert dump_obj_as(list[int], ['1', 2]) == [1, 2]

    def test_python_mode_keeps_python_objects(self):
        from src.compat import dump_obj_as

        result = dump_obj_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'})
        assert isinstance(result['c'], datetime)

    def test_json_mode_serializes_objects(self):
        from src.compat import dump_obj_as

        result = dump_obj_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'}, mode='json')
        assert isinstance(result['c'], str)

    def test_include(self):
        from src.compat import dump_obj_as

        assert dump_obj_as(_DumpModel, {'a': 1, 'b': 'z', 'D_ALIAS': 'y'}, include={'a', 'b'}) == {'a': 1, 'b': 'z'}

    def test_exclude(self):
        from src.compat import dump_obj_as

        result = dump_obj_as(_DumpModel, {'a': 1, 'b': 'z', 'D_ALIAS': 'y'}, exclude={'b'})
        assert 'b' not in result
        assert result['a'] == 1

    def test_by_alias(self):
        from src.compat import dump_obj_as

        assert dump_obj_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'}, by_alias=True)['D_ALIAS'] == 'y'

    def test_exclude_unset(self):
        from src.compat import dump_obj_as

        assert dump_obj_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'}, exclude_unset=True) == {'a': 1, 'd': 'y'}

    def test_exclude_defaults(self):
        from src.compat import dump_obj_as

        assert dump_obj_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'}, exclude_defaults=True) == {'a': 1, 'd': 'y'}

    def test_exclude_none(self):
        from src.compat import dump_obj_as

        assert 'b' not in dump_obj_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'}, exclude_none=True)

    def test_model_instance_input(self):
        from src.compat import dump_obj_as

        assert dump_obj_as(_DumpModel, _DumpModel(a=1, D_ALIAS='y'))['a'] == 1

    def test_invalid_input_raises(self):
        from src.compat import dump_obj_as

        with pytest.raises(ValidationError):
            dump_obj_as(int, 'abc')


class TestDumpJsonAs:
    """dump_json_as 函数测试"""

    def test_returns_str_and_parseable(self):
        from src.compat import dump_json_as

        result = dump_json_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'})
        assert isinstance(result, str)
        assert json.loads(result)['a'] == 1

    def test_default_keeps_unicode(self):
        from src.compat import dump_json_as

        assert dump_json_as(dict[str, str], {'k': '中文'}) == '{"k":"中文"}'

    def test_ensure_ascii_escapes_unicode(self):
        from src.compat import dump_json_as

        assert dump_json_as(dict[str, str], {'k': '中文'}, ensure_ascii=True) == '{"k":"\\u4e2d\\u6587"}'

    def test_indent(self):
        from src.compat import dump_json_as

        assert dump_json_as(dict[str, int], {'a': 1}, indent=2) == '{\n  "a": 1\n}'

    def test_by_alias_and_exclude_none(self):
        from src.compat import dump_json_as

        parsed = json.loads(dump_json_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'}, by_alias=True, exclude_none=True))
        assert parsed['D_ALIAS'] == 'y'
        assert 'b' not in parsed

    def test_include_and_exclude(self):
        from src.compat import dump_json_as

        parsed = json.loads(dump_json_as(_DumpModel, {'a': 1, 'b': 'z', 'D_ALIAS': 'y'}, include={'a', 'b'}))
        assert parsed == {'a': 1, 'b': 'z'}

    def test_exclude_unset(self):
        from src.compat import dump_json_as

        parsed = json.loads(dump_json_as(_DumpModel, {'a': 1, 'D_ALIAS': 'y'}, exclude_unset=True))
        assert parsed == {'a': 1, 'd': 'y'}

    def test_roundtrip_with_parse_json_as(self):
        from src.compat import dump_json_as, parse_json_as

        model = _SimpleModel(x=1, y='t')
        assert parse_json_as(_SimpleModel, dump_json_as(_SimpleModel, model)) == model

    def test_invalid_input_raises(self):
        from src.compat import dump_json_as

        with pytest.raises(ValidationError):
            dump_json_as(int, 'abc')
