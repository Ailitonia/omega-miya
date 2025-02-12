"""
@Author         : Ailitonia
@Date           : 2024/3/27 2:30
@FileName       : compat
@Project        : nonebot2_miya
@Description    : 一些兼容和 patch 模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated, Any, Literal

from pydantic import AnyHttpUrl, AnyUrl, BeforeValidator, TypeAdapter

# Compatibility for pydantic_core._pydantic_core.Url in V2
# See https://github.com/pydantic/pydantic/discussions/8211 and https://github.com/pydantic/pydantic/discussions/6395
AnyUrlAdapter = TypeAdapter(AnyUrl)
AnyUrlStr = Annotated[str, BeforeValidator(lambda v: str(AnyUrlAdapter.validate_python(v)))]
"""使用 Annotated Validator 将 AnyUrl 格式转换为 str"""

AnyHttpUrlAdapter = TypeAdapter(AnyHttpUrl)
AnyHttpUrlStr = Annotated[str, BeforeValidator(lambda v: str(AnyHttpUrlAdapter.validate_python(v)))]
"""使用 Annotated Validator 将 AnyHttpUrl 格式转换为 str"""


def parse_obj_as[T](
        type_: type[T],
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None,
) -> T:
    """Validate a Python object against the model.

    `parse_obj_as` is deprecated. Use `pydantic.TypeAdapter.validate_python` instead.
    """
    return TypeAdapter(type_).validate_python(obj, strict=strict, from_attributes=from_attributes, context=context)


def parse_json_as[T](
        type_: type[T],
        data: str | bytes,
        *,
        strict: bool | None = None,
        context: dict[str, Any] | None = None,
) -> T:
    """Validate a JSON string or bytes against the model.

    Usage docs: https://docs.pydantic.dev/2.8/concepts/json/#json-parsing
    """
    return TypeAdapter(type_).validate_json(data, strict=strict, context=context)


def dump_obj_as[T](
        type_: type[T],
        obj: Any,
        *,
        mode: Literal['json', 'python'] = 'python',
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
) -> Any:
    """Validate and dump an instance of the adapted type to a Python object."""
    custom_type_adapter = TypeAdapter(type_)
    validated_instance = custom_type_adapter.validate_python(obj)
    return custom_type_adapter.dump_python(
        validated_instance,
        mode=mode,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
    )


def dump_json_as[T](
        type_: type[T],
        obj: Any,
        *,
        encoding: str = 'utf-8',
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
) -> str:
    """Validate and serialize an instance of the adapted type to JSON."""
    custom_type_adapter = TypeAdapter(type_)
    validated_instance = custom_type_adapter.validate_python(obj)
    return custom_type_adapter.dump_json(
        validated_instance,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
    ).decode(encoding=encoding)


__all__ = [
    'AnyUrlStr',
    'AnyHttpUrlStr',
    'parse_obj_as',
    'parse_json_as',
    'dump_obj_as',
    'dump_json_as',
]
