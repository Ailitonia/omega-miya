"""
@Author         : Ailitonia
@Date           : 2023/7/15 3:49
@FileName       : permission
@Project        : nonebot2_miya
@Description    : 自定义 Permission 依赖注入
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.permission import Permission, SUPERUSER

from nonebot.adapters.onebot.v11.permission import (
    GROUP_ADMIN as ONEBOT_V11_GROUP_ADMIN,
    GROUP_OWNER as ONEBOT_V11_GROUP_OWNER,
    PRIVATE as ONEBOT_V11_PRIVATE
)
from nonebot.adapters.qq.permission import (
    GUILD_CHANNEL_ADMIN as QQ_GUILD_CHANNEL_ADMIN,
    GUILD_ADMIN as QQ_GUILD_ADMIN,
    GUILD_OWNER as QQ_GUILD_OWNER
)
from nonebot.adapters.telegram.permission import (
    GROUP_ADMIN as TELEGRAM_GROUP_ADMIN,
    GROUP_CREATOR as TELEGRAM_GROUP_CREATOR,
    PRIVATE as TELEGRAM_PRIVATE
)


IS_ADMIN: Permission = (
        SUPERUSER
        | ONEBOT_V11_GROUP_ADMIN
        | ONEBOT_V11_GROUP_OWNER
        | ONEBOT_V11_PRIVATE
        | QQ_GUILD_CHANNEL_ADMIN
        | QQ_GUILD_ADMIN
        | QQ_GUILD_OWNER
        | TELEGRAM_GROUP_ADMIN
        | TELEGRAM_GROUP_CREATOR
        | TELEGRAM_PRIVATE
)
"""匹配具有管理员身份的消息类型事件"""


__all__ = [
    'IS_ADMIN'
]
