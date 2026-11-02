"""
@Author         : Ailitonia
@Date           : 2026/11/6 19:24
@FileName       : helpers
@Project        : omega-miya
@Description    : CLI 测试公共辅助函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.cli.command import CliQueryArguments


def parse_cli(argv: list[str]) -> 'CliQueryArguments':
    """一行式 CLI 参数解析: 构造解析器并解析为 CliQueryArguments"""
    from src.cli import build_cli_parser, parse_cli_args

    return parse_cli_args(build_cli_parser().parse_args(argv))


def make_cli_args(**overrides: Any) -> 'CliQueryArguments':
    """构造全字段默认关闭的 CliQueryArguments, 以关键字覆盖指定字段"""
    from src.cli.command import CliQueryArguments

    return CliQueryArguments(**overrides)
