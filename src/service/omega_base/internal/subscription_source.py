"""
@Author         : Ailitonia
@Date           : 2022/12/09 21:00
@FileName       : subscription_source.py
@Project        : nonebot2_miya 
@Description    : 数据库订阅源常用方法
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal, Optional

from src.database.internal.entity import Entity, EntityDAL
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType, SubscriptionSourceDAL


class InternalSubscriptionSource(abc.ABC):
    """封装后用于插件调用的数据库实体操作对象"""

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        self.db_session: AsyncSession = ...
        self.sub_type: str = ...
        self.sub_id: str = ...

    @classmethod
    @abc.abstractmethod
    async def query_type_all(cls, session: AsyncSession) -> list[SubscriptionSource]:
        """查询 sub_type 对应的全部订阅源"""
        raise NotImplementedError

    async def query_subscription_source(self) -> SubscriptionSource:
        """查询订阅源"""
        return await SubscriptionSourceDAL(session=self.db_session).query_unique(sub_type=self.sub_type,
                                                                                 sub_id=self.sub_id)

    async def add_upgrade(self, sub_user_name: str, sub_info: Optional[str] = None) -> None:
        """新增订阅源, 若已存在则更新"""
        source_dal = SubscriptionSourceDAL(session=self.db_session)
        try:
            source = await source_dal.query_unique(sub_type=self.sub_type, sub_id=self.sub_id)
            await source_dal.update(id_=source.id, sub_user_name=sub_user_name, sub_info=sub_info)
        except NoResultFound:
            await source_dal.add(sub_type=self.sub_type, sub_id=self.sub_id, sub_user_name=sub_user_name,
                                 sub_info=sub_info)

    async def delete(self) -> None:
        """删除订阅源"""
        source = await self.query_subscription_source()
        await SubscriptionSourceDAL(session=self.db_session).delete(id_=source.id)

    async def query_all_entity_subscribed(self, entity_type: Optional[str] = None) -> list[Entity]:
        """查询订阅了该订阅源的所有 Entity 对象"""
        source = await self.query_subscription_source()
        dal = EntityDAL(session=self.db_session)
        return await dal.query_all_entity_subscribed_source(sub_source_index_id=source.id, entity_type=entity_type)


class InternalBilibiliLiveSubscriptionSource(InternalSubscriptionSource):
    """Bilibili 直播订阅源"""

    def __init__(self, session: AsyncSession, live_room_id: str | int):
        self.db_session = session
        self.sub_type: Literal['bili_live'] = SubscriptionSourceType.bili_live.value
        self.sub_id = str(live_room_id)

    @classmethod
    async def query_type_all(cls, session: AsyncSession) -> list[SubscriptionSource]:
        return await SubscriptionSourceDAL(session=session).query_type_all(sub_type='bili_live')


class InternalBilibiliDynamicSubscriptionSource(InternalSubscriptionSource):
    """Bilibili 动态订阅源"""

    def __init__(self, session: AsyncSession, uid: str | int):
        self.db_session = session
        self.sub_type: Literal['bili_dynamic'] = SubscriptionSourceType.bili_dynamic.value
        self.sub_id = str(uid)

    @classmethod
    async def query_type_all(cls, session: AsyncSession) -> list[SubscriptionSource]:
        return await SubscriptionSourceDAL(session=session).query_type_all(sub_type='bili_dynamic')


class InternalPixivUserSubscriptionSource(InternalSubscriptionSource):
    """Pixiv 用户订阅源"""

    def __init__(self, session: AsyncSession, uid: str | int):
        self.db_session = session
        self.sub_type: Literal['pixiv_user'] = SubscriptionSourceType.pixiv_user.value
        self.sub_id = str(uid)

    @classmethod
    async def query_type_all(cls, session: AsyncSession) -> list[SubscriptionSource]:
        return await SubscriptionSourceDAL(session=session).query_type_all(sub_type='pixiv_user')


class InternalPixivisionSubscriptionSource(InternalSubscriptionSource):
    """Pixivision 特辑订阅源"""

    def __init__(self, session: AsyncSession):
        self.db_session = session
        self.sub_type: Literal['pixivision'] = SubscriptionSourceType.pixivision.value
        self.sub_id = 'pixivision'

    @classmethod
    async def query_type_all(cls, session: AsyncSession) -> list[SubscriptionSource]:
        return await SubscriptionSourceDAL(session=session).query_type_all(sub_type='pixivision')


class InternalWeiboUserSubscriptionSource(InternalSubscriptionSource):
    """微博用户订阅源"""

    def __init__(self, session: AsyncSession, uid: str | int):
        self.db_session = session
        self.sub_type: Literal['weibo_user'] = SubscriptionSourceType.weibo_user.value
        self.sub_id = str(uid)

    @classmethod
    async def query_type_all(cls, session: AsyncSession) -> list[SubscriptionSource]:
        return await SubscriptionSourceDAL(session=session).query_type_all(sub_type='weibo_user')


__all__ = [
    'InternalSubscriptionSource',
    'InternalBilibiliLiveSubscriptionSource',
    'InternalBilibiliDynamicSubscriptionSource',
    'InternalPixivUserSubscriptionSource',
    'InternalPixivisionSubscriptionSource',
    'InternalWeiboUserSubscriptionSource'
]
