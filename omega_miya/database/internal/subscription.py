"""
@Author         : Ailitonia
@Date           : 2022/04/03 23:31
@FileName       : subscription.py
@Project        : nonebot2_miya 
@Description    : Internal Subscription Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from enum import Enum, unique
from pydantic import BaseModel
from typing import List, Literal, Type, Optional
from omega_miya.result import BoolResult

from ..schemas.subscription_source import SubscriptionSource, SubscriptionSourceModel
from ..schemas.entity import Entity, EntityModel
from ..schemas.related_entity import RelatedEntity, RelatedEntityModel


@unique
class EnumSubscriptionSource(Enum):
    bili_live = 'bili_live'  # BiliBili 直播订阅
    bili_dynamic = 'bili_dynamic'  # BiliBili 动态订阅
    pixiv_user = 'pixiv_user'  # Pixiv 画师订阅
    pixivision = 'pixivision'  # Pixivision 文章订阅


class BaseSubscriptionSource(BaseModel):
    """订阅模型基类"""
    sub_type: EnumSubscriptionSource
    sub_id: str

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class InternalSubscriptionSource(object):
    """封装后用于插件调用的数据库订阅源基类"""
    _base_subscription_source_model: Type[BaseSubscriptionSource] = BaseSubscriptionSource

    def __init__(
            self,
            sub_type: Literal['bili_live', 'bili_dynamic', 'pixiv_user', 'pixivision'],
            sub_id: str):
        self.subscription_source = self._base_subscription_source_model.parse_obj({
            'sub_type': sub_type,
            'sub_id': sub_id
        })
        self.subscription_source_model: Optional[SubscriptionSourceModel] = None

    def __repr__(self):
        return f'<InternalSubscriptionSource|{str(self.subscription_source.sub_type).upper()}' \
               f'(sub_type={self.subscription_source.sub_type}, sub_id={self.subscription_source.sub_id})>'

    @classmethod
    async def query_all_by_sub_type(cls, sub_type: str) -> List[SubscriptionSourceModel]:
        """查询符合 sub_type 的全部结果"""
        if sub_type not in EnumSubscriptionSource.__members__.keys():
            raise ValueError(f'Illegal parameter, sub_type must be in '
                             f'"{"/".join(x for x in EnumSubscriptionSource.__members__.keys())}"')
        return (await SubscriptionSource.query_all_by_type(sub_type=sub_type)).result

    async def get_subscription_source_model(self) -> SubscriptionSourceModel:
        """获取并初始化 subscription_source_model"""
        if not isinstance(self.subscription_source_model, SubscriptionSourceModel):
            subscription_source = SubscriptionSource(
                sub_id=self.subscription_source.sub_id, sub_type=self.subscription_source.sub_type.value)
            self.subscription_source_model = (await subscription_source.query()).result

        assert isinstance(self.subscription_source_model, SubscriptionSourceModel), 'Query sub source model failed'
        return self.subscription_source_model

    @property
    def query(self):
        """get_subscription_source_model 别名"""
        return self.get_subscription_source_model

    async def exist(self) -> bool:
        """订阅源是否存在信息"""
        subscription_source = SubscriptionSource(
            sub_id=self.subscription_source.sub_id, sub_type=self.subscription_source.sub_type.value)
        return await subscription_source.exist()

    async def add_upgrade(self, sub_user_name: str, sub_info: Optional[str] = None) -> BoolResult:
        """新增或更新订阅源信息"""
        return await SubscriptionSource(
            sub_id=self.subscription_source.sub_id,
            sub_type=self.subscription_source.sub_type.value
        ).add_upgrade_unique_self(sub_user_name=sub_user_name, sub_info=sub_info)

    async def delete(self) -> BoolResult:
        """仅删除订阅源信息"""
        return await SubscriptionSource(
            sub_id=self.subscription_source.sub_id,
            sub_type=self.subscription_source.sub_type.value
        ).query_and_delete_unique_self()

    async def query_all_subscribed_entity(self, *, entity_type: Optional[str] = None) -> List[EntityModel]:
        """查询订阅本来源的 Entity

        :param entity_type: 筛选 entity_type
        """
        subscription = await self.get_subscription_source_model()
        query_result = await Entity.query_all_by_subscribed_source_index_id(id_=subscription.id,
                                                                            entity_type=entity_type)
        return query_result.result

    async def query_all_subscribed_related_entity(
            self, *, relation_type: Optional[str] = None) -> List[RelatedEntityModel]:
        """查询订阅本来源的 RelatedEntity

        :param relation_type: 筛选 relation_type
        """
        subscription = await self.get_subscription_source_model()
        query_result = await RelatedEntity.query_all_by_subscribed_source_index_id(id_=subscription.id,
                                                                                   relation_type=relation_type)
        return query_result.result


___all__ = [
    'InternalSubscriptionSource'
]
