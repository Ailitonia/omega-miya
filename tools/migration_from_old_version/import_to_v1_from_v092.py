"""
@Author         : Ailitonia
@Date           : 2024/5/24 下午8:40
@FileName       : import_from_v092
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime, date
from typing import Optional

import ujson as json
from nonebot.log import logger
from pydantic import BaseModel, ConfigDict

from src.database import BotSelfDAL, SubscriptionSourceDAL, EmailBoxDAL, begin_db_session
from src.resource import TemporaryResource
from src.service.omega_api import register_get_route
from src.service.omega_base import OmegaEntity


class DateBaseModel(BaseModel):
    model_config = ConfigDict(extra='ignore')


class _BotSelf(DateBaseModel):
    """BotSelf Model"""
    self_id: str
    bot_type: str
    bot_status: int
    bot_info: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class _SubscriptionSource(DateBaseModel):
    """订阅源 Model"""
    sub_type: str
    sub_id: str
    sub_user_name: str
    sub_info: Optional[str] = None


class _EmailBox(DateBaseModel):
    """邮箱 Model"""
    address: str
    server_host: str
    protocol: str
    port: int
    password: str


class _EntityInfo(DateBaseModel):
    bot_id: str
    entity_type: str
    entity_id: str
    parent_id: str
    entity_name: Optional[str] = None
    entity_info: Optional[str] = None


class _EntityFriendship(DateBaseModel):
    status: str = 'normal'
    mood: float = 0
    friendship: float = 0
    energy: float = 0
    currency: float = 0
    response_threshold: float = 0


class _EntityAuthSetting(DateBaseModel):
    module: str
    plugin: str
    node: str
    available: int
    value: Optional[str] = None


class _EntityBoundMailbox(DateBaseModel):
    address: str
    bind_info: Optional[str] = None


class _EntitySubscribed(DateBaseModel):
    sub_type: str
    sub_id: str
    sub_user_name: str
    sub_info: Optional[str]


class _Entity(DateBaseModel):
    info: _EntityInfo
    friendship: _EntityFriendship
    signin_date: list[date]
    auth_setting: list[_EntityAuthSetting]
    bound_mailbox: list[_EntityBoundMailbox]
    subscribed_source: list[_EntitySubscribed]


class _OutputData(DateBaseModel):
    bots: list[_BotSelf]
    sub_sources: list[_SubscriptionSource]
    email_box: list[_EmailBox]
    entities: list[_Entity]


@register_get_route('input_v092_data')
async def input_v092_data():
    async with TemporaryResource('output_data.json').async_open('r', encoding='utf8') as af:
        data = _OutputData.model_validate(json.loads(await af.read()))

    logger.info('start import bot data')
    async with begin_db_session() as session:
        bot_dal = BotSelfDAL(session=session)
        for bot in data.bots:
            await bot_dal.add(self_id=bot.self_id, bot_type=bot.bot_type, bot_status=bot.bot_status, bot_info=bot.bot_info)
        await bot_dal.commit_session()
    logger.success('bot data import completed')

    logger.info('start import subscription source data')
    async with begin_db_session() as session:
        sub_dal = SubscriptionSourceDAL(session=session)
        for source in data.sub_sources:
            await sub_dal.add(sub_type=source.sub_type, sub_id=source.sub_id, sub_user_name=source.sub_user_name, sub_info=source.sub_info)
        await sub_dal.commit_session()

    async with begin_db_session() as session:
        sub_dal = SubscriptionSourceDAL(session=session)
        available_subscription_source = await sub_dal.query_all()
    logger.success('subscription source data import completed')

    logger.info('start import email box data')
    async with begin_db_session() as session:
        email_dal = EmailBoxDAL(session=session)
        for mailbox in data.email_box:
            await email_dal.add(address=mailbox.address, server_host=mailbox.server_host, protocol=mailbox.protocol, port=mailbox.port, password=mailbox.password)
        await email_dal.commit_session()

    async with begin_db_session() as session:
        email_dal = EmailBoxDAL(session=session)
        available_mailbox = await email_dal.query_all()
        available_mailbox_map = {x.address: x for x in available_mailbox}
    logger.success('email box data import completed')

    logger.info('start import entity data')
    for entity_data in data.entities:
        async with begin_db_session() as session:
            info = entity_data.info
            entity = OmegaEntity(session=session, bot_id=info.bot_id, entity_type=info.entity_type, entity_id=info.entity_id, parent_id=info.parent_id)
            await entity.add_upgrade(entity_name=info.entity_name, entity_info=info.entity_info)

            friendship = entity_data.friendship
            await entity.set_friendship(
                status=friendship.status,
                mood=friendship.mood,
                friendship=friendship.friendship,
                energy=friendship.energy,
                currency=friendship.currency,
                response_threshold=friendship.response_threshold
            )

            signin_date = entity_data.signin_date
            for date_ in signin_date:
                await entity.sign_in(date_=date_, sign_in_info='import form old version(v0.9.2)')

            auth_setting = entity_data.auth_setting
            for auth in auth_setting:
                await entity.set_auth_setting(
                    module=auth.module, plugin=auth.plugin, node=auth.node, available=auth.available, value=auth.value
                )

            bound_mailbox = entity_data.bound_mailbox
            for mailbox in bound_mailbox:
                await entity.bind_email_box(
                    email_box=available_mailbox_map.get(mailbox.address),
                    bind_info=f'{entity.entity_name}-{mailbox.address}'
                )

            subscribed_source = entity_data.subscribed_source
            for source in subscribed_source:
                target_source = [
                    x for x in available_subscription_source
                    if (x.sub_id == source.sub_id and x.sub_type.value == source.sub_type)
                ]
                if len(target_source) == 1:
                    await entity.add_subscription(subscription_source=target_source[0], sub_info=source.sub_info)

            await entity.commit_session()
        logger.info(f'{entity} data import completed')

    logger.success('entity data import completed')


__all__ = []
