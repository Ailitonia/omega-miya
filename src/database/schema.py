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

from sqlalchemy import Sequence, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import BigInteger, Date, DateTime, Float, Integer, String

from .config import database_config
from .schema_base import OmegaDeclarativeBase as Base
from .types import IndexInt


class SystemSettingOrm(Base):
    """系统参数表, 存放运行时配置"""
    __tablename__ = f'{database_config.db_prefix}system_setting'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    setting_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True, comment='参数名称')
    setting_value: Mapped[str] = mapped_column(String(512), nullable=False, index=True, comment='参数值')
    info: Mapped[str] = mapped_column(String(512), nullable=True, comment='参数说明')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"SystemSettingOrm(setting_name={self.setting_name!r}, setting_value={self.setting_value!r}, "
                f"info={self.info!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class PluginOrm(Base):
    """插件表, 存放插件信息"""
    __tablename__ = f'{database_config.db_prefix}plugin'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    plugin_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True, comment='插件名称')
    module_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, unique=True, comment='插件模块名称')
    enabled: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment='启用状态, 1: 启用, 0: 禁用, -1: 失效或未安装'
    )
    info: Mapped[str] = mapped_column(String(256), nullable=True, comment='附加说明')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"PluginOrm(plugin_name={self.plugin_name!r}, module_name={self.module_name!r}, "
                f"enabled={self.enabled!r}, info={self.info!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class StatisticOrm(Base):
    """统计信息表, 存放插件运行统计"""
    __tablename__ = f'{database_config.db_prefix}statistic'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    module_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='插件模块名称')
    plugin_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='插件显示名称')
    bot_self_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='对应的Bot')
    parent_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='对应调用用户父实体信息')
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='对应调用用户实体信息')
    call_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment='调用时间')
    call_info: Mapped[str] = mapped_column(String(4096), nullable=True, index=False, comment='调用信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"StatisticOrm(module_name={self.module_name!r}, plugin_name={self.plugin_name!r}, "
                f"bot_self_id={self.bot_self_id!r}, parent_entity_id={self.parent_entity_id!r}, "
                f"entity_id={self.entity_id!r}, call_time={self.call_time!r}, call_info={self.call_info!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class HistoryOrm(Base):
    """记录表"""
    __tablename__ = f'{database_config.db_prefix}history'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    time: Mapped[int] = mapped_column(BigInteger, nullable=False, comment='事件发生的时间戳')
    bot_self_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='收到事件的机器人id')
    parent_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='事件对应对象父实体id')
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='事件对应对象实体id')
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='事件类型')
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='事件id')
    raw_data: Mapped[str] = mapped_column(String(4096), nullable=False, comment='原始事件内容')
    msg_data: Mapped[str] = mapped_column(String(4096), nullable=True, comment='经处理的事件内容')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"HistoryOrm(time={self.time!r}, bot_self_id={self.bot_self_id!r}, "
                f"parent_entity_id={self.parent_entity_id!r}, entity_id={self.entity_id!r}, "
                f"event_type={self.event_type!r}, event_id={self.event_id!r}, "
                f"raw_data={self.raw_data!r}, msg_data={self.msg_data!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class BotSelfOrm(Base):
    """Bot表 对应不同机器人协议端"""
    __tablename__ = f'{database_config.db_prefix}bots'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    self_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True, comment='bot身份id, 用于识别bot, qq号等'
    )
    bot_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='Bot类型, 具体使用的协议')
    bot_status: Mapped[int] = mapped_column(Integer, nullable=False, comment='Bot在线状态')
    bot_info: Mapped[str] = mapped_column(String(512), nullable=True, comment='Bot描述信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    bots_entity: Mapped[list['EntityOrm']] = relationship(
        'EntityOrm', back_populates='entity_back_bots', cascade='all, delete-orphan', passive_deletes=True
    )

    def __repr__(self) -> str:
        return (f"BotSelfOrm(self_id={self.self_id!r}, bot_type={self.bot_type!r}, bot_status={self.bot_status!r}, "
                f"bot_info={self.bot_info!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class EntityOrm(Base):
    """实体表, 存放用户/群组/频道等所有需要交互的对象, 所有属性/好感度/权限/订阅等操作实例对象均以此为基准"""
    __tablename__ = f'{database_config.db_prefix}entity'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    bot_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(BotSelfOrm.id, ondelete='CASCADE'), nullable=False, comment='所属bot'
    )
    entity_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment='实体身份id, 不同类型实体可能相同, qq号/群号等'
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='实体类型')
    parent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='父实体id, qq号/群号等')
    entity_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='实体名称')
    entity_info: Mapped[str] = mapped_column(String(512), nullable=True, comment='实体描述信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    entity_back_bots: Mapped[BotSelfOrm] = relationship(
        BotSelfOrm, back_populates='bots_entity', lazy='joined', innerjoin=True
    )

    entity_friendship: Mapped[list['FriendshipOrm']] = relationship(
        'FriendshipOrm', back_populates='friendship_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_signin: Mapped[list['SignInOrm']] = relationship(
        'SignInOrm', back_populates='signin_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_auth: Mapped[list['AuthSettingOrm']] = relationship(
        'AuthSettingOrm', back_populates='auth_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_cooldown: Mapped[list['CoolDownOrm']] = relationship(
        'CoolDownOrm', back_populates='cooldown_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_email_box_bind: Mapped[list['EmailBoxBindOrm']] = relationship(
        'EmailBoxBindOrm',
        back_populates='email_box_bind_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_subscription: Mapped[list['SubscriptionOrm']] = relationship(
        'SubscriptionOrm', back_populates='subscription_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )

    def __repr__(self) -> str:
        return (f"EntityOrm(bot_index_id={self.bot_index_id!r}, entity_id={self.entity_id!r}, "
                f"entity_type={self.entity_type!r}, parent_id={self.parent_id!r}, "
                f"entity_name={self.entity_name!r}, entity_info={self.entity_info!r} "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class FriendshipOrm(Base):
    """好感度及状态表, 养成系统基础表单"""
    __tablename__ = f'{database_config.db_prefix}friendship'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    entity_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, comment='当前状态')
    mood: Mapped[float] = mapped_column(Float, nullable=False, comment='情绪值, 大于0: 好心情, 小于零: 坏心情')
    friendship: Mapped[float] = mapped_column(Float, nullable=False, comment='好感度/亲密度, 大于0: 友好, 小于0: 厌恶')
    energy: Mapped[float] = mapped_column(Float, nullable=False, comment='能量值')
    currency: Mapped[float] = mapped_column(Float, nullable=False, comment='持有货币')
    response_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, comment='响应阈值, 控制对交互做出响应的概率或频率, 根据具体插件使用数值'
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    friendship_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_friendship', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f"FriendshipOrm(entity_index_id={self.entity_index_id!r}, status={self.status!r}, "
                f"mood={self.mood!r}, friendship={self.friendship!r}, energy={self.energy!r}, "
                f"currency={self.currency!r}, response_threshold={self.response_threshold!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class SignInOrm(Base):
    """签到表, 养成系统基础表单"""
    __tablename__ = f'{database_config.db_prefix}sign_in'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    entity_index_id: Mapped[int] = mapped_column(Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False)
    sign_in_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment='签到日期')
    sign_in_info: Mapped[str] = mapped_column(String(64), nullable=True, comment='签到信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    signin_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_signin', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f"SignInOrm(entity_index_id={self.entity_index_id!r}, sign_in_date={self.sign_in_date!r}, "
                f"sign_in_info={self.sign_in_info!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class AuthSettingOrm(Base):
    """授权配置表, 主要用于权限管理, 同时兼用于存放使用插件时需要持久化的配置"""
    __tablename__ = f'{database_config.db_prefix}auth_setting'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    entity_index_id: Mapped[int] = mapped_column(Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='模块名')
    plugin: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='插件名')
    node: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='权限节点/配置名')
    available: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment='需求值, 0=deny/disable, 1=allow/enable, 1<=level'
    )
    value: Mapped[str] = mapped_column(String(8192), nullable=True, comment='若为插件配置项且对象具有的配置信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    auth_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_auth', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f"AuthSettingOrm(entity_index_id={self.entity_index_id!r}, module={self.module!r}, "
                f"plugin={self.plugin!r}, node={self.node!r}, available={self.available!r}, value={self.value!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class CoolDownOrm(Base):
    """冷却事件表"""
    __tablename__ = f'{database_config.db_prefix}cooldown'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    entity_index_id: Mapped[int] = mapped_column(Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='冷却事件, 用于唯一标识某个/类冷却')
    stop_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment='冷却结束时间')
    description: Mapped[str] = mapped_column(String(128), nullable=True, comment='事件描述')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    cooldown_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_cooldown', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f"CoolDownOrm(entity_index_id={self.entity_index_id!r}, event={self.event!r}, "
                f"stop_at={self.stop_at!r}, description={self.description!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class EmailBoxOrm(Base):
    """邮箱表"""
    __tablename__ = f'{database_config.db_prefix}email_box'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    address: Mapped[str] = mapped_column(String(128), nullable=False, index=True, unique=True, comment='邮箱地址')
    server_host: Mapped[str] = mapped_column(String(128), nullable=False, comment='IMAP/POP3服务器地址')
    protocol: Mapped[str] = mapped_column(String(16), nullable=False, comment='协议')
    port: Mapped[int] = mapped_column(Integer, nullable=False, comment='服务器端口')
    password: Mapped[str] = mapped_column(String(256), nullable=False, comment='密码')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    email_box_email_box_bind: Mapped[list['EmailBoxBindOrm']] = relationship(
        'EmailBoxBindOrm',
        back_populates='email_box_bind_back_email_box', cascade='all, delete-orphan', passive_deletes=True
    )

    def __repr__(self) -> str:
        return (f"EmailBoxOrm(address={self.address!r}, server_host={self.server_host!r}, "
                f"protocol={self.protocol!r}, port={self.port!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class EmailBoxBindOrm(Base):
    """邮箱绑定表"""
    __tablename__ = f'{database_config.db_prefix}email_box_bind'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    email_box_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(EmailBoxOrm.id, ondelete='CASCADE'), nullable=False
    )
    entity_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False
    )
    bind_info: Mapped[str] = mapped_column(String(64), nullable=True, comment='邮箱绑定信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    email_box_bind_back_email_box: Mapped[EmailBoxOrm] = relationship(
        EmailBoxOrm, back_populates='email_box_email_box_bind', lazy='joined', innerjoin=True
    )
    email_box_bind_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_email_box_bind', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f"EmailBoxBindOrm(email_box_index_id={self.email_box_index_id!r}, "
                f"entity_index_id={self.entity_index_id!r}, bind_info={self.bind_info!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class SubscriptionSourceOrm(Base):
    """订阅源表"""
    __tablename__ = f'{database_config.db_prefix}subscription_source'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    sub_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='订阅类型')
    sub_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='订阅id，直播间房间号/用户uid等')
    sub_user_name: Mapped[str] = mapped_column(String(64), nullable=False, comment='订阅用户的名称')
    sub_info: Mapped[str] = mapped_column(String(64), nullable=True, comment='订阅源信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    subscription_source_subscription: Mapped[list['SubscriptionOrm']] = relationship(
        'SubscriptionOrm',
        back_populates='subscription_back_subscription_source', cascade='all, delete-orphan', passive_deletes=True
    )

    def __repr__(self) -> str:
        return (f"SubscriptionSourceOrm(sub_type={self.sub_type!r}, sub_id={self.sub_id!r}, "
                f"sub_user_name={self.sub_user_name!r}, sub_info={self.sub_info!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class SubscriptionOrm(Base):
    """订阅表"""
    __tablename__ = f'{database_config.db_prefix}subscription'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    sub_source_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(SubscriptionSourceOrm.id, ondelete='CASCADE'), nullable=False
    )
    entity_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False
    )
    sub_info: Mapped[str] = mapped_column(String(64), nullable=True, comment='订阅信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    subscription_back_subscription_source: Mapped[SubscriptionSourceOrm] = relationship(
        SubscriptionSourceOrm, back_populates='subscription_source_subscription', lazy='joined', innerjoin=True
    )
    subscription_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_subscription', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f"SubscriptionOrm(sub_source_index_id={self.sub_source_index_id!r}, "
                f"entity_index_id={self.entity_index_id!r}, sub_info={self.sub_info!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class BiliDynamicOrm(Base):
    """B站动态表"""
    __tablename__ = f'{database_config.db_prefix}bili_dynamic'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    dynamic_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, unique=True, comment='动态id')
    dynamic_type: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment='动态类型')
    uid: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment='用户uid')
    content: Mapped[str] = mapped_column(String(4096), nullable=False, comment='动态内容')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"BiliDynamicOrm(dynamic_id={self.dynamic_id!r}, dynamic_type={self.dynamic_type!r}, "
                f"uid={self.uid!r}, content={self.content!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class ArtworkCollectionOrm(Base):
    """图库作品表"""
    __tablename__ = f'{database_config.db_prefix}artwork_collection'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    # 作品信息部分
    origin: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='作品来源/收录该作品的站点')
    aid: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='作品id')
    title: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment='作品标题title')
    uid: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='作者uid')
    uname: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment='作者名')
    # 分类分级信息
    classification: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment='标记标签, -1=未知, 0=未分类, 1=AI生成, 2=外部来源, 3=人工分类'
    )
    rating: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment='分级标签, -1=Unknown, 0=G, 1=S, 2=Q, 3=E'
    )
    # 作品图片信息
    width: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment='原始图片宽度')
    height: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment='原始图片高度')
    tags: Mapped[str] = mapped_column(String(1024), nullable=False, comment='作品标签')
    description: Mapped[str] = mapped_column(String(1024), nullable=True, comment='作品描述')
    source: Mapped[str] = mapped_column(String(512), nullable=False, comment='作品原始出处地址')
    cover_page: Mapped[str] = mapped_column(String(512), nullable=False, comment='作品首页/封面原图链接')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"ArtworkCollectionOrm(artwork_id={self.aid!r}, title={self.title!r}, "
                f"uid={self.uid!r}, uname={self.uname!r}, "
                f"classification={self.classification!r}, rating={self.rating!r}, "
                f"width={self.width!r}, height={self.height!r}, tags={self.tags!r}, "
                f"source={self.source!r}, cover_page={self.cover_page!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class PixivisionArticleOrm(Base):
    """Pixivision 表"""
    __tablename__ = f'{database_config.db_prefix}pixivision_article'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    aid: Mapped[int] = mapped_column(Integer, nullable=False, index=True, unique=True, comment='aid')
    title: Mapped[str] = mapped_column(String(256), nullable=False, comment='title')
    description: Mapped[str] = mapped_column(String(1024), nullable=False, comment='description')
    tags: Mapped[str] = mapped_column(String(1024), nullable=False, comment='tags')
    artworks_id: Mapped[str] = mapped_column(String(1024), nullable=False, comment='article artwork_id')
    url: Mapped[str] = mapped_column(String(1024), nullable=False, comment='url')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"PixivisionArticleOrm(aid={self.aid!r}, title={self.title!r}, description={self.description!r}, "
                f"tags={self.tags!r}, artworks_id={self.artworks_id!r}, url={self.url!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class WeiboDetailOrm(Base):
    """微博内容表"""
    __tablename__ = f'{database_config.db_prefix}weibo_detail'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    mid: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, unique=True, comment='微博id')
    uid: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment='用户uid')
    content: Mapped[str] = mapped_column(String(4096), nullable=False, comment='微博内容')
    retweeted_content: Mapped[str] = mapped_column(String(4096), nullable=False, comment='转发的微博内容')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"WeiboDetailOrm(mid={self.mid!r}, uid={self.uid!r}, "
                f"content={self.content!r}, retweeted_content={self.retweeted_content!r}, "
                f"created_at={self.created_at!r}, updated_at={self.updated_at!r})")


class WordBankOrm(Base):
    """问答语料词句表"""
    __tablename__ = f'{database_config.db_prefix}word_bank'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    key_word: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment='匹配目标')
    reply_entity: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment='响应对象, 可为群号/用户qq/频道id等标识'
    )
    result_word: Mapped[str] = mapped_column(String(8192), nullable=False, comment='结果文本')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f"WordBankOrm(key_word={self.key_word!r}, reply_entity={self.reply_entity!r}, "
                f"result_word={self.result_word!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r})")


__all__ = [
    'Base',
    'SystemSettingOrm',
    'PluginOrm',
    'StatisticOrm',
    'HistoryOrm',
    'BotSelfOrm',
    'EntityOrm',
    'FriendshipOrm',
    'SignInOrm',
    'AuthSettingOrm',
    'CoolDownOrm',
    'EmailBoxOrm',
    'EmailBoxBindOrm',
    'SubscriptionSourceOrm',
    'SubscriptionOrm',
    'BiliDynamicOrm',
    'ArtworkCollectionOrm',
    'PixivisionArticleOrm',
    'WeiboDetailOrm',
    'WordBankOrm',
]
