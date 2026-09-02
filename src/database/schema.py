"""
@Author         : Ailitonia
@Date           : 2022/12/01 22:04
@FileName       : table_meta.py
@Project        : nonebot2_miya
@Description    : database table schema
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Identity, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import BigInteger, Date, DateTime, Integer, Numeric, SmallInteger, String

from .config import database_config
from .schema_base import OmegaDeclarativeBase as Base
from .types import CommonJSON, CommonLongText, IndexInt


class GlobalCacheOrm(Base):
    """全局缓存表, 存放各种需要持久化的缓存数据"""
    __tablename__ = f'{database_config.db_prefix}global_cache'
    __table_args__ = (
        database_config.table_args,
    )

    cache_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    cache_value: Mapped[str] = mapped_column(CommonLongText, nullable=False)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    def __repr__(self) -> str:
        return (f'GlobalCacheOrm(cache_name={self.cache_name}, '
                f'cache_key={self.cache_key}, expired_at={self.expired_at}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class SystemSettingOrm(Base):
    """系统参数表, 存放运行时配置"""
    __tablename__ = f'{database_config.db_prefix}system_setting'
    __table_args__ = (
        database_config.table_args,
    )

    setting_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    setting_value: Mapped[str] = mapped_column(CommonLongText, nullable=False)
    info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    def __repr__(self) -> str:
        return (f'SystemSettingOrm(setting_name={self.setting_name}, setting_key={self.setting_key}, '
                f'setting_value={self.setting_value}, info={self.info or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class PluginOrm(Base):
    """插件表, 存放插件信息"""
    __tablename__ = f'{database_config.db_prefix}plugin'
    __table_args__ = (
        database_config.table_args,
    )

    plugin_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    module_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    enabled: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    def __repr__(self) -> str:
        return (f'PluginOrm(plugin_name={self.plugin_name}, module_name={self.module_name}, '
                f'enabled={self.enabled}, info={self.info or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class StatisticOrm(Base):
    """统计信息表"""
    __tablename__ = f'{database_config.db_prefix}statistic'
    __table_args__ = (
        Index(None, 'call_timestamp', 'plugin_name', 'module_name'),
        Index(None, 'plugin_name', 'module_name', 'call_timestamp'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    plugin_name: Mapped[str] = mapped_column(String(255), nullable=False)
    module_name: Mapped[str] = mapped_column(String(255), nullable=False)
    call_timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    call_entity_meta: Mapped[dict[str, Any]] = mapped_column(CommonJSON, nullable=False, default=dict)
    call_data: Mapped[dict[str, Any]] = mapped_column(CommonJSON, nullable=False, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    def __repr__(self) -> str:
        return (f'StatisticsOrm(plugin_name={self.plugin_name}, module_name={self.module_name}, '
                f'call_timestamp={self.call_timestamp}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class HistoryOrm(Base):
    """消息历史记录表"""
    __tablename__ = f'{database_config.db_prefix}history'
    __table_args__ = (
        UniqueConstraint('bot_self_id', 'message_id'),
        UniqueConstraint('message_id', 'bot_self_id', 'event_entity_id', 'user_entity_id'),
        Index(None, 'bot_self_id', 'event_entity_id', 'user_entity_id', 'message_type', 'received_timestamp'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    received_timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    bot_self_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    message_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message_plain_text: Mapped[str] = mapped_column(CommonLongText, nullable=False)
    message_raw: Mapped[dict[str, Any]] = mapped_column(CommonJSON, nullable=False, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    def __repr__(self) -> str:
        return (f'HistoryOrm(received_timestamp={self.received_timestamp}, message_id={self.message_id}, '
                f'bot_self_id={self.bot_self_id}, event_entity_id={self.event_entity_id}, '
                f'user_entity_id={self.user_entity_id}, message_type={self.message_type}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class BotSelfOrm(Base):
    """Bot表, 对应不同机器人协议端"""
    __tablename__ = f'{database_config.db_prefix}bot'
    __table_args__ = (
        UniqueConstraint('bot_type', 'self_id'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    bot_type: Mapped[str] = mapped_column(String(64), nullable=False)
    self_id: Mapped[str] = mapped_column(String(64), nullable=False)
    bot_status: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    bot_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    entities_belonged_to_bot: Mapped[list['EntityOrm']] = relationship(
        'EntityOrm',
        back_populates='entity_parent_bot',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )

    def __repr__(self) -> str:
        return (f'BotSelfOrm(bot_type={self.bot_type}, self_id={self.self_id}, '
                f'bot_status={self.bot_status}, bot_info={self.bot_info or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class EntityOrm(Base):
    """实体表, 存放用户/群组/频道等所有需要交互的对象, 所有属性/好感度/权限/订阅等操作实例对象均以此为基准"""
    __tablename__ = f'{database_config.db_prefix}entity'
    __table_args__ = (
        UniqueConstraint('bot_index_id', 'entity_type', 'entity_id'),
        Index(None, 'entity_type', 'entity_id'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    bot_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(BotSelfOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, comment='实体类型')
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, comment='实体平台ID')
    entity_name: Mapped[str] = mapped_column(String(64), nullable=False, comment='实体名称')
    entity_info: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='实体描述信息')
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    entity_parent_bot: Mapped[BotSelfOrm] = relationship(
        BotSelfOrm,
        back_populates='entities_belonged_to_bot',
        lazy='joined',
        innerjoin=True,
    )
    friendship_belonged_to_entity: Mapped[list['FriendshipOrm']] = relationship(
        'FriendshipOrm',
        back_populates='friendship_parent_entity',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    sign_in_belonged_to_entity: Mapped[list['SignInOrm']] = relationship(
        'SignInOrm',
        back_populates='sign_in_parent_entity',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    auth_belonged_to_entity: Mapped[list['AuthSettingOrm']] = relationship(
        'AuthSettingOrm',
        back_populates='auth_parent_entity',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    cooldown_belonged_to_entity: Mapped[list['CooldownOrm']] = relationship(
        'CooldownOrm',
        back_populates='cooldown_parent_entity',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    subscription_belonged_to_entity: Mapped[list['SubscriptionOrm']] = relationship(
        'SubscriptionOrm',
        back_populates='subscription_parent_entity',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    subscription_sources_entity_had: Mapped[list['SubscriptionSourceOrm']] = relationship(
        'SubscriptionSourceOrm',
        secondary=f'{database_config.db_prefix}subscription',
        back_populates='entities_subscription_source_had',
        lazy='raise',
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (f'EntityOrm(bot_index_id={self.bot_index_id}, entity_type={self.entity_type}, '
                f'entity_id={self.entity_id}, entity_name={self.entity_name}, '
                f'entity_info={self.entity_info or "null"} '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class FriendshipOrm(Base):
    """好感度及状态表, 养成系统基础表单"""
    __tablename__ = f'{database_config.db_prefix}friendship'
    __table_args__ = (
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    entity_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(EntityOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default='normal', comment='当前状态')
    mood: Mapped[Decimal] = mapped_column(Numeric(6, 2, asdecimal=True), nullable=False, comment='情绪值')
    friendship: Mapped[Decimal] = mapped_column(Numeric(18, 4, asdecimal=True), nullable=False, comment='好感度')
    energy: Mapped[Decimal] = mapped_column(Numeric(18, 4, asdecimal=True), nullable=False, comment='能量值')
    currency: Mapped[Decimal] = mapped_column(Numeric(18, 4, asdecimal=True), nullable=False, comment='持有货币')
    rsp_threshold: Mapped[Decimal] = mapped_column(Numeric(6, 2, asdecimal=True), nullable=False, comment='响应阈值')
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    friendship_parent_entity: Mapped[EntityOrm] = relationship(
        EntityOrm,
        back_populates='friendship_belonged_to_entity',
        lazy='joined',
        innerjoin=True,
    )

    def __repr__(self) -> str:
        return (f'FriendshipOrm(entity_index_id={self.entity_index_id}, status={self.status}, '
                f'mood={self.mood}, friendship={self.friendship}, energy={self.energy}, '
                f'currency={self.currency}, rsp_threshold={self.rsp_threshold}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class SignInOrm(Base):
    """签到表, 养成系统基础表单"""
    __tablename__ = f'{database_config.db_prefix}sign_in'
    __table_args__ = (
        UniqueConstraint('entity_index_id', 'sign_in_date'),
        Index(None, 'sign_in_date', 'entity_index_id'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    entity_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(EntityOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
    )
    sign_in_date: Mapped[date] = mapped_column(Date, nullable=False, comment='签到日期')
    sign_in_info: Mapped[str | None] = mapped_column(String(64), nullable=True, comment='签到信息')
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    sign_in_parent_entity: Mapped[EntityOrm] = relationship(
        EntityOrm,
        back_populates='sign_in_belonged_to_entity',
        lazy='joined',
        innerjoin=True,
    )

    def __repr__(self) -> str:
        return (f'SignInOrm(entity_index_id={self.entity_index_id}, sign_in_date={self.sign_in_date}, '
                f'sign_in_info={self.sign_in_info or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class AuthSettingOrm(Base):
    """授权配置表, 主要用于权限管理, 同时兼用于存放使用插件时需要持久化的配置"""
    __tablename__ = f'{database_config.db_prefix}auth_setting'
    __table_args__ = (
        UniqueConstraint('entity_index_id', 'module', 'plugin', 'node'),
        Index(None, 'module', 'plugin', 'node', 'available'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    entity_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(EntityOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
    )
    module: Mapped[str] = mapped_column(String(255), nullable=False, comment='配置模块名称')
    plugin: Mapped[str] = mapped_column(String(255), nullable=False, comment='配置插件名称')
    node: Mapped[str] = mapped_column(String(64), nullable=False, comment='权限节点/配置名')
    available: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    value: Mapped[dict[str, Any]] = mapped_column(CommonJSON, nullable=False, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    auth_parent_entity: Mapped[EntityOrm] = relationship(
        EntityOrm,
        back_populates='auth_belonged_to_entity',
        lazy='joined',
        innerjoin=True,
    )

    def __repr__(self) -> str:
        return (f'AuthSettingOrm(entity_index_id={self.entity_index_id}, module={self.module}, '
                f'plugin={self.plugin}, node={self.node}, available={self.available}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class CooldownOrm(Base):
    """冷却事件表"""
    __tablename__ = f'{database_config.db_prefix}cooldown'
    __table_args__ = (
        UniqueConstraint('entity_index_id', 'event'),
        Index(None, 'event', 'stop_at'),
        Index(None, 'stop_at', 'event'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    entity_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(EntityOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
    )
    event: Mapped[str] = mapped_column(String(64), nullable=False, comment='冷却事件, 用于唯一标识某个/类冷却')
    stop_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment='冷却结束时间')
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='事件描述')
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    cooldown_parent_entity: Mapped[EntityOrm] = relationship(
        EntityOrm,
        back_populates='cooldown_belonged_to_entity',
        lazy='joined',
        innerjoin=True,
    )

    def __repr__(self) -> str:
        return (f'CooldownOrm(entity_index_id={self.entity_index_id}, event={self.event}, '
                f'stop_at={self.stop_at}, description={self.description or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class SubscriptionSourceOrm(Base):
    """订阅源表"""
    __tablename__ = f'{database_config.db_prefix}subscription_source'
    __table_args__ = (
        UniqueConstraint('sub_type', 'sub_id'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    sub_type: Mapped[str] = mapped_column(String(64), nullable=False, comment='订阅类型')
    sub_id: Mapped[str] = mapped_column(String(64), nullable=False, comment='订阅id，直播间房间号/用户uid等')
    sub_user_name: Mapped[str] = mapped_column(String(64), nullable=False, comment='订阅用户的名称')
    sub_info: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='订阅源信息')
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    subscription_belonged_to_source: Mapped[list['SubscriptionOrm']] = relationship(
        'SubscriptionOrm',
        back_populates='subscription_parent_source',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    entities_subscription_source_had: Mapped[list[EntityOrm]] = relationship(
        EntityOrm,
        secondary=f'{database_config.db_prefix}subscription',
        back_populates='subscription_sources_entity_had',
        lazy='raise',
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (f'SubscriptionSourceOrm(sub_type={self.sub_type}, sub_id={self.sub_id}, '
                f'sub_user_name={self.sub_user_name}, sub_info={self.sub_info or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class SubscriptionOrm(Base):
    """订阅表"""
    __tablename__ = f'{database_config.db_prefix}subscription'
    __table_args__ = (
        Index(None, 'entity_index_id', 'sub_source_index_id'),
        database_config.table_args,
    )

    sub_source_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(SubscriptionSourceOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    entity_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(EntityOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    sub_info: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='订阅信息')
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    subscription_parent_source: Mapped[SubscriptionSourceOrm] = relationship(
        SubscriptionSourceOrm,
        back_populates='subscription_belonged_to_source',
        lazy='joined',
        innerjoin=True,
    )
    subscription_parent_entity: Mapped[EntityOrm] = relationship(
        EntityOrm,
        back_populates='subscription_belonged_to_entity',
        lazy='joined',
        innerjoin=True,
    )

    def __repr__(self) -> str:
        return (f'SubscriptionOrm(sub_source_index_id={self.sub_source_index_id}, '
                f'entity_index_id={self.entity_index_id}, sub_info={self.sub_info or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class SocialMediaContentOrm(Base):
    """社交媒体平台内容表"""
    __tablename__ = f'{database_config.db_prefix}social_media_content'
    __table_args__ = (
        UniqueConstraint('source', 'm_type', 'm_id'),
        Index('ix_social_media_content_uid_search', 'source', 'm_type', 'm_uid'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, comment='出处平台')
    m_type: Mapped[str] = mapped_column(String(64), nullable=False, comment='内容原始类型')
    m_id: Mapped[str] = mapped_column(String(64), nullable=False, comment='内容原始ID')
    m_uid: Mapped[str] = mapped_column(String(64), nullable=False, comment='内容发布者ID')
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment='内容标题')
    raw_data: Mapped[dict[str, Any]] = mapped_column(CommonJSON, nullable=False, default=dict)
    content: Mapped[str | None] = mapped_column(CommonLongText, nullable=True, comment='内容文本')
    ref_content: Mapped[str | None] = mapped_column(CommonLongText, nullable=True, comment='引用/转发内容文本')
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    def __repr__(self) -> str:
        return (f'SocialMediaContentOrm(source={self.source}, m_type={self.m_type}, '
                f'm_id={self.m_id}, m_uid={self.m_uid}, title={self.title}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class ArtworkCollectionOrm(Base):
    """图库作品表"""
    __tablename__ = f'{database_config.db_prefix}artwork_collection'
    __table_args__ = (
        UniqueConstraint('origin', 'aid'),
        Index(None, 'origin', 'uid'),
        Index('ix_artwork_common_search', 'origin', 'classification', 'rating', 'orientation'),
        Index('ix_artwork_classification_rating', 'classification', 'rating'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    origin: Mapped[str] = mapped_column(String(64), nullable=False, comment='作品来源/收录站点')
    aid: Mapped[str] = mapped_column(String(64), nullable=False, comment='作品原始ID/收录站点ID')
    uid: Mapped[str] = mapped_column(String(64), nullable=False, comment='作者ID')
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    uname: Mapped[str] = mapped_column(String(255), nullable=False)
    # 分类分级信息
    classification: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment='-2=忽略, -1=未知, 0=未分类, 1=AI生成, 2=外部来源, 3=人工分类'
    )
    rating: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment='-1=Unknown, 0=G, 1=S, 2=Q, 3=E'
    )
    # 作品图片信息
    width: Mapped[int] = mapped_column(Integer, nullable=False, comment='原始图片宽度')
    height: Mapped[int] = mapped_column(Integer, nullable=False, comment='原始图片高度')
    orientation: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment='宽高方位, 1=横图 0=方图 -1=竖图')
    url: Mapped[str] = mapped_column(CommonLongText, nullable=False, comment='作品在该来源/收录站点的访问地址')
    source: Mapped[str | None] = mapped_column(CommonLongText, nullable=True, comment='作品原始出处地址')
    cover_page: Mapped[str | None] = mapped_column(CommonLongText, nullable=True, comment='作品首页/封面图片链接')
    raw_tags: Mapped[str | None] = mapped_column(CommonLongText, nullable=True)
    description: Mapped[str | None] = mapped_column(CommonLongText, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    review_records_belonged_to_artwork: Mapped[list['ArtworkReviewRecordsOrm']] = relationship(
        'ArtworkReviewRecordsOrm',
        back_populates='review_record_parent_artwork',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    tags_belonged_to_artwork: Mapped[list['ArtworkWithTagsOrm']] = relationship(
        'ArtworkWithTagsOrm',
        back_populates='tag_parent_artwork',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    tags_name_artwork_had: Mapped[list['ArtworkTagOrm']] = relationship(
        'ArtworkTagOrm',
        secondary=f'{database_config.db_prefix}artwork_with_tags',
        back_populates='artworks_tag_name_had',
        lazy='raise',
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (f'ArtworkCollectionOrm(origin={self.origin}, aid={self.aid}, title={self.title}, '
                f'uid={self.uid}, uname={self.uname}, classification={self.classification}, rating={self.rating}, '
                f'width={self.width}, height={self.height}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class ArtworkReviewRecordsOrm(Base):
    """图库作品评审记录表"""
    __tablename__ = f'{database_config.db_prefix}artwork_review_records'
    __table_args__ = (
        Index(None, 'artwork_index_id', 'review_timestamp'),
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    artwork_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(ArtworkCollectionOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
    )
    review_timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False, comment='评审时间戳')
    review_classification: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment='评审分类结果')
    review_rating: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment='评审分级结果')
    review_from: Mapped[str] = mapped_column(String(255), nullable=False, comment='评审来源')
    review_info: Mapped[str] = mapped_column(String(255), nullable=False, comment='评审附加信息')
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    review_record_parent_artwork: Mapped[ArtworkCollectionOrm] = relationship(
        ArtworkCollectionOrm,
        back_populates='review_records_belonged_to_artwork',
        lazy='joined',
        innerjoin=True,
    )

    def __repr__(self) -> str:
        return (f'ArtworkReviewRecordsOrm(artwork_index_id={self.artwork_index_id}, '
                f'review_timestamp={self.review_timestamp}, review_classification={self.review_classification}, '
                f'review_rating={self.review_rating}, review_from={self.review_from}, '
                f'review_info={self.review_info or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class ArtworkTagOrm(Base):
    """图库作品标签表"""
    __tablename__ = f'{database_config.db_prefix}artwork_tag'
    __table_args__ = (
        database_config.table_args,
    )

    id: Mapped[int] = mapped_column(IndexInt, Identity(), primary_key=True)
    tag_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    tag_alt_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='Tag的别名或翻译名')
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    artwork_tags_belonged_to_tag_name: Mapped[list['ArtworkWithTagsOrm']] = relationship(
        'ArtworkWithTagsOrm',
        back_populates='artwork_tag_parent_tag_name',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='raise',
    )
    artworks_tag_name_had: Mapped[list[ArtworkCollectionOrm]] = relationship(
        ArtworkCollectionOrm,
        secondary=f'{database_config.db_prefix}artwork_with_tags',
        back_populates='tags_name_artwork_had',
        lazy='raise',
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (f'ArtworkTagOrm(tag_name={self.tag_name}, tag_alt_name={self.tag_alt_name or "null"}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


class ArtworkWithTagsOrm(Base):
    """图库作品标签关联表"""
    __tablename__ = f'{database_config.db_prefix}artwork_with_tags'
    __table_args__ = (
        Index(None, 'tag_index_id', 'artwork_index_id'),
        database_config.table_args,
    )

    artwork_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(ArtworkCollectionOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    tag_index_id: Mapped[int] = mapped_column(
        IndexInt,
        ForeignKey(ArtworkTagOrm.id, onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.now)

    # 设置级联和关系加载
    tag_parent_artwork: Mapped[ArtworkCollectionOrm] = relationship(
        ArtworkCollectionOrm,
        back_populates='tags_belonged_to_artwork',
        lazy='joined',
        innerjoin=True,
    )
    artwork_tag_parent_tag_name: Mapped[ArtworkTagOrm] = relationship(
        ArtworkTagOrm,
        back_populates='artwork_tags_belonged_to_tag_name',
        lazy='joined',
        innerjoin=True,
    )

    def __repr__(self) -> str:
        return (f'ArtworkWithTagsOrm(artwork_index_id={self.artwork_index_id}, tag_index_id={self.tag_index_id}, '
                f'created_at={self.created_at or "unknown"}, updated_at={self.updated_at or "unknown"})')


__all__ = [
    'GlobalCacheOrm',
    'SystemSettingOrm',
    'PluginOrm',
    'StatisticOrm',
    'HistoryOrm',
    'BotSelfOrm',
    'EntityOrm',
    'FriendshipOrm',
    'SignInOrm',
    'AuthSettingOrm',
    'CooldownOrm',
    'SubscriptionSourceOrm',
    'SubscriptionOrm',
    'SocialMediaContentOrm',
    'ArtworkCollectionOrm',
    'ArtworkReviewRecordsOrm',
    'ArtworkTagOrm',
    'ArtworkWithTagsOrm',
]
