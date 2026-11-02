"""
@Author         : Ailitonia
@Date           : 2026/8/21 21:11
@FileName       : cli
@Project        : omega-miya
@Description    : 命令行参数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from .command import build_cli_parser, parse_cli_args, parse_cli_command
from .handler import (
    run_bot,
    run_database_check,
    run_database_downgrade,
    run_database_revision,
    run_database_stamp,
    run_database_upgrade,
    run_database_upgrade_to_head,
    run_tool_execute,
)

if TYPE_CHECKING:
    from .command import CliQueryArguments

    type CliHandler = Callable[[CliQueryArguments], None]
    """命令行执行函数"""

DISPATCH_HANDLERS: dict[str, 'CliHandler'] = {
    'run': run_bot,
    'tool_execute': run_tool_execute,
    'database_check': run_database_check,
    'database_upgrade': run_database_upgrade,
    'database_upgrade_to_head': run_database_upgrade_to_head,
    'database_downgrade': run_database_downgrade,
    'database_revision': run_database_revision,
    'database_stamp': run_database_stamp,
}
"""派发命令行执行函数"""


def execute_cli_handler(args: 'CliQueryArguments') -> None:
    enabled_options = args.enabled_options
    if len(enabled_options) > 1:
        raise ValueError(f'parsed mutually exclusive options: {enabled_options}, only 1 allowed')

    _command = enabled_options[0] if enabled_options else 'run'
    _handler = DISPATCH_HANDLERS.get(_command, run_bot)
    _handler(args)


__all__ = [
    'build_cli_parser',
    'execute_cli_handler',
    'parse_cli_args',
    'parse_cli_command',
]
