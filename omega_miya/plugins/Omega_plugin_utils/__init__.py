from nonebot.plugin import Export
from nonebot.rule import Rule
from nonebot.typing import Bot, Event
from omega_miya.plugins.Omega_Base import DBGroup


def init_export(plugin_export: Export, custom_name: str, usage: str, **kwargs: str) -> Export:
    setattr(plugin_export, 'custom_name', custom_name)
    setattr(plugin_export, 'usage', usage)
    for key, value in kwargs.items():
        setattr(plugin_export, key, value)
    return plugin_export


# Plugin permission rule
# Only using for group
def has_notice_permission() -> Rule:
    async def _has_notice_permission(bot: Bot, event: Event, state: dict) -> bool:
        # 检查当前消息类型
        if event.detail_type != 'group':
            return False
        else:
            if DBGroup(group_id=event.group_id).permission_notice().result == 1:
                return True
            else:
                return False
    return Rule(_has_notice_permission)


def has_command_permission() -> Rule:
    async def _has_command_permission(bot: Bot, event: Event, state: dict) -> bool:
        # 检查当前消息类型
        if event.detail_type != 'group':
            return False
        else:
            if DBGroup(group_id=event.group_id).permission_command().result == 1:
                return True
            else:
                return False
    return Rule(_has_command_permission)


# 规划权限等级: 10+一般插件, 20+限制插件(涉及调用api), 50+后期组用工作插件, 80+涩图插件
def permission_level(level: int) -> Rule:
    async def _has_command_permission(bot: Bot, event: Event, state: dict) -> bool:
        # 检查当前消息类型
        if event.detail_type != 'group':
            return False
        else:
            if DBGroup(group_id=event.group_id).permission_level().result >= level:
                return True
            else:
                return False
    return Rule(_has_command_permission)
