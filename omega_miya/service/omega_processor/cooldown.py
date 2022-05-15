"""
@Author         : Ailitonia
@Date           : 2021/08/28 20:33
@FileName       : cooldown.py
@Project        : nonebot2_miya
@Description    : 插件命令冷却系统
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime, timedelta
from pydantic import BaseModel
from nonebot import get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from omega_miya.service.omega_processor_tools import parse_processor_state
from omega_miya.database import InternalBotUser, InternalBotGroup
from omega_miya.utils.process_utils import run_async_catching_exception


global_config = get_driver().config
SUPERUSERS = global_config.superusers


_cooldown_event_prefix: str = 'plugin_cd_'
_log_prefix: str = '<lc>CooldownPreprocessor</lc> | '


async def preprocessor_cooldown(matcher: Matcher, bot: Bot, event: MessageEvent):
    """冷却处理"""

    # 跳过由 got 等事件处理函数创建临时 matcher 避免冷却在命令交互中被不正常触发
    if matcher.temp:
        return

    # 从 state 中解析已配置的冷却要求
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name}) ignored with disable processor')
        return

    # 跳过声明无冷却时间的
    if processor_state.cool_down <= 0:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name}) ignored with non-cooldown')
        return

    group_id = getattr(event, 'group_id', None)
    user_id = event.user_id

    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name}) ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    cd_skip_tag: bool = False
    cd_expired_tag: bool = True
    cd_expired_time: datetime = datetime.now()
    cooldown_event = f'{_cooldown_event_prefix}{plugin_name}_{processor_state.name}'

    # 检查用户冷却
    user_cd_check_result = await _check_user_cooldown(
        user_id=str(user_id), bot_self_id=bot.self_id, cooldown_event=cooldown_event,
        cooldown_time=int(processor_state.cool_down * processor_state.user_cool_down_override),
        plugin_name=plugin_name, module_name=module_name, add_user_name=event.sender.nickname
    )
    if not isinstance(user_cd_check_result, Exception):
        cd_skip_tag = True if user_cd_check_result.allow_skip is True else cd_skip_tag
        if not user_cd_check_result.is_expired:
            cd_expired_tag = user_cd_check_result.is_expired
            cd_expired_time = user_cd_check_result.expired_time

    # 检查群组冷却
    if group_id is not None:
        group_cd_check_result = await _check_group_cooldown(
            group_id=str(group_id), bot_self_id=bot.self_id, cooldown_event=cooldown_event,
            cooldown_time=processor_state.cool_down, plugin_name=plugin_name, module_name=module_name
        )
        if not isinstance(group_cd_check_result, Exception):
            cd_skip_tag = True if group_cd_check_result.allow_skip is True else cd_skip_tag
            if not group_cd_check_result.is_expired:
                cd_expired_tag = group_cd_check_result.is_expired
                cd_expired_time = group_cd_check_result.expired_time

    if cd_skip_tag:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name})/Matcher({processor_state.name}) '
                                      f'<ly>Group({group_id})/User({user_id})</ly> allowed to skip cooldown')
        return
    elif cd_expired_tag:
        logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name})/Matcher({processor_state.name}) '
                                      f'<ly>Group({group_id})/User({user_id})</ly> cooldown expired')
        return
    else:
        logger.opt(colors=True).info(f'{_log_prefix}Plugin({plugin_name})/Matcher({processor_state.name}) '
                                     f'<ly>Group({group_id})/User({user_id})</ly> still in cooldown')
        if processor_state.echo_processor_result:
            echo_message = f'冷却中, 请稍后再试!\n冷却结束时间: {cd_expired_time.strftime("%Y/%m/%d %H:%M:%S")}'
            await run_async_catching_exception(bot.send)(event=event, message=echo_message, at_sender=True)
        raise IgnoredException('冷却中')


class _CooldownCheckingResult(BaseModel):
    """冷却检查结果"""
    expired_time: datetime
    is_expired: bool
    allow_skip: bool


@run_async_catching_exception
async def _check_user_cooldown(
        user_id: str,
        bot_self_id: str,
        cooldown_event: str,
        cooldown_time: int,
        plugin_name: str,
        module_name: str,
        *,
        add_user_name: str = ''
) -> _CooldownCheckingResult:
    """检查用户冷却, 若用户不存在则在数据库中初始化用户 Entity"""
    user = InternalBotUser(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=str(user_id))
    cd_expired_tag = True
    cd_expired_time = datetime.now()

    try:
        # 先检查是否有跳过冷却权限
        skip_cd = await user.check_permission_skip_cooldown(module=module_name, plugin=plugin_name)
        if skip_cd:
            logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name}) skip with User({user_id}) permission')
            return _CooldownCheckingResult(expired_time=cd_expired_time, is_expired=cd_expired_tag, allow_skip=True)

        # 处理冷却
        global_cd_expired, global_cd_expired_time = await user.check_global_cooldown_expired()
        event_cd_expired, event_cd_expired_time = await user.check_cool_down_expired(cool_down_event=cooldown_event)
        if not global_cd_expired:
            cd_expired_tag = global_cd_expired
            cd_expired_time = global_cd_expired_time
        if not event_cd_expired:
            cd_expired_tag = event_cd_expired
            cd_expired_time = event_cd_expired_time

    except Exception as e:
        logger.opt(colors=True).debug(
            f'{_log_prefix}Plugin({plugin_name}) check User({user_id}) cooldown failed, {e}')
        add_user = await user.add_only(entity_name=add_user_name, related_entity_name=add_user_name)
        if add_user.success:
            logger.opt(colors=True).debug(f'{_log_prefix}Add and init User({user_id}) succeed')
        else:
            logger.opt(colors=True).debug(f'{_log_prefix}Add User({user_id}) failed, {add_user.info}')

    # 没有冷却的话就要新增冷却
    if cd_expired_tag:
        try:
            add_cd_result = await user.set_cool_down(cool_down_event=cooldown_event,
                                                     expired_time=timedelta(seconds=cooldown_time))
            if add_cd_result.success:
                logger.opt(colors=True).debug(
                    f'{_log_prefix}Refresh User({user_id}) Cooldown({cooldown_event}) succeed')
            else:
                logger.opt(colors=True).error(
                    f'{_log_prefix}Refresh User({user_id}) Cooldown({cooldown_event}) failed, {add_cd_result.info}')
        except Exception as e:
            logger.opt(colors=True).error(
                f'{_log_prefix}Refresh User({user_id}) Cooldown({cooldown_event}) failed, {e}')

    return _CooldownCheckingResult(expired_time=cd_expired_time, is_expired=cd_expired_tag, allow_skip=False)


@run_async_catching_exception
async def _check_group_cooldown(
        group_id: str,
        bot_self_id: str,
        cooldown_event: str,
        cooldown_time: int,
        plugin_name: str,
        module_name: str,
        *,
        add_group_name: str = ''
) -> _CooldownCheckingResult:
    """检查用户冷却, 若用户不存在则在数据库中初始化用户 Entity"""
    group = InternalBotGroup(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=str(group_id))
    cd_expired_tag = True
    cd_expired_time = datetime.now()

    try:
        # 先检查是否有跳过冷却权限
        skip_cd = await group.check_permission_skip_cooldown(module=module_name, plugin=plugin_name)
        if skip_cd:
            logger.opt(colors=True).debug(f'{_log_prefix}Plugin({plugin_name}) skip with Group({group_id}) permission')
            return _CooldownCheckingResult(expired_time=cd_expired_time, is_expired=cd_expired_tag, allow_skip=True)

        # 处理冷却
        global_cd_expired, global_cd_expired_time = await group.check_global_cooldown_expired()
        event_cd_expired, event_cd_expired_time = await group.check_cool_down_expired(cool_down_event=cooldown_event)
        if not global_cd_expired:
            cd_expired_tag = global_cd_expired
            cd_expired_time = global_cd_expired_time
        if not event_cd_expired:
            cd_expired_tag = event_cd_expired
            cd_expired_time = event_cd_expired_time

    except Exception as e:
        logger.opt(colors=True).debug(
            f'{_log_prefix}Plugin({plugin_name}) check Group({group_id}) cooldown failed, {e}')
        add_group = await group.add_only(entity_name=add_group_name, related_entity_name=add_group_name)
        if add_group.success:
            logger.opt(colors=True).debug(f'{_log_prefix}Add and init Group({group_id}) succeed')
        else:
            logger.opt(colors=True).error(f'{_log_prefix}Add Group({group_id}) failed, {add_group.info}')

    # 没有冷却的话就要新增冷却
    if cd_expired_tag:
        try:
            add_cd_result = await group.set_cool_down(cool_down_event=cooldown_event,
                                                      expired_time=timedelta(seconds=cooldown_time))
            if add_cd_result.success:
                logger.opt(colors=True).debug(
                    f'{_log_prefix}Refresh Group({group_id}) Cooldown({cooldown_event}) succeed')
            else:
                logger.opt(colors=True).error(
                    f'{_log_prefix}Refresh Group({group_id}) Cooldown({cooldown_event}) failed, {add_cd_result.info}')
        except Exception as e:
            logger.opt(colors=True).error(
                f'{_log_prefix}Refresh Group({group_id}) Cooldown({cooldown_event}) failed, {e}')

    return _CooldownCheckingResult(expired_time=cd_expired_time, is_expired=cd_expired_tag, allow_skip=False)


__all__ = [
    'preprocessor_cooldown'
]
