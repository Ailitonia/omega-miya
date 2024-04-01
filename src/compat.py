"""
@Author         : Ailitonia
@Date           : 2024/3/27 2:30
@FileName       : compat
@Project        : nonebot2_miya
@Description    : 一些兼容和 patch 模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated, Any, Type, TypeVar

from pydantic import AfterValidator, AnyUrl, AnyHttpUrl, TypeAdapter


T = TypeVar('T')


# Compatibility for pydantic_core._pydantic_core.Url in V2
# See https://github.com/pydantic/pydantic/discussions/8211 and https://github.com/pydantic/pydantic/discussions/6395
AnyUrlStr = Annotated[AnyUrl, AfterValidator(lambda v: str(v))]
"""使用 Annotated Validator 将 AnyUrl 格式转换为 str"""
AnyHttpUrlStr = Annotated[AnyHttpUrl, AfterValidator(lambda v: str(v))]
"""使用 Annotated Validator 将 AnyHttpUrl 格式转换为 str"""


def parse_obj_as(
        type_: Type[T],
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None,
) -> T:
    """`parse_obj_as` is deprecated. Use `pydantic.TypeAdapter.validate_python` instead."""
    return TypeAdapter(type_).validate_python(obj, strict=strict, from_attributes=from_attributes, context=context)


__all__ = [
    'AnyUrlStr',
    'AnyHttpUrlStr',
    'parse_obj_as'
]
