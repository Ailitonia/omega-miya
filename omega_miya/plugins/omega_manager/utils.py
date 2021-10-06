"""
@Author         : Ailitonia
@Date           : 2021/10/06 23:01
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 操作工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from omega_miya.database import DBBotGroup, DBUser


async def upgrade_group_member(user_info: dict, group: DBBotGroup) -> None:
    # 更新群成员用户信息
    user_qq = user_info.get('user_id')
    user_nickname = user_info.get('nickname')
    user_group_nickmane = user_info.get('card')
    if not user_group_nickmane:
        user_group_nickmane = user_nickname

    _user = DBUser(user_id=user_qq)
    _result = await _user.add(nickname=user_nickname)
    if not _result.success():
        logger.error(f'Omega Manager | Add Group user {user_qq} failed, {_result.info}')

    _result = await group.member_add(user=_user, user_group_nickname=user_group_nickmane)
    if _result.error:
        logger.error(f'Omega Manager | Upgrade Group member {user_qq} failed, {_result.info}')


__all__ = [
    'upgrade_group_member'
]
