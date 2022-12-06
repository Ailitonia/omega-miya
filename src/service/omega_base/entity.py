"""
@Author         : Ailitonia
@Date           : 2022/12/05 22:37
@FileName       : entity.py
@Project        : nonebot2_miya 
@Description    : 数据库 Entity 常用方法, 用户/群组/频道等相关操作
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from datetime import date, datetime
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal, Optional

from nonebot.params import Depends
from fastapi import Depends as FastapiDepends
from src.database.utils import get_db_session

from src.database.internal.auth_setting import AuthSetting, AuthSettingDAL
from src.database.internal.bot import BotSelf, BotSelfDAL
from src.database.internal.entity import Entity, EntityDAL, EntityType
from src.database.internal.friendship import Friendship, FriendshipDAL
from src.database.internal.sign_in import SignInDAL


class InternalEntity(object):
    """封装后用于插件调用的数据库实体操作对象"""

    def __init__(self, session: AsyncSession, bot_id: str, entity_type: str, entity_id: str, parent_id: str):
        EntityType.verify(entity_type)
        self.db_session = session
        self.bot_id = bot_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.parent_id = parent_id

    @property
    def tid(self) -> str:
        return f'{self.entity_type}_{self.entity_id}'

    @classmethod
    async def query_entity_type_all(cls, session: AsyncSession, entity_type: str) -> list[Entity]:
        """查询符合 entity_type 的全部结果"""
        return await EntityDAL(session=session).query_entity_type_all(entity_type=entity_type)

    async def query_bot_self(self) -> BotSelf:
        """查询 Entity 对应的 Bot"""
        return await BotSelfDAL(session=self.db_session).query_unique(self_id=self.bot_id)

    async def query_entity(self) -> Entity:
        """查询 Entity"""
        bot = await self.query_bot_self()
        return await EntityDAL(session=self.db_session).query_unique(bot_index_id=bot.id, entity_type=self.entity_type,
                                                                     entity_id=self.entity_id, parent_id=self.parent_id)

    async def add_upgrade(self, entity_name: str, entity_info: Optional[str] = None) -> None:
        """新增 Entity, 若已存在则更新"""
        bot = await self.query_bot_self()
        entity_dal = EntityDAL(session=self.db_session)
        try:
            entity = await entity_dal.query_unique(bot_index_id=bot.id, entity_id=self.entity_id,
                                                   entity_type=self.entity_type, parent_id=self.parent_id)
            await entity_dal.update(id_=entity.id, entity_name=entity_name, entity_info=entity_info)
        except NoResultFound:
            await entity_dal.add(bot_index_id=bot.id, entity_id=self.entity_id, entity_type=self.entity_type,
                                 parent_id=self.parent_id, entity_name=entity_name, entity_info=entity_info)

    async def delete(self) -> None:
        """删除 Entity"""
        entity = await self.query_entity()
        return await EntityDAL(session=self.db_session).delete(id_=entity.id)

    async def set_friendship(
            self,
            status: str = 'normal',
            mood: float = 0,
            friendship: float = 0,
            energy: float = 0,
            currency: float = 0,
            response_threshold: float = 0
    ) -> None:
        """设置或更新好感度"""
        entity = await self.query_entity()
        friendship_dal = FriendshipDAL(session=self.db_session)
        try:
            _friendship = await friendship_dal.query_unique(entity_index_id=entity.id)
            await friendship_dal.update(id_=_friendship.id, status=status, mood=mood, friendship=friendship,
                                        energy=energy, currency=currency, response_threshold=response_threshold)
        except NoResultFound:
            await friendship_dal.add(entity_index_id=entity.id, status=status, mood=mood, friendship=friendship,
                                     energy=energy, currency=currency, response_threshold=response_threshold)

    async def change_friendship(
            self,
            *,
            status: Optional[str] = None,
            mood: float = 0,
            friendship: float = 0,
            energy: float = 0,
            currency: float = 0,
            response_threshold: float = 0
    ):
        """变更好感度, 在现有好感度数值上加/减"""
        entity = await self.query_entity()
        friendship_dal = FriendshipDAL(session=self.db_session)
        try:
            _friendship = await friendship_dal.query_unique(entity_index_id=entity.id)

            status = _friendship.status if status is None else status
            mood += _friendship.mood
            friendship += _friendship.friendship
            energy += _friendship.energy
            currency += _friendship.currency
            response_threshold += _friendship.response_threshold

            await friendship_dal.update(id_=_friendship.id, status=status, mood=mood, friendship=friendship,
                                        energy=energy, currency=currency, response_threshold=response_threshold)
        except NoResultFound:
            await friendship_dal.add(entity_index_id=entity.id, status='normal', mood=mood, friendship=friendship,
                                     energy=energy, currency=currency, response_threshold=response_threshold)

    async def query_friendship(self) -> Friendship:
        """获取好感度, 没有则直接初始化"""
        entity = await self.query_entity()
        friendship_dal = FriendshipDAL(session=self.db_session)
        try:
            friendship = await friendship_dal.query_unique(entity_index_id=entity.id)
        except NoResultFound:
            await self.set_friendship()
            friendship = await friendship_dal.query_unique(entity_index_id=entity.id)
        return friendship

    async def sign_in(
            self,
            *,
            date_: Optional[date | datetime] = None,
            sign_in_info: Optional[str] = None,
    ) -> None:
        """签到

        :param date_: 指定签到日期
        :param sign_in_info: 签到信息
        """
        entity = await self.query_entity()
        sign_in_dal = SignInDAL(session=self.db_session)

        if isinstance(date_, datetime):
            sign_in_date = date_.date()
            sign_in_info = 'Fixed Sign In' if sign_in_info is None else sign_in_info
        elif isinstance(date_, date):
            sign_in_date = date_
            sign_in_info = 'Fixed Sign In' if sign_in_info is None else sign_in_info
        else:
            sign_in_date = datetime.now().date()

        try:
            signin = await sign_in_dal.query_unique(entity_index_id=entity.id, sign_in_date=sign_in_date)
            sign_in_info = 'Duplicate Sign In' if sign_in_info is None else sign_in_info
            await sign_in_dal.update(id_=signin.id, sign_in_info=sign_in_info)
        except NoResultFound:
            sign_in_info = 'Normal Sign In' if sign_in_info is None else sign_in_info
            await sign_in_dal.add(entity_index_id=entity.id, sign_in_date=sign_in_date, sign_in_info=sign_in_info)

    async def check_today_sign_in(self) -> bool:
        """检查今日是否已经签到"""
        entity = await self.query_entity()
        sign_in_dal = SignInDAL(session=self.db_session)
        try:
            await sign_in_dal.query_unique(entity_index_id=entity.id, sign_in_date=datetime.now().date())
            result = True
        except NoResultFound:
            result = False
        return result

    async def query_sign_in_days(self) -> list[date]:
        """查询所有的签到记录, 返回签到日期列表"""
        entity = await self.query_entity()
        return await SignInDAL(session=self.db_session).query_entity_sign_in_days(entity_index_id=entity.id)

    async def query_continuous_sign_in_day(self) -> int:
        """查询到现在为止最长连续签到日数"""
        sign_in_history = await self.query_sign_in_days()
        if not sign_in_history:
            return 0

        date_now_ordinal = datetime.now().date().toordinal()
        # 先将签到记录中的日期转化为整数便于比较
        all_sign_in_list = list(set([x.toordinal() for x in sign_in_history]))
        # 去重后由大到小排序
        all_sign_in_list.sort(reverse=True)
        # 如果今日日期不等于已签到日期最大值, 说明今日没有签到, 则连签日数为0
        if date_now_ordinal != all_sign_in_list[0]:
            return 0

        # 从大到小检查(即日期从后向前检查), 如果当日序号大小大于与今日日期之差, 说明在这里断签了
        for index, value in enumerate(all_sign_in_list):
            if index != date_now_ordinal - value:
                return index
        else:
            # 如果全部遍历完了那就说明全部没有断签
            return len(all_sign_in_list)

    async def query_last_missing_sign_in_day(self) -> int:
        """查询上一次断签的时间, 返回 ordinal datetime"""
        sign_in_history = await self.query_sign_in_days()
        date_now_ordinal = datetime.now().date().toordinal()

        # 还没有签到过, 对应断签日期就是今天
        if not sign_in_history:
            return date_now_ordinal

        # 有签到记录则处理签到记录
        # 先将签到记录中的日期转化为整数便于比较
        all_sign_in_list = list(set([x.toordinal() for x in sign_in_history]))
        # 去重后由大到小排序
        all_sign_in_list.sort(reverse=True)

        # 如果今日日期不等于已签到日期最大值, 说明今日没有签到, 断签日为今日
        if date_now_ordinal != all_sign_in_list[0]:
            return date_now_ordinal

        # 从大到小检查(即日期从后向前检查), 如果当日序号大小大于与今日日期之差, 说明在这里断签了
        # 这里要返回对应最早连签前一天的 ordinal datetime
        for index, value in enumerate(all_sign_in_list):
            if index != date_now_ordinal - value:
                return all_sign_in_list[index - 1] - 1
        else:
            # 如果全部遍历完了那就说明全部没有返回开始签到的前一天
            return date_now_ordinal - len(all_sign_in_list)

    async def query_all_auth_setting(self) -> list[AuthSetting]:
        """查询全部的权限配置"""
        entity = await self.query_entity()
        return await AuthSettingDAL(session=self.db_session).query_entity_all(entity_index_id=entity.id)

    async def query_plugin_all_auth_setting(self, module: str, plugin: str) -> list[AuthSetting]:
        """查询具有某个插件的全部的权限配置"""
        entity = await self.query_entity()
        return await AuthSettingDAL(session=self.db_session).query_entity_all(entity_index_id=entity.id,
                                                                              module=module, plugin=plugin)

    async def query_auth_setting(self, module: str, plugin: str, node: str) -> AuthSetting:
        """查询具体某个权限配置, 没有则直接初始化"""
        ...


class EntityDependClass(abc.ABC):
    """Internal Entity 依赖类"""

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        self.bot_id: str = ...
        self.entity_id: str = ...
        self.entity_type: str = ...
        self.parent_id: str = ...

    def __call__(self, session: AsyncSession = Depends(get_db_session)) -> InternalEntity:
        return InternalEntity(session=session, bot_id=self.bot_id, entity_id=self.entity_id,
                              entity_type=self.entity_type, parent_id=self.parent_id)

    def convert_fastapi_depend(self) -> "EntityDependClass":
        """转换为 Fast API Depends"""

        class __InnerDependClass(EntityDependClass):
            def __init__(self, bot_id: str, entity_id: str, entity_type: str, parent_id: str):
                self.bot_id = bot_id
                self.entity_id = entity_id
                self.entity_type = entity_type
                self.parent_id = parent_id

            def __call__(self, session: AsyncSession = FastapiDepends(get_db_session)) -> InternalEntity:
                return InternalEntity(session=session, bot_id=self.bot_id, entity_id=self.entity_id,
                                      entity_type=self.entity_type, parent_id=self.parent_id)

        return __InnerDependClass(self.bot_id, self.entity_id, self.entity_type, self.parent_id)


class QQUserDependClass(EntityDependClass):
    """QQ 用户 Entity 依赖类"""
    def __init__(self, bot_id: str, user_id: str):
        self.bot_id = bot_id
        self.entity_id = user_id
        self.entity_type: Literal['qq_user'] = 'qq_user'
        self.parent_id = bot_id


class QQGroupDependClass(EntityDependClass):
    """QQ 群组 Entity 依赖类"""
    def __init__(self, bot_id: str, group_id: str):
        self.bot_id = bot_id
        self.entity_id = group_id
        self.entity_type: Literal['qq_group'] = 'qq_group'
        self.parent_id = bot_id


class QQGuildDependClass(EntityDependClass):
    """QQ 频道 Entity 依赖类"""
    def __init__(self, bot_id: str, bot_tiny_id: str, guild_id: str):
        self.bot_id = bot_id
        self.entity_id = guild_id
        self.entity_type: Literal['qq_guild'] = 'qq_guild'
        self.parent_id = bot_tiny_id


class QQGuildUserDependClass(EntityDependClass):
    """QQ 频道系统内用户 Entity 依赖类"""
    def __init__(self, bot_id: str, guild_id: str, guild_user_id: str):
        self.bot_id = bot_id
        self.entity_id = guild_user_id
        self.entity_type: Literal['qq_guild_user'] = 'qq_guild_user'
        self.parent_id = guild_id


class QQGuildChannelDependClass(EntityDependClass):
    """QQ 频道子频道 Entity 依赖类"""
    def __init__(self, bot_id: str, guild_id: str, channel_id: str):
        self.bot_id = bot_id
        self.entity_id = channel_id
        self.entity_type: Literal['qq_guild_channel'] = 'qq_guild_channel'
        self.parent_id = guild_id


__all__ = [
    'InternalEntity',
    'QQUserDependClass',
    'QQGroupDependClass',
    'QQGuildDependClass',
    'QQGuildUserDependClass',
    'QQGuildChannelDependClass'
]
