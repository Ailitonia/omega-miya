"""
@Author         : Ailitonia
@Date           : 2022/11/28 21:24
@FileName       : omega_api.py
@Project        : nonebot2_miya 
@Description    : Omega 后端 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

# TODO #1 规范 api 请求及响应模型
# TODO #2 规范 api 依赖注入
# TODO #3 添加 api 认证

import inspect
from typing import TypeVar, ParamSpec, Callable, Coroutine
from nonebot import get_driver, get_app
from nonebot.log import logger

from .model import BaseApiModel, BaseApiReturn

P = ParamSpec("P")
R = TypeVar("R")


def register_get_route(path: str, *, enabled: bool = True):
    """包装 async function 并注册为服务

    :param path: 请求路径
    :param enabled: 启用开关, 用于插件配置控制
    """
    if not path.startswith('/'):
        path = '/' + path

    def decorator(func: Callable[P, Coroutine[None, None, R]]) -> Callable[P, Coroutine[None, None, R]]:
        if not inspect.iscoroutinefunction(func):
            raise ValueError('The decorated function must be coroutine function')

        if not enabled:
            return func

        driver = get_driver()
        if 'fastapi' not in driver.type:
            raise RuntimeError('fastapi driver not enabled')

        app = get_app()
        app.get(path)(func)

        host = str(driver.config.host)
        port = driver.config.port
        if host in ["0.0.0.0", "127.0.0.1"]:
            host = "localhost"
        logger.opt(colors=True).info(
            f"Service <lc>{inspect.getmodule(func).__name__}</lc> running at: "
            f"<b><u>http://{host}:{port}/{path.removeprefix('/')}</u></b>"
        )

        return func

    return decorator


__all__ = [
    'register_get_route',
    'BaseApiModel',
    'BaseApiReturn'
]
