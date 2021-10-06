"""
@Author         : Ailitonia
@Date           : 2021/10/06 23:45
@FileName       : role_utils.py
@Project        : nonebot2_miya 
@Description    : qq身份检验工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from nonebot import logger
from nonebot.adapters.cqhttp.bot import Bot


@dataclass
class UserRole:
    role: str
    expired_at: datetime  # 身份信息缓存过期时间


# 缓存身份信息过期时间, 单位秒, 默认为 300 秒
ROLE_EXPIRED_TIME: int = 300
# 存放所在群组的身份
GROUP_USER_ROLE: Dict[int, Dict[int, UserRole]] = {}


class RoleChecker(object):
    def __init__(self, group_id: int, user_id: int, bot: Bot):
        self.group_id = group_id
        self.user_id = user_id
        self.bot = bot

    async def _get_group_role(self) -> str:
        global GROUP_USER_ROLE
        role = GROUP_USER_ROLE.get(self.group_id, {}).get(self.user_id)
        if role is not None and role.expired_at >= datetime.now():
            return role.role
        else:
            user_role = (await self.bot.get_group_member_info(group_id=self.group_id, user_id=self.user_id)).get('role')
            GROUP_USER_ROLE.update({
                self.group_id: {
                    self.user_id: UserRole(
                        role=user_role,
                        expired_at=datetime.now() + timedelta(seconds=ROLE_EXPIRED_TIME))}
            })
            logger.debug(f'RoleChecker | Refresh user {self.user_id} role in group {self.group_id}')
            return user_role

    async def get_role(self) -> str:
        return await self._get_group_role()

    async def is_group_owner(self) -> bool:
        role = await self._get_group_role()
        if role == 'owner':
            return True
        else:
            return False

    async def is_group_admin(self) -> bool:
        role = await self._get_group_role()
        if role in ['owner', 'admin']:
            return True
        else:
            return False

    async def is_group_member(self) -> bool:
        role = await self._get_group_role()
        if role == 'member':
            return True
        else:
            return False


__all__ = [
    'RoleChecker'
]
