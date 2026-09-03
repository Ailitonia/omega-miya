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

from .command import build_cli_parser, parse_cli_args
from .hanlder import (
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

DISPATCH_HANDERS: dict[str, 'CliHandler'] = {
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
    enabled_arg_in_mutually_exclusive_commands = [k for k, v in args.model_dump().items() if v]
    if len(enabled_arg_in_mutually_exclusive_commands) > 1:
        raise ValueError('parsed exceeding options, only need 1')

    handler = DISPATCH_HANDERS.get(enabled_arg_in_mutually_exclusive_commands[0], run_bot)
    handler(args)


__all__ = [
    'build_cli_parser',
    'execute_cli_handler',
    'parse_cli_args',
]
