"""
@Author         : Ailitonia
@Date           : 2022/12/05 22:37
@FileName       : entity.py
@Project        : nonebot2_miya
@Description    : 数据库 Entity 常用方法, 用户/群组/频道等相关操作
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import DatabaseError, NoResultFound

from src.compat import parse_obj_as
from src.database.internal.bot import BotSelf, BotSelfDAL, BotType
from src.database.internal.entity import (
    AuthSetting,
    Cooldown,
    Entity,
    EntityDAL,
    EntityType,
    Friendship,
    SignIn,
    SubscribedSource,
)
from .consts import (
    CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX,
    CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX,
    GLOBAL_COOLDOWN_EVENT,
    SKIP_COOLDOWN_PERMISSION_NODE,
    CharacterAttribute,
    CharacterProfile,
    PermissionGlobal,
    PermissionLevel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.database.internal.subscription_source import SubscriptionSource


type EntityAcquireType = Literal['event', 'user']
"""Entity 对象的类型, event: 事件本身所在场景的对象(群组频道等), user: 触发事件的用户对象"""

type DefaultIntValueFactory = Callable[[], int]
type DefaultDictFactory = Callable[[], dict[str, Any]]


class EntityInitParams(BaseModel):
    """构造 OmegaEntity 的参数"""
    bot_type: BotType
    bot_id: str
    entity_type: EntityType
    entity_id: str
    entity_extra: dict[str, Any]
    entity_name: str | None = Field(default=None)
    entity_info: str | None = Field(default=None)

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)

    @property
    def kwargs(self) -> dict[str, Any]:
        return self.model_dump()


class OmegaEntity:
    """封装后用于统一调用的 Entity 数据库及其相关数据方法的封装"""

    def __init__(
            self,
            session: 'AsyncSession',
            bot_type: str,
            bot_id: str,
            entity_type: str,
            entity_id: str,
            entity_name: str | None = None,
            entity_extra: dict[str, Any] | None = None,
            entity_info: str | None = None
    ) -> None:
        self.bot_type = BotType(bot_type)
        self.bot_id = bot_id
        self.entity_type = EntityType(entity_type)
        self.entity_id = entity_id
        self.entity_name: str = f'{entity_type}_{entity_id}' if entity_name is None else entity_name
        self.entity_extra: dict[str, Any] = entity_extra if entity_extra is not None else {}
        self.entity_info = entity_info

        self._db_session = session
        self._bot: BotSelf | None = None
        self._entity: Entity | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(type={self.entity_type}, entity_id={self.entity_id}, bot_id={self.bot_id})'

    @property
    def tid(self) -> str:
        return f'{self.entity_type}_{self.entity_id}'

    @property
    def init_params(self) -> EntityInitParams:
        return EntityInitParams(
            bot_type=self.bot_type,
            bot_id=self.bot_id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            entity_name=self.entity_name,
            entity_extra=self.entity_extra,
            entity_info=self.entity_info,
        )

    # ------------------------------------------------------------------ #
    # Entity 自身及初始化相关方法
    # ------------------------------------------------------------------ #

    @property
    def not_init(self) -> bool:
        return self._entity is None or self._bot is None

    @classmethod
    async def init_from_entity_index_id(cls, session: 'AsyncSession', index_id: int) -> Self:
        """从 Entity 的索引 ID 初始化, 从数据库中查询(不插入)并填充自身及所属 bot 数据

        只有确认 Entity 存在时才使用, Entity 或所属 bot 不存在时抛出 NoResultFound
        """
        entity = await EntityDAL(session).query_unique(index_id=index_id)
        bot = await BotSelfDAL(session).query_unique(index_id=entity.bot_index_id)
        new_obj = cls(
            session=session,
            bot_type=bot.bot_type,
            bot_id=bot.self_id,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            entity_name=entity.entity_name,
            entity_extra=entity.entity_extra,
            entity_info=entity.entity_info,
        )
        new_obj._bot = bot
        new_obj._entity = entity
        return new_obj

    async def init_self(self) -> None:
        """初始化自身, 从数据库中查询(或插入)并填充自身及所属 bot 数据

        Entity 不存在时插入新行; 所属 bot 不会自动创建, 不存在时抛出 NoResultFound
        """
        bot = await BotSelfDAL(self._db_session).query_unique(
            bot_type=self.bot_type,
            self_id=self.bot_id,
        )
        try:
            entity = await EntityDAL(self._db_session).query_unique(
                bot_type=self.bot_type,
                bot_self_id=self.bot_id,
                entity_type=self.entity_type,
                entity_id=self.entity_id,
            )
        except NoResultFound:
            entity = await EntityDAL(self._db_session).add_ignore_exist(
                bot_type=self.bot_type,
                bot_self_id=self.bot_id,
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                entity_name=self.entity_name,
                entity_extra=self.entity_extra,
                entity_info=self.entity_info,
            )
        self._bot = bot
        self._entity = entity

    async def commit_session(self) -> None:
        """提交所有数据库更改"""
        await self._db_session.commit()

    async def rollback_session(self) -> None:
        """回滚所有数据库更改"""
        await self._db_session.rollback()

    async def query_bot_self(self) -> BotSelf:
        """查询 Entity 对应的 Bot 数据"""
        if self.not_init:
            await self.init_self()
        if self._bot is None:
            raise RuntimeError('Entity initialization failed and bot data was not populated')
        return self._bot

    async def query_entity_self(self) -> Entity:
        """查询 Entity 自身数据"""
        if self.not_init:
            await self.init_self()
        if self._entity is None:
            raise RuntimeError('Entity initialization failed and self data was not populated')
        return self._entity

    async def upsert_self(
            self,
            entity_name: str,
            entity_info: str | None = None,
    ) -> None:
        """新增 Entity, 若已存在则更新"""
        await EntityDAL(self._db_session).add_update_exist(
            bot_type=self.bot_type,
            bot_self_id=self.bot_id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            entity_name=entity_name,
            entity_extra=self.entity_extra,
            entity_info=entity_info,
        )
        await self.init_self()

    async def delete(self) -> None:
        """删除 Entity

        删除后实例缓存的 Entity 数据失效 (`not_init` 转为 True), 后续访问将按需重新初始化 (重建) Entity
        """
        entity = await self.query_entity_self()
        await EntityDAL(session=self._db_session).delete_from_index(index_id=entity.id)
        self._entity = None
        self._bot = None

    # ------------------------------------------------------------------ #
    # Friendship 好感度及状态相关方法
    # ------------------------------------------------------------------ #

    async def set_friendship(
            self,
            status: str | None = None,
            mood: Decimal | None = None,
            friendship: Decimal | None = None,
            energy: Decimal | None = None,
            currency: Decimal | None = None,
            rsp_threshold: Decimal | None = None,
    ) -> Friendship:
        """设置或更新好感度"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).set_entity_friendship(
            entity_index_id=entity.id,
            status=status,
            mood=mood,
            friendship=friendship,
            energy=energy,
            currency=currency,
            rsp_threshold=rsp_threshold,
        )

    async def alter_friendship(
            self,
            *,
            mood: Decimal = Decimal('0'),
            friendship: Decimal = Decimal('0'),
            energy: Decimal = Decimal('0'),
            currency: Decimal = Decimal('0'),
            rsp_threshold: Decimal = Decimal('0'),
    ) -> Friendship:
        """变更好感度, 在现有好感度数值上加/减"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).alter_entity_friendship(
            entity_index_id=entity.id,
            mood=mood,
            friendship=friendship,
            energy=energy,
            currency=currency,
            rsp_threshold=rsp_threshold,
        )

    async def query_friendship(self) -> Friendship:
        """获取好感度, 没有则直接初始化"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).query_entity_friendship(entity_index_id=entity.id)

    # ------------------------------------------------------------------ #
    # SignIn 签到相关方法
    # ------------------------------------------------------------------ #

    async def sign_in(
            self,
            *,
            date_: date | datetime | None = None,
            sign_in_info: str | None = None,
    ) -> SignIn:
        """签到

        若不指定签到日期则为当天, 重复签到 (同一实体同一日期已存在记录) 时显式指定 sign_in_info 则覆盖为指定值
        :param date_: 指定签到日期
        :param sign_in_info: 签到信息
        """
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).set_entity_sign_in(
            entity_index_id=entity.id,
            date_=date_,
            sign_in_info=sign_in_info,
        )

    async def check_today_sign_in(self) -> bool:
        """检查今日是否已经签到"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).check_entity_date_is_sign_in(
            entity_index_id=entity.id,
            date_=datetime.now().date(),
        )

    async def query_sign_in_days(self) -> list[date]:
        """查询所有的签到记录, 返回签到日期列表"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).query_entity_sign_in_days(entity_index_id=entity.id)

    @staticmethod
    async def _parse_continuous_sign_in_day(date_list: list[date]) -> tuple[int, int]:
        """解析截至今日的当前连续签到日数及上一次断签的日期

        仅统计截至今日连续未间断的签到日数, 今日未签到则连续日数为 0;
        晚于今日的签到记录 (未来日期) 不参与计算
        :return: (当前连续签到的日数, 上一次断签日期的 ordinal)
        """
        date_now_ordinal = datetime.now().date().toordinal()

        # 先将签到记录中的日期转化为整数便于比较, 忽略未来日期, 去重后由大到小排序
        all_sign_in_list = sorted(
            {x.toordinal() for x in date_list if x.toordinal() <= date_now_ordinal},
            reverse=True,
        )

        # 还没有签到过, 对应断签日期就是今天
        if not all_sign_in_list:
            return 0, date_now_ordinal

        # 如果今日日期不等于已签到日期最大值, 说明今日没有签到, 则连签日数为0, 断签日为今日
        if date_now_ordinal != all_sign_in_list[0]:
            return 0, date_now_ordinal

        # 从大到小检查(即日期从后向前检查), 如果当日序号大小大于与今日日期之差, 说明在这里断签了
        # 断签的日期应该对应最早签到日期的前一天
        for index, value in enumerate(all_sign_in_list):
            if index != date_now_ordinal - value:
                return index, all_sign_in_list[index - 1] - 1

        # 如果全部遍历完了那就说明全部没有断签, 断签日期为开始签到的前一天
        return len(all_sign_in_list), date_now_ordinal - len(all_sign_in_list)

    async def check_and_execute_sign_in_with_alter_friendship(
            self,
            *,
            date_: date | datetime | None = None,
            sign_in_info: str | None = None,
            alter_friendship: Decimal = Decimal('0'),
            alter_energy: Decimal = Decimal('0'),
            alter_currency: Decimal = Decimal('0'),
    ) -> tuple[SignIn, Friendship]:
        """执行签到和好感度等变化

        同一事务中处理签到表和好感度表更新; 同一对象存在并发签到处理中时立即抛出 RuntimeError 不阻塞等待;
        重复签到判定使用锁定读, 确保好感度奖励不重复发放; 关键区内普通读若与已提交状态不一致同样抛出 RuntimeError;
        SQLite 后端行锁/NOWAIT 为空操作, 由写入序列化兜底正确性;
        指定日期已签到时不再变更好感度 (防止重复发放), 仅按重复签到规则更新签到记录,
        可通过返回的 SignIn.sign_in_info 是否为 'Duplicate Sign In' 区分本次是否为重复签到
        :return: (SignIn: 本次签到信息, Friendship: 签到完成后好感度信息)
        """
        entity = await self.query_entity_self()
        try:
            async with EntityDAL(self._db_session).safe_begin_transaction():
                # 行锁须在重复签到检查之前获取; NOWAIT 快速失败, 由业务层处理并发冲突
                try:
                    await EntityDAL(self._db_session).query_unique(
                        bot_type=self.bot_type,
                        bot_self_id=self.bot_id,
                        entity_type=self.entity_type,
                        entity_id=self.entity_id,
                        populate_existing=True,
                        with_for_update=True,
                        nowait_for_update=True,
                    )
                except DatabaseError as e:
                    if EntityDAL.is_lock_nowait_error(e):
                        raise RuntimeError(
                            f'Entity {self.tid} 正在并发签到处理中, 请稍后重试'
                        ) from e
                    raise

                # 仅取一次当前日期, 避免 check 与 insert 分别取 now 在跨午夜时不一致
                # (sign_in_info 原样透传, DAL 按日期值区分 Normal/Fixed Sign In 默认信息)
                if date_ is None:
                    sign_in_date = datetime.now().date()
                elif isinstance(date_, datetime):
                    sign_in_date = date_.date()
                else:
                    sign_in_date = date_

                # 锁定读判定: 当前读不受事务一致性快照影响, 覆盖快照确立后锁获取前的并发提交窗口
                already_signed = await EntityDAL(self._db_session).check_entity_date_is_sign_in(
                    entity_index_id=entity.id,
                    date_=sign_in_date,
                    with_for_update=True,
                )
                sign_in_result = await self.sign_in(
                    date_=sign_in_date,
                    sign_in_info=sign_in_info,
                )
                if already_signed:
                    friendship_result = await self.query_friendship()
                else:
                    friendship_result = await self.alter_friendship(
                        friendship=alter_friendship,
                        energy=alter_energy,
                        currency=alter_currency,
                    )
        except NoResultFound as e:
            # 持锁后普通读仍读不到已提交数据, 说明本事务一致性快照已过期 (REPEATABLE READ),
            # 继续执行将基于错误数据, 抛出由业务层处理
            raise RuntimeError(
                f'Entity {self.tid} 数据被并发修改, 事务读视图不一致, 请重试'
            ) from e
        return sign_in_result, friendship_result

    # ------------------------------------------------------------------ #
    # AuthSetting 通用授权及配置相关方法
    # ------------------------------------------------------------------ #

    async def query_all_auth_setting(self) -> list[AuthSetting]:
        """查询 Entity 全部的权限配置"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).query_entity_any_auth_settings(
            entity_index_id=entity.id,
        )

    async def query_plugin_all_auth_setting(self, module: str, plugin: str) -> list[AuthSetting]:
        """查询 Entity 具有某个插件的全部的权限配置"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).query_entity_any_auth_settings(
            entity_index_id=entity.id,
            module=module,
            plugin=plugin,
        )

    async def query_auth_setting(self, module: str, plugin: str, node: str) -> AuthSetting:
        """查询 Entity 具体某个权限配置"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).query_entity_auth_setting(
            entity_index_id=entity.id,
            module=module,
            plugin=plugin,
            node=node,
        )

    async def verify_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            *,
            available: int = 1,
            strict_match_available: bool = True,
    ) -> Literal[-1, 0, 1]:
        """检查 Entity 对应权限节点是否启用/符合需求值, 这个方法会返回状态码表示权限验证的结果

        :param module: 权限节点对应模块
        :param plugin: 权限节点对应插件
        :param node: 权限节点
        :param available: 启用/需求值
        :param strict_match_available: True: 查询 available 必须等于传入参数的结果,
            False: 查询 available 需大于等于传入参数的结果
        :return: 结果状态码
            -1: 已查找到条目, 该权限节点不符合需求/被拒绝
            0: 条目不存在, Entity 没有配置该权限节点
            1: 已查找到条目, 该权限节点符合需求/验证通过
        """
        try:
            auth_setting = await self.query_auth_setting(module=module, plugin=plugin, node=node)
            if strict_match_available and auth_setting.available == available:
                return 1
            elif not strict_match_available and auth_setting.available >= available:
                return 1
            else:
                return -1
        except NoResultFound:
            return 0

    async def set_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            available: int,
            value: dict[str, Any],
    ) -> AuthSetting:
        """设置 Entity 权限节点参数值"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).set_entity_auth_setting(
            entity_index_id=entity.id,
            module=module,
            plugin=plugin,
            node=node,
            available=available,
            value=value,
        )

    async def delete_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
    ) -> None:
        """删除 Entity 权限节点"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).delete_entity_auth_setting(
            entity_index_id=entity.id,
            module=module,
            plugin=plugin,
            node=node,
        )

    # ------------------------------------------------------------------ #
    # AuthSetting 内置权限分支相关方法
    # ------------------------------------------------------------------ #

    async def query_global_permission(self) -> AuthSetting:
        """查询 Entity 全局功能开关"""
        return await self.query_auth_setting(
            module=PermissionGlobal.module,
            plugin=PermissionGlobal.plugin,
            node=PermissionGlobal.node,
        )

    async def check_global_permission(self) -> bool:
        """检查 Entity 是否打开全局功能开关"""
        verified = await self.verify_auth_setting(
            module=PermissionGlobal.module,
            plugin=PermissionGlobal.plugin,
            node=PermissionGlobal.node,
            available=1,
            strict_match_available=True,
        )
        return verified == 1

    async def enable_global_permission(self) -> AuthSetting:
        """打开 Entity 全局功能开关"""
        return await self.set_auth_setting(
            module=PermissionGlobal.module,
            plugin=PermissionGlobal.plugin,
            node=PermissionGlobal.node,
            available=1,
            value={},
        )

    async def disable_global_permission(self) -> AuthSetting:
        """关闭 Entity 全局功能开关"""
        return await self.set_auth_setting(
            module=PermissionGlobal.module,
            plugin=PermissionGlobal.plugin,
            node=PermissionGlobal.node,
            available=0,
            value={},
        )

    async def query_permission_level(self) -> AuthSetting:
        """查询 Entity 权限等级"""
        return await self.query_auth_setting(
            module=PermissionLevel.module,
            plugin=PermissionLevel.plugin,
            node=PermissionLevel.node
        )

    async def check_permission_level(self, level: int) -> bool:
        """检查 Entity 权限等级是否达到要求"""
        verified = await self.verify_auth_setting(
            module=PermissionLevel.module,
            plugin=PermissionLevel.plugin,
            node=PermissionLevel.node,
            available=level,
            strict_match_available=False,
        )
        return verified == 1

    async def set_permission_level(self, level: int) -> AuthSetting:
        """设置 Entity 权限等级"""
        return await self.set_auth_setting(
            module=PermissionLevel.module,
            plugin=PermissionLevel.plugin,
            node=PermissionLevel.node,
            available=level,
            value={},
        )

    async def check_permission_skip_cooldown(self, module: str, plugin: str) -> bool:
        """检查 Entity 是否有插件跳过冷却的权限"""
        verified = await self.verify_auth_setting(
            module=module,
            plugin=plugin,
            node=SKIP_COOLDOWN_PERMISSION_NODE,
            available=1,
            strict_match_available=True,
        )
        return verified == 1

    async def enable_plugin_skip_cooldown_permission(self, module: str, plugin: str) -> AuthSetting:
        """启用 Entity 某插件跳过冷却权限"""
        return await self.set_auth_setting(
            module=module,
            plugin=plugin,
            node=SKIP_COOLDOWN_PERMISSION_NODE,
            available=1,
            value={},
        )

    async def disable_plugin_skip_cooldown_permission(self, module: str, plugin: str) -> AuthSetting:
        """关闭 Entity 某插件跳过冷却权限"""
        return await self.set_auth_setting(
            module=module,
            plugin=plugin,
            node=SKIP_COOLDOWN_PERMISSION_NODE,
            available=0,
            value={},
        )

    # ------------------------------------------------------------------ #
    # Cooldown 冷却事件相关方法
    # ------------------------------------------------------------------ #

    async def query_cooldown(self, cooldown_event: str) -> Cooldown:
        """查询冷却"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).query_entity_cooldown(
            entity_index_id=entity.id,
            event=cooldown_event,
        )

    async def set_cooldown(
            self,
            cooldown_event: str,
            expired_time: datetime | timedelta,
            description: str | None = None
    ) -> Cooldown:
        """设置冷却

        :param cooldown_event: 设置的冷却事件
        :param expired_time: datetime: 冷却过期时间; timedelta: 以现在时间为准新增的冷却时间
        :param description: 冷却描述信息
        """
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).set_entity_cooldown(
            entity_index_id=entity.id,
            event=cooldown_event,
            expired_time=expired_time,
            description=description,
        )

    async def check_cooldown_expired(self, cooldown_event: str) -> tuple[bool, datetime]:
        """查询冷却是否到期

        :return: (True=已到期或不存在该冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
        """
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).check_entity_cooldown_is_expired(
            entity_index_id=entity.id,
            event=cooldown_event,
        )

    async def set_global_cooldown(self, expired_time: datetime | timedelta) -> Cooldown:
        """设置全局冷却

        :param expired_time: datetime: 冷却过期时间; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cooldown(
            cooldown_event=GLOBAL_COOLDOWN_EVENT,
            expired_time=expired_time,
            description='OmegaGlobalCooldown 全局冷却',
        )

    async def check_global_cooldown_expired(self) -> tuple[bool, datetime]:
        """查询全局冷却是否到期

        :return: (True=已到期或不存在该冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
        """
        return await self.check_cooldown_expired(cooldown_event=GLOBAL_COOLDOWN_EVENT)

    # ------------------------------------------------------------------ #
    # OmegaInternalCharacter 内置角色档案相关方法
    # ------------------------------------------------------------------ #

    async def set_character_attribute(self, attr_name: str, attr_value: int) -> AuthSetting:
        """设置 Entity 对象的角色属性, 属性应当为 int 类型"""
        value = parse_obj_as(dict[str, int], {attr_name: attr_value})
        return await self.set_auth_setting(
            module=CharacterAttribute.module,
            plugin=CharacterAttribute.plugin,
            node=attr_name,
            available=1,
            value=value,
        )

    async def set_character_profile(self, profile_name: str, profile_value: dict[str, Any]) -> AuthSetting:
        """设置 Entity 对象的角色档案, 档案内容应当为 dict 类型"""
        value = parse_obj_as(dict[str, dict[str, Any]], {profile_name: profile_value})
        return await self.set_auth_setting(
            module=CharacterProfile.module,
            plugin=CharacterProfile.plugin,
            node=profile_name,
            available=1,
            value=value,
        )

    async def delete_character_attribute(self, attribute_name: str) -> None:
        """删除 Entity 对象的角色属性"""
        return await self.delete_auth_setting(
            module=CharacterAttribute.module,
            plugin=CharacterAttribute.plugin,
            node=attribute_name,
        )

    async def delete_character_profile(self, profile_name: str) -> None:
        """删除 Entity 对象的角色档案"""
        return await self.delete_auth_setting(
            module=CharacterProfile.module,
            plugin=CharacterProfile.plugin,
            node=profile_name,
        )

    async def query_all_character_attribute(self) -> list[AuthSetting]:
        """获取 Entity 对象所有的角色属性"""
        return await self.query_plugin_all_auth_setting(
            module=CharacterAttribute.module,
            plugin=CharacterAttribute.plugin,
        )

    async def query_all_character_profile(self) -> list[AuthSetting]:
        """获取 Entity 对象所有的角色档案"""
        return await self.query_plugin_all_auth_setting(
            module=CharacterProfile.module,
            plugin=CharacterProfile.plugin,
        )

    async def query_character_attribute(
            self,
            attr_name: str,
            *,
            default_factory: DefaultIntValueFactory | None = None,
    ) -> int:
        """查询 Entity 对象的角色属性, 提供 `default_factory` 时若无角色属性则动态生成

        以下情形视为属性不可用: 属性未配置 (NoResultFound)、属性被禁用 (available != 1)、
        属性值缺失 (KeyError) 或属性值无法转换为 int (TypeError/ValueError);
        提供 `default_factory` 时重新生成并落库 (重置 available 为 1), 否则抛出对应异常
        """
        try:
            attribute = await self.query_auth_setting(
                module=CharacterAttribute.module,
                plugin=CharacterAttribute.plugin,
                node=attr_name,
            )

            if attribute.available != 1:
                raise ValueError(f'CharacterAttribute {attr_name!r} is not available (available != 1)')

            attribute_value = int(attribute.value[attr_name])
        except (NoResultFound, ValueError, KeyError, TypeError):
            if default_factory is None:
                raise

            attribute_value = default_factory()
            await self.set_character_attribute(attr_name=attr_name, attr_value=attribute_value)

        return attribute_value

    async def query_character_profile(
            self,
            profile_name: str,
            *,
            default_factory: DefaultDictFactory | None = None,
    ) -> dict[str, Any]:
        """查询 Entity 对象的角色档案, 提供 `default_factory` 时若无角色档案则动态生成

        以下情形视为档案不可用: 档案未配置 (NoResultFound)、档案被禁用 (available != 1)、
        档案值缺失 (KeyError) 或档案值不可索引 (TypeError);
        提供 `default_factory` 时重新生成并落库 (重置 available 为 1), 否则抛出对应异常
        """
        try:
            profile = await self.query_auth_setting(
                module=CharacterProfile.module,
                plugin=CharacterProfile.plugin,
                node=profile_name,
            )

            if profile.available != 1:
                raise ValueError(f'CharacterProfile {profile_name!r} is not available (available != 1)')

            profile_value = profile.value[profile_name]
        except (NoResultFound, ValueError, KeyError, TypeError):
            if default_factory is None:
                raise

            profile_value = default_factory()
            await self.set_character_profile(profile_name=profile_name, profile_value=profile_value)

        return profile_value

    async def set_character_attribute_setter_cooldown(
            self,
            attr_name: str,
            expired_time: datetime | timedelta,
    ) -> Cooldown:
        """设置更新 Entity 对象角色属性时的冷却

        :param attr_name: 角色属性名称
        :param expired_time: datetime: 冷却过期时间; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cooldown(
            cooldown_event=f'{CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX}_{attr_name}',
            expired_time=expired_time,
            description=f'角色{attr_name!r}属性更新冷却',
        )

    async def set_character_profile_setter_cooldown(
            self,
            profile_name: str,
            expired_time: datetime | timedelta,
    ) -> Cooldown:
        """设置更新 Entity 对象角色档案时的冷却

        :param profile_name: 角色档案名称
        :param expired_time: datetime: 冷却过期时间; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cooldown(
            cooldown_event=f'{CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX}_{profile_name}',
            expired_time=expired_time,
            description=f'角色{profile_name!r}档案更新冷却',
        )

    async def check_character_attribute_setter_cooldown_expired(self, attr_name: str) -> tuple[bool, datetime]:
        """查询更新 Entity 对象角色属性时的冷却是否到期

        :param attr_name: 角色属性名称
        :return: (True=已到期或不存在该冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
        """
        return await self.check_cooldown_expired(
            cooldown_event=f'{CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX}_{attr_name}'
        )

    async def check_character_profile_setter_cooldown_expired(self, profile_name: str) -> tuple[bool, datetime]:
        """查询更新 Entity 对象角色档案时的冷却是否到期

        :param profile_name: 角色档案名称
        :return: (True=已到期或不存在该冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
        """
        return await self.check_cooldown_expired(
            cooldown_event=f'{CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX}_{profile_name}'
        )

    # ------------------------------------------------------------------ #
    # Subscription 订阅相关方法
    # ------------------------------------------------------------------ #

    async def add_subscription(
            self,
            subscription_source: 'SubscriptionSource',
            sub_info: str | None = None,
    ) -> SubscribedSource:
        """添加订阅"""
        entity = await self.query_entity_self()
        result = await EntityDAL(session=self._db_session).set_entity_subscription(
            entity_index_id=entity.id,
            sub_source_index_id=subscription_source.id,
            sub_info=sub_info,
        )
        return result.subscription_parent_source

    async def delete_subscription(self, subscription_source: 'SubscriptionSource') -> None:
        """删除订阅"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).delete_entity_subscription(
            entity_index_id=entity.id,
            sub_source_index_id=subscription_source.id,
        )

    async def query_subscribed_source(self, sub_type: str | None = None) -> list[SubscribedSource]:
        """查询全部已订阅的订阅源

        Entity 不存在时返回空列表 (与其他查询方法不同, 本方法不会自动初始化 Entity)
        :param sub_type: 可选: 根据 sub_type 筛选, 若无则为全部类型
        """
        try:
            entity = await EntityDAL(self._db_session).query_unique(
                bot_type=self.bot_type,
                bot_self_id=self.bot_id,
                entity_type=self.entity_type,
                entity_id=self.entity_id,
            )
        except NoResultFound:
            return []
        return await EntityDAL(self._db_session).query_entity_subscribed_source(
            entity_index_id=entity.id,
            sub_type=sub_type,
        )


__all__ = [
    'EntityAcquireType',
    'EntityInitParams',
    'OmegaEntity',
]
