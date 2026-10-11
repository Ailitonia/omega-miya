"""
@Author         : Ailitonia
@Date           : 2023/7/5 2:00
@FileName       : helper
@Project        : nonebot2_miya
@Description    : 工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from arclet.alconna import Subcommand
from nonebot.plugin import get_loaded_plugins, get_plugin
from nonebot.rule import CommandRule
from nonebot_plugin_alconna.rule import AlconnaRule

from src.service.omega_base.internal.consts import SKIP_COOLDOWN_PERMISSION_NODE
from src.service.omega_processor.universal.processor_utils import parse_processor_state


def get_all_plugins_desc() -> str:
    """获取全部配置了自定义信息的插件信息"""
    plugins_custom_name = '\n'.join(sorted(
        plugin.metadata.name for plugin in get_loaded_plugins()
        if plugin.metadata and plugin.matcher  # 没有 matcher 的插件基本为 library, 忽略
    ))
    return f'现在已安装的插件有: \n\n{plugins_custom_name}\n\n使用"/omega help [插件名]"即可查看插件详情及帮助'


def get_plugin_desc(plugin_name: str, *, for_superuser: bool = False) -> str:
    """获取指定的配置了自定义信息的插件信息"""
    for plugin in get_loaded_plugins():
        if not plugin.metadata:
            continue

        if plugin_name == plugin.metadata.name:

            plugin_usage = (
                f'{plugin.metadata.name}\n{"-" * 16}\n'
                f'{plugin.metadata.description}\n\n用法:\n{plugin.metadata.usage}'
            )

            if for_superuser:
                processor_info = '\n'.join(
                    f'\n[{s.name}]\nLevel: {s.level if s.level < 2 ** 15 - 1 else "Unlimited"}/Node: {s.auth_node}\n'
                    f'ExtraNode: {", ".join(s.extra_auth_node) if s.extra_auth_node else None}\nCooldown: {s.cooldown}'
                    for s in (parse_processor_state(m._default_state) for m in plugin.matcher)
                    if s.name and s.enable_processor
                )
                desc_msg = f'{plugin_usage}\n\n可配置权限及冷却信息:{processor_info if processor_info else "无"}'
                break
            else:
                desc_msg = plugin_usage
                break
    else:
        desc_msg = f'未找到插件{plugin_name!r}, 请检查输入插件名是否正确'
    return desc_msg


def get_plugin_auth_node(plugin_name: str) -> list[str]:
    """根据插件名获取可配置的权限节点名称清单"""
    plugin = get_plugin(plugin_id=plugin_name)
    if plugin is None:
        return []

    # 仅解析声明了 processor state 的 matcher; state 键见 processor_utils.__OMEGA_STATE_KEY
    states = [
        parse_processor_state(matcher._default_state)
        for matcher in plugin.matcher
        if '_OMEGA_INTERNAL_PROCESSOR' in matcher._default_state
    ]

    nodes = [s.auth_node for s in states if s.auth_node is not None]

    # 如果有 extra_auth_node 也加入到可配置的权限节点中
    nodes.extend(extra_node for s in states if s.extra_auth_node for extra_node in s.extra_auth_node)

    # 如果有冷却配置就把跳过冷却的权限加入到可配置的权限节点中
    if any(s.cooldown for s in states):
        nodes.append(SKIP_COOLDOWN_PERMISSION_NODE)

    return sorted(set(nodes))


def list_command_by_priority() -> str:
    """根据 priority 列出命令清单"""
    priority_map: dict[int, list[str]] = {}

    for plugin in get_loaded_plugins():

        if plugin.metadata is not None:

            for matcher in plugin.matcher:
                command_info_parts: list[str] = []

                for checker in matcher.rule.checkers:
                    if isinstance(checker.call, CommandRule):
                        # 原生 CommandRule 命令
                        command_info_parts.extend('.'.join(cmd) for cmd in sorted(checker.call.cmds))
                    elif isinstance(checker.call, AlconnaRule) and (alconna := checker.call.command()) is not None:
                        # alconna 命令, 列出主命令及其子命令
                        if not isinstance(alconna.command, str) or not alconna.command:
                            continue
                        subcommands = [x.name for x in alconna.options if isinstance(x, Subcommand)]
                        if subcommands:
                            command_info_parts.append(f'{alconna.command} <{", ".join(subcommands)}>')
                        else:
                            command_info_parts.append(alconna.command)

                if not command_info_parts:
                    continue

                matcher_info = f'{plugin.metadata.name}: {"/".join(command_info_parts)}'

                if plugin_list := priority_map.get(matcher.priority):
                    plugin_list.append(matcher_info)
                else:
                    priority_map[matcher.priority] = [matcher_info]

    priority_info: str = ''

    for priority in sorted(priority_map):
        matcher_info = '\n'.join(sorted(priority_map[priority].copy()))
        priority_info += f'[Priority - {priority}]\n{matcher_info}\n\n'

    return priority_info.strip()


__all__ = [
    'get_all_plugins_desc',
    'get_plugin_desc',
    'get_plugin_auth_node',
    'list_command_by_priority',
]
