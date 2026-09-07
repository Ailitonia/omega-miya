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
