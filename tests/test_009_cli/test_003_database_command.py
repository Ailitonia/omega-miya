"""
@Author         : Ailitonia
@Date           : 2026/11/6 19:24
@FileName       : test_003_database_command
@Project        : omega-miya
@Description    : CLI 数据库命令解析与处理器测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

import pytest

from tests.test_009_cli.helpers import make_cli_args, parse_cli


class TestParseDatabaseCommands:
    """数据库命令行参数解析测试"""

    @pytest.mark.parametrize(
        ('argv', 'field', 'expected'),
        [
            (['--run'], 'run', True),
            (['--database-check'], 'database_check', True),
            (['--database-upgrade-to-head'], 'database_upgrade_to_head', True),
            (['--database-upgrade', 'abc123'], 'database_upgrade', 'abc123'),
            (['--database-downgrade', 'abc123'], 'database_downgrade', 'abc123'),
            (['--database-revision', 'add table'], 'database_revision', 'add table'),
            (['--database-stamp', 'head'], 'database_stamp', 'head'),
        ],
    )
    def test_command_parsed_to_field(self, argv: list[str], field: str, expected: Any):
        args = parse_cli(argv)
        assert getattr(args, field) == expected
        assert args.enabled_options == [field]

    def test_numeric_revision_coerced_to_str(self):
        """数字形式的版本号参数被模型强制转换为字符串"""
        args = parse_cli(['--database-upgrade', '123'])
        assert args.database_upgrade == '123'
        assert isinstance(args.database_upgrade, str)

    @pytest.mark.parametrize(
        'argv',
        [
            ['--run', '--database-check'],
            ['--database-check', '--database-upgrade', 'head'],
            ['--database-upgrade', 'a', '--database-downgrade', 'b'],
        ],
    )
    def test_mutually_exclusive_rejected(self, argv: list[str]):
        """互斥组同时提供多个命令时 argparse 拒绝解析"""
        from src.cli import build_cli_parser

        parser = build_cli_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(argv)

    @pytest.mark.parametrize(
        'command',
        ['--tool-execute', '--database-upgrade', '--database-downgrade', '--database-revision', '--database-stamp'],
    )
    @pytest.mark.parametrize('value', ['', '   '])
    def test_empty_value_rejected(self, command: str, value: str):
        """带值命令的空值/纯空白值被 argparse 拒绝, 不进入模型与派发层"""
        from src.cli import build_cli_parser

        parser = build_cli_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([command, value])


class TestDatabaseHandlerGuards:
    """数据库命令处理器守卫子句测试 (falsy 参数在 nonebot 初始化前拒绝)"""

    @pytest.mark.parametrize(
        ('handler_name', 'field'),
        [
            ('run_database_upgrade', 'database_upgrade'),
            ('run_database_downgrade', 'database_downgrade'),
            ('run_database_revision', 'database_revision'),
            ('run_database_stamp', 'database_stamp'),
        ],
    )
    @pytest.mark.parametrize('value', [None, ''])
    def test_falsy_argument_rejected(self, handler_name: str, field: str, value: str | None):
        import src.cli.handler as cli_handler

        handler = getattr(cli_handler, handler_name)
        args = make_cli_args(**{field: value})
        with pytest.raises(ValueError, match='not provide'):
            handler(args)


class TestDatabaseHandlers:
    """数据库命令处理器 happy path 测试 (patch 项目自有 migrate 函数为记录型 fake)"""

    @pytest.fixture
    def recorded_migrate_calls(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
        """将 src.database.migrate 的命令函数替换为记录型 fake, 断言处理器不触达真实数据库"""
        import src.database.migrate as migrate

        calls: list[tuple[str, dict[str, Any]]] = []

        def _make_fake(name: str):
            def _fake(**kwargs: Any) -> None:
                calls.append((name, kwargs))

            return _fake

        for name in (
                'run_check_current',
                'run_upgrade_migrations',
                'run_downgrade_migrations',
                'run_revision',
                'run_stamp',
        ):
            monkeypatch.setattr(migrate, name, _make_fake(name))

        return calls

    def test_database_check(self, recorded_migrate_calls):
        from src.cli.handler import run_database_check

        run_database_check(make_cli_args(database_check=True))
        assert recorded_migrate_calls == [('run_check_current', {})]

    def test_database_upgrade_to_head(self, recorded_migrate_calls):
        from src.cli.handler import run_database_upgrade_to_head

        run_database_upgrade_to_head(make_cli_args(database_upgrade_to_head=True))
        assert recorded_migrate_calls == [('run_upgrade_migrations', {'revision': 'head'})]

    def test_database_upgrade(self, recorded_migrate_calls):
        from src.cli.handler import run_database_upgrade

        run_database_upgrade(make_cli_args(database_upgrade='abc123'))
        assert recorded_migrate_calls == [('run_upgrade_migrations', {'revision': 'abc123'})]

    def test_database_downgrade(self, recorded_migrate_calls):
        from src.cli.handler import run_database_downgrade

        run_database_downgrade(make_cli_args(database_downgrade='abc123'))
        assert recorded_migrate_calls == [('run_downgrade_migrations', {'revision': 'abc123'})]

    def test_database_revision(self, recorded_migrate_calls):
        from src.cli.handler import run_database_revision

        run_database_revision(make_cli_args(database_revision='add table'))
        assert recorded_migrate_calls == [('run_revision', {'message': 'add table'})]

    def test_database_stamp(self, recorded_migrate_calls):
        from src.cli.handler import run_database_stamp

        run_database_stamp(make_cli_args(database_stamp='abc123'))
        assert recorded_migrate_calls == [('run_stamp', {'revision_id': 'abc123'})]


class TestDispatchTableStructure:
    """派发表与模型字段的结构一致性测试 (防模型字段与派发表漂移)"""

    def test_dispatch_keys_match_model_fields(self):
        from src.cli import DISPATCH_HANDLERS
        from src.cli.command import CliQueryArguments

        assert set(CliQueryArguments.model_fields) - {'extra_args'} == set(DISPATCH_HANDLERS)

    def test_dispatch_values_are_handlers(self):
        import src.cli.handler as cli_handler
        from src.cli import DISPATCH_HANDLERS

        expected = {
            'run': cli_handler.run_bot,
            'tool_execute': cli_handler.run_tool_execute,
            'database_check': cli_handler.run_database_check,
            'database_upgrade': cli_handler.run_database_upgrade,
            'database_upgrade_to_head': cli_handler.run_database_upgrade_to_head,
            'database_downgrade': cli_handler.run_database_downgrade,
            'database_revision': cli_handler.run_database_revision,
            'database_stamp': cli_handler.run_database_stamp,
        }
        assert DISPATCH_HANDLERS == expected
