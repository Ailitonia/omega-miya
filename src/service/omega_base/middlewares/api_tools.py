"""
@Author         : Ailitonia
@Date           : 2023/7/3 0:45
@FileName       : api_tools
@Project        : nonebot2_miya
@Description    : 平台 API 调用适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Callable, Type, TypeVar, Union

from nonebot.log import logger
from nonebot.internal.adapter.bot import Bot

from .const import SupportedPlatform
from .exception import AdapterNotSupported
from .types import ApiCaller


__API_CALLERS: dict[str, Type[ApiCaller]] = {}

ApiCaller_T = TypeVar("ApiCaller_T", bound=Type[ApiCaller])
T = TypeVar("T")


def register_api_caller(adapter_name: str) -> Callable[[T], T]:
    """注册不同平台 API 适配器"""

    def decorator(api_caller: ApiCaller_T) -> ApiCaller_T:
        """注册不同平台 API 适配器"""
        global __API_CALLERS

        if adapter_name not in SupportedPlatform.supported_adapter_names:
            raise AdapterNotSupported(adapter_name=adapter_name)

        if adapter_name in __API_CALLERS.keys():
            logger.warning(f'Duplicate {api_caller.__name__!r} for {adapter_name!r} has been registered')
            return api_caller

        __API_CALLERS[adapter_name] = api_caller
        logger.opt(colors=True).debug(f'ApiCaller <e>{api_caller.__name__!r}</e> is registered')
        return api_caller

    return decorator


def get_api_caller(platform: Union[str, Bot]) -> Type[ApiCaller]:
    """根据适配平台获取 ApiCaller"""

    adapter_name = platform.adapter.get_name() if isinstance(platform, Bot) else platform

    if adapter_name not in SupportedPlatform.supported_adapter_names or adapter_name not in __API_CALLERS.keys():
        raise AdapterNotSupported(adapter_name=adapter_name)
    return __API_CALLERS[adapter_name]


__all__ = [
    'register_api_caller',
    'get_api_caller'
]
