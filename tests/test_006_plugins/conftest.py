"""
@Author         : Ailitonia
@Date           : 2026/10/12
@FileName       : conftest
@Project        : omega-miya
@Description    : omega_core_manager 插件单元测试 fixtures

    - 模块顶层在收集期向进程环境变量注入随机超级管理员 ID (先于 nonebug 执行 nonebot.init()),
      合并而非覆盖 .env.test 既有 SUPERUSERS, 仅当前测试进程内生效
    - fixture 提供已落库的数字 self_id OneBot V11 Bot / 插件启用状态守护
    - 遵守项目约定: `src.*` 导入必须留在函数体内 (测试模块在 nonebot 初始化前被收集导入)

@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import json
import os
import random
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from dotenv import get_key

from tests.utils import (
    first_respond_registry_sandbox as _first_respond_registry_sandbox_cm,
)
from tests.utils import (
    persisted_numeric_obv11_bot,
    preserve_plugin_row,
)

if TYPE_CHECKING:
    from src.database.internal.bot import BotSelf

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_configured_superusers() -> list[str]:
    """读取当前生效的超级用户配置 (进程环境变量优先, 其次 .env.test / .env)"""
    raw = os.environ.get('SUPERUSERS')
    if raw is None:
        for env_file in ('.env.test', '.env'):
            raw = get_key(_PROJECT_ROOT / env_file, 'SUPERUSERS')
            if raw is not None:
                break
    if raw is None:
        return []
    try:
        return [str(x) for x in json.loads(raw)]
    except json.JSONDecodeError:
        return [raw]


_EXISTING_SUPERUSERS = _load_configured_superusers()

TEST_SUPERUSER_ID = str(random.randint(100_000_000, 999_999_999))
"""本测试会话注入的随机超级管理员 ID"""
while TEST_SUPERUSER_ID in _EXISTING_SUPERUSERS:
    TEST_SUPERUSER_ID = str(random.randint(100_000_000, 999_999_999))

# 收集期注入 (nonebug 在执行期才 nonebot.init()), 合并既有配置避免遮蔽其他用例依赖的超级用户
os.environ['SUPERUSERS'] = json.dumps([*_EXISTING_SUPERUSERS, TEST_SUPERUSER_ID])


@pytest.fixture
def test_superuser_id() -> int:
    """本测试会话注入的随机超级管理员 ID (int 形式, 用于构造 OneBot V11 事件)"""
    return int(TEST_SUPERUSER_ID)


@pytest.fixture(scope='class')
async def numeric_bot() -> AsyncGenerator['BotSelf', None]:
    """测试用 OneBot V11 Bot: 随机数字 self_id 且已落库, 测试类结束后清理"""
    async with persisted_numeric_obv11_bot() as bot:
        yield bot


@pytest.fixture
async def core_manager_enabled_guard() -> AsyncGenerator[None, None]:
    """保证 omega_core_manager 插件行存在且启用, 测试后恢复原状态

    插件管理预处理器对非超级用户校验插件启用状态, 且不看 processor state;
    全量套件中 test_001_database 的迁移检查会清空插件表, 不能依赖启动时播种的行仍然存在
    """
    async with preserve_plugin_row('omega_core_manager', 'src.plugins.omega_core_manager', ensure_enabled=True):
        yield


@pytest.fixture(autouse=True)
def first_respond_registry_sandbox() -> Generator[None, None, None]:
    """omega_base 多 Bot 响应去重注册表沙箱 (快照清空, 测试后恢复)

    本目录用例共享同一超管 ID 但使用不同的测试 Bot, 不清空注册表会导致后续 Bot 的事件被忽略
    """
    with _first_respond_registry_sandbox_cm():
        yield
