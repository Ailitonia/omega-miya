from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.permission import Permission

from .models import GuildMessageEvent


async def _guild(event: GuildMessageEvent) -> bool:
    return True


async def _guild_admin(bot: Bot, event: GuildMessageEvent):
    roles = {
        role["role_name"]
        for role in (
            await bot.get_guild_member_profile(
                guild_id=event.guild_id, user_id=event.user_id
            )
        )["roles"]
    }
    return "管理员" in roles


async def _guild_owner(bot: Bot, event: GuildMessageEvent):
    roles = {
        role["role_name"]
        for role in (
            await bot.get_guild_member_profile(
                guild_id=event.guild_id, user_id=event.user_id
            )
        )["roles"]
    }
    return "频道主" in roles


async def _guild_superuser(bot: Bot, event: GuildMessageEvent) -> bool:
    return (
        f"{bot.adapter.get_name().lower()}:{event.get_user_id()}"
        in bot.config.superusers
    ) or (event.get_user_id() in bot.config.superusers)


GUILD: Permission = Permission(_guild)
"""匹配任意频道消息类型事件"""
GUILD_SUPERUSER: Permission = Permission(_guild_superuser)
"""匹配任意超级用户频道消息类型事件"""
GUILD_ADMIN: Permission = Permission(_guild_admin)
"""匹配任意频道管理员消息类型事件"""
GUILD_OWNER: Permission = Permission(_guild_owner)
"""匹配任意频道频道主消息类型事件"""

__all__ = ["GUILD", "GUILD_OWNER", "GUILD_ADMIN", "GUILD_SUPERUSER"]
