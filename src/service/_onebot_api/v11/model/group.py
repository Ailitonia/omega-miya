"""
@Author         : Ailitonia
@Date           : 2022/04/13 23:23
@FileName       : group.py
@Project        : nonebot2_miya 
@Description    : Onebot group model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from pydantic import AnyHttpUrl
from .base_model import BaseOnebotModel


class GroupInfo(BaseOnebotModel):
    """群信息

    - group_id, 群号
    - group_name, 群名称
    - group_memo, 群备注
    - group_create_time, 群创建时间
    - group_level, 群等级
    - member_count, 成员数
    - max_member_count, 最大成员数（群容量）
    """
    group_id: str
    group_name: str
    member_count: int
    max_member_count: int


class GroupUserHonor(BaseOnebotModel):
    """群荣耀"""
    user_id: str
    nickname: str
    avatar: AnyHttpUrl
    description: str


class GroupTalkative(BaseOnebotModel):
    """群龙王"""
    user_id: str
    nickname: str
    avatar: AnyHttpUrl
    day_count: int


class GroupHonor(BaseOnebotModel):
    """群荣耀信息"""
    group_id: str
    current_talkative: Optional[GroupTalkative]
    talkative_list: Optional[list[GroupUserHonor]]
    performer_list: Optional[list[GroupUserHonor]]
    legend_list: Optional[list[GroupUserHonor]]
    strong_newbie_list: Optional[list[GroupUserHonor]]
    emotion_list: Optional[list[GroupUserHonor]]






__all__ = [
    'GroupInfo',
    'GroupHonor'
]
