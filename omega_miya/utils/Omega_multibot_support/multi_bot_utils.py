"""
@Author         : Ailitonia
@Date           : 2021/08/10 22:53
@FileName       : multi_bot_utils.py
@Project        : nonebot2_miya 
@Description    : Multi Bot Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.typing import T_State
from nonebot.permission import Permission
from nonebot.adapters.cqhttp.event import Event
from nonebot.adapters.cqhttp.bot import Bot


class MultiBotUtils(object):
    @classmethod
    async def first_response_bot_permission_updater(
            cls, bot: Bot, event: Event, state: T_State, permission: Permission) -> Permission:
        """
        T_PermissionUpdater
        :param bot: 事件响应 bot
        :param event: 事件
        :param state: matcher 运行时 state
        :param permission: 上次 reject 或 pause 前的 permission
        """
        # stats默认执行初始化于omega_miya.utils.Omega_bot_manager.set_first_response_bot_state
        _bot_self_id = state.get('_first_response_bot')
        _original_permission = state.get('_original_permission')
        _original_session_id = state.get('_original_session_id')

        async def _first_response_bot(_bot: Bot, _event: Event) -> bool:
            return _bot.self_id == _bot_self_id and str(event.self_id) == _bot_self_id and _event.get_session_id(
            ) == _original_session_id and await _original_permission(bot, event)

        return Permission(_first_response_bot)


__all__ = [
    'MultiBotUtils'
]
