"""
@Author         : Ailitonia
@Date           : 2024/5/12 下午11:39
@FileName       : output_core_data
@Project        : omega-miya-dev
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import date, datetime
from enum import Enum, unique
from typing import Literal

from omega_miya.database.internal.entity import BaseInternalEntity
from omega_miya.database.schemas import BotSelf, EmailBox, RelatedEntity, SubscriptionSource
from omega_miya.local_resource import TmpResource
from omega_miya.service.omega_api import register_get_route
from pydantic import BaseModel, Field


class DateBaseModel(BaseModel):
    class Config:
        extra = 'ignore'
        from_orm = True


@register_get_route('echo')
async def echo():
    return 'Hello world!'


@register_get_route('query_bots')
async def query_bots():
    @unique
    class _BotType(Enum):
        """Bot 类型"""
        console: Literal['Console'] = 'Console'
        onebot_v11: Literal['OneBot V11'] = 'OneBot V11'
        onebot_v12: Literal['OneBot V12'] = 'OneBot V12'
        qq: Literal['QQ'] = 'QQ'
        telegram: Literal['Telegram'] = 'Telegram'

    class _BotSelf(DateBaseModel):
        """BotSelf Model"""
        self_id: str
        bot_type: _BotType
        bot_status: int
        bot_info: str | None = None
        created_at: datetime | None = None
        updated_at: datetime | None = None

    class _Data(DateBaseModel):
        data: list[_BotSelf]

    result = await BotSelf.query_all()
    return _Data(data=result.result)


@register_get_route('query_sub_sources')
async def query_sub_sources():
    @unique
    class _SubscriptionSourceType(Enum):
        """订阅源 类型"""
        bili_live: Literal['bili_live'] = 'bili_live'
        bili_dynamic: Literal['bili_dynamic'] = 'bili_dynamic'
        pixiv_user: Literal['pixiv_user'] = 'pixiv_user'
        pixivision: Literal['pixivision'] = 'pixivision'
        weibo_user: Literal['weibo_user'] = 'weibo_user'

    class _SubscriptionSource(DateBaseModel):
        """订阅源 Model"""
        sub_type: _SubscriptionSourceType
        sub_id: str
        sub_user_name: str
        sub_info: str | None = None

    class _Data(DateBaseModel):
        data: list[_SubscriptionSource]

    result = await SubscriptionSource.query_all()
    return _Data(data=result.result)


@register_get_route('query_email_box')
async def query_email_box():
    class _EmailBox(DateBaseModel):
        """邮箱 Model"""
        address: str
        server_host: str
        protocol: str
        port: int
        password: str

    class _Data(DateBaseModel):
        data: list[_EmailBox]

    result = await EmailBox.query_all()
    return _Data(data=result.result)


@register_get_route('query_entities')
async def query_entities():
    @unique
    class _EntityType(Enum):
        """实体对象类型"""
        onebot_v11_user: Literal['onebot_v11_user'] = 'onebot_v11_user'  # QQ 用户
        onebot_v11_group: Literal['onebot_v11_group'] = 'onebot_v11_group'  # QQ 群组
        onebot_v11_guild: Literal['onebot_v11_guild'] = 'onebot_v11_guild'  # QQ 频道 (Onebot 协议)
        onebot_v11_guild_user: Literal['onebot_v11_guild_user'] = 'onebot_v11_guild_user'  # QQ 频道系统内用户 (Onebot 协议)
        onebot_v11_guild_channel: Literal['onebot_v11_guild_channel'] = 'onebot_v11_guild_channel'  # QQ 频道子频道 (Onebot 协议)

    class _EntityInfo(DateBaseModel):
        bot_id: str
        entity_type: _EntityType
        entity_id: str
        parent_id: str
        entity_name: str | None = None
        entity_info: str | None = None

    class _EntityFriendship(DateBaseModel):
        status: str = 'normal'
        mood: float = 0
        friendship: float = Field(default=0, alias='friend_ship')
        energy: float = 0
        currency: float = 0
        response_threshold: float = 0

    class _EntityAuthSetting(DateBaseModel):
        module: str
        plugin: str
        node: str
        available: int
        value: str | None = None

    class _EntityBoundMailbox(DateBaseModel):
        address: str
        bind_info: str | None = None

    class _EntitySubscribed(DateBaseModel):
        sub_type: str
        sub_id: str
        sub_user_name: str
        sub_info: str | None

    class _Entity(DateBaseModel):
        info: _EntityInfo
        friendship: _EntityFriendship
        signin_date: list[date]
        auth_setting: list[_EntityAuthSetting]
        bound_mailbox: list[_EntityBoundMailbox]
        subscribed_source: list[_EntitySubscribed]

    class _Data(DateBaseModel):
        entity_data: list[_Entity]

    new_entities = []
    result = await RelatedEntity.query_all()
    for x in result.result:
        entity = await BaseInternalEntity.init_from_index_id(id_=x.id)

        if entity.relation_type == 'bot_group' and entity.entity_model.entity_type == 'qq_group':
            entity_type = 'onebot_v11_group'
        elif entity.relation_type == 'bot_user' and entity.entity_model.entity_type == 'qq_user':
            entity_type = 'onebot_v11_user'
        elif entity.relation_type == 'group_user' and entity.entity_model.entity_type == 'qq_user':
            entity_type = 'onebot_v11_user'
        else:
            continue

        info = _EntityInfo(
            bot_id=entity.bot_id,
            entity_id=entity.entity_id,
            entity_type=entity_type,
            parent_id=entity.bot_id,
            entity_name=entity.entity_model.entity_name,
            entity_info=entity.entity_model.entity_info
        )
        friendship = _EntityFriendship.parse_obj(await entity.get_friendship_model())
        signin_date = await entity.query_sign_in_history()
        auth_setting = await entity.query_all_auth_setting()
        bound_mailbox = await entity.query_bound_email_box()
        subscribed_source = await entity.query_all_subscribed_source()

        new_entity = _Entity(
            info=info,
            friendship=friendship,
            signin_date=signin_date,
            auth_setting=auth_setting,
            bound_mailbox=bound_mailbox,
            subscribed_source=subscribed_source
        )
        new_entities.append(new_entity)
    return _Data(entity_data=new_entities)


@register_get_route('output_data')
async def output_data():
    class _OutputData(DateBaseModel):
        bots: list
        sub_sources: list
        email_box: list
        entities: list

    bots = await query_bots()
    sub_sources = await query_sub_sources()
    email_box = await query_email_box()
    entities = await query_entities()

    data = _OutputData(
        bots=bots.data,
        sub_sources=sub_sources.data,
        email_box=email_box.data,
        entities=entities.entity_data
    )

    async with TmpResource('output_data.json').async_open('w', encoding='utf8') as af:
        await af.write(data.json(ensure_ascii=False))

    return True
