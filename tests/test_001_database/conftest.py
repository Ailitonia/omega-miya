"""
@Author         : Ailitonia
@Date           : 2026/8/23 15:40
@FileName       : conftest.py
@Project        : omega-miya
@Description    : database 单元测试 fixtures

注意:
- 测试模块在 pytest 收集阶段导入时 NoneBot 尚未初始化 (nonebug 在 session fixture 中才执行 nonebot.init()),
  此时顶层导入 src.* 会触发 src/database/config.py 的 get_plugin_config 失败并 sys.exit,
  因此所有 src.* 的导入一律放在 fixture/测试函数体内
- 本目录测试直接复用 src.database 的数据库连接, 操作 .env.test 配置的测试数据库, 禁止将测试环境指向生产数据库运行
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pytest

from tests.utils import unique_test_id


# ---------------------------------------------------------------------- #
# test_003_dal_crud 共享测试数据 fixtures (class 作用域, 每个消费类获得独立随机值)
# ---------------------------------------------------------------------- #


@pytest.fixture(scope='class')
def test_bot_type() -> str:
    """测试用 Bot 类型 (须为 BotType 枚举成员, 不可随机化)"""
    return 'OneBot V11'


@pytest.fixture(scope='class')
def test_bot_self_id() -> str:
    return unique_test_id('TEST_BOT')


@pytest.fixture(scope='class')
def test_sub_type() -> str:
    return unique_test_id('TEST_SUB_TYPE')


@pytest.fixture(scope='class')
def test_sub_id() -> str:
    return unique_test_id('TEST_SUB_ID')


@pytest.fixture(scope='class')
def test_sub_user_name() -> str:
    return unique_test_id('TEST_SUB_USER_NAME')
