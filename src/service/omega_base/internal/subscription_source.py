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
from typing import TYPE_CHECKING

from sqlalchemy.exc import NoResultFound

from src.database.internal.entity import Entity, EntityDAL
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceDAL, SubscriptionSourceType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class InternalSubscriptionSource(abc.ABC):
    """封装后用于插件调用的数据库实体操作对象"""

    __slots__ = ('db_session', 'sub_id',)
    db_session: 'AsyncSession'
    sub_id: str

    @abc.abstractmethod
    def __init__(self, session: 'AsyncSession', *args, **kwargs):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_sub_type(cls) -> str:
        raise NotImplementedError

    @classmethod
    async def query_type_all(cls, session: 'AsyncSession') -> list[SubscriptionSource]:
        """查询 sub_type 对应的全部订阅源"""
        return await SubscriptionSourceDAL(session=session).query_type_all(sub_type=cls.get_sub_type())

    async def query_subscription_source(self) -> SubscriptionSource:
        """查询订阅源"""
        return await SubscriptionSourceDAL(session=self.db_session).query_unique(
            sub_type=self.get_sub_type(), sub_id=self.sub_id
        )

    async def add_upgrade(self, sub_user_name: str, sub_info: str | None = None) -> None:
        """新增订阅源, 若已存在则更新"""
        source_dal = SubscriptionSourceDAL(session=self.db_session)
        try:
            source = await source_dal.query_unique(sub_type=self.get_sub_type(), sub_id=self.sub_id)
            await source_dal.update(id_=source.id, sub_user_name=sub_user_name, sub_info=sub_info)
        except NoResultFound:
            await source_dal.add(
                sub_type=self.get_sub_type(), sub_id=self.sub_id, sub_user_name=sub_user_name, sub_info=sub_info
            )

    async def delete(self) -> None:
        """删除订阅源"""
        source = await self.query_subscription_source()
        await SubscriptionSourceDAL(session=self.db_session).delete(id_=source.id)

    async def query_all_entity_subscribed(self, entity_type: str | None = None) -> list[Entity]:
        """查询订阅了该订阅源的所有 Entity 对象"""
        source = await self.query_subscription_source()
        dal = EntityDAL(session=self.db_session)
        return await dal.query_all_entity_subscribed_source(sub_source_index_id=source.id, entity_type=entity_type)


class InternalBilibiliLiveSubscriptionSource(InternalSubscriptionSource):
    """Bilibili 直播订阅源"""

    def __init__(self, session: 'AsyncSession', live_room_id: str | int):
        self.db_session = session
        self.sub_id = str(live_room_id)

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.bili_live.value


class InternalBilibiliDynamicSubscriptionSource(InternalSubscriptionSource):
    """Bilibili 动态订阅源"""

    def __init__(self, session: 'AsyncSession', uid: str | int):
        self.db_session = session
        self.sub_id = str(uid)

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.bili_dynamic.value


class InternalPixivUserSubscriptionSource(InternalSubscriptionSource):
    """Pixiv 用户订阅源"""

    def __init__(self, session: 'AsyncSession', uid: str | int):
        self.db_session = session
        self.sub_id = str(uid)

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.pixiv_user.value


class InternalPixivisionSubscriptionSource(InternalSubscriptionSource):
    """Pixivision 特辑订阅源"""

    def __init__(self, session: 'AsyncSession'):
        self.db_session = session
        self.sub_id = 'pixivision'

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.pixivision.value

    async def add_upgrade(self, sub_user_name: str = '', sub_info: str | None = None) -> None:
        return await super().add_upgrade(sub_user_name='pixivision', sub_info='Pixivision特辑订阅')


class InternalWeiboUserSubscriptionSource(InternalSubscriptionSource):
    """微博用户订阅源"""

    def __init__(self, session: 'AsyncSession', uid: str | int):
        self.db_session = session
        self.sub_id = str(uid)

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.weibo_user.value


__all__ = [
    'InternalSubscriptionSource',
    'InternalBilibiliLiveSubscriptionSource',
    'InternalBilibiliDynamicSubscriptionSource',
    'InternalPixivUserSubscriptionSource',
    'InternalPixivisionSubscriptionSource',
    'InternalWeiboUserSubscriptionSource',
]
