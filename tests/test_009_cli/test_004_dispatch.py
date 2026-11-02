"""
@Author         : Ailitonia
@Date           : 2026/11/6 19:24
@FileName       : test_004_dispatch
@Project        : omega-miya
@Description    : CLI execute_cli_handler 派发语义测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pytest

from tests.test_009_cli.helpers import make_cli_args, parse_cli


class TestExecuteCliHandler:
    """execute_cli_handler 派发语义测试"""

    @pytest.mark.parametrize(
        ('argv', 'command'),
        [
            (['--run'], 'run'),
            (['--tool-execute', 'some_tool:main'], 'tool_execute'),
            (['--database-check'], 'database_check'),
            (['--database-upgrade-to-head'], 'database_upgrade_to_head'),
            (['--database-upgrade', 'abc123'], 'database_upgrade'),
            (['--database-downgrade', 'abc123'], 'database_downgrade'),
            (['--database-revision', 'msg'], 'database_revision'),
            (['--database-stamp', 'abc123'], 'database_stamp'),
        ],
    )
    def test_dispatch_to_mapped_handler(self, monkeypatch: pytest.MonkeyPatch, argv: list[str], command: str):
        """每个命令派发到派发表映射的处理器, 且透传同一个 args 对象"""
        from src import cli

        received = []
        monkeypatch.setitem(cli.DISPATCH_HANDLERS, command, received.append)

        args = parse_cli(argv)
        cli.execute_cli_handler(args)

        assert len(received) == 1
        assert received[0] is args

    def test_dispatch_passes_extra_args(self, monkeypatch: pytest.MonkeyPatch):
        """位置参数随 args 对象透传到处理器"""
        from src import cli

        received = []
        monkeypatch.setitem(cli.DISPATCH_HANDLERS, 'tool_execute', received.append)

        args = parse_cli(['--tool-execute', 'some_tool:main', 'a', 'b'])
        cli.execute_cli_handler(args)

        assert len(received) == 1
        assert received[0].extra_args == ['a', 'b']

    def test_empty_options_fallback_to_run(self, monkeypatch: pytest.MonkeyPatch):
        """无启用选项时兜底派发 run (与 parse_cli_command 空参默认 --run 语义一致)"""
        from src import cli

        received = []
        monkeypatch.setitem(cli.DISPATCH_HANDLERS, 'run', received.append)

        args = make_cli_args()
        cli.execute_cli_handler(args)

        assert len(received) == 1
        assert received[0] is args

    def test_empty_string_value_fallback_to_run(self, monkeypatch: pytest.MonkeyPatch):
        """程序式构造的空串命令值按 falsy 视为未启用, 兜底派发 run (CLI 路径的空值已由 argparse 层拒绝)"""
        from src import cli

        received = []
        monkeypatch.setitem(cli.DISPATCH_HANDLERS, 'run', received.append)

        args = make_cli_args(database_revision='')
        cli.execute_cli_handler(args)

        assert len(received) == 1
        assert received[0] is args

    def test_multiple_enabled_options_rejected(self):
        """多个启用选项被拒绝, 报错信息包含冲突的选项名"""
        from src.cli import execute_cli_handler

        args = make_cli_args(run=True, database_check=True)
        with pytest.raises(ValueError, match=r"mutually exclusive options: \['run', 'database_check'\]"):
            execute_cli_handler(args)
