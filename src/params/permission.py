"""
@Author         : Ailitonia
@Date           : 2023/7/15 3:49
@FileName       : permission
@Project        : nonebot2_miya
@Description    : 自定义 Permission 依赖注入
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from arclet.alconna import Arparma
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN as ONEBOT_V11_GROUP_ADMIN
from nonebot.adapters.onebot.v11.permission import GROUP_OWNER as ONEBOT_V11_GROUP_OWNER
from nonebot.adapters.onebot.v11.permission import PRIVATE as ONEBOT_V11_PRIVATE
from nonebot.adapters.telegram.permission import GROUP_ADMIN as TELEGRAM_GROUP_ADMIN
from nonebot.adapters.telegram.permission import GROUP_CREATOR as TELEGRAM_GROUP_CREATOR
from nonebot.adapters.telegram.permission import PRIVATE as TELEGRAM_PRIVATE
from nonebot.permission import SUPERUSER, Permission
from nonebot.typing import T_State

IS_ADMIN: Permission = (
        SUPERUSER
        | ONEBOT_V11_GROUP_ADMIN
        | ONEBOT_V11_GROUP_OWNER
        | ONEBOT_V11_PRIVATE
        | TELEGRAM_GROUP_ADMIN
        | TELEGRAM_GROUP_CREATOR
        | TELEGRAM_PRIVATE
)
"""匹配具有管理员身份的消息类型事件"""


async def check_event_is_admin(event: BaseEvent, bot: BaseBot, _s: T_State, _a: Arparma) -> bool:
    """alconna assign additional 检查: 事件触发对象是否为管理员"""
    return await IS_ADMIN(bot, event)


async def check_event_is_superuser(event: BaseEvent, bot: BaseBot, _s: T_State, _a: Arparma) -> bool:
    """alconna assign additional 检查: 事件触发对象是否为超级用户"""
    return await SUPERUSER(bot, event)


__all__ = [
    'IS_ADMIN',
    'check_event_is_admin',
    'check_event_is_superuser',
]
