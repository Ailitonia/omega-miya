"""
@Author         : Ailitonia
@Date           : 2026/8/21 22:19
@FileName       : command
@Project        : omega-miya
@Description    : 命令行参数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import argparse
import sys
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field


def _nonempty_str(value: str) -> str:
    """argparse 参数值类型: 拒绝空值及纯空白字符串"""
    if not value.strip():
        raise argparse.ArgumentTypeError('value must not be empty')
    return value


def build_cli_parser() -> argparse.ArgumentParser:
    """定义并返回 CLI 的参数解析器"""
    parser = argparse.ArgumentParser(
        prog='omega-miya',
        description='omega-miya入口脚本',
        epilog='python bot.py [COMMAND] [OPTIONS], 不带任何参数时默认执行 --run',
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--run', action='store_true', help='启动Omega Miya')
    group.add_argument('--tool-execute', type=_nonempty_str, metavar='MODULE[:FUNC]',
                       help='执行 tools/ 下的工具模块入口函数, 例如 --tool-execute some_tool:main')
    group.add_argument('--database-check', action='store_true', help='检查数据库版本')
    group.add_argument('--database-upgrade-to-head', action='store_true', help='升级数据库到最新')
    group.add_argument('--database-upgrade', type=_nonempty_str, help='升级数据库到指定版本')
    group.add_argument('--database-downgrade', type=_nonempty_str, help='降级数据库到指定版本')
    group.add_argument('--database-revision', type=_nonempty_str, help='生成数据库迁移版本')
    group.add_argument('--database-stamp', type=_nonempty_str, help='手动标记数据库版本')
    parser.add_argument('extra_args', nargs='*')
    return parser


class CliQueryArguments(BaseModel):
    """CLI 命令的解析结果 Model"""
    run: bool = False
    tool_execute: str | None = None
    database_check: bool = False
    database_upgrade_to_head: bool = False
    database_upgrade: str | None = None
    database_downgrade: str | None = None
    database_revision: str | None = None
    database_stamp: str | None = None
    extra_args: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True)

    @property
    def enabled_options(self) -> list[str]:
        """解析结果中已启用的可选命令名, 不包含 `extra_args` 参数组"""
        return [k for k, v in self.model_dump(exclude={'extra_args'}).items() if v]


def parse_cli_args(args: argparse.Namespace) -> CliQueryArguments:
    """解析查询命令参数"""
    return CliQueryArguments.model_validate(args)


def parse_cli_command(argv: Sequence[str] | None = None) -> CliQueryArguments:
    """构造解析器并解析命令行参数

    不带任何参数时默认执行为 ``--run``; 提供了参数时执行解析与校验
    """
    if argv is None:
        argv = sys.argv[1:]
    return parse_cli_args(build_cli_parser().parse_args(list(argv) or ['--run']))


__all__ = [
    'CliQueryArguments',
    'build_cli_parser',
    'parse_cli_args',
    'parse_cli_command',
]
