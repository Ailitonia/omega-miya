"""
@Author         : Ailitonia
@Date           : 2022/03/29 21:36
@FileName       : entity.py
@Project        : nonebot2_miya 
@Description    : Internal Entity Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel, root_validator
from typing import Type, Literal, List, Union, Optional
from datetime import timedelta, datetime, date
from omega_miya.result import BoolResult

from .consts import (PermissionGlobal, PermissionLevel,
                     SKIP_COOLDOWN_PERMISSION_NODE, GLOBAL_COOLDOWN_EVENT, RATE_LIMITING_COOLDOWN_EVENT)

from ..schemas import DatabaseErrorInfo
from ..schemas.bot_self import BotSelf, BotSelfModel
from ..schemas.entity import ENTITY_TYPE, Entity, EntityModel
from ..schemas.related_entity import RELATION_TYPE, RelatedEntity, RelatedEntityModel
from ..schemas.friendship import Friendship, FriendshipModel
from ..schemas.sign_in import SignIn
from ..schemas.auth_setting import AuthSetting, AuthSettingModel
from ..schemas.cool_down import CoolDown, CoolDownModel
from ..schemas.email_box import EmailBox, EmailBoxModel
from ..schemas.email_box_bind import EmailBoxBind
from ..schemas.subscription_source import SubscriptionSource, SubscriptionSourceModel
from ..schemas.subscription import Subscription


class BaseEntity(BaseModel):
    """实体模型基类"""
    entity_id: str
    entity_type: ENTITY_TYPE

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class BotSelfEntity(BaseEntity):
    """Bot 自身(特殊, 是所有对应群组、好友的父实体)"""
    entity_type: Literal['bot_self'] = 'bot_self'


class QQUserEntity(BaseEntity):
    """用户"""
    entity_type: Literal['qq_user'] = 'qq_user'


class QQGroupEntity(BaseEntity):
    """群组"""
    entity_type: Literal['qq_group'] = 'qq_group'


class GuildBotSelfEntity(BaseEntity):
    """频道系统内 Bot 自身(特殊, 是所有对应频道、子频道的父实体)
    (QQ频道的账号系统独立于 QQ 本体, 所以各个 ID 并不能和 QQ 通用.也无法通过 tiny_id 获取到 QQ号
    """
    entity_type: Literal['guild_bot_self'] = 'guild_bot_self'


class QQGuildUserEntity(BaseEntity):
    """频道系统内用户
    (QQ频道的账号系统独立于 QQ 本体, 所以各个 ID 并不能和 QQ 通用.也无法通过 tiny_id 获取到 QQ号
    """
    entity_type: Literal['qq_guild_user'] = 'qq_guild_user'


class QQGuildEntity(BaseEntity):
    """频道"""
    entity_type: Literal['qq_guild'] = 'qq_guild'


class QQChannelEntity(BaseEntity):
    """子频道"""
    entity_type: Literal['qq_channel'] = 'qq_channel'


class BaseRelation(BaseModel):
    """实体关系模型基类"""
    bot_self_id: str
    relation_type: RELATION_TYPE
    parent_entity: BaseEntity
    child_entity: BaseEntity

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False

    @classmethod
    def get_relation_type(cls) -> str:
        raise NotImplementedError


class BotGroupRelation(BaseRelation):
    """Bot 所在群"""
    relation_type: Literal['bot_group'] = 'bot_group'
    parent_entity: BotSelfEntity
    child_entity: QQGroupEntity

    @root_validator(pre=True)
    def parent_is_must_bot(cls, values):
        parent_id = values.get('parent_entity', {}).get('entity_id')
        bot_self_id = values.get('bot_self_id')

        if bot_self_id != parent_id:
            raise ValueError('BotGroupRelation parent entity must be Bot self')
        return values

    @classmethod
    def get_relation_type(cls) -> str:
        return 'bot_group'


class BotUserRelation(BaseRelation):
    """Bot 的好友/直接用户/临时会话"""
    relation_type: Literal['bot_user'] = 'bot_user'
    parent_entity: BotSelfEntity
    child_entity: QQUserEntity

    @root_validator(pre=True)
    def parent_is_must_bot(cls, values):
        parent_id = values.get('parent_entity', {}).get('entity_id')
        bot_self_id = values.get('bot_self_id')

        if bot_self_id != parent_id:
            raise ValueError('BotUserRelation parent entity must be Bot self')
        return values

    @classmethod
    def get_relation_type(cls) -> str:
        return 'bot_user'


class BotGuildRelation(BaseRelation):
    """Bot 所在频道"""
    relation_type: Literal['bot_guild'] = 'bot_guild'
    parent_entity: GuildBotSelfEntity
    child_entity: QQGuildEntity

    @classmethod
    def get_relation_type(cls) -> str:
        return 'bot_guild'


class GuildUserRelation(BaseRelation):
    """频道成员"""
    relation_type: Literal['bot_guild'] = 'guild_user'
    parent_entity: QQGuildEntity
    child_entity: QQGuildUserEntity

    @classmethod
    def get_relation_type(cls) -> str:
        return 'guild_user'


class GuildChannelRelation(BaseRelation):
    """子频道"""
    relation_type: Literal['guild_channel'] = 'guild_channel'
    parent_entity: QQGuildEntity
    child_entity: QQChannelEntity

    @classmethod
    def get_relation_type(cls) -> str:
        return 'guild_channel'


class GroupUserRelation(BaseRelation):
    """群成员"""
    relation_type: Literal['group_user'] = 'group_user'
    parent_entity: QQGroupEntity
    child_entity: QQUserEntity

    @classmethod
    def get_relation_type(cls) -> str:
        return 'group_user'


class BaseInternalEntity(object):
    """封装后用于插件调用的数据库关联实体基类"""
    _base_relation_model: Type[BaseRelation] = BaseRelation

    def __init__(self, bot_id: str, parent_id: str, entity_id: str):
        self.bot_id = bot_id
        self.parent_id = parent_id
        self.entity_id = entity_id
        self.relation = self._base_relation_model.parse_obj({
            'bot_self_id': bot_id,
            'parent_entity': {
                'entity_id': parent_id
            },
            'child_entity': {
                'entity_id': entity_id
            }
        })
        self.bot_self_model: Optional[BotSelfModel] = None
        self.parent_model: Optional[EntityModel] = None
        self.entity_model: Optional[EntityModel] = None
        self.relation_model: Optional[RelatedEntityModel] = None

    def __repr__(self):
        return f'<InternalEntity|{str(self.relation.relation_type).upper()}(bot_id={self.bot_id}, ' \
               f'parent_id={self.parent_id}, entity_id={self.entity_id}, relation_model={repr(self.relation)})>'

    @classmethod
    def parse_from_relation_model(cls, model: Union[BaseRelation, dict]) -> "BaseInternalEntity":
        """从 model 实例化"""
        parsed_relation = cls._base_relation_model.parse_obj(model)
        return cls(bot_id=parsed_relation.bot_self_id,
                   parent_id=parsed_relation.parent_entity.entity_id,
                   entity_id=parsed_relation.child_entity.entity_id)

    @classmethod
    async def query_all(cls) -> List[RelatedEntityModel]:
        """查询符合 relation_type 的全部结果"""
        relation_type = cls._base_relation_model.schema().get('properties', {}).get('relation_type', {}).get('default')
        if not relation_type:
            raise ValueError(f'Get sub_type from <cls._base_relation_model({cls._base_relation_model})> failed')
        return (await RelatedEntity.query_all_by_type(relation_type=relation_type)).result

    @classmethod
    async def query_by_index_id(cls, id_: int) -> RelatedEntityModel:
        """根据索引 id 查询"""
        relation = (await RelatedEntity.query_by_index_id(id_=id_)).result
        assert isinstance(relation, RelatedEntityModel), 'Query relation model failed'
        return relation

    @classmethod
    async def query_related_entity_by_index_id(cls, id_: int) -> (RelatedEntityModel, EntityModel, BotSelfModel):
        """根据索引 id 查询 RelatedEntityModel 及其对应 EntityModel, BotSelfModel

        :return: Tuple[RelatedEntityModel, EntityModel, BotSelfModel]
        """
        _re, _e, _bs = await RelatedEntity.query_related_entity_by_index_id(id_=id_)
        _re_m = RelatedEntityModel.from_orm(_re)
        _e_m = EntityModel.from_orm(_e)
        _bs_m = BotSelfModel.from_orm(_bs)
        return _re_m, _e_m, _bs_m

    @classmethod
    async def init_from_index_id(cls, id_: int) -> "BaseInternalEntity":
        """从索引 id 实例化"""
        relation, entity, bot_self = await cls.query_related_entity_by_index_id(id_=id_)
        parent_entity = (await Entity.query_by_index_id(id_=relation.parent_entity_id)).result
        model = {
            'bot_self_id': bot_self.self_id,
            'relation_type': relation.relation_type,
            'parent_entity': {
                'entity_id': parent_entity.entity_id,
                'entity_type': parent_entity.entity_type
            },
            'child_entity': {
                'entity_id': entity.entity_id,
                'entity_type': entity.entity_type
            }
        }
        new_related_entity = cls.parse_from_relation_model(model=model)
        new_related_entity.bot_self_model = bot_self
        new_related_entity.parent_model = parent_entity
        new_related_entity.entity_model = entity
        new_related_entity.relation_model = relation
        return new_related_entity

    async def get_bot_self_model(self) -> BotSelfModel:
        """获取并初始化 bot_self_model"""
        if not isinstance(self.bot_self_model, BotSelfModel):
            bot_self = BotSelf(self_id=self.bot_id)
            self.bot_self_model = (await bot_self.query()).result

        assert isinstance(self.bot_self_model, BotSelfModel), 'Query bot self model failed'
        return self.bot_self_model

    async def get_parent_model(self) -> EntityModel:
        """获取并初始化父实体 model"""
        if not isinstance(self.parent_model, EntityModel):
            parent = Entity(entity_id=self.parent_id, entity_type=self.relation.parent_entity.entity_type)
            self.parent_model = (await parent.query()).result

        assert isinstance(self.parent_model, EntityModel), 'Query parent model failed'
        return self.parent_model

    async def get_entity_model(self) -> EntityModel:
        """获取并初始化本实体 model"""
        if not isinstance(self.entity_model, EntityModel):
            entity = Entity(entity_id=self.entity_id, entity_type=self.relation.child_entity.entity_type)
            self.entity_model = (await entity.query()).result

        assert isinstance(self.entity_model, EntityModel), 'Query entity model failed'
        return self.entity_model

    async def get_relation_model(self) -> RelatedEntityModel:
        """获取并初始化关联实体 model"""
        if not isinstance(self.relation_model, RelatedEntityModel):
            bot_self = await self.get_bot_self_model()
            entity = await self.get_entity_model()
            parent = await self.get_parent_model()

            relation = RelatedEntity(
                bot_id=bot_self.id,
                entity_id=entity.id,
                parent_entity_id=parent.id,
                relation_type=self.relation.relation_type
            )
            self.relation_model = (await relation.query()).result

        assert isinstance(self.relation_model, RelatedEntityModel), 'Query relation model failed'
        return self.relation_model

    @property
    def query(self):
        """get_relation_model 别名"""
        return self.get_relation_model

    async def add_upgrade_parent(self, parent_entity_name: str, parent_entity_info: Optional[str] = None) -> BoolResult:
        """新增或更新父实体信息, 一般在新增或更新实体时使用"""
        return await Entity(
            entity_id=self.parent_id,
            entity_type=self.relation.parent_entity.entity_type
        ).add_upgrade_unique_self(entity_name=parent_entity_name, entity_info=parent_entity_info)

    async def add_only_parent(self, parent_entity_name: str, parent_entity_info: Optional[str] = None) -> BoolResult:
        """仅新增父实体信息, 一般在新增实体时使用"""
        return await Entity(
            entity_id=self.parent_id,
            entity_type=self.relation.parent_entity.entity_type
        ).add_only(entity_name=parent_entity_name, entity_info=parent_entity_info)

    async def add_upgrade_entity(self, entity_name: str, entity_info: Optional[str] = None) -> BoolResult:
        """新增或更新实体信息, 一般在新增或更新实体时使用"""
        return await Entity(
            entity_id=self.entity_id,
            entity_type=self.relation.child_entity.entity_type
        ).add_upgrade_unique_self(entity_name=entity_name, entity_info=entity_info)

    async def add_only_entity(self, entity_name: str, entity_info: Optional[str] = None) -> BoolResult:
        """仅新增实体信息, 一般在新增实体时使用"""
        return await Entity(
            entity_id=self.entity_id,
            entity_type=self.relation.child_entity.entity_type
        ).add_only(entity_name=entity_name, entity_info=entity_info)

    async def add_upgrade_relation(self, related_entity_name: str) -> BoolResult:
        """新增或更新关联实体信息, 一般在新增或更新实体时使用"""
        bot_self = await self.get_bot_self_model()
        entity = await self.get_entity_model()
        parent = await self.get_parent_model()
        return await RelatedEntity(
            bot_id=bot_self.id,
            entity_id=entity.id,
            parent_entity_id=parent.id,
            relation_type=self.relation.relation_type
        ).add_upgrade_unique_self(entity_name=related_entity_name)

    async def add_only_relation(self, related_entity_name: str) -> BoolResult:
        """仅新增关联实体信息, 一般在新增实体时使用"""
        bot_self = await self.get_bot_self_model()
        entity = await self.get_entity_model()
        parent = await self.get_parent_model()
        return await RelatedEntity(
            bot_id=bot_self.id,
            entity_id=entity.id,
            parent_entity_id=parent.id,
            relation_type=self.relation.relation_type
        ).add_only(entity_name=related_entity_name)

    async def add_upgrade(
            self,
            parent_entity_name: str,
            entity_name: str,
            related_entity_name: str,
            parent_entity_info: Optional[str] = None,
            entity_info: Optional[str] = None) -> BoolResult:
        """新增或更新"""
        parent_result = await self.add_upgrade_parent(
            parent_entity_name=parent_entity_name, parent_entity_info=parent_entity_info)
        if parent_result.error:
            return BoolResult(error=True, info=f'Add/Upgrade parent failed, {parent_result.info}', result=False)

        entity_result = await self.add_upgrade_entity(entity_name=entity_name, entity_info=entity_info)
        if entity_result.error:
            return BoolResult(error=True, info=f'Add/Upgrade entity failed, {entity_result.info}', result=False)

        relation_result = await self.add_upgrade_relation(related_entity_name=related_entity_name)
        if relation_result.error:
            return BoolResult(error=True, info=f'Add/Upgrade relation failed, {relation_result.info}', result=False)
        return BoolResult(error=False, info='Success', result=True)

    async def add_only(
            self,
            parent_entity_name: str = '',
            entity_name: str = '',
            related_entity_name: str = '',
            parent_entity_info: Optional[str] = None,
            entity_info: Optional[str] = None) -> BoolResult:
        """仅新增"""
        parent_result = await self.add_only_parent(
            parent_entity_name=parent_entity_name, parent_entity_info=parent_entity_info)
        if parent_result.error:
            return BoolResult(error=True, info=f'Add parent failed, {parent_result.info}', result=False)

        entity_result = await self.add_only_entity(entity_name=entity_name, entity_info=entity_info)
        if entity_result.error:
            return BoolResult(error=True, info=f'Add entity failed, {entity_result.info}', result=False)

        relation_result = await self.add_only_relation(related_entity_name=related_entity_name)
        if relation_result.error:
            return BoolResult(error=True, info=f'Add relation failed, {relation_result.info}', result=False)
        return BoolResult(error=False, info='Success', result=True)

    async def delete(self) -> BoolResult:
        """仅删除关联实体"""
        bot_self = await self.get_bot_self_model()
        entity = await self.get_entity_model()
        parent = await self.get_parent_model()
        return await RelatedEntity(
            bot_id=bot_self.id,
            entity_id=entity.id,
            parent_entity_id=parent.id,
            relation_type=self.relation.relation_type
        ).query_and_delete_unique_self()

    async def upgrade_or_reset_friendship(
            self,
            status: str = 'normal',
            mood: float = 0,
            friend_ship: float = 0,
            energy: float = 0,
            currency: float = 0,
            response_threshold: float = 0) -> BoolResult:
        """更新/初始化好感度"""
        related_entity = await self.get_relation_model()
        return await Friendship(entity_id=related_entity.id).add_upgrade_unique_self(
            status=status,
            mood=mood,
            friend_ship=friend_ship,
            energy=energy,
            currency=currency,
            response_threshold=response_threshold
        )

    async def get_friendship_model(self) -> FriendshipModel:
        """获取好感度, 没有则直接初始化"""
        related_entity = await self.get_relation_model()
        _result = await Friendship(entity_id=related_entity.id).query()
        if _result.error and _result.info == DatabaseErrorInfo.no_ret_f.value:
            await self.upgrade_or_reset_friendship()
            _result = await Friendship(entity_id=related_entity.id).query()

        assert isinstance(_result.result, FriendshipModel), f'Query friendship model failed, {_result.info}'
        return _result.result

    async def add_friendship(
            self,
            *,
            status: Optional[str] = None,
            mood: float = 0,
            friend_ship: float = 0,
            energy: float = 0,
            currency: float = 0,
            response_threshold: float = 0) -> BoolResult:
        """在现有好感度数值上加/减"""
        now_friendship = await self.get_friendship_model()
        status = now_friendship.status if status is None else status
        mood += now_friendship.mood
        friend_ship += now_friendship.friend_ship
        energy += now_friendship.energy
        currency += now_friendship.currency
        response_threshold += now_friendship.response_threshold
        return await self.upgrade_or_reset_friendship(
            status=status,
            mood=mood,
            friend_ship=friend_ship,
            energy=energy,
            currency=currency,
            response_threshold=response_threshold
        )

    async def sign_in(
            self,
            *,
            sign_in_info: Optional[str] = 'Normal sign in',
            date_: Optional[Union[date, datetime]] = None) -> BoolResult:
        """签到

        :param sign_in_info: 签到信息
        :param date_: 指定签到日期
        """
        related_entity = await self.get_relation_model()

        if isinstance(date_, datetime):
            sign_in_date = date_.date()
        elif isinstance(date_, date):
            sign_in_date = date_
        else:
            sign_in_date = datetime.now().date()
        return await SignIn(
            entity_id=related_entity.id, sign_in_date=sign_in_date).add_upgrade_unique_self(sign_in_info=sign_in_info)

    async def check_today_sign_in(self) -> bool:
        """检查今天是否已经签到"""
        related_entity = await self.get_relation_model()
        today = datetime.now().date()
        return await SignIn(entity_id=related_entity.id, sign_in_date=today).exist()

    async def query_sign_in_history(self) -> List[date]:
        """查询所有签到记录, 返回签到日期列表"""
        related_entity = await self.get_relation_model()
        return await SignIn.query_entity_all_signin_date(entity_id=related_entity.id)

    async def query_continuous_sign_in_day(self) -> int:
        """查询到现在为止最长连续签到日数"""
        sign_in_history = await self.query_sign_in_history()
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
        sign_in_history = await self.query_sign_in_history()
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

    @classmethod
    async def query_all_by_auth_node(
            cls,
            module: str,
            plugin: str,
            node: str,
            available: int = 1,
            *,
            require_available: bool = True,
            relation_type: Optional[str] = None) -> List[RelatedEntityModel]:
        """根据权限节点查询符合条件的结果

        :param module: 权限节点对应模块
        :param plugin: 权限节点对应插件
        :param node: 权限节点
        :param available: 启用/需求值
        :param require_available: True: 查询 available 大于等于传入参数的结果, False: 查询 available 等于传入参数的结果
        :param relation_type: None: 查询本 RelatedEntity 对应的 relation_type, relation_type: 查询对应 relation_type 的结果
        """
        if relation_type is None:
            relation_type = cls._base_relation_model.get_relation_type()

        return (await RelatedEntity.query_all_by_auth_node(
            module=module,
            plugin=plugin,
            node=node,
            available=available,
            require_available=require_available,
            relation_type=relation_type)).result

    async def query_all_auth_setting(self) -> List[AuthSettingModel]:
        """查询全部的权限配置"""
        related_entity = await self.get_relation_model()
        return (await AuthSetting.query_all_by_entity_id(entity_id=related_entity.id)).result

    async def query_plugin_auth_settings(self, module: str, plugin: str) -> list[AuthSettingModel]:
        """查具有某个插件的全部的权限配置"""
        related_entity = await self.get_relation_model()
        auth_settings_result = await AuthSetting.query_entity_plugin_auth_nodes(entity_id=related_entity.id,
                                                                                module=module, plugin=plugin)
        return auth_settings_result.result

    async def query_auth_setting(self, module: str, plugin: str, node: str) -> Optional[AuthSettingModel]:
        """查询对应 auth_setting"""
        related_entity = await self.get_relation_model()
        auth_setting = AuthSetting(entity_id=related_entity.id, module=module, plugin=plugin, node=node)
        return (await auth_setting.query()).result

    async def query_global_permission(self) -> Optional[AuthSettingModel]:
        """查询全局功能开关"""
        return await self.query_auth_setting(module=PermissionGlobal.module, plugin=PermissionGlobal.plugin,
                                             node=PermissionGlobal.node)

    async def query_permission_level(self) -> Optional[AuthSettingModel]:
        """查询权限等级"""
        return await self.query_auth_setting(module=PermissionLevel.module, plugin=PermissionLevel.plugin,
                                             node=PermissionLevel.node)

    async def check_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            available: int = 1,
            *,
            require_available: bool = True
    ) -> bool:
        """检查对应权限节点是否启用/符合需求值

        :param module: 权限节点对应模块
        :param plugin: 权限节点对应插件
        :param node: 权限节点
        :param available: 启用/需求值
        :param require_available: True: 查询 available 大于等于传入参数的结果, False: 查询 available 必须等于传入参数的结果
        """
        related_entity = await self.get_relation_model()
        auth_setting = await AuthSetting(entity_id=related_entity.id, module=module, plugin=plugin, node=node).query()
        if auth_setting.error:
            return False

        if require_available:
            if auth_setting.result.available >= available:
                return True
        else:
            if auth_setting.result.available == available:
                return True
        return False

    async def verify_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            available: int = 1,
            *,
            require_available: bool = True
    ) -> Literal[-2, -1, 0, 1]:
        """检查对应权限节点是否启用/符合需求值, 与 check_auth_setting 方法不同, 这个方法不会返回状态码表示权限验证的结果

        :param module: 权限节点对应模块
        :param plugin: 权限节点对应插件
        :param node: 权限节点
        :param available: 启用/需求值
        :param require_available: True: 查询 available 大于等于传入参数的结果, False: 查询 available 必须等于传入参数的结果
        :return: 结果状态码
            -2: 查询失败, 其他数据库异常
            -1: 已查找到条目, 该权限节点不符合需求/被拒绝
            0: 条目不存在, entity 没有配置该权限节点
            1: 已查找到条目, 该权限节点符合需求/验证通过
        """
        related_entity = await self.get_relation_model()
        auth_setting = await AuthSetting(entity_id=related_entity.id, module=module, plugin=plugin, node=node).query()

        if auth_setting.error and auth_setting.info == DatabaseErrorInfo.no_ret_f.value:
            return 0
        elif auth_setting.error:
            return -2

        if require_available:
            if auth_setting.result.available >= available:
                return 1
        else:
            if auth_setting.result.available == available:
                return 1
        return -1

    async def check_global_permission(self) -> bool:
        """检查是否打开全局功能开关"""
        return await self.check_auth_setting(module=PermissionGlobal.module, plugin=PermissionGlobal.plugin,
                                             node=PermissionGlobal.node, available=1, require_available=False)

    async def check_permission_skip_cooldown(self, module: str, plugin: str) -> bool:
        """检查是否有插件跳过冷却的权限"""
        return await self.check_auth_setting(module=module, plugin=plugin, node=SKIP_COOLDOWN_PERMISSION_NODE,
                                             available=1, require_available=False)

    async def check_permission_level(self, level: int) -> bool:
        """检查权限等级是否达到要求"""
        return await self.check_auth_setting(module=PermissionLevel.module, plugin=PermissionLevel.plugin,
                                             node=PermissionLevel.node, available=level, require_available=True)

    async def set_auth_setting(
            self, module: str, plugin: str, node: str, available: int, *, value: Optional[str] = None) -> BoolResult:
        """设置权限节点参数值"""
        related_entity = await self.get_relation_model()
        return await AuthSetting(
            entity_id=related_entity.id, module=module, plugin=plugin, node=node
        ).add_upgrade_unique_self(available=available, value=value)

    async def enable_global_permission(self) -> BoolResult:
        """打开全局功能开关"""
        return await self.set_auth_setting(module=PermissionGlobal.module, plugin=PermissionGlobal.plugin,
                                           node=PermissionGlobal.node, available=1)

    async def disable_global_permission(self) -> BoolResult:
        """关闭全局功能开关"""
        return await self.set_auth_setting(module=PermissionGlobal.module, plugin=PermissionGlobal.plugin,
                                           node=PermissionGlobal.node, available=0)

    async def enable_skip_cooldown_permission(self, module: str, plugin: str) -> BoolResult:
        """启用插件跳过冷却权限"""
        return await self.set_auth_setting(module=module, plugin=plugin, node=SKIP_COOLDOWN_PERMISSION_NODE,
                                           available=1)

    async def disable_skip_cooldown_permission(self, module: str, plugin: str) -> BoolResult:
        """关闭插件跳过冷却权限"""
        return await self.set_auth_setting(module=module, plugin=plugin, node=SKIP_COOLDOWN_PERMISSION_NODE,
                                           available=0)

    async def set_permission_level(self, level: int) -> BoolResult:
        """设置权限等级"""
        return await self.set_auth_setting(module=PermissionLevel.module, plugin=PermissionLevel.plugin,
                                           node=PermissionLevel.node, available=level)

    async def query_cool_down(self, cool_down_event: str) -> Optional[CoolDownModel]:
        """查询冷却"""
        related_entity = await self.get_relation_model()
        cool_down = CoolDown(entity_id=related_entity.id, event=cool_down_event)
        return (await cool_down.query()).result

    async def set_cool_down(
            self,
            cool_down_event: str,
            expired_time: Union[datetime, timedelta],
            description: Optional[str] = None) -> BoolResult:
        """设置冷却

        :param cool_down_event: 设置的冷却事件
        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
        :param description: 冷却描述信息
        """
        if isinstance(expired_time, datetime):
            stop_at = expired_time
        elif isinstance(expired_time, timedelta):
            stop_at = datetime.now() + expired_time
        else:
            raise ValueError('arg: "time" must be <datetime> or <timedelta>')

        related_entity = await self.get_relation_model()
        cool_down = CoolDown(entity_id=related_entity.id, event=cool_down_event)
        return await cool_down.add_upgrade_unique_self(stop_at=stop_at, description=description)

    async def check_cool_down_expired(self, cool_down_event: str) -> (bool, datetime):
        """查询冷却是否到期

        :return: 冷却是否已到期, (若仍在冷却中的)到期时间
        """
        related_entity = await self.get_relation_model()
        cool_down = await CoolDown(entity_id=related_entity.id, event=cool_down_event).query()

        if cool_down.error:
            return True, datetime.now()

        if cool_down.result.stop_at <= datetime.now():
            return True, cool_down.result.stop_at
        else:
            return False, cool_down.result.stop_at

    async def set_global_cooldown(self, expired_time: Union[datetime, timedelta]) -> BoolResult:
        """设置全局冷却

        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cool_down(
            cool_down_event=GLOBAL_COOLDOWN_EVENT, expired_time=expired_time, description='Global Cooldown')

    async def check_global_cooldown_expired(self) -> (bool, datetime):
        """查询全局冷却是否到期

        :return: 冷却是否已到期, (若仍在冷却中的)到期时间
        """
        return await self.check_cool_down_expired(cool_down_event=GLOBAL_COOLDOWN_EVENT)

    async def set_rate_limiting_cooldown(self, expired_time: Union[datetime, timedelta]) -> BoolResult:
        """设置流控专用冷却

        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cool_down(
            cool_down_event=RATE_LIMITING_COOLDOWN_EVENT, expired_time=expired_time, description='Rate Limiting')

    async def check_rate_limiting_cooldown_expired(self) -> (bool, datetime):
        """查询流控专用冷却是否到期

        :return: 冷却是否已到期, (若仍在冷却中的)到期时间
        """
        return await self.check_cool_down_expired(cool_down_event=RATE_LIMITING_COOLDOWN_EVENT)

    async def bind_email_box(self, address: str, *, bind_info: Optional[str] = None) -> BoolResult:
        """绑定邮箱"""
        related_entity = await self.get_relation_model()
        email_box = await EmailBox(address=address).query()
        if email_box.error:
            return BoolResult(error=True, info=f'Query email box failed, {email_box.info}', result=False)
        email_box_bind = EmailBoxBind(email_box_id=email_box.result.id, entity_id=related_entity.id)
        return await email_box_bind.add_upgrade_unique_self(bind_info=bind_info)

    async def unbind_email_box(self, address: str) -> BoolResult:
        """解绑邮箱"""
        related_entity = await self.get_relation_model()
        email_box = await EmailBox(address=address).query()
        if email_box.error:
            return BoolResult(error=True, info=f'Query email box failed, {email_box.info}', result=False)
        email_box_bind = EmailBoxBind(email_box_id=email_box.result.id, entity_id=related_entity.id)
        return await email_box_bind.query_and_delete_unique_self()

    async def query_bound_email_box(self) -> List[EmailBoxModel]:
        """查询已绑定的全部邮箱"""
        related_entity = await self.get_relation_model()
        return (await EmailBox.query_all_by_bound_entity_index_id(id_=related_entity.id)).result

    async def add_subscription(self, sub_type: str, sub_id: str, *, sub_info: Optional[str] = None) -> BoolResult:
        """添加订阅"""
        related_entity = await self.get_relation_model()
        subscription_source = await SubscriptionSource(sub_type=sub_type, sub_id=sub_id).query()
        if subscription_source.error:
            return BoolResult(
                error=True, info=f'Query subscription source failed, {subscription_source.info}', result=False)
        subscription = Subscription(sub_source_id=subscription_source.result.id, entity_id=related_entity.id)
        return await subscription.add_upgrade_unique_self(sub_info=sub_info)

    async def delete_subscription(self, sub_type: str, sub_id: str) -> BoolResult:
        """删除订阅"""
        related_entity = await self.get_relation_model()
        subscription_source = await SubscriptionSource(sub_type=sub_type, sub_id=sub_id).query()
        if subscription_source.error:
            return BoolResult(
                error=True, info=f'Query subscription source failed, {subscription_source.info}', result=False)
        subscription = Subscription(sub_source_id=subscription_source.result.id, entity_id=related_entity.id)
        return await subscription.query_and_delete_unique_self()

    async def query_all_subscribed_source(self, sub_type: Optional[str] = None) -> List[SubscriptionSourceModel]:
        """查询全部已订阅的订阅源

        :param sub_type: 筛选 sub_type
        """
        related_entity = await self.get_relation_model()
        return (
            await SubscriptionSource.query_all_by_subscribed_entity_index_id(id_=related_entity.id, sub_type=sub_type)
        ).result


class InternalBotGroup(BaseInternalEntity):
    _base_relation_model: Type[BaseRelation] = BotGroupRelation


class InternalBotUser(BaseInternalEntity):
    _base_relation_model: Type[BaseRelation] = BotUserRelation


class InternalBotGuild(BaseInternalEntity):
    _base_relation_model: Type[BaseRelation] = BotGuildRelation


class InternalGuildChannel(BaseInternalEntity):
    _base_relation_model: Type[BaseRelation] = GuildChannelRelation


class _InternalGroupUser(BaseInternalEntity):
    """Deactivated"""
    _base_relation_model: Type[BaseRelation] = GroupUserRelation


class InternalGuildUser(BaseInternalEntity):
    _base_relation_model: Type[BaseRelation] = GuildUserRelation


__all__ = [
    'BaseInternalEntity',
    'InternalBotGroup',
    'InternalBotUser',
    'InternalBotGuild',
    'InternalGuildChannel',
    'InternalGuildUser'
]
