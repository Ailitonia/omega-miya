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

from sqlalchemy.exc import NoResultFound

from src.compat import parse_obj_as
from src.database.internal.bot import BotSelf, BotSelfDAL
from src.database.internal.entity import AuthSetting, Cooldown, Entity, EntityDAL, EntityType, Friendship, SignIn
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

type DefaultIntValueFactory = Callable[[], int]
type DefaultDictFactory = Callable[[], dict[str, Any]]


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
            entity_info: str | None = None
    ) -> None:
        self.bot_type = bot_type
        self.bot_id = bot_id
        self.entity_type = EntityType(entity_type)
        self.entity_id = entity_id
        self.entity_name = f'{entity_type}_{entity_id}' if entity_name is None else entity_name
        self.entity_info = entity_info

        self._db_session = session
        self._bot: BotSelf | None = None
        self._entity: Entity | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(type={self.entity_type}, entity_id={self.entity_id}, bot_id={self.bot_id})'

    @property
    def tid(self) -> str:
        return f'{self.entity_type}_{self.entity_id}'

    # ------------------------------------------------------------------ #
    # Entity 自身及初始化相关方法
    # ------------------------------------------------------------------ #

    @property
    def not_init(self) -> bool:
        return self._entity is None or self._bot is None

    @classmethod
    async def init_from_entity_index_id(cls, session: 'AsyncSession', index_id: int) -> Self:
        """从 Entity 的索引 ID 初始化, 从数据库中查询(或插入)并填充自身及所属 bot 数据, 只有确认 Entity 存在时才使用"""
        entity = await EntityDAL(session).query_unique(index_id=index_id)
        bot = await BotSelfDAL(session).query_unique(index_id=entity.bot_index_id)
        new_obj = cls(
            session=session,
            bot_type=bot.bot_type,
            bot_id=bot.self_id,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            entity_name=entity.entity_name,
            entity_info=entity.entity_info,
        )
        new_obj._bot = bot
        new_obj._entity = entity
        return new_obj

    async def init_self(self) -> None:
        """初始化自身, 从数据库中查询(或插入)并填充自身及所属 bot 数据"""
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
            entity_info=entity_info,
        )
        await self.init_self()

    async def delete(self) -> None:
        """删除 Entity"""
        entity = await self.query_entity_self()
        await EntityDAL(session=self._db_session).delete_from_index(index_id=entity.id)

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
        """解析到现在为止最长连续签到日数及上一次断签的日期

        :return: (最长连续签到的日数, 上一次断签日期的 ordinal datetime)
        """
        date_now_ordinal = datetime.now().date().toordinal()

        # 还没有签到过, 对应断签日期就是今天
        if not date_list:
            return 0, date_now_ordinal

        # 有签到记录则处理签到记录
        # 先将签到记录中的日期转化为整数便于比较, 去重后由大到小排序
        all_sign_in_list = sorted({x.toordinal() for x in date_list}, reverse=True)

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

        同一事务中处理签到表和好感度表更新, 确保并发与原子性
        :return: (SignIn: 本次签到信息, Friendship: 签到完成后好感度信息)
        """
        async with EntityDAL(self._db_session).safe_begin_transaction():
            sign_in_result = await self.sign_in(
                date_=date_,
                sign_in_info=sign_in_info,
            )
            friendship_result = await self.alter_friendship(
                friendship=alter_friendship,
                energy=alter_energy,
                currency=alter_currency,
            )
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
        """检查 Entity 对应权限节点是否启用/符合需求值, 与 check_auth_setting 方法不同, 这个方法会返回状态码表示权限验证的结果

        :param module: 权限节点对应模块
        :param plugin: 权限节点对应插件
        :param node: 权限节点
        :param available: 启用/需求值
        :param strict_match_available: True: 查询 available 必须等于传入参数的结果, False: 查询 available 需大于等于传入参数的结果
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
        return True if verified == 1 else False

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
        return True if verified == 1 else False

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
        return True if verified == 1 else False

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
        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
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

        :return: (True=已到期或不存在改冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
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

        :return: (True=已到期或不存在改冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
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
        """设置 Entity 对象的角色档案, 档案内容应当为 str 类型"""
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
        """查询 Entity 对象的角色属性, 提供 `default_factory` 时若无角色属性则动态生成"""
        try:
            attribute = await self.query_auth_setting(
                module=CharacterAttribute.module,
                plugin=CharacterAttribute.plugin,
                node=attr_name,
            )

            if attribute.available != 1:
                raise ValueError('CharacterAttribute is not available')

            attribute_value = int(attribute.value[attr_name])
        except (NoResultFound, ValueError, KeyError):
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
        """查询 Entity 对象的角色档案, 提供 `default_factory` 时若无角色档案则动态生成"""
        try:
            profile = await self.query_auth_setting(
                module=CharacterProfile.module,
                plugin=CharacterProfile.plugin,
                node=profile_name,
            )

            if profile.available != 1:
                raise ValueError('CharacterProfile is not available')

            if profile.value is None:
                raise ValueError('CharacterProfile can not be None')

            profile_value = profile.value[profile_name]
        except (NoResultFound, ValueError) as e:
            if default_factory is None:
                raise e

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
        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
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
        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cooldown(
            cooldown_event=f'{CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX}_{profile_name}',
            expired_time=expired_time,
            description=f'角色{profile_name!r}档案更新冷却',
        )

    async def check_character_attribute_setter_cooldown_expired(self, attr_name: str) -> tuple[bool, datetime]:
        """查询更新 Entity 对象角色属性时的冷却是否到期

        :param attr_name: 角色属性名称
        :return: (True=已到期或不存在改冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
        """
        return await self.check_cooldown_expired(
            cooldown_event=f'{CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX}_{attr_name}'
        )

    async def check_character_profile_setter_cooldown_expired(self, profile_name: str) -> tuple[bool, datetime]:
        """查询更新 Entity 对象角色档案时的冷却是否到期

        :param profile_name: 角色档案名称
        :return: (True=已到期或不存在改冷却事件, 到期时间), (False=未到期且仍在冷却中, 到期时间)
        """
        return await self.check_cooldown_expired(
            cooldown_event=f'{CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX}_{profile_name}'
        )

    # ------------------------------------------------------------------ #
    # Subscription 订阅相关方法
    # ------------------------------------------------------------------ #

    async def add_subscription(self, subscription_source: 'SubscriptionSource', sub_info: str | None = None):
        """添加订阅"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).set_entity_subscription(
            entity_index_id=entity.id,
            sub_source_index_id=subscription_source.id,
            sub_info=sub_info,
        )

    async def delete_subscription(self, subscription_source: 'SubscriptionSource') -> None:
        """删除订阅"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self._db_session).delete_entity_subscription(
            entity_index_id=entity.id,
            sub_source_index_id=subscription_source.id,
        )

    async def query_subscribed_source(self, sub_type: str | None = None):
        """查询全部已订阅的订阅源

        :param sub_type: 可选: 根据 sub_type 筛选, 若无则为全部类型
        """
        try:
            entity = await EntityDAL(self._db_session).query_unique(
                bot_type=self.bot_type,
                bot_self_id=self.bot_id,
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                load_all_rel=True,
            )
            if sub_type is not None:
                return [x for x in entity.subscription_sources_entity_had if x.sub_type == sub_type]
            return entity.subscription_sources_entity_had
        except NoResultFound:
            return []


__all__ = [
    'OmegaEntity',
]
