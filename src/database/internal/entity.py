"""
@Author         : Ailitonia
@Date           : 2022/12/03 15:24
@FileName       : entity.py
@Project        : nonebot2_miya
@Description    : Entity DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum, unique
from typing import Annotated, Any, Literal, overload

from pydantic import Field
from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import selectinload

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import (
    AuthSettingOrm,
    BotSelfOrm,
    CooldownOrm,
    EntityOrm,
    FriendshipOrm,
    SignInOrm,
    SubscriptionOrm,
    SubscriptionSourceOrm,
)


@unique
class EntityType(StrEnum):
    """实体对象类型"""
    CONSOLE_USER = 'console_user'  # nonebot-console 用户

    ONEBOT_V11_USER = 'onebot_v11_user'  # QQ 用户 (OneBot 协议)
    ONEBOT_V11_GROUP = 'onebot_v11_group'  # QQ 群组 (OneBot 协议)
    ONEBOT_V11_GUILD = 'onebot_v11_guild'  # QQ 频道 (OneBot 协议)
    ONEBOT_V11_GUILD_USER = 'onebot_v11_guild_user'  # QQ 频道系统内用户 (OneBot 协议)
    ONEBOT_V11_GUILD_CHANNEL = 'onebot_v11_guild_channel'  # QQ 频道子频道 (OneBot 协议)

    QQGUILD_GUILD = 'qqguild_guild'  # [Deactivate] QQ 频道子频道 (QQGuild 协议)
    QQGUILD_USER = 'qqguild_user'  # [Deactivate] QQ 频道系统内用户 (QQGuild 协议)
    QQGUILD_CHANNEL = 'qqguild_channel'  # [Deactivate] QQ 频道子频道 (QQGuild 协议)

    QQ_GUILD = 'qq_guild'  # QQ 频道频道 (QQ 官方协议)
    QQ_CHANNEL = 'qq_channel'  # QQ 频道子频道 (QQ 官方协议)
    QQ_GROUP = 'qq_group'  # QQ 群 (预留非频道场景) (QQ 官方协议)
    QQ_USER = 'qq_user'  # QQ 用户 (预留非频道用户) (QQ 官方协议)
    QQ_GUILD_USER = 'qq_guild_user'  # QQ 频道系统内用户 (QQ 官方协议)

    TELEGRAM_USER = 'telegram_user'  # Telegram 用户
    TELEGRAM_GROUP = 'telegram_group'  # Telegram 群组
    TELEGRAM_CHANNEL = 'telegram_channel'  # Telegram 频道

    @classmethod
    def get_supported_target_names(cls) -> set[str]:
        return {member.value for _, member in cls.__members__.items()}


class _BaseEntity(BaseDataOutModel):
    """实体对象数据 (只包括基本数据供关联表使用, 避免递归加载)"""
    id: int
    bot_index_id: int
    entity_type: EntityType
    entity_id: str
    entity_name: str


class _Bot(BaseDataOutModel):
    """实体归属的 Bot 数据  (只包括基本数据供关联表使用, 避免递归加载)"""
    id: int
    bot_type: str
    self_id: str
    bot_status: int
    bot_info: str | None


class Friendship(BaseDataOutModel):
    """好感度数据"""
    id: int
    entity_index_id: int
    status: str
    mood: Decimal
    friendship: Decimal
    energy: Decimal
    currency: Decimal
    rsp_threshold: Decimal
    created_at: datetime | None
    updated_at: datetime | None

    # 级联数据
    friendship_parent_entity: _BaseEntity


class SignIn(BaseDataOutModel):
    """签到数据"""
    id: int
    entity_index_id: int
    sign_in_date: date
    sign_in_info: str | None
    created_at: datetime | None
    updated_at: datetime | None

    # 级联数据
    sign_in_parent_entity: _BaseEntity


class AuthSetting(BaseDataOutModel):
    """授权配置数据"""
    id: int
    entity_index_id: int
    module: str
    plugin: str
    node: str
    available: int
    value: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None

    # 级联数据
    auth_parent_entity: _BaseEntity


class Cooldown(BaseDataOutModel):
    """冷却事件数据"""
    id: int
    entity_index_id: int
    event: str
    stop_at: datetime
    description: str | None
    created_at: datetime | None
    updated_at: datetime | None

    # 级联数据
    cooldown_parent_entity: _BaseEntity


class _SubscribedSource(BaseDataOutModel):
    """已定义的订阅源数据  (只包括基本数据供关联表使用, 避免递归加载)"""
    id: int
    sub_type: str
    sub_id: str
    sub_user_name: str
    sub_info: str | None


class _Subscription(BaseDataOutModel):
    """订阅数据  (只包括基本数据供关联表使用, 避免递归加载)"""
    sub_source_index_id: int
    entity_index_id: int
    sub_info: str | None

    # 级联数据
    subscription_parent_source: _SubscribedSource
    subscription_parent_entity: _BaseEntity


class Entity(_BaseEntity):
    """实体对象数据"""
    entity_info: str | None
    created_at: datetime | None
    updated_at: datetime | None

    # 级联数据
    entity_parent_bot: _Bot

    def __str__(self) -> str:
        return f'Entity.{self.entity_type.value}(entity_id={self.entity_id}, name={self.entity_name})'


class EntityWithFullRel(Entity):
    """实体对象数据 (包含全部级联属性)"""
    friendship_belonged_to_entity: Annotated[list[Friendship], Field(default_factory=list)]
    sign_in_belonged_to_entity: Annotated[list[SignIn], Field(default_factory=list)]
    auth_belonged_to_entity: Annotated[list[AuthSetting], Field(default_factory=list)]
    cooldown_belonged_to_entity: Annotated[list[Cooldown], Field(default_factory=list)]
    subscription_sources_entity_had: Annotated[list[_SubscribedSource], Field(default_factory=list)]


class EntityDAL(BaseDataAccessLayer[EntityOrm, Entity]):
    """实体对象 数据库操作对象"""

    async def _count_entity_all(self) -> int:
        """查询 entity 全表行数"""
        stmt = select(func.count()).select_from(EntityOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _count_entity_friendship_all(self) -> int:
        """查询 friendship 全表行数"""
        stmt = select(func.count()).select_from(FriendshipOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _count_entity_sign_in_all(self) -> int:
        """查询 sign_in 全表行数"""
        stmt = select(func.count()).select_from(SignInOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _count_entity_auth_setting_all(self) -> int:
        """查询 auth_setting 全表行数"""
        stmt = select(func.count()).select_from(AuthSettingOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _count_entity_cooldown_all(self) -> int:
        """查询 cooldown 全表行数"""
        stmt = select(func.count()).select_from(CooldownOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _count_entity_subscription_all(self) -> int:
        """查询 subscription 全表行数"""
        stmt = select(func.count()).select_from(SubscriptionOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表 (含friendship/sign_in/auth_setting/cooldown/subscription等关联表)

        敏感操作, 方法内不执行 commit, 可由外层事务 rollback
        按子表到父表的顺序删除, 不依赖数据库外键级联
        """
        await self.db_session.execute(delete(SubscriptionOrm))
        await self.db_session.execute(delete(CooldownOrm))
        await self.db_session.execute(delete(AuthSettingOrm))
        await self.db_session.execute(delete(SignInOrm))
        await self.db_session.execute(delete(FriendshipOrm))
        await self.db_session.execute(delete(EntityOrm))
        self.db_session.expunge_all()

    # ------------------------------------------------------------------ #
    # Entity 对象自身相关方法
    # ------------------------------------------------------------------ #

    async def _select_unique(
            self,
            bot_type: str,
            bot_self_id: str,
            entity_type: str,
            entity_id: str,
            *,
            load_all_rel: bool = False,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> EntityOrm:
        stmt = (
            select(EntityOrm)
            .where(EntityOrm.entity_parent_bot.has(and_(
                BotSelfOrm.bot_type == bot_type,
                BotSelfOrm.self_id == bot_self_id,
            )))
            .where(EntityOrm.entity_type == entity_type)
            .where(EntityOrm.entity_id == entity_id)
        )

        if load_all_rel:
            stmt = (stmt
                    .options(selectinload(EntityOrm.friendship_belonged_to_entity))
                    .options(selectinload(EntityOrm.sign_in_belonged_to_entity))
                    .options(selectinload(EntityOrm.auth_belonged_to_entity))
                    .options(selectinload(EntityOrm.cooldown_belonged_to_entity))
                    .options(selectinload(EntityOrm.subscription_sources_entity_had)))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def _select_from_index_id(
            self,
            index_id: int,
            *,
            load_all_rel: bool = False,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> EntityOrm:
        stmt = select(EntityOrm).where(EntityOrm.id == index_id)

        if load_all_rel:
            stmt = (stmt
                    .options(selectinload(EntityOrm.friendship_belonged_to_entity))
                    .options(selectinload(EntityOrm.sign_in_belonged_to_entity))
                    .options(selectinload(EntityOrm.auth_belonged_to_entity))
                    .options(selectinload(EntityOrm.cooldown_belonged_to_entity))
                    .options(selectinload(EntityOrm.subscription_sources_entity_had)))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    @overload
    async def query_unique(
            self,
            bot_type: str | None,
            bot_self_id: str | None,
            entity_type: str | None,
            entity_id: str | None,
            index_id: int | None,
            *,
            load_all_rel: Literal[False] = False,
            populate_existing: bool = False,
    ) -> Entity:
        ...

    @overload
    async def query_unique(
            self,
            bot_type: str | None,
            bot_self_id: str | None,
            entity_type: str | None,
            entity_id: str | None,
            index_id: int | None,
            *,
            load_all_rel: Literal[True],
            populate_existing: bool = False,
    ) -> EntityWithFullRel:
        ...

    async def query_unique(
            self,
            bot_type: str | None = None,
            bot_self_id: str | None = None,
            entity_type: str | None = None,
            entity_id: str | None = None,
            index_id: int | None = None,
            *,
            load_all_rel: bool = False,
            populate_existing: bool = False,
    ) -> Entity | EntityWithFullRel:
        if index_id is not None:
            item = await self._select_from_index_id(
                index_id,
                load_all_rel=load_all_rel,
                populate_existing=populate_existing,
            )
        elif (bot_type is not None
              and bot_self_id is not None
              and entity_type is not None
              and entity_id is not None):
            item = await self._select_unique(
                bot_type,
                bot_self_id,
                entity_type,
                entity_id,
                load_all_rel=load_all_rel,
                populate_existing=populate_existing,
            )
        else:
            raise ValueError('bot_type/bot_self_id/entity_type/entity_id must both be provided when index_id is None')

        if load_all_rel:
            return EntityWithFullRel.model_validate(item)
        else:
            return Entity.model_validate(item)

    async def query_all(
            self,
            *,
            populate_existing: bool = False,
    ) -> list[Entity]:
        """查询全部实体条目 (不加载级联属性)"""
        stmt = select(EntityOrm).order_by(EntityOrm.entity_type, EntityOrm.entity_id)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[Entity], (await self.db_session.execute(stmt)).scalars().all())

    async def query_type_all(
            self,
            bot_type: str,
            bot_self_id: str,
            entity_type: str,
            *,
            populate_existing: bool = False,
    ) -> list[Entity]:
        """查询符合 entity_type 的全部实体条目 (不加载级联属性)"""
        stmt = (
            select(EntityOrm)
            .options(selectinload(EntityOrm.entity_parent_bot))
            .where(EntityOrm.entity_parent_bot.has(and_(
                BotSelfOrm.bot_type == bot_type,
                BotSelfOrm.self_id == bot_self_id)
            ))
            .where(EntityOrm.entity_type == entity_type)
            .order_by(EntityOrm.entity_type, EntityOrm.entity_id)
        )

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[Entity], (await self.db_session.execute(stmt)).scalars().all())

    async def add_update_exist(
            self,
            bot_type: str,
            bot_self_id: str,
            entity_type: str,
            entity_id: str,
            entity_name: str,
            entity_info: str | None = None
    ) -> Entity:
        """向数据库插入新行, 存在则更新

        通过捕获异常实现, 性能较差, 且并发时仍可能出现死锁或需要重试

        Note: SQLite 后端在嵌套事务 (SAVEPOINT) 场景下, 插入分支可能因驱动 legacy 事务控制
        (会话事务不显式发送 BEGIN, SAVEPOINT 直接开启物理事务且 RELEASE 即提交) 而被提前提交,
        外层事务 rollback 无法撤销; MySQL/PostgreSQL 后端不受影响
        """
        select_bot_stmt = (select(BotSelfOrm)
                           .where(BotSelfOrm.bot_type == bot_type)
                           .where(BotSelfOrm.self_id == bot_self_id)
                           .execution_options(populate_existing=True))
        bot_item = (await self.db_session.execute(select_bot_stmt)).scalar_one()

        new_obj = EntityOrm(
            bot_index_id=bot_item.id,
            entity_type=EntityType(entity_type),
            entity_id=entity_id,
            entity_name=entity_name,
            entity_info=entity_info,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_unique(
                    bot_type,
                    bot_self_id,
                    entity_type,
                    entity_id,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.entity_name = entity_name
                exist_obj.entity_info = entity_info
                await session.flush()

        # 重新加载实体及其所属 bot, 确保返回数据模型时关系属性已加载
        entity_item = await self._select_unique(
            bot_type,
            bot_self_id,
            entity_type,
            entity_id,
            load_all_rel=False,
            populate_existing=True,
        )
        return Entity.model_validate(entity_item)

    async def add_ignore_exist(
            self,
            bot_type: str,
            bot_self_id: str,
            entity_type: str,
            entity_id: str,
            entity_name: str,
            entity_info: str | None = None
    ) -> Entity:
        """向数据库插入新行, 若已存在则忽略

        Note: SQLite 后端在嵌套事务 (SAVEPOINT) 场景下, 插入分支可能因驱动 legacy 事务控制
        (会话事务不显式发送 BEGIN, SAVEPOINT 直接开启物理事务且 RELEASE 即提交) 而被提前提交,
        外层事务 rollback 无法撤销; MySQL/PostgreSQL 后端不受影响
        """
        select_bot_stmt = (select(BotSelfOrm)
                           .where(BotSelfOrm.bot_type == bot_type)
                           .where(BotSelfOrm.self_id == bot_self_id)
                           .execution_options(populate_existing=True))
        bot_item = (await self.db_session.execute(select_bot_stmt)).scalar_one()

        new_obj = EntityOrm(
            bot_index_id=bot_item.id,
            entity_type=EntityType(entity_type),
            entity_id=entity_id,
            entity_name=entity_name,
            entity_info=entity_info,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 插入失败说明是已存在的条目, 忽略本次提交的实体信息; 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise

        # 重新加载实体及其所属 bot, 确保返回数据模型时关系属性已加载
        entity_item = await self._select_unique(
            bot_type,
            bot_self_id,
            entity_type,
            entity_id,
            load_all_rel=False,
            populate_existing=True,
        )
        return Entity.model_validate(entity_item)

    async def delete_from_index(self, index_id: int) -> None:
        stmt = delete(EntityOrm).where(EntityOrm.id == index_id)
        await self.db_session.execute(stmt)

    # ------------------------------------------------------------------ #
    # Friendship 好感度及状态相关方法
    # ------------------------------------------------------------------ #

    async def _select_entity_friendship(
            self,
            entity_index_id: int,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> FriendshipOrm:
        stmt = select(FriendshipOrm).where(FriendshipOrm.entity_index_id == entity_index_id)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def set_entity_friendship(
            self,
            entity_index_id: int,
            *,
            status: str | None = None,
            mood: Decimal | None = None,
            friendship: Decimal | None = None,
            energy: Decimal | None = None,
            currency: Decimal | None = None,
            rsp_threshold: Decimal | None = None,
    ) -> Friendship:
        """设置或更新好感度"""
        new_obj = FriendshipOrm(
            entity_index_id=entity_index_id,
            status=status or 'normal',
            mood=mood if mood is not None else Decimal('0'),
            friendship=friendship if friendship is not None else Decimal('0'),
            energy=energy if energy is not None else Decimal('0'),
            currency=currency if currency is not None else Decimal('0'),
            rsp_threshold=rsp_threshold if rsp_threshold is not None else Decimal('0'),
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_entity_friendship(
                    entity_index_id,
                    populate_existing=True,
                    with_for_update=True,
                )
                if status is not None:
                    exist_obj.status = status
                if mood is not None:
                    exist_obj.mood = mood
                if friendship is not None:
                    exist_obj.friendship = friendship
                if energy is not None:
                    exist_obj.energy = energy
                if currency is not None:
                    exist_obj.currency = currency
                if rsp_threshold is not None:
                    exist_obj.rsp_threshold = rsp_threshold
                await session.flush()

        # 重新加载确保返回数据模型时关系属性已加载
        friendship_item = await self._select_entity_friendship(entity_index_id, populate_existing=True)
        return Friendship.model_validate(friendship_item)

    async def change_entity_friendship(
            self,
            entity_index_id: int,
            *,
            mood: Decimal = Decimal('0'),
            friendship: Decimal = Decimal('0'),
            energy: Decimal = Decimal('0'),
            currency: Decimal = Decimal('0'),
            rsp_threshold: Decimal = Decimal('0'),
    ) -> Friendship:
        """变更好感度, 在现有好感度数值上加/减"""
        new_obj = FriendshipOrm(
            entity_index_id=entity_index_id,
            status='normal',
            mood=mood,
            friendship=friendship,
            energy=energy,
            currency=currency,
            rsp_threshold=rsp_threshold,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_entity_friendship(
                    entity_index_id,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.mood += mood
                exist_obj.friendship += friendship
                exist_obj.energy += energy
                exist_obj.currency += currency
                exist_obj.rsp_threshold += rsp_threshold
                await session.flush()

        # 重新加载确保返回数据模型时关系属性已加载
        friendship_item = await self._select_entity_friendship(entity_index_id, populate_existing=True)
        return Friendship.model_validate(friendship_item)

    async def query_entity_friendship(self, entity_index_id: int) -> Friendship:
        """获取实体的好感度信息, 没有则直接初始化"""
        try:
            friendship_item = await self._select_entity_friendship(entity_index_id, populate_existing=True)
        except NoResultFound:
            await self.set_entity_friendship(entity_index_id)
            friendship_item = await self._select_entity_friendship(entity_index_id, populate_existing=True)
        return Friendship.model_validate(friendship_item)

    # ------------------------------------------------------------------ #
    # SignIn 签到相关方法
    # ------------------------------------------------------------------ #

    async def _select_entity_sign_in(
            self,
            entity_index_id: int,
            date_: date,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> SignInOrm:
        stmt = (select(SignInOrm)
                .where(SignInOrm.entity_index_id == entity_index_id)
                .where(SignInOrm.sign_in_date == date_))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def set_entity_sign_in(
            self,
            entity_index_id: int,
            *,
            date_: date | datetime | None = None,
            sign_in_info: str | None = None,
    ) -> SignIn:
        """为实体添加签到信息, 若不指定签到日期则为当天

        重复签到 (同一实体同一日期已存在记录) 时: 显式指定 sign_in_info 则覆盖为指定值,
        未指定则标记为 'Duplicate Sign In'
        """
        if isinstance(date_, datetime):
            sign_in_date = date_.date()
            default_info = 'Fixed Sign In'
        elif isinstance(date_, date):
            sign_in_date = date_
            default_info = 'Fixed Sign In'
        else:
            sign_in_date = datetime.now().date()
            default_info = 'Normal Sign In'

        new_obj = SignInOrm(
            entity_index_id=entity_index_id,
            sign_in_date=sign_in_date,
            sign_in_info=default_info if sign_in_info is None else sign_in_info,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_entity_sign_in(
                    entity_index_id,
                    sign_in_date,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.sign_in_info = 'Duplicate Sign In' if sign_in_info is None else sign_in_info
                await session.flush()

        # 重新加载确保返回数据模型时关系属性已加载
        sign_in_item = await self._select_entity_sign_in(entity_index_id, sign_in_date, populate_existing=True)
        return SignIn.model_validate(sign_in_item)

    async def check_entity_today_is_sign_in(
            self,
            entity_index_id: int,
            *,
            date_: date | datetime | None = None,
    ) -> bool:
        """检查日期是否已经签到"""
        if isinstance(date_, datetime):
            sign_in_date = date_.date()
        elif isinstance(date_, date):
            sign_in_date = date_
        else:
            sign_in_date = datetime.now().date()

        try:
            await self._select_entity_sign_in(entity_index_id, sign_in_date, populate_existing=True)
            return True
        except NoResultFound:
            return False

    async def query_entity_sign_in_days(self, entity_index_id: int) -> list[date]:
        """查询实体所有的签到记录, 返回签到日期列表"""
        stmt = (select(SignInOrm.sign_in_date)
                .where(SignInOrm.entity_index_id == entity_index_id)
                .execution_options(populate_existing=True))

        return list((await self.db_session.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------ #
    # AuthSetting 授权及实体配置相关方法
    # ------------------------------------------------------------------ #

    async def _select_entity_auth_setting(
            self,
            entity_index_id: int,
            module: str,
            plugin: str,
            node: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> AuthSettingOrm:
        stmt = (select(AuthSettingOrm)
                .where(AuthSettingOrm.entity_index_id == entity_index_id)
                .where(AuthSettingOrm.module == module)
                .where(AuthSettingOrm.plugin == plugin)
                .where(AuthSettingOrm.node == node))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_entity_auth_setting(
            self,
            entity_index_id: int,
            module: str,
            plugin: str,
            node: str,
            *,
            populate_existing: bool = False,
    ) -> AuthSetting:
        item = await self._select_entity_auth_setting(
            entity_index_id,
            module,
            plugin,
            node,
            populate_existing=populate_existing,
        )
        return AuthSetting.model_validate(item)

    async def query_entity_any_auth_settings(
            self,
            entity_index_id: int,
            module: str | None = None,
            plugin: str | None = None,
            *,
            populate_existing: bool = False,
    ) -> list[AuthSetting]:
        """查询 Entity 具有的全部/某个模块/插件的权限配置"""
        stmt = (select(AuthSettingOrm)
                .where(AuthSettingOrm.entity_index_id == entity_index_id)
                .order_by(AuthSettingOrm.module, AuthSettingOrm.plugin, AuthSettingOrm.node))

        if module is not None:
            stmt = stmt.where(AuthSettingOrm.module == module)
        if plugin is not None:
            stmt = stmt.where(AuthSettingOrm.plugin == plugin)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[AuthSetting], (await self.db_session.execute(stmt)).scalars().all())

    async def query_module_plugin_any_auth_settings(
            self,
            module: str,
            plugin: str,
            *,
            populate_existing: bool = False,
    ) -> list[AuthSetting]:
        """查询某个模块/插件所有已配置的权限配置"""
        stmt = (select(AuthSettingOrm)
                .where(AuthSettingOrm.module == module)
                .where(AuthSettingOrm.plugin == plugin)
                .order_by(AuthSettingOrm.module, AuthSettingOrm.plugin, AuthSettingOrm.node))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[AuthSetting], (await self.db_session.execute(stmt)).scalars().all())

    async def query_entities_has_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            *,
            available: int = 1,
            strict_match: bool = True,
            populate_existing: bool = False,
    ) -> list[Entity]:
        """根据权限节点查询具备该节点的实体对象"""
        stmt = (
            select(EntityOrm)
            .where(EntityOrm.auth_belonged_to_entity.any(and_(
                AuthSettingOrm.module == module,
                AuthSettingOrm.plugin == plugin,
                AuthSettingOrm.node == node,
                AuthSettingOrm.available == available if strict_match else AuthSettingOrm.available >= available,
            )))
            .order_by(EntityOrm.entity_type, EntityOrm.entity_id)
        )

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[Entity], (await self.db_session.execute(stmt)).scalars().all())

    async def set_entity_auth_setting(
            self,
            entity_index_id: int,
            module: str,
            plugin: str,
            node: str,
            available: int,
            value: dict[str, Any],
    ) -> AuthSetting:
        """设置 Entity 权限或配置节点参数值"""
        value = parse_obj_as(dict[str, Any], value)

        new_obj = AuthSettingOrm(
            entity_index_id=entity_index_id,
            module=module,
            plugin=plugin,
            node=node,
            available=available,
            value=value,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_entity_auth_setting(
                    entity_index_id,
                    module,
                    plugin,
                    node,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.available = available
                exist_obj.value = value
                await session.flush()

        # 重新加载确保返回数据模型时关系属性已加载
        auth_setting_item = await self._select_entity_auth_setting(
            entity_index_id,
            module,
            plugin,
            node,
            populate_existing=True,
        )
        return AuthSetting.model_validate(auth_setting_item)

    async def delete_entity_auth_setting(
            self,
            entity_index_id: int,
            module: str,
            plugin: str,
            node: str,
    ) -> None:
        stmt = (delete(AuthSettingOrm)
                .where(AuthSettingOrm.entity_index_id == entity_index_id)
                .where(AuthSettingOrm.module == module)
                .where(AuthSettingOrm.plugin == plugin)
                .where(AuthSettingOrm.node == node))
        await self.db_session.execute(stmt)

    # ------------------------------------------------------------------ #
    # Cooldown 冷却事件相关方法
    # ------------------------------------------------------------------ #

    async def _select_entity_cooldown(
            self,
            entity_index_id: int,
            event: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> CooldownOrm:
        stmt = (select(CooldownOrm)
                .where(CooldownOrm.entity_index_id == entity_index_id)
                .where(CooldownOrm.event == event))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_entity_cooldown(
            self,
            entity_index_id: int,
            event: str,
            *,
            populate_existing: bool = False,
    ) -> Cooldown:
        item = await self._select_entity_cooldown(
            entity_index_id,
            event,
            populate_existing=populate_existing,
        )
        return Cooldown.model_validate(item)

    async def check_entity_cooldown_is_expired(
            self,
            entity_index_id: int,
            event: str,
    ) -> tuple[bool, datetime]:
        """查询冷却是否到期

        :return: (True=已到期或不存在改冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
        """
        try:
            cooldown = await self.query_entity_cooldown(entity_index_id, event)
            if cooldown.stop_at <= datetime.now():
                return True, cooldown.stop_at
            else:
                return False, cooldown.stop_at
        except NoResultFound:
            return True, datetime.now()

    async def set_entity_cooldown(
            self,
            entity_index_id: int,
            event: str,
            expired_time: datetime | timedelta,
            description: str | None = None,
    ) -> Cooldown:
        """设置冷却

        :param entity_index_id: Entity 索引 ID
        :param event: 冷却事件名
        :param expired_time: datetime 类型时指定为冷却过期时间, timedelta 类型时指定为以现在时间为准新增的冷却时长
        :param description: 冷却事件名描述
        """
        if isinstance(expired_time, datetime):
            stop_at = expired_time
        elif isinstance(expired_time, timedelta):
            stop_at = datetime.now() + expired_time
        else:
            raise TypeError('expired_time must be datetime or timedelta')

        new_obj = CooldownOrm(
            entity_index_id=entity_index_id,
            event=event,
            stop_at=stop_at,
            description=description,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_entity_cooldown(
                    entity_index_id,
                    event,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.stop_at = stop_at
                if description is not None:
                    exist_obj.description = description
                await session.flush()

        # 重新加载确保返回数据模型时关系属性已加载
        cooldown_item = await self._select_entity_cooldown(
            entity_index_id,
            event,
            populate_existing=True,
        )
        return Cooldown.model_validate(cooldown_item)

    async def delete_entity_cooldown(
            self,
            entity_index_id: int,
            event: str,
    ) -> None:
        stmt = (delete(CooldownOrm)
                .where(CooldownOrm.entity_index_id == entity_index_id)
                .where(CooldownOrm.event == event))
        await self.db_session.execute(stmt)

    async def clear_all_expired_cooldown(self) -> None:
        stmt = delete(CooldownOrm).where(CooldownOrm.stop_at <= datetime.now())
        await self.db_session.execute(stmt)

    # ------------------------------------------------------------------ #
    # Subscription 订阅相关方法
    # ------------------------------------------------------------------ #

    async def _select_entity_subscription(
            self,
            entity_index_id: int,
            sub_source_index_id: int,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> SubscriptionOrm:
        stmt = (select(SubscriptionOrm)
                .where(SubscriptionOrm.entity_index_id == entity_index_id)
                .where(SubscriptionOrm.sub_source_index_id == sub_source_index_id))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_entity_subscribed_source(
            self,
            entity_index_id: int,
            sub_type: str | None = None,
            *,
            populate_existing: bool = False,
    ) -> list[_SubscribedSource]:
        stmt = (
            select(SubscriptionSourceOrm)
            .where(SubscriptionSourceOrm.entities_subscription_source_had.any(EntityOrm.id == entity_index_id))
        )

        if sub_type is not None:
            stmt = stmt.where(SubscriptionSourceOrm.sub_type == sub_type)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[_SubscribedSource], (await self.db_session.execute(stmt)).scalars().all())

    async def set_entity_subscription(
            self,
            entity_index_id: int,
            sub_source_index_id: int,
            sub_info: str | None = None,
    ) -> _Subscription:
        """设置 Entity 订阅"""
        new_obj = SubscriptionOrm(
            sub_source_index_id=sub_source_index_id,
            entity_index_id=entity_index_id,
            sub_info=sub_info,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_entity_subscription(
                    entity_index_id=entity_index_id,
                    sub_source_index_id=sub_source_index_id,
                    populate_existing=True,
                    with_for_update=True,
                )
                if sub_info is not None:
                    exist_obj.sub_info = sub_info
                await session.flush()

        # 重新加载确保返回数据模型时关系属性已加载
        subscription_item = await self._select_entity_subscription(
            entity_index_id=entity_index_id,
            sub_source_index_id=sub_source_index_id,
            populate_existing=True,
        )
        return _Subscription.model_validate(subscription_item)

    async def delete_entity_subscription(
            self,
            entity_index_id: int,
            sub_source_index_id: int,
    ) -> None:
        stmt = (delete(SubscriptionOrm)
                .where(SubscriptionOrm.entity_index_id == entity_index_id)
                .where(SubscriptionOrm.sub_source_index_id == sub_source_index_id))
        await self.db_session.execute(stmt)


__all__ = [
    'AuthSetting',
    'Cooldown',
    'Entity',
    'EntityDAL',
    'EntityType',
    'EntityWithFullRel',
    'Friendship',
    'SignIn',
]
