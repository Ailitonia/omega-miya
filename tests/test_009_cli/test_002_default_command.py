"""
@Author         : Ailitonia
@Date           : 2026/11/6 11:16
@FileName       : test_002_default_command
@Project        : omega-miya
@Description    : CLI 默认命令(不带参数时默认 --run)测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import sys

import pytest


class TestParseCliCommandDefault:
    """parse_cli_command 空参数默认 --run 测试"""

    def test_empty_argv_defaults_to_run(self):
        from src.cli import parse_cli_command

        args = parse_cli_command([])
        assert args.run is True
        assert args.enabled_options == ['run']

    def test_none_argv_reads_sys_argv(self, monkeypatch: pytest.MonkeyPatch):
        """argv 为 None 时读取 sys.argv, 裸启动(无额外参数)同样默认 --run"""
        from src.cli import parse_cli_command

        monkeypatch.setattr(sys, 'argv', ['bot.py'])
        args = parse_cli_command(None)
        assert args.run is True

    def test_explicit_command_unchanged(self):
        """提供了参数时保持原有解析行为, 不注入默认命令"""
        from src.cli import parse_cli_command

        args = parse_cli_command(['--tool-execute', 'some_tool:main'])
        assert args.run is False
        assert args.tool_execute == 'some_tool:main'

    def test_non_command_argv_still_rejected(self):
        """带参但缺少必需命令时仍按原有行为报错, 不静默回退 --run"""
        from src.cli import parse_cli_command

        with pytest.raises(SystemExit):
            parse_cli_command(['stray'])


class TestOmegaMiyaMainDefault:
    """bot.omega_miya_main 裸启动端到端派发测试"""

    def test_bare_invocation_dispatches_run(self, monkeypatch: pytest.MonkeyPatch):
        import bot
        import src.cli

        received = []
        monkeypatch.setattr(sys, 'argv', ['bot.py'])
        monkeypatch.setattr(src.cli, 'execute_cli_handler', received.append)

        bot.omega_miya_main()

        assert len(received) == 1
        assert received[0].run is True
