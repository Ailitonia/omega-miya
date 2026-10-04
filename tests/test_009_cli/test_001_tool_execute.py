"""
@Author         : Ailitonia
@Date           : 2026/9/1 21:00
@FileName       : test_001_tool_execute
@Project        : omega-miya
@Description    : CLI --tool-execute 命令测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pytest


class TestParseToolTarget:
    """工具执行目标解析测试"""

    def test_full_target(self):
        from src.cli.hanlder import _parse_tool_target

        assert _parse_tool_target('some_tool:main') == ('tools.some_tool', 'main')

    def test_default_func(self):
        from src.cli.hanlder import _parse_tool_target

        assert _parse_tool_target('some_tool') == ('tools.some_tool', 'main')

    def test_nested_module(self):
        from src.cli.hanlder import _parse_tool_target

        assert _parse_tool_target('migration_from_old_version.import_to_v1_from_v092:main') == (
            'tools.migration_from_old_version.import_to_v1_from_v092',
            'main',
        )

    @pytest.mark.parametrize(
        'target',
        [
            '',
            ':main',
            'some_tool:',
            'some_tool:1func',
            'some..tool:main',
            '.some_tool:main',
            'some/tool:main',
            'some_tool:main:extra',
        ],
    )
    def test_invalid_target(self, target: str):
        from src.cli.hanlder import _parse_tool_target

        with pytest.raises(ValueError, match='invalid tool target'):
            _parse_tool_target(target)


class TestToolExecuteCliArgs:
    """--tool-execute 命令行参数解析与派发登记测试"""

    def test_parse_tool_execute_arg(self):
        from src.cli import build_cli_parser, parse_cli_args

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', 'some_tool:main']))
        assert args.tool_execute == 'some_tool:main'

    def test_dispatch_handler_registered(self):
        from src.cli import DISPATCH_HANDERS

        assert 'tool_execute' in DISPATCH_HANDERS


class TestParseExtraArgs:
    """CLI 位置参数 extra_args 解析测试"""

    def test_default_empty(self):
        from src.cli import build_cli_parser, parse_cli_args

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--run']))
        assert args.extra_args == []

    def test_extra_args_after_option(self):
        from src.cli import build_cli_parser, parse_cli_args

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', 'some_tool:main', 'a', 'b', 'c']))
        assert args.extra_args == ['a', 'b', 'c']

    def test_extra_args_with_double_dash(self):
        """-- 之后的 - 前缀参数应被当作位置参数捕获"""
        from src.cli import build_cli_parser, parse_cli_args

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', 'some_tool:main', '--', '--flag', '-x']))
        assert args.extra_args == ['--flag', '-x']

    def test_bare_dash_arg_rejected(self):
        """未经 -- 分隔的 - 前缀参数会被 argparse 拒绝"""
        from src.cli import build_cli_parser

        parser = build_cli_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['--tool-execute', 'some_tool:main', '--flag'])

    def test_intermixed_positionals_rejected(self):
        """位置参数被选项分隔为两段时 argparse 无法二次消费, 报 unrecognized arguments"""
        from src.cli import build_cli_parser

        parser = build_cli_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['a', '--tool-execute', 'some_tool:main', 'b'])

    def test_numeric_extra_args_keep_str(self):
        from src.cli import build_cli_parser, parse_cli_args

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', 'some_tool:main', '123', '4.5']))
        assert args.extra_args == ['123', '4.5']
        assert all(isinstance(x, str) for x in args.extra_args)

    @pytest.mark.parametrize(
        'argv',
        [
            ['--run', 'x'],
            ['--database-upgrade', 'head', 'x', 'y'],
        ],
    )
    def test_extra_args_with_other_commands(self, argv: list[str]):
        """非 tool-execute 命令也可解析 extra_args (由各自 handler 决定是否使用)"""
        from src.cli import build_cli_parser, parse_cli_args

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(argv))
        expected = argv[1:] if argv[0] == '--run' else argv[2:]
        assert args.extra_args == expected


class TestEnabledOptions:
    """CliQueryArguments.enabled_options 属性测试"""

    def test_excludes_extra_args(self):
        from src.cli import build_cli_parser, parse_cli_args

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', 'some_tool:main', 'a', 'b']))
        assert args.enabled_options == ['tool_execute']

    def test_all_default_empty(self):
        from src.cli.command import CliQueryArguments

        args = CliQueryArguments(
            run=False,
            tool_execute=None,
            database_check=False,
            database_upgrade_to_head=False,
            database_upgrade=None,
            database_downgrade=None,
            database_revision=None,
            database_stamp=None,
        )
        assert args.enabled_options == []

    def test_multiple_enabled(self):
        from src.cli.command import CliQueryArguments

        args = CliQueryArguments(
            run=True,
            tool_execute='some_tool:main',
            database_check=False,
            database_upgrade_to_head=False,
            database_upgrade=None,
            database_downgrade=None,
            database_revision=None,
            database_stamp=None,
        )
        assert args.enabled_options == ['run', 'tool_execute']


class TestExecuteCliHandlerDispatch:
    """execute_cli_handler 派发测试"""

    def test_dispatch_with_extra_args(self, monkeypatch: pytest.MonkeyPatch):
        from src import cli
        from src.cli import build_cli_parser, parse_cli_args

        received = []
        monkeypatch.setitem(cli.DISPATCH_HANDERS, 'tool_execute', received.append)

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', 'some_tool:main', 'a', 'b']))
        cli.execute_cli_handler(args)

        assert len(received) == 1
        assert received[0] is args
        assert received[0].extra_args == ['a', 'b']

    def test_exceeding_options(self):
        from src.cli import execute_cli_handler
        from src.cli.command import CliQueryArguments

        args = CliQueryArguments(
            run=True,
            tool_execute='some_tool:main',
            database_check=False,
            database_upgrade_to_head=False,
            database_upgrade=None,
            database_downgrade=None,
            database_revision=None,
            database_stamp=None,
        )
        with pytest.raises(ValueError, match='parsed exceeding options'):
            execute_cli_handler(args)


class TestRunToolExecuteExtraArgs:
    """run_tool_execute 透传 extra_args 到入口函数测试"""

    @pytest.fixture
    def fake_tool_module(self):
        """向 sys.modules 注入伪造的 tools 模块, 入口函数记录收到的位置参数, 测试后移除"""
        import sys
        import types

        import tools  # noqa: F401 确保父包已导入

        module = types.ModuleType('tools._test_cli_fake')
        received: list[tuple[str, tuple[str, ...]]] = []

        def main(*args: str) -> None:
            received.append(('sync', args))

        async def amain(*args: str) -> None:
            received.append(('async', args))

        module.main = main
        module.amain = amain
        sys.modules['tools._test_cli_fake'] = module
        try:
            yield received
        finally:
            sys.modules.pop('tools._test_cli_fake', None)

    def test_sync_entry_receives_extra_args(self, fake_tool_module):
        from src.cli import build_cli_parser, parse_cli_args
        from src.cli.hanlder import run_tool_execute

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', '_test_cli_fake:main', 'x', 'y']))
        run_tool_execute(args)

        assert fake_tool_module == [('sync', ('x', 'y'))]

    def test_async_entry_receives_extra_args(self, fake_tool_module):
        from src.cli import build_cli_parser, parse_cli_args
        from src.cli.hanlder import run_tool_execute

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', '_test_cli_fake:amain', 'x', 'y']))
        run_tool_execute(args)

        assert fake_tool_module == [('async', ('x', 'y'))]

    def test_entry_called_without_args(self, fake_tool_module):
        from src.cli import build_cli_parser, parse_cli_args
        from src.cli.hanlder import run_tool_execute

        parser = build_cli_parser()
        args = parse_cli_args(parser.parse_args(['--tool-execute', '_test_cli_fake:main']))
        run_tool_execute(args)

        assert fake_tool_module == [('sync', ())]
