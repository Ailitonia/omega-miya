import datetime
from omega_miya.database import DBCoolDownEvent, Result
from dataclasses import dataclass, field


@dataclass
class PluginCoolDown:
    """
    插件冷却工具类, 用于声明当前 matcher 权限及冷却等信息, 并负责处理具体冷却事件
        - type: 冷却类型
        - cool_down_time: 冷却时间, 单位秒
    """
    type: str
    cool_down_time: int
    global_group_type: str = field(default=DBCoolDownEvent.global_group_type, init=False)
    global_user_type: str = field(default=DBCoolDownEvent.global_user_type, init=False)
    group_type: str = field(default=DBCoolDownEvent.group_type, init=False)
    user_type: str = field(default=DBCoolDownEvent.user_type, init=False)
    skip_auth_node: str = field(default='skip_cd', init=False)

    @classmethod
    async def check_and_set_global_group_cool_down(cls, group_id, seconds: int) -> Result.IntResult:
        """
        :return:
            result = 1: Success with still CoolDown with duration in info
            result = 0: Success with not in CoolDown and set a new CoolDown event
            result = -1: Error
        """
        check = await DBCoolDownEvent.check_global_group_cool_down_event(group_id=group_id)
        if check.success() and check.result == 1:
            return check
        elif check.success() and check.result in [0, 2]:
            result = await DBCoolDownEvent.add_global_group_cool_down_event(
                group_id=group_id,
                stop_at=datetime.datetime.now() + datetime.timedelta(seconds=seconds))
            if result.error:
                return Result.IntResult(error=True, info=f'Set CoolDown Event failed, {result.info}', result=-1)
            else:
                return Result.IntResult(error=False, info='Success set CoolDown Event', result=0)
        else:
            return check

    @classmethod
    async def check_and_set_global_user_cool_down(cls, user_id: int, seconds: int) -> Result.IntResult:
        """
        :return:
            result = 1: Success with still CoolDown with duration in info
            result = 0: Success with not in CoolDown and set a new CoolDown event
            result = -1: Error
        """
        check = await DBCoolDownEvent.check_global_user_cool_down_event(user_id=user_id)
        if check.success() and check.result == 1:
            return check
        elif check.success() and check.result in [0, 2]:
            result = await DBCoolDownEvent.add_global_user_cool_down_event(
                user_id=user_id,
                stop_at=datetime.datetime.now() + datetime.timedelta(seconds=seconds))
            if result.error:
                return Result.IntResult(error=True, info=f'Set CoolDown Event failed, {result.info}', result=-1)
            else:
                return Result.IntResult(error=False, info='Success set CoolDown Event', result=0)
        else:
            return check

    @classmethod
    async def check_and_set_group_cool_down(cls, plugin: str, group_id: int, seconds: int) -> Result.IntResult:
        """
        :return:
            result = 1: Success with still CoolDown with duration in info
            result = 0: Success with not in CoolDown and set a new CoolDown event
            result = -1: Error
        """
        check = await DBCoolDownEvent.check_group_cool_down_event(plugin=plugin, group_id=group_id)
        if check.success() and check.result == 1:
            return check
        elif check.success() and check.result in [0, 2]:
            result = await DBCoolDownEvent.add_group_cool_down_event(
                plugin=plugin,
                group_id=group_id,
                stop_at=datetime.datetime.now() + datetime.timedelta(seconds=seconds))
            if result.error:
                return Result.IntResult(error=True, info=f'Set CoolDown Event failed, {result.info}', result=-1)
            else:
                return Result.IntResult(error=False, info='Success set CoolDown Event', result=0)
        else:
            return check

    @classmethod
    async def check_and_set_user_cool_down(cls, plugin: str, user_id: int, seconds: int) -> Result.IntResult:
        """
        :return:
            result = 1: Success with still CoolDown with duration in info
            result = 0: Success with not in CoolDown and set a new CoolDown event
            result = -1: Error
        """
        check = await DBCoolDownEvent.check_user_cool_down_event(plugin=plugin, user_id=user_id)
        if check.success() and check.result == 1:
            return check
        elif check.success() and check.result in [0, 2]:
            result = await DBCoolDownEvent.add_user_cool_down_event(
                plugin=plugin,
                user_id=user_id,
                stop_at=datetime.datetime.now() + datetime.timedelta(seconds=seconds))
            if result.error:
                return Result.IntResult(error=True, info=f'Set CoolDown Event failed, {result.info}', result=-1)
            else:
                return Result.IntResult(error=False, info='Success set CoolDown Event', result=0)
        else:
            return check


__all__ = [
    'PluginCoolDown'
]
