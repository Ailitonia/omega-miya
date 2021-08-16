import datetime
from omega_miya.database import DBCoolDownEvent, Result
from dataclasses import dataclass, field


@dataclass
class PluginCoolDown:
    type: str
    cool_down_time: int
    global_type: str = field(default='global', init=False)
    plugin_type: str = field(default='plugin', init=False)
    group_type: str = field(default='group', init=False)
    user_type: str = field(default='user', init=False)
    skip_auth_node: str = field(default='skip_cd', init=False)

    @classmethod
    async def check_and_set_global_cool_down(cls, minutes: int) -> Result.IntResult:
        check = await DBCoolDownEvent.check_global_cool_down_event()
        if check.result == 1:
            return check
        elif check.result in [0, 2]:
            if minutes <= 0:
                return check
            await DBCoolDownEvent.add_global_cool_down_event(
                stop_at=datetime.datetime.now() + datetime.timedelta(minutes=minutes))
            return check
        else:
            return check

    @classmethod
    async def check_and_set_plugin_cool_down(cls, minutes: int, plugin: str) -> Result.IntResult:
        check = await DBCoolDownEvent.check_plugin_cool_down_event(plugin=plugin)
        if check.result == 1:
            return check
        elif check.result in [0, 2]:
            if minutes <= 0:
                return check
            await DBCoolDownEvent.add_plugin_cool_down_event(
                stop_at=datetime.datetime.now() + datetime.timedelta(minutes=minutes), plugin=plugin)
            return check
        else:
            return check

    @classmethod
    async def check_and_set_group_cool_down(cls, minutes: int, plugin: str, group_id: int) -> Result.IntResult:
        check = await DBCoolDownEvent.check_group_cool_down_event(plugin=plugin, group_id=group_id)
        if check.result == 1:
            return check
        elif check.result in [0, 2]:
            if minutes <= 0:
                return check
            await DBCoolDownEvent.add_group_cool_down_event(
                stop_at=datetime.datetime.now() + datetime.timedelta(minutes=minutes), plugin=plugin, group_id=group_id)
            return check
        else:
            return check

    @classmethod
    async def check_and_set_user_cool_down(cls, minutes: int, plugin: str, user_id: int) -> Result.IntResult:
        check = await DBCoolDownEvent.check_user_cool_down_event(plugin=plugin, user_id=user_id)
        if check.result == 1:
            return check
        elif check.result in [0, 2]:
            if minutes <= 0:
                return check
            await DBCoolDownEvent.add_user_cool_down_event(
                stop_at=datetime.datetime.now() + datetime.timedelta(minutes=minutes), plugin=plugin, user_id=user_id)
            return check
        else:
            return check


__all__ = [
    'PluginCoolDown'
]
