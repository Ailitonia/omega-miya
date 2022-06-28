"""
@Author         : Ailitonia
@Date           : 2022/05/22 1:17
@FileName       : permission.py
@Project        : nonebot2_miya 
@Description    : Guild Permission
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.permission import Permission

from .models import GuildMessageEvent


async def _guild(event: GuildMessageEvent) -> bool:
    return True


async def _guild_superuser(bot: Bot, event: GuildMessageEvent) -> bool:
    return (
        f"{bot.adapter.get_name().split(maxsplit=1)[0].lower()}:{event.get_user_id()}"
        in bot.config.superusers
        or event.get_user_id() in bot.config.superusers
    )  # 兼容旧配置


GUILD: Permission = Permission(_guild)
"""匹配任意频道消息类型事件"""
GUILD_SUPERUSER: Permission = Permission(_guild_superuser)
"""匹配任意超级用户频道消息类型事件"""


__all__ = ["GUILD", "GUILD_SUPERUSER"]