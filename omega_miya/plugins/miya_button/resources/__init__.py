from typing import Literal
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent

from omega_miya.result import BoolResult
from omega_miya.database import InternalBotGroup
from omega_miya.utils.process_utils import run_async_catching_exception


from .model import Voice
from .miya_voice import miya_voices


_VOICE_RESOURCE_NODE: Literal['miya_button_resource'] = 'miya_button_resource'
"""配置按钮语音资源的节点"""
_DEFAULT_VOICE_RESOURCE: Voice = miya_voices
"""默认的按钮资源"""
_INTERNAL_VOICE_RESOURCE: dict[str, Voice] = {
    'Miya按钮': miya_voices
}


def get_voice_resource(resource_name: str | None = None) -> Voice:
    if resource_name is None:
        return _DEFAULT_VOICE_RESOURCE
    return _INTERNAL_VOICE_RESOURCE.get(resource_name, _DEFAULT_VOICE_RESOURCE)


def get_available_voice_resource() -> list[str]:
    return [x for x in _INTERNAL_VOICE_RESOURCE.keys()]


@run_async_catching_exception
async def _get_voice_resource_name(bot: Bot, event: GroupMessageEvent, matcher: Matcher) -> str | None:
    """根据当前 event 获取对应按钮资源名"""
    entity = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.group_id))
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    node = await entity.query_auth_setting(module=module_name, plugin=plugin_name, node=_VOICE_RESOURCE_NODE)
    if node is None:
        return None
    elif node.available:
        return node.value
    else:
        return None


async def get_voice_resource_name(bot: Bot, event: GroupMessageEvent, matcher: Matcher) -> str | None:
    """根据当前 event 获取对应对象按钮资源名"""
    result = await _get_voice_resource_name(bot=bot, event=event, matcher=matcher)
    if isinstance(result, Exception):
        result = None
    return result


@run_async_catching_exception
async def set_voice_resource(resource_name: str, bot: Bot, event: GroupMessageEvent, matcher: Matcher) -> BoolResult:
    """根据当前 event 配置对应对象按钮资源"""
    entity = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.group_id))
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    result = await entity.set_auth_setting(module=module_name, plugin=plugin_name, node=_VOICE_RESOURCE_NODE,
                                           available=1, value=resource_name)
    return result


__all__ = [
    'Voice',
    'get_voice_resource',
    'get_available_voice_resource',
    'get_voice_resource_name',
    'set_voice_resource'
]
