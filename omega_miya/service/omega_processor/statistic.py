"""
@Author         : Ailitonia
@Date           : 2021/08/14 18:26
@FileName       : statistic.py
@Project        : nonebot2_miya 
@Description    : 插件调用统计
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from nonebot import logger
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.event import Event, MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.bot import Bot

from omega_miya.database import Statistic
from omega_miya.service.omega_processor_tools import parse_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception


_log_prefix: str = '<lc>Statistic</lc> | '


def _generate_call_id(event: Event) -> str:
    """根据 event 生成 call_id"""
    if isinstance(event, GroupMessageEvent):
        call_id = f'group_{event.group_id}'
    elif isinstance(event, MessageEvent):
        call_id = f'user_{event.user_id}'
    else:
        call_id = f'bot_{event.self_id}'
    return call_id


async def postprocessor_statistic(matcher: Matcher, bot: Bot, event: Event):
    """插件统计处理"""

    # 跳过临时会话
    if matcher.temp:
        logger.opt(colors=True).debug(f'{_log_prefix}Temp matcher, ignore')
        return

    # 跳过没有配置自定义名称的(一般来说这样的插件也不用展示统计信息)
    custom_plugin_name = getattr(matcher.plugin.module, '__plugin_custom_name__', None)
    if custom_plugin_name is None:
        logger.opt(colors=True).debug(f'{_log_prefix}Non-custom-name plugin, ignore')
        return

    # 从 state 中解析 processor 配置要求
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({custom_plugin_name}) ignored with disable processor')
        return

    # 跳过不需要 processor 交互的 matcher (一般来说这样的都是后台或响应式的不用展示统计信息)
    if not processor_state.echo_processor_result:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({custom_plugin_name}) ignored with disable echo')
        return

    call_id = _generate_call_id(event=event)
    if isinstance(event, MessageEvent):
        call_info = event.raw_message
    else:
        call_info = event.post_type

    statistic = Statistic(module_name=module_name, plugin_name=custom_plugin_name, bot_self_id=bot.self_id,
                          call_id=call_id, call_time=datetime.now())
    statistic_add_result = await run_async_catching_exception(statistic.add_upgrade_unique_self)(call_info=call_info)

    if isinstance(statistic_add_result, Exception):
        logger.opt(colors=True).error(
            f'{_log_prefix}Add Plugin({custom_plugin_name}) statistic failed with exception, {statistic_add_result}')
    elif statistic_add_result.success:
        logger.opt(colors=True).debug(f'{_log_prefix}Add Plugin({custom_plugin_name}) statistic succeed')
    else:
        logger.opt(colors=True).error(
            f'{_log_prefix}Add Plugin({custom_plugin_name}) statistic failed, error: {statistic_add_result.info}')


__all__ = [
    'postprocessor_statistic'
]
