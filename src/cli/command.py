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

from pydantic import BaseModel, ConfigDict


def build_cli_parser() -> argparse.ArgumentParser:
    """定义并返回 CLI 的参数解析器"""
    parser = argparse.ArgumentParser(
        prog='omega-miya',
        description='omega-miya入口脚本',
        epilog='python bot.py [COMMAND] [OPTIONS]',
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--run', action='store_true', help='启动Omega Miya')
    group.add_argument('--database-check', action='store_true', help='检查数据库版本')
    group.add_argument('--database-upgrade-to-head', action='store_true', help='升级数据库到最新')
    group.add_argument('--database-upgrade', type=str, help='升级数据库到指定版本')
    group.add_argument('--database-downgrade', type=str, help='降级数据库到指定版本')
    group.add_argument('--database-revision', type=str, help='生成数据库迁移版本')
    group.add_argument('--database-stamp', type=str, help='手动标记数据库版本')
    return parser


class CliQueryArguments(BaseModel):
    """CLI 命令的解析结果 Model"""
    run: bool
    database_check: bool
    database_upgrade_to_head: bool
    database_upgrade: str | None
    database_downgrade: str | None
    database_revision: str | None
    database_stamp: str | None

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True)


def parse_cli_args(args: argparse.Namespace) -> CliQueryArguments:
    """解析查询命令参数"""
    return CliQueryArguments.model_validate(args)


__all__ = [
    'CliQueryArguments',
    'build_cli_parser',
    'parse_cli_args',
]
