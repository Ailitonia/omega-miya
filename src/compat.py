"""
@Author         : Ailitonia
@Date           : 2024/3/27 2:30
@FileName       : compat
@Project        : nonebot2_miya
@Description    : 一些兼容和 patch 模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated

from pydantic import AfterValidator, AnyUrl, AnyHttpUrl

# Compatibility for pydantic_core._pydantic_core.Url in V2
# See https://github.com/pydantic/pydantic/discussions/8211 and https://github.com/pydantic/pydantic/discussions/6395
AnyUrlStr = Annotated[AnyUrl, AfterValidator(lambda v: str(v))]
"""使用 Annotated Validator 将 AnyUrl 格式转换为 str"""
AnyHttpUrlStr = Annotated[AnyHttpUrl, AfterValidator(lambda v: str(v))]
"""使用 Annotated Validator 将 AnyHttpUrl 格式转换为 str"""


__all__ = [
    'AnyUrlStr',
    'AnyHttpUrlStr'
]
