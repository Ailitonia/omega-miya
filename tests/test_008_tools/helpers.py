"""
@Author         : Ailitonia
@Date           : 2026/10/8 20:00
@FileName       : helpers
@Project        : omega-miya
@Description    : test_008_tools 共享测试工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from types import ModuleType

import pytest


def capture_async_sleep(monkeypatch: pytest.MonkeyPatch, module: ModuleType) -> list[float]:
    """向目标模块注入记录调用参数的假 async_sleep, 返回调用记录列表

    替换的是目标模块命名空间内的 async_sleep 名字, 不触碰进程共享的 asyncio.sleep
    """
    sleep_calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(module, 'async_sleep', _fake_sleep)
    return sleep_calls
