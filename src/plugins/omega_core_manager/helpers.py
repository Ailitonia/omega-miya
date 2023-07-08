"""
@Author         : Ailitonia
@Date           : 2023/7/5 2:00
@FileName       : helper
@Project        : nonebot2_miya
@Description    : 工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import get_loaded_plugins, get_plugin
from nonebot.rule import CommandRule

from src.service.omega_base.internal.consts import SKIP_COOLDOWN_PERMISSION_NODE
from src.service.omega_processor.plugin_utils import parse_processor_state


def get_all_plugins_desc() -> str:
    """获取全部配置了自定义信息的插件信息"""
    plugins_custom_name = '\n'.join(sorted(plugin.metadata.name for plugin in get_loaded_plugins() if plugin.metadata))
    return f'现在已安装的插件有: \n\n{plugins_custom_name}\n\n使用"/help [插件名]"即可查看插件详情及帮助'


def get_plugin_desc(plugin_name: str, *, for_superuser: bool = False) -> str:
    """获取指定的配置了自定义信息的插件信息"""
    for plugin in get_loaded_plugins():
        if not plugin.metadata:
            continue

        if plugin_name == plugin.metadata.name:

            plugin_usage = (
                f'{plugin.metadata.name}\n{"-"*16}\n'
                f'{plugin.metadata.description}\n\n用法:\n{plugin.metadata.usage}'
            )

            if for_superuser:
                processor_info = '\n'.join(
                    f'\n[{s.name}]\nLevel: {s.level if s.level < 4294967296 else "Unlimited"}/Node: {s.auth_node}\n'
                    f'ExtraNode: {", ".join(s.extra_auth_node) if s.extra_auth_node else None}\nCooldown: {s.cooldown}'
                    for s in (parse_processor_state(m._default_state) for m in plugin.matcher)
                    if s.name and s.enable_processor
                )
                desc_msg = f'{plugin_usage}\n\n可配置权限及冷却信息:{processor_info if processor_info else "无"}'
                break
            else:
                processor_info = '\n'.join(
                    f'\n[{s.name}]\nLevel: {s.level if s.level < 4294967296 else "Unlimited"}/Cooldown: {s.cooldown}'
                    for s in (parse_processor_state(m._default_state) for m in plugin.matcher)
                    if s.name and s.enable_processor
                )
                desc_msg = f'{plugin_usage}\n\n需要的权限等级和命令冷却时间:\n{processor_info if processor_info else "无"}'
                break
    else:
        desc_msg = f'未找到插件{plugin_name!r}, 请检查输入插件名是否正确'
    return desc_msg


def get_plugin_auth_node(plugin_name: str) -> list[str]:
    """根据插件名获取可配置的权限节点名称清单"""
    plugin = get_plugin(name=plugin_name)
    if plugin is None:
        return []

    nodes = [s.auth_node for s in (
        parse_processor_state(m._default_state) for m in plugin.matcher
    ) if s.auth_node is not None]

    # 如果有 extra_auth_node 也加入到可配置的权限节点中
    nodes.extend((extra_node for s in (
        parse_processor_state(m._default_state) for m in plugin.matcher
    ) if s.extra_auth_node for extra_node in s.extra_auth_node))

    # 如果有冷却配置就把跳过冷却的权限加入到可配置的权限节点中
    if any(s.cooldown for s in (parse_processor_state(m._default_state) for m in plugin.matcher)):
        nodes.append(SKIP_COOLDOWN_PERMISSION_NODE)

    return sorted(list(set(nodes)))


def list_command_by_priority() -> str:
    """根据 priority 列出命令清单"""
    priority_map: dict[int, list[str]] = {}

    for plugin in get_loaded_plugins():

        if plugin.metadata is not None:

            for matcher in plugin.matcher:
                command_info = '/'.join(
                    '.'.join(cmd)
                    for x in matcher.rule.checkers for cmd in sorted(x.call.cmds)
                    if isinstance(x.call, CommandRule)
                )
                matcher_info = f'{plugin.metadata.name}: {command_info}'

                if plugin_list := priority_map.get(matcher.priority):
                    plugin_list.append(matcher_info)
                else:
                    priority_map[matcher.priority] = [matcher_info]

    priority_info: str = ''

    for priority in sorted(priority_map):
        matcher_info = "\n".join(sorted(priority_map[priority].copy()))
        priority_info += f'[Priority - {priority}]\n{matcher_info}\n\n'

    return priority_info.strip()


__all__ = [
    'get_all_plugins_desc',
    'get_plugin_desc',
    'get_plugin_auth_node',
    'list_command_by_priority'
]
