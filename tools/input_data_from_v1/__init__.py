"""
@Author         : Ailitonia
@Date           : 2026/10/3 01:30
@FileName       : input_data_from_v1
@Project        : omega-miya
@Description    : v1 核心数据导入工具, 将 dump_data_from_v1 导出的数据导入 v2 数据库
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import nonebot
from nonebot.log import logger
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

if TYPE_CHECKING:
    from src.resource import TemporaryResource

EntityIndexIdMap = dict[tuple[str, str, str, str], int]
"""实体自然键 (bot_type, bot_self_id, entity_type, entity_id) -> v2 索引 ID 映射"""

SourceIndexIdMap = dict[tuple[str, str], int]
"""订阅源自然键 (sub_type, sub_id) -> v2 索引 ID 映射"""


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


def _get_entity_index_id(entity_index_id_map: EntityIndexIdMap, entity_ref: _EntityRef) -> int | None:
    """从实体自然键映射中获取 v2 索引 ID"""
    key = (entity_ref.bot_type, entity_ref.bot_self_id, entity_ref.entity_type, entity_ref.entity_id)
    return entity_index_id_map.get(key)


async def import_bot_self_data() -> None:
    """导入 BotSelf 数据"""
    from src.database import BotSelfDAL

    imported_count = 0
    async with BotSelfDAL.create() as dal:
        async for bot in stream_load_items_from_file(gene_output_json_file('bot_self'), BotSelf):
            await dal.add_update_exist(
                bot_type=bot.bot_type,
                self_id=bot.self_id,
                bot_status=bot.bot_status,
                bot_info=bot.bot_info,
            )
            imported_count += 1
    logger.info(f'BotSelf data imported, total {imported_count} items')


async def import_subscription_source_data() -> SourceIndexIdMap:
    """导入 SubscriptionSource 数据, 返回订阅源自然键 -> v2 索引 ID 映射"""
    from src.database import SubscriptionSourceDAL

    source_index_id_map: SourceIndexIdMap = {}
    async with SubscriptionSourceDAL.create() as dal:
        output_file = gene_output_json_file('subscription_source')
        async for source in stream_load_items_from_file(output_file, SubscriptionSource):
            imported_item = await dal.add_update_exist(
                sub_type=source.sub_type,
                sub_id=source.sub_id,
                sub_user_name=source.sub_user_name,
                sub_info=source.sub_info,
            )
            source_index_id_map[(source.sub_type, source.sub_id)] = imported_item.id
    logger.info(f'SubscriptionSource data imported, total {len(source_index_id_map)} items')
    return source_index_id_map


async def import_entity_data() -> EntityIndexIdMap:
    """导入 Entity 数据, 返回实体自然键 -> v2 索引 ID 映射

    v2 `EntityType` 不支持的实体类型 (如 v1 遗留的 qq_* / *_guild* 类型) 整体跳过并按类型统计
    """
    from src.database import EntityDAL
    from src.database.internal.entity import EntityType

    entity_index_id_map: EntityIndexIdMap = {}
    skipped_entity_type_counter: dict[str, int] = {}
    async with EntityDAL.create() as dal:
        async for entity in stream_load_items_from_file(gene_output_json_file('entity'), Entity):
            try:
                entity_type = EntityType(entity.entity_type)
            except ValueError:
                skipped_count = skipped_entity_type_counter.get(entity.entity_type, 0)
                skipped_entity_type_counter[entity.entity_type] = skipped_count + 1
                continue

            imported_item = await dal.add_update_exist(
                bot_type=entity.entity_parent_bot.bot_type,
                bot_self_id=entity.entity_parent_bot.self_id,
                entity_type=entity_type,
                entity_id=entity.entity_id,
                entity_name=entity.entity_name,
                entity_extra=entity.entity_extra,
                entity_info=entity.entity_info,
            )
            entity_key = (
                entity.entity_parent_bot.bot_type,
                entity.entity_parent_bot.self_id,
                entity.entity_type,
                entity.entity_id,
            )
            entity_index_id_map[entity_key] = imported_item.id

    if skipped_entity_type_counter:
        skipped_detail = ', '.join(
            f'{entity_type}({count})' for entity_type, count in skipped_entity_type_counter.items()
        )
        logger.warning(
            f'Entity data import skipped unsupported entity type(s): {skipped_detail}, '
            f'total {sum(skipped_entity_type_counter.values())} items'
        )
    logger.info(f'Entity data imported, total {len(entity_index_id_map)} items')
    return entity_index_id_map


async def import_friendship_data(entity_index_id_map: EntityIndexIdMap) -> None:
    """导入 Friendship 数据 (依赖 import_entity_data 的索引 ID 映射)"""
    from src.database import EntityDAL

    imported_count = 0
    skipped_count = 0
    async with EntityDAL.create() as dal:
        async for friendship in stream_load_items_from_file(gene_output_json_file('friendship'), Friendship):
            entity_index_id = _get_entity_index_id(entity_index_id_map, friendship.friendship_parent_entity)
            if entity_index_id is None:
                skipped_count += 1
                logger.warning(
                    f'Friendship of {friendship.friendship_parent_entity!r} not found in imported Entity, skipped'
                )
                continue

            await dal.set_entity_friendship(
                entity_index_id,
                status=friendship.status,
                mood=friendship.mood,
                friendship=friendship.friendship,
                energy=friendship.energy,
                currency=friendship.currency,
                rsp_threshold=friendship.rsp_threshold,
            )
            imported_count += 1
    logger.info(f'Friendship data imported, total {imported_count} items, skipped {skipped_count} items')


async def import_sign_in_data(entity_index_id_map: EntityIndexIdMap) -> None:
    """导入 SignIn 数据 (依赖 import_entity_data 的索引 ID 映射)"""
    from src.database import EntityDAL

    imported_count = 0
    skipped_count = 0
    async with EntityDAL.create() as dal:
        async for sign_in in stream_load_items_from_file(gene_output_json_file('sign_in'), SignIn):
            entity_index_id = _get_entity_index_id(entity_index_id_map, sign_in.sign_in_parent_entity)
            if entity_index_id is None:
                skipped_count += 1
                logger.warning(f'SignIn of {sign_in.sign_in_parent_entity!r} not found in imported Entity, skipped')
                continue

            await dal.set_entity_sign_in(
                entity_index_id,
                date_=sign_in.sign_in_date,
                sign_in_info=sign_in.sign_in_info,
            )
            imported_count += 1
    logger.info(f'SignIn data imported, total {imported_count} items, skipped {skipped_count} items')


async def import_auth_setting_data(entity_index_id_map: EntityIndexIdMap) -> None:
    """导入 AuthSetting 数据 (依赖 import_entity_data 的索引 ID 映射)"""
    from src.database import EntityDAL

    imported_count = 0
    skipped_count = 0
    async with EntityDAL.create() as dal:
        async for auth_setting in stream_load_items_from_file(gene_output_json_file('auth_setting'), AuthSetting):
            entity_index_id = _get_entity_index_id(entity_index_id_map, auth_setting.auth_parent_entity)
            if entity_index_id is None:
                skipped_count += 1
                logger.warning(
                    f'AuthSetting of {auth_setting.auth_parent_entity!r} not found in imported Entity, skipped'
                )
                continue

            await dal.set_entity_auth_setting(
                entity_index_id,
                module=auth_setting.module,
                plugin=auth_setting.plugin,
                node=auth_setting.node,
                available=auth_setting.available,
                value=auth_setting.value,
            )
            imported_count += 1
    logger.info(f'AuthSetting data imported, total {imported_count} items, skipped {skipped_count} items')


async def import_subscription_data(
        entity_index_id_map: EntityIndexIdMap,
        source_index_id_map: SourceIndexIdMap,
) -> None:
    """导入 Subscription 数据 (依赖 import_entity_data 与 import_subscription_source_data 的索引 ID 映射)"""
    from src.database import EntityDAL

    imported_count = 0
    skipped_count = 0
    async with EntityDAL.create() as dal:
        output_file = gene_output_json_file('subscription')
        async for subscription in stream_load_items_from_file(output_file, Subscription):
            entity_index_id = _get_entity_index_id(entity_index_id_map, subscription.subscription_parent_entity)
            source_ref = subscription.subscription_parent_source
            source_key = (source_ref.sub_type, source_ref.sub_id)
            source_index_id = source_index_id_map.get(source_key)
            if entity_index_id is None or source_index_id is None:
                skipped_count += 1
                logger.warning(f'Subscription of {subscription.subscription_parent_entity!r} -> {source_key!r} '
                               f'not found in imported data, skipped')
                continue

            await dal.set_entity_subscription(
                entity_index_id,
                source_index_id,
                sub_info=subscription.sub_info,
            )
            imported_count += 1
    logger.info(f'Subscription data imported, total {imported_count} items, skipped {skipped_count} items')


async def import_system_setting_data() -> None:
    """导入 SystemSetting 数据"""
    from src.database import SystemSettingDAL

    imported_count = 0
    async with SystemSettingDAL.create() as dal:
        async for setting in stream_load_items_from_file(gene_output_json_file('system_setting'), SystemSetting):
            await dal.add_update_exist(
                setting_name=setting.setting_name,
                setting_key=setting.setting_key,
                setting_value=setting.setting_value,
                info=setting.info,
            )
            imported_count += 1
    logger.info(f'SystemSetting data imported, total {imported_count} items')


async def main() -> None:
    """导入全部 v1 核心数据"""
    await import_bot_self_data()
    source_index_id_map = await import_subscription_source_data()
    entity_index_id_map = await import_entity_data()
    await import_friendship_data(entity_index_id_map)
    await import_sign_in_data(entity_index_id_map)
    await import_auth_setting_data(entity_index_id_map)
    await import_subscription_data(entity_index_id_map, source_index_id_map)
    await import_system_setting_data()
    logger.info('All v1 core data import finished')


if __name__ == '__main__':
    nonebot.init(log_level='INFO')

    asyncio.run(main())
