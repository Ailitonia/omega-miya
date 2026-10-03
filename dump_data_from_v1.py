"""
@Author         : Ailitonia
@Date           : 2026/10/2 19:28
@FileName       : dump_data_from_v1
@Project        : omega-miya
@Description    : 核心数据导出工具, 执行 v1 -> v2 跨版本更新前导出核心数据
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

import nonebot
from nonebot.log import logger
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.database.internal.auth_setting import AuthSetting as _V1AuthSetting
    from src.database.internal.entity import Entity as _V1Entity
    from src.database.internal.friendship import Friendship as _V1Friendship
    from src.database.internal.sign_in import SignIn as _V1SignIn
    from src.database.internal.subscription import Subscription as _V1Subscription
    from src.resource import TemporaryResource


class _DataModel(BaseModel):
    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True, frozen=True)


def _truncate_to_v2_limit(field_desc: str, value: str | None, max_length: int, item_desc: str) -> str | None:
    """将字段值截断至 v2 数据库字段长度限制, 超长时记录警告

    v2 的部分 string 字段长度小于 v1 (如 bot_info/entity_info 由 512 缩短为 255),
    按字符截断 (与 MySQL utf8mb4 字符计数语义一致), 避免导入 v2 时报 Data too long
    """
    if value is not None and len(value) > max_length:
        logger.warning(
            f'{field_desc} of {item_desc} length {len(value)} exceeds v2 limit {max_length}, truncated'
        )
        return value[:max_length]
    return value


class _BotRef(_DataModel):
    """归属 Bot 自然键引用 (对应 v2 `entity_parent_bot` 级联数据, 以自然键代替索引 ID)"""
    bot_type: str
    self_id: str


class _EntityRef(_DataModel):
    """实体对象自然键引用 (对应 v2 各关联表 `_BaseEntity` 级联数据, 以自然键代替索引 ID)"""
    bot_type: str
    bot_self_id: str
    entity_type: str
    entity_id: str


class _SourceRef(_DataModel):
    """订阅源自然键引用 (对应 v2 `subscription_parent_source` 级联数据, 以自然键代替索引 ID)"""
    sub_type: str
    sub_id: str


class BotSelf(_DataModel):
    """Bot 自身数据 (v2 `bot_info` 字段长度限制为 255)"""
    bot_type: str
    self_id: str
    bot_status: int
    bot_info: str | None

    @field_validator('bot_info')
    @classmethod
    def _truncate_bot_info(cls, value: str | None, info: ValidationInfo) -> str | None:
        item_desc = f"Bot(type={info.data.get('bot_type')}, self_id={info.data.get('self_id')})"
        return _truncate_to_v2_limit('BotSelf.bot_info', value, max_length=255, item_desc=item_desc)


class SubscriptionSource(_DataModel):
    """订阅源数据"""
    sub_type: str
    sub_id: str
    sub_user_name: str
    sub_info: str | None


class Entity(_DataModel):
    """实体对象数据 (v2 `entity_info` 字段长度限制为 255)"""
    entity_parent_bot: _BotRef
    entity_type: str
    entity_id: str
    entity_name: str
    entity_extra: dict[str, Any]
    entity_info: str | None

    @field_validator('entity_info')
    @classmethod
    def _truncate_entity_info(cls, value: str | None, info: ValidationInfo) -> str | None:
        item_desc = f"Entity(type={info.data.get('entity_type')}, entity_id={info.data.get('entity_id')})"
        return _truncate_to_v2_limit('Entity.entity_info', value, max_length=255, item_desc=item_desc)


class Friendship(_DataModel):
    """好感度数据"""
    friendship_parent_entity: _EntityRef
    status: str
    mood: Decimal
    friendship: Decimal
    energy: Decimal
    currency: Decimal
    rsp_threshold: Decimal


class SignIn(_DataModel):
    """签到数据"""
    sign_in_parent_entity: _EntityRef
    sign_in_date: date
    sign_in_info: str | None


class AuthSetting(_DataModel):
    """授权配置数据"""
    auth_parent_entity: _EntityRef
    module: str
    plugin: str
    node: str
    available: int
    value: dict[str, Any]


class Subscription(_DataModel):
    """订阅数据"""
    subscription_parent_source: _SourceRef
    subscription_parent_entity: _EntityRef
    sub_info: str | None


class SystemSetting(_DataModel):
    """系统参数数据"""
    setting_name: str
    setting_key: str
    setting_value: str
    info: str | None


async def stream_dump_items_to_file[T: 'BaseModel'](items: Iterable[T], output_file: TemporaryResource):
    """流式导出 JSON 数据到目标文件, 每行一个, 使用 `|=+>`, `<-=|` 分别作为行前后缀进行校验"""
    item_json_iter = (item.model_dump_json(ensure_ascii=False) for item in items)
    async with output_file.async_open('w', encoding='utf-8') as af:
        await af.writelines(f'|=+> {json_line} <-=|\n' for json_line in item_json_iter)


async def stream_load_items_from_file[T: 'BaseModel'](output_file: TemporaryResource, target_model: type[T]):
    """流式读取 JSON 数据并解析为数据模型, 每行一个, 使用 `|=+>`, `<-=|` 分别作为行前后缀进行校验"""
    async with output_file.async_open('r', encoding='utf-8') as af:
        async for line in af:
            if line.startswith('|=+> ') and line.endswith(' <-=|\n'):
                json_line = line.removeprefix('|=+> ').removesuffix(' <-=|\n').strip()
                try:
                    item = target_model.model_validate_json(json_line)
                    yield item
                except Exception as e:
                    logger.error(f'Failed to parse line: {line.strip()}. Error: {e}')
            else:
                logger.warning(f'Line format invalid: {line.strip()}')


def gene_output_json_file(target_name: str) -> TemporaryResource:
    from src.resource import TemporaryResource
    return TemporaryResource('v1_dump_data', f'{target_name}.json')


async def _query_bot_ref_map() -> dict[int, _BotRef]:
    """查询全部 Bot 自身数据, 并建立索引 ID -> 自然键引用映射"""
    from src.database import BotSelfDAL

    async with BotSelfDAL.begin_dal_session() as dal:
        all_bots = await dal.query_all()

    return {bot.id: _BotRef(bot_type=bot.bot_type.value, self_id=bot.self_id) for bot in all_bots}


async def _query_entity_ref_map() -> dict[int, _EntityRef]:
    """查询全部实体对象数据, 并建立索引 ID -> 自然键引用映射"""
    from src.database import EntityDAL

    bot_ref_map = await _query_bot_ref_map()

    async with EntityDAL.begin_dal_session() as dal:
        all_entities = await dal.query_all()

    entity_ref_map: dict[int, _EntityRef] = {}
    for entity in all_entities:
        bot_ref = bot_ref_map.get(entity.bot_index_id)
        if bot_ref is None:
            logger.warning(f'Entity(id={entity.id}) bot_index_id={entity.bot_index_id} not found in BotSelf, skipped')
            continue
        entity_ref_map[entity.id] = _EntityRef(
            bot_type=bot_ref.bot_type,
            bot_self_id=bot_ref.self_id,
            entity_type=entity.entity_type.value,
            entity_id=entity.entity_id,
        )
    return entity_ref_map


async def _query_source_ref_map() -> dict[int, _SourceRef]:
    """查询全部订阅源数据, 并建立索引 ID -> 自然键引用映射"""
    from src.database import SubscriptionSourceDAL

    async with SubscriptionSourceDAL.begin_dal_session() as dal:
        all_sources = await dal.query_all()

    return {source.id: _SourceRef(sub_type=source.sub_type.value, sub_id=source.sub_id) for source in all_sources}


def _parse_auth_setting_value(auth_setting: _V1AuthSetting) -> dict[str, Any]:
    """解析 v1 AuthSetting 中 JSON 文本格式的 value 字段

    v1 的 value 为插件自定义配置文本, 多数为 JSON 对象文本, 但也存在纯数值/字符串等非 JSON 对象文本,
    统一转换为 dict: JSON 对象文本直接解析, 其余内容包装为 `{'value': <内容>}` 以保留原始数据
    """
    if not auth_setting.value:
        return {}

    try:
        parsed_value = json.loads(auth_setting.value)
    except json.JSONDecodeError:
        return {'value': auth_setting.value}

    if isinstance(parsed_value, dict):
        return parsed_value
    return {'value': parsed_value}


async def dump_bot_self_data() -> None:
    """导出 BotSelf 数据 -> bot_self.json"""
    from src.database import BotSelfDAL

    async with BotSelfDAL.begin_dal_session() as dal:
        all_bots = await dal.query_all()

    output_data_iter = (
        BotSelf.model_validate({
            'bot_type': bot.bot_type,
            'self_id': bot.self_id,
            'bot_status': bot.bot_status,
            'bot_info': bot.bot_info,
        })
        for bot in all_bots
    )

    output_file = gene_output_json_file('bot_self')
    await stream_dump_items_to_file(output_data_iter, output_file)
    logger.info(f'BotSelf data dumped to {output_file.path}, total {len(all_bots)} items')


async def dump_subscription_source_data() -> None:
    """导出 SubscriptionSource 数据 -> subscription_source.json"""
    from src.database import SubscriptionSourceDAL

    async with SubscriptionSourceDAL.begin_dal_session() as dal:
        all_sources = await dal.query_all()

    output_data_iter = (
        SubscriptionSource(
            sub_type=source.sub_type.value,
            sub_id=source.sub_id,
            sub_user_name=source.sub_user_name,
            sub_info=source.sub_info,
        )
        for source in all_sources
    )

    output_file = gene_output_json_file('subscription_source')
    await stream_dump_items_to_file(output_data_iter, output_file)
    logger.info(f'SubscriptionSource data dumped to {output_file.path}, total {len(all_sources)} items')


async def dump_entity_data() -> None:
    """导出 Entity 数据 -> entity.json"""
    from src.database import EntityDAL

    bot_ref_map = await _query_bot_ref_map()

    async with EntityDAL.begin_dal_session() as dal:
        all_entities = await dal.query_all()

    def _gene_dump_item(entity: _V1Entity) -> Entity | None:
        bot_ref = bot_ref_map.get(entity.bot_index_id)
        if bot_ref is None:
            logger.warning(f'Entity(id={entity.id}) bot_index_id={entity.bot_index_id} not found in BotSelf, skipped')
            return None
        return Entity(
            entity_parent_bot=bot_ref,
            entity_type=entity.entity_type.value,
            entity_id=entity.entity_id,
            entity_name=entity.entity_name,
            entity_extra={},
            entity_info=entity.entity_info,
        )

    output_data_list = [item for item in (_gene_dump_item(entity) for entity in all_entities) if item is not None]

    output_file = gene_output_json_file('entity')
    await stream_dump_items_to_file(output_data_list, output_file)
    logger.info(f'Entity data dumped to {output_file.path}, total {len(output_data_list)} items')


async def dump_friendship_data() -> None:
    """导出 Friendship 数据 -> friendship.json"""
    from src.database import FriendshipDAL

    entity_ref_map = await _query_entity_ref_map()

    async with FriendshipDAL.begin_dal_session() as dal:
        all_friendship = await dal.query_all()

    def _gene_dump_item(friendship: _V1Friendship) -> Friendship | None:
        entity_ref = entity_ref_map.get(friendship.entity_index_id)
        if entity_ref is None:
            logger.warning(
                f'Friendship(id={friendship.id}) entity_index_id={friendship.entity_index_id} '
                f'not found in Entity, skipped'
            )
            return None
        return Friendship(
            friendship_parent_entity=entity_ref,
            status=friendship.status,
            mood=Decimal(str(friendship.mood)),
            friendship=Decimal(str(friendship.friendship)),
            energy=Decimal(str(friendship.energy)),
            currency=Decimal(str(friendship.currency)),
            rsp_threshold=Decimal(str(friendship.response_threshold)),
        )

    output_data_list = [
        item for item in (_gene_dump_item(friendship) for friendship in all_friendship) if item is not None
    ]

    output_file = gene_output_json_file('friendship')
    await stream_dump_items_to_file(output_data_list, output_file)
    logger.info(f'Friendship data dumped to {output_file.path}, total {len(output_data_list)} items')


async def dump_sign_in_data() -> None:
    """导出 SignIn 数据 -> sign_in.json"""
    from src.database import SignInDAL

    entity_ref_map = await _query_entity_ref_map()

    async with SignInDAL.begin_dal_session() as dal:
        all_sign_in = await dal.query_all()

    def _gene_dump_item(sign_in: _V1SignIn) -> SignIn | None:
        entity_ref = entity_ref_map.get(sign_in.entity_index_id)
        if entity_ref is None:
            logger.warning(
                f'SignIn(id={sign_in.id}) entity_index_id={sign_in.entity_index_id} not found in Entity, skipped'
            )
            return None
        return SignIn(
            sign_in_parent_entity=entity_ref,
            sign_in_date=sign_in.sign_in_date,
            sign_in_info=sign_in.sign_in_info,
        )

    output_data_list = [item for item in (_gene_dump_item(sign_in) for sign_in in all_sign_in) if item is not None]

    output_file = gene_output_json_file('sign_in')
    await stream_dump_items_to_file(output_data_list, output_file)
    logger.info(f'SignIn data dumped to {output_file.path}, total {len(output_data_list)} items')


async def dump_auth_setting_data() -> None:
    """导出 AuthSetting 数据 -> auth_setting.json"""
    from src.database import AuthSettingDAL

    entity_ref_map = await _query_entity_ref_map()

    async with AuthSettingDAL.begin_dal_session() as dal:
        all_auth_setting = await dal.query_all()

    def _gene_dump_item(auth_setting: _V1AuthSetting) -> AuthSetting | None:
        entity_ref = entity_ref_map.get(auth_setting.entity_index_id)
        if entity_ref is None:
            logger.warning(
                f'AuthSetting(id={auth_setting.id}) entity_index_id={auth_setting.entity_index_id} '
                f'not found in Entity, skipped'
            )
            return None
        return AuthSetting(
            auth_parent_entity=entity_ref,
            module=auth_setting.module,
            plugin=auth_setting.plugin,
            node=auth_setting.node,
            available=auth_setting.available,
            value=_parse_auth_setting_value(auth_setting),
        )

    output_data_list = [
        item for item in (_gene_dump_item(auth_setting) for auth_setting in all_auth_setting) if item is not None
    ]

    output_file = gene_output_json_file('auth_setting')
    await stream_dump_items_to_file(output_data_list, output_file)
    logger.info(f'AuthSetting data dumped to {output_file.path}, total {len(output_data_list)} items')


async def dump_subscription_data() -> None:
    """导出 Subscription 数据 -> subscription.json"""
    from src.database import SubscriptionDAL

    entity_ref_map = await _query_entity_ref_map()
    source_ref_map = await _query_source_ref_map()

    async with SubscriptionDAL.begin_dal_session() as dal:
        all_subscription = await dal.query_all()

    def _gene_dump_item(subscription: _V1Subscription) -> Subscription | None:
        entity_ref = entity_ref_map.get(subscription.entity_index_id)
        source_ref = source_ref_map.get(subscription.sub_source_index_id)
        if entity_ref is None:
            logger.warning(
                f'Subscription(id={subscription.id}) entity_index_id={subscription.entity_index_id} '
                f'not found in Entity, skipped'
            )
            return None
        if source_ref is None:
            logger.warning(
                f'Subscription(id={subscription.id}) sub_source_index_id={subscription.sub_source_index_id} '
                f'not found in SubscriptionSource, skipped'
            )
            return None
        return Subscription(
            subscription_parent_source=source_ref,
            subscription_parent_entity=entity_ref,
            sub_info=subscription.sub_info,
        )

    output_data_list = [
        item for item in (_gene_dump_item(subscription) for subscription in all_subscription) if item is not None
    ]

    output_file = gene_output_json_file('subscription')
    await stream_dump_items_to_file(output_data_list, output_file)
    logger.info(f'Subscription data dumped to {output_file.path}, total {len(output_data_list)} items')


async def dump_system_setting_data() -> None:
    """导出 SystemSetting 数据 -> system_setting.json"""
    from src.database import SystemSettingDAL

    async with SystemSettingDAL.begin_dal_session() as dal:
        all_settings = await dal.query_all()

    output_data_iter = (
        SystemSetting(
            setting_name=setting.setting_name,
            setting_key=setting.setting_key,
            setting_value=setting.setting_value,
            info=setting.info,
        )
        for setting in all_settings
    )

    output_file = gene_output_json_file('system_setting')
    await stream_dump_items_to_file(output_data_iter, output_file)
    logger.info(f'SystemSetting data dumped to {output_file.path}, total {len(all_settings)} items')


async def dump_all_data() -> None:
    """导出全部核心数据"""
    await dump_bot_self_data()
    await dump_subscription_source_data()
    await dump_entity_data()
    await dump_friendship_data()
    await dump_sign_in_data()
    await dump_auth_setting_data()
    await dump_subscription_data()
    await dump_system_setting_data()
    logger.info('All v1 core data dump finished')


if __name__ == '__main__':
    nonebot.init(log_level='INFO')

    asyncio.run(dump_all_data())
