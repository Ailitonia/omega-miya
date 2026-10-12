"""
@Author         : Ailitonia
@Date           : 2026/10/13
@FileName       : conftest.py
@Project        : omega-miya
@Description    : dal_crud 单元测试共享 fixtures

注意:
- 测试模块在 pytest 收集阶段导入时 NoneBot 尚未初始化 (nonebug 在 session fixture 中才执行 nonebot.init()),
  此时顶层导入 src.* 会触发 src/database/config.py 的 get_plugin_config 失败并 sys.exit,
  因此所有 src.* 的导入一律放在 fixture/测试函数体内 (define_dal_fixtures 同样以字符串路径惰性解析 DAL 类)
- 本目录测试直接复用 src.database 的数据库连接, 操作 .env.test 配置的测试数据库, 禁止将测试环境指向生产数据库运行
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import inspect
from collections.abc import AsyncGenerator
from typing import Any

import pytest


def define_dal_fixtures(
        dal_path: str,
        fixture_name: str,
        *,
        extra_dependencies: tuple[str, ...] = (),
) -> tuple[Any, Any]:
    """定义 DAL 测试 fixture 对: class 级 DAL fixture + autouse `_clean_table` 清表 fixture

    DAL 类以字符串路径在 fixture 执行时惰性解析 (importlib), 避免收集期导入 src.*;
    DAL fixture 以显式 name=fixture_name 注册, 各模块可使用不同的 fixture 名;
    `_clean_table` 通过动态签名声明对 DAL fixture 的依赖, 在每个测试用例执行前清空数据表并提交;
    extra_dependencies 声明 DAL fixture 的前置依赖 fixture 名 (如需先播种父行的场景, 仅用于保证初始化顺序)

    :return: (dal_fixture, clean_table_fixture), 在测试模块顶层解包赋值即可被 pytest 收集
    """

    async def _dal_fixture(**kwargs: Any) -> AsyncGenerator[Any, None]:
        import importlib

        module_name, _, class_name = dal_path.rpartition('.')
        dal_cls = getattr(importlib.import_module(module_name), class_name)

        async with dal_cls.create() as dal:
            yield dal

    _dal_fixture.__name__ = fixture_name
    if extra_dependencies:
        _dal_fixture.__signature__ = inspect.Signature(parameters=[  # type: ignore[attr-defined]
            inspect.Parameter(name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for name in extra_dependencies
        ])

    async def _clean_table(**kwargs: Any) -> None:
        """每个测试用例执行前清空数据表"""
        dal = kwargs[fixture_name]
        await dal._clear_all()
        await dal.commit_session()

    _clean_table.__signature__ = inspect.Signature(parameters=[  # type: ignore[attr-defined]
        inspect.Parameter(fixture_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ])

    dal_fixture = pytest.fixture(scope='class', name=fixture_name)(_dal_fixture)
    clean_table_fixture = pytest.fixture(autouse=True)(_clean_table)
    return dal_fixture, clean_table_fixture


@pytest.fixture
def require_savepoint_support() -> None:
    """SQLite 后端跳过嵌套事务 (SAVEPOINT) 语义相关用例

    SQLite 后端 (aiosqlite 默认 legacy 事务控制, 会话事务不显式发送 BEGIN) 下,
    外层事务的首个语句若为 SAVEPOINT 则物理事务由 SAVEPOINT 开启且 RELEASE 即提交,
    外层 rollback 无法撤销插入, 属驱动层限制而非 DAL 逻辑问题, 故本平台跳过该用例
    """
    from src.database.config import database_config

    if database_config.database == 'sqlite':
        pytest.skip('SQLite 驱动 legacy 事务控制下嵌套插入无法被外层事务回滚, 跳过')
