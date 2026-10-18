"""
@Author         : Ailitonia
@Date           : 2026/10/12
@FileName       : conftest
@Project        : omega-miya
@Description    : omega_core_manager 插件单元测试 fixtures
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING

import pytest

from tests.utils import (
    first_respond_registry_sandbox as _first_respond_registry_sandbox_cm,
)
from tests.utils import persisted_numeric_obv11_bot

if TYPE_CHECKING:
    from src.database.internal.bot import BotSelf


@pytest.fixture(scope='class')
async def numeric_bot() -> AsyncGenerator['BotSelf', None]:
    """测试用 OneBot V11 Bot: 随机数字 self_id 且已落库, 测试类结束后清理"""
    async with persisted_numeric_obv11_bot() as bot:
        yield bot


@pytest.fixture(autouse=True)
def first_respond_registry_sandbox() -> Generator[None, None, None]:
    """omega_base 多 Bot 响应去重注册表沙箱 (快照清空, 测试后恢复)

    本目录用例共享同一超管 ID 但使用不同的测试 Bot, 不清空注册表会导致后续 Bot 的事件被忽略
    """
    with _first_respond_registry_sandbox_cm():
        yield
