import datetime
from omega_miya.utils.Omega_Base import DBCoolDownEvent, Result
from dataclasses import dataclass


@dataclass
class PluginCoolDown:
    plugin_name: str
    type: str
    cool_down_time: int


def check_and_set_global_cool_down(minutes: int) -> Result:
    check = DBCoolDownEvent.check_global_cool_down_event()
    if check.result == 1:
        return check
    elif check.result == 0:
        if minutes <= 0:
            return check
        DBCoolDownEvent.add_global_cool_down_event(
            stop_at=datetime.datetime.now() + datetime.timedelta(minutes=minutes))
        return check
    else:
        return check


def check_and_set_plugin_cool_down(minutes: int, plugin: str) -> Result:
    check = DBCoolDownEvent.check_plugin_cool_down_event(plugin=plugin)
    if check.result == 1:
        return check
    elif check.result == 0:
        if minutes <= 0:
            return check
        DBCoolDownEvent.add_plugin_cool_down_event(
            stop_at=datetime.datetime.now() + datetime.timedelta(minutes=minutes), plugin=plugin)
        return check
    else:
        return check


def check_and_set_group_cool_down(minutes: int, plugin: str, group_id: int) -> Result:
    check = DBCoolDownEvent.check_group_cool_down_event(plugin=plugin, group_id=group_id)
    if check.result == 1:
        return check
    elif check.result == 0:
        if minutes <= 0:
            return check
        DBCoolDownEvent.add_group_cool_down_event(
            stop_at=datetime.datetime.now() + datetime.timedelta(minutes=minutes), plugin=plugin, group_id=group_id)
        return check
    else:
        return check


def check_and_set_user_cool_down(minutes: int, plugin: str, user_id: int) -> Result:
    check = DBCoolDownEvent.check_user_cool_down_event(plugin=plugin, user_id=user_id)
    if check.result == 1:
        return check
    elif check.result == 0:
        if minutes <= 0:
            return check
        DBCoolDownEvent.add_user_cool_down_event(
            stop_at=datetime.datetime.now() + datetime.timedelta(minutes=minutes), plugin=plugin, user_id=user_id)
        return check
    else:
        return check


__all__ = [
    'PluginCoolDown',
    'check_and_set_global_cool_down',
    'check_and_set_plugin_cool_down',
    'check_and_set_group_cool_down',
    'check_and_set_user_cool_down'
]
