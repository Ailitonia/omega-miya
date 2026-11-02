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

from tests.test_009_cli.helpers import make_cli_args, parse_cli


class TestParseToolTarget:
    """工具执行目标解析测试"""

    def test_full_target(self):
        from src.cli.handler import _parse_tool_target

        assert _parse_tool_target('some_tool:main') == ('tools.some_tool', 'main')

    def test_default_func(self):
        from src.cli.handler import _parse_tool_target

        assert _parse_tool_target('some_tool') == ('tools.some_tool', 'main')

    def test_nested_module(self):
        from src.cli.handler import _parse_tool_target

        assert _parse_tool_target('migration_from_old_version.import_to_v1_from_v092:main') == (
            'tools.migration_from_old_version.import_to_v1_from_v092',
            'main',
        )

    def test_deeply_nested_module(self):
        from src.cli.handler import _parse_tool_target

        assert _parse_tool_target('a.b.c:func') == ('tools.a.b.c', 'func')

    def test_keyword_like_name_accepted(self):
        """isidentifier 不排除 Python 关键字, 关键字名通过格式校验, 是否可导入由后续 import 阶段决定"""
        from src.cli.handler import _parse_tool_target

        assert _parse_tool_target('import') == ('tools.import', 'main')

    def test_unicode_identifier_accepted(self):
        from src.cli.handler import _parse_tool_target

        assert _parse_tool_target('工具') == ('tools.工具', 'main')

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
            ' ',
            'some tool:main',
            'some_tool:main func',
        ],
    )
    def test_invalid_target(self, target: str):
        from src.cli.handler import _parse_tool_target

        with pytest.raises(ValueError, match='invalid tool target'):
            _parse_tool_target(target)


class TestToolExecuteCliArgs:
    """--tool-execute 命令行参数解析与派发登记测试"""

    def test_parse_tool_execute_arg(self):
        args = parse_cli(['--tool-execute', 'some_tool:main'])
        assert args.tool_execute == 'some_tool:main'

    def test_dispatch_handler_registered(self):
        from src.cli import DISPATCH_HANDLERS

        assert 'tool_execute' in DISPATCH_HANDLERS


class TestParseExtraArgs:
    """CLI 位置参数 extra_args 解析测试"""

    def test_default_empty(self):
        args = parse_cli(['--run'])
        assert args.extra_args == []

    def test_extra_args_after_option(self):
        args = parse_cli(['--tool-execute', 'some_tool:main', 'a', 'b', 'c'])
        assert args.extra_args == ['a', 'b', 'c']

    def test_extra_args_with_double_dash(self):
        """-- 之后的 - 前缀参数应被当作位置参数捕获"""
        args = parse_cli(['--tool-execute', 'some_tool:main', '--', '--flag', '-x'])
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
        args = parse_cli(['--tool-execute', 'some_tool:main', '123', '4.5'])
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
        args = parse_cli(argv)
        expected = argv[1:] if argv[0] == '--run' else argv[2:]
        assert args.extra_args == expected


class TestEnabledOptions:
    """CliQueryArguments.enabled_options 属性测试"""

    def test_excludes_extra_args(self):
        args = parse_cli(['--tool-execute', 'some_tool:main', 'a', 'b'])
        assert args.enabled_options == ['tool_execute']

    def test_all_default_empty(self):
        args = make_cli_args()
        assert args.enabled_options == []

    def test_multiple_enabled(self):
        args = make_cli_args(run=True, tool_execute='some_tool:main')
        assert args.enabled_options == ['run', 'tool_execute']

    def test_empty_string_value_excluded(self):
        """空串命令值按 falsy 过滤为未启用 (CLI 路径的空值已由 argparse 层拒绝)"""
        args = make_cli_args(database_revision='')
        assert args.enabled_options == []


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
        from src.cli.handler import run_tool_execute

        args = parse_cli(['--tool-execute', '_test_cli_fake:main', 'x', 'y'])
        run_tool_execute(args)

        assert fake_tool_module == [('sync', ('x', 'y'))]

    def test_async_entry_receives_extra_args(self, fake_tool_module):
        from src.cli.handler import run_tool_execute

        args = parse_cli(['--tool-execute', '_test_cli_fake:amain', 'x', 'y'])
        run_tool_execute(args)

        assert fake_tool_module == [('async', ('x', 'y'))]

    def test_entry_called_without_args(self, fake_tool_module):
        from src.cli.handler import run_tool_execute

        args = parse_cli(['--tool-execute', '_test_cli_fake:main'])
        run_tool_execute(args)

        assert fake_tool_module == [('sync', ())]


class TestRunToolExecuteErrors:
    """run_tool_execute 错误路径测试"""

    @pytest.fixture
    def fake_tool_module(self):
        """向 sys.modules 注入伪造的 tools 模块, 包含函数入口与非函数属性, 测试后移除"""
        import sys
        import types

        import tools  # noqa: F401 确保父包已导入

        module = types.ModuleType('tools._test_cli_fake_err')

        def main(*args: str) -> None:
            pass

        module.main = main
        module.NOT_A_FUNC = 42
        sys.modules['tools._test_cli_fake_err'] = module
        try:
            yield module
        finally:
            sys.modules.pop('tools._test_cli_fake_err', None)

    def test_empty_target_rejected(self):
        """空 target 在 nonebot 初始化前即被守卫子句拒绝"""
        from src.cli.handler import run_tool_execute

        args = make_cli_args(tool_execute='')
        with pytest.raises(ValueError, match='not provide tool target'):
            run_tool_execute(args)

    def test_invalid_target_rejected(self):
        """非法 target 在 nonebot 初始化前即被目标解析拒绝"""
        from src.cli.handler import run_tool_execute

        args = make_cli_args(tool_execute='some/tool:main')
        with pytest.raises(ValueError, match='invalid tool target'):
            run_tool_execute(args)

    def test_module_not_found(self):
        from src.cli.handler import run_tool_execute

        args = parse_cli(['--tool-execute', '_test_cli_nonexistent_tool'])
        with pytest.raises(ValueError, match='tool module not found'):
            run_tool_execute(args)

    def test_function_not_found(self, fake_tool_module):
        from src.cli.handler import run_tool_execute

        args = parse_cli(['--tool-execute', '_test_cli_fake_err:nonexistent'])
        with pytest.raises(ValueError, match='tool function not found'):
            run_tool_execute(args)

    def test_target_not_function(self, fake_tool_module):
        from src.cli.handler import run_tool_execute

        args = parse_cli(['--tool-execute', '_test_cli_fake_err:NOT_A_FUNC'])
        with pytest.raises(TypeError, match='not function'):
            run_tool_execute(args)

    def test_internal_dependency_missing_propagates(self, tmp_path, monkeypatch: pytest.MonkeyPatch):
        """工具模块内部依赖缺失时原样抛出 ModuleNotFoundError, 不转换为目标模块缺失的友好提示"""
        import importlib

        import tools

        dep_name = '_test_cli_missing_dep'
        (tmp_path / '_test_cli_depfail.py').write_text(f'import {dep_name}\n', encoding='utf-8')
        monkeypatch.setattr(tools, '__path__', [*tools.__path__, str(tmp_path)])
        importlib.invalidate_caches()

        from src.cli.handler import run_tool_execute

        args = parse_cli(['--tool-execute', '_test_cli_depfail'])
        with pytest.raises(ModuleNotFoundError) as exc_info:
            run_tool_execute(args)
        assert exc_info.value.name == dep_name
