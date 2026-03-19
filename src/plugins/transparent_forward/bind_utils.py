"""
@Author         : Ailitonia
@Date           : 2026/3/19 16:05
@FileName       : bind_utils
@Project        : omega-miya
@Description    : 绑定工具模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string

from nonebot import get_driver, logger
from nonebot.rule import Rule
from pydantic import BaseModel, ConfigDict

from src.compat import parse_json_as
from src.database import AuthSettingDAL, begin_db_session
from src.params.depends import EVENT_ENTITY_INTERFACE, EVENT_MATCHER_INTERFACE
from src.service import OmegaGlobalCache, scheduler
from .config import transparent_forward_plugin_config
from .consts import (
    TRANSPARENT_FORWARD_CUSTOM_MODULE_NAME,
    TRANSPARENT_FORWARD_CUSTOM_PLUGIN_NAME,
    TRANSPARENT_FORWARD_TARGET_NODE_PREFIX,
    VERIFICATION_CODE_ENTITY_KEY_PREFIX,
)

_VERIFICATION_CODE_CACHE = OmegaGlobalCache(
    cache_name='transparent_forward_plugin_verification_code',
    default_ttl=transparent_forward_plugin_config.transparent_forward_plugin_verification_code_cache_ttl,
)
"""初始化转发验证码全局缓存"""
_BOUND_ENTITY_TID: set[str] = set()
"""已有绑定的 entity tid, 减少数据库查询"""
_BIND_ENTITY_INDEX_MAP: dict[int, set[int]] = {}
"""转发绑定会话 id 缓存, source_entity_index_id -> [target_entity_index_id]"""


class ForwardSetting(BaseModel):
    source_entity_tid: str
    target_entity_index_id: int
    target_entity_tid: str
    target_entity_name: str | None = None

    model_config = ConfigDict(extra='ignore')


class EventHasForwardTarget:
    """检查当前事件是否有配置有转发目标(在已绑定的 entity tid 缓存中)"""

    __slots__ = ()

    async def __call__(self, entity_interface: EVENT_ENTITY_INTERFACE) -> bool:
        return entity_interface.entity.tid in _BOUND_ENTITY_TID  # caught NoResultFound exception


def event_has_forward_target_setting() -> Rule:
    """匹配已配置有转发目标的会话"""

    return Rule(EventHasForwardTarget())


@scheduler.scheduled_job(
    'cron',
    minute='*/15',
    second='13',
    id='transparent_forward_plugin_sync_cache',
    coalesce=True,
)
@get_driver().on_startup
async def _sync_transparent_forward_plugin_cache() -> None:
    """同步验证码缓存"""
    try:
        await _VERIFICATION_CODE_CACHE.sync_internal()
        await _update_bind_entity_index_map()
        logger.opt(colors=True).success('<lc>TransparentForward</lc> | <lg>缓存同步成功</lg>')
    except Exception as e:
        logger.opt(colors=True).error(f'<lc>TransparentForward</lc> | <r>缓存同步失败</r>, {e}')


async def generate_bind_verification_code(interface: 'EVENT_MATCHER_INTERFACE') -> str:
    """为当前会话生成转发绑定验证码"""
    verification_code = ''.join(random.sample(string.ascii_letters, k=6))
    entity = await interface.entity.query_entity_self()
    entity_key = f'{VERIFICATION_CODE_ENTITY_KEY_PREFIX}{entity.id}'
    await _VERIFICATION_CODE_CACHE.save(verification_code, entity_key)
    return verification_code


async def query_verification_code_bind_entity_index_id(code: str) -> int | None:
    """根据验证码反查待绑定的会话 index id"""
    entity_key = await _VERIFICATION_CODE_CACHE.load(code)

    # 查询成功后使验证码立即过期失效
    if entity_key is not None:
        await _VERIFICATION_CODE_CACHE.save(
            key=code,
            value='',
            ttl_delta=-transparent_forward_plugin_config.transparent_forward_plugin_verification_code_cache_ttl * 2,
        )

    return int(entity_key.removeprefix(VERIFICATION_CODE_ENTITY_KEY_PREFIX)) if entity_key else None


async def _update_bind_entity_index_map() -> None:
    """更新绑定会话 id 缓存"""
    async with begin_db_session() as session:
        all_bind_entity_maps = await AuthSettingDAL(session=session).query_module_plugin_all(
            module=TRANSPARENT_FORWARD_CUSTOM_MODULE_NAME,
            plugin=TRANSPARENT_FORWARD_CUSTOM_PLUGIN_NAME,
        )
        new_bind_entity_index_map: dict[int, set[int]] = {}
        _BOUND_ENTITY_TID.clear()
        for x in all_bind_entity_maps:
            if x.node.startswith(TRANSPARENT_FORWARD_TARGET_NODE_PREFIX) and x.available == 1 and x.value:
                forward_setting = parse_json_as(ForwardSetting, x.value)
                if x.entity_index_id in new_bind_entity_index_map:
                    new_bind_entity_index_map[x.entity_index_id].add(forward_setting.target_entity_index_id)
                else:
                    new_bind_entity_index_map[x.entity_index_id] = {forward_setting.target_entity_index_id}
                _BOUND_ENTITY_TID.add(forward_setting.source_entity_tid)

        _BIND_ENTITY_INDEX_MAP.clear()
        _BIND_ENTITY_INDEX_MAP.update(new_bind_entity_index_map)


async def bind_forward_entity(
        source_entity: 'EVENT_ENTITY_INTERFACE',
        target_entity_index_id: int,
        target_entity_tid: str,
        target_entity_name: str | None = None,
) -> None:
    """绑定转发对象"""
    await source_entity.entity.set_auth_setting(
        module=TRANSPARENT_FORWARD_CUSTOM_MODULE_NAME,
        plugin=TRANSPARENT_FORWARD_CUSTOM_PLUGIN_NAME,
        node=f'{TRANSPARENT_FORWARD_TARGET_NODE_PREFIX}{target_entity_index_id}',
        available=1,
        value=ForwardSetting(
            source_entity_tid=source_entity.entity.tid,
            target_entity_index_id=target_entity_index_id,
            target_entity_tid=target_entity_tid,
            target_entity_name=target_entity_name,
        ).model_dump_json()
    )

    # 立即提交并刷新缓存
    await source_entity.entity.commit_session()
    await _update_bind_entity_index_map()


async def unbind_forward_entity(source_entity: 'EVENT_MATCHER_INTERFACE', target_entity_index_id: int) -> None:
    """取消绑定转发对象"""
    await source_entity.entity.set_auth_setting(
        module=TRANSPARENT_FORWARD_CUSTOM_MODULE_NAME,
        plugin=TRANSPARENT_FORWARD_CUSTOM_PLUGIN_NAME,
        node=f'{TRANSPARENT_FORWARD_TARGET_NODE_PREFIX}{target_entity_index_id}',
        available=0,
    )

    # 立即提交并刷新缓存
    await source_entity.entity.commit_session()
    await _update_bind_entity_index_map()


async def query_bound_target_entities(source_entity: 'EVENT_MATCHER_INTERFACE') -> dict[int, str]:
    """查询源会话已绑定的转发目标会话"""
    result = await source_entity.entity.query_plugin_all_auth_setting(
        module=TRANSPARENT_FORWARD_CUSTOM_MODULE_NAME,
        plugin=TRANSPARENT_FORWARD_CUSTOM_PLUGIN_NAME,
    )
    return {
        (setting := parse_json_as(ForwardSetting, x.value)).target_entity_index_id:
            (setting.target_entity_name or setting.target_entity_tid)
        for x in result
        if x.node.startswith(TRANSPARENT_FORWARD_TARGET_NODE_PREFIX) and x.available == 1 and x.value
    }


def query_bound_target_entity_index_ids(source_entity_index_id: int) -> set[int]:
    """查询缓存已绑定的转发对象 entity index id"""
    return _BIND_ENTITY_INDEX_MAP.get(source_entity_index_id, set())


__all__ = [
    'generate_bind_verification_code',
    'query_verification_code_bind_entity_index_id',
    'bind_forward_entity',
    'unbind_forward_entity',
    'query_bound_target_entities',
    'query_bound_target_entity_index_ids',
    'event_has_forward_target_setting',
]
