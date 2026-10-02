"""
@Author         : Ailitonia
@Date           : 2026/10/2 10:45
@FileName       : conftest
@Project        : omega-miya
@Description    : test_004_tools 共享 fixtures(路径清理/样例数据/命名空间重绑定录制)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import shutil
from collections.abc import Generator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

from tests.utils import rebind_module_namespace

if TYPE_CHECKING:
    from src.resource import TemporaryResource


@pytest.fixture
def excel_tmp_folder() -> Generator['TemporaryResource', None, None]:
    """路径语义用例的临时目录资源(可继续拼接子路径), 用例结束后整体清理"""
    from src.resource import TemporaryResource

    folder = TemporaryResource('excel_tools_test')
    yield folder
    shutil.rmtree(folder.path, ignore_errors=True)


@pytest.fixture
def tz_aware_sample() -> dict[str, Any]:
    """时区感知 datetime 的非法样例字段(openpyxl 无法写出, 用于触发写出失败路径)"""
    return {'name': 'tz', 'count': 1, 'score': 1.0, 'enabled': True, 'created_at': datetime(2024, 1, 1, tzinfo=UTC)}


@pytest.fixture
def recorded_sleep(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> list[float | None]:
    """以替身 asyncio.sleep 录制 run_async_delay 实际传入的 delay(重绑定模块命名空间, 不污染全局 asyncio)

    以 @pytest.mark.parametrize('recorded_sleep', [True], indirect=True) 额外将模块内 random.gauss 固定为 -1.0
    """
    import src.utils.process_utils as process_utils

    recorded: list[float | None] = []

    async def _fake_sleep(*, delay: float | None = None) -> None:
        recorded.append(delay)

    rebind_module_namespace(monkeypatch, process_utils, 'asyncio', sleep=_fake_sleep)
    if getattr(request, 'param', False):
        rebind_module_namespace(monkeypatch, process_utils, 'random', gauss=lambda mu, sigma: -1.0)

    return recorded
