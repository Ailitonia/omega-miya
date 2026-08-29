"""
@Author         : Ailitonia
@Date           : 2026/08/20 15:30
@FileName       : conftest.py
@Project        : omega-miya
@Description    : pytest 配置, 初始化 nonebug 测试必要的依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import os

import nonebot
import pytest
from nonebug import NONEBOT_INIT_KWARGS
from pytest_asyncio import is_async_test

os.environ['ENVIRONMENT'] = 'test'
"""设置环境及配置文件为 test"""


def pytest_configure(config: pytest.Config):
    """通过 pytest_configure 钩子函数自定义 NoneBot 初始化的参数"""
    config.stash[NONEBOT_INIT_KWARGS] = {
        'LOG_LEVEL': os.getenv('LOG_LEVEL'),
    }


def pytest_collection_modifyitems(items: list[pytest.Item]):
    """自动为所有异步测试统一设置 session 级别的 Event Loop, 避免重复装饰每个测试函数

    - 为每个异步测试动态添加 @pytest.mark.asyncio(loop_scope='session') 标记
    - 测试套件中有大量异步用例，且它们需要共享某些长生命周期的异步资源（数据库连接池、HTTP Session、WebSocket 连接等）
    - 减少频繁创建/销毁 Event Loop 的开销，提升测试速度
    """
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope='session')
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope='session', autouse=True)
async def after_nonebot_init(after_nonebot_init: None):
    """nonebug 初始化 nonebot.init() 后流程

    通常不需要自行初始化 NoneBot, NoneBug 已经运行了 nonebot.init()
    """
    import src.database  # noqa: F401
    # from nonebot.adapters.console import Adapter as ConsoleAdapter

    # 加载适配器
    # driver = nonebot.get_driver()
    # driver.register_adapter(ConsoleAdapter)

    # 加载插件
    nonebot.load_plugins('src/service')
    nonebot.load_plugins('src/plugins')
