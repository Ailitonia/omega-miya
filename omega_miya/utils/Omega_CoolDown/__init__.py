from nonebot import get_plugin, get_driver, logger
from nonebot.adapters.cqhttp import MessageSegment, Message
from nonebot.exception import IgnoredException
from nonebot.message import run_preprocessor
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from omega_miya.utils.Omega_plugin_utils import \
    check_and_set_global_cool_down, check_and_set_plugin_cool_down, \
    check_and_set_group_cool_down, check_and_set_user_cool_down
from omega_miya.utils.Omega_Base import DBCoolDownEvent


@run_preprocessor
async def handle_plugin_cooldown(matcher: Matcher, bot: Bot, event: Event, state: T_State):
    group_id = event.dict().get('group_id')
    user_id = event.dict().get('user_id')

    global_config = get_driver().config
    superusers = global_config.superusers

    # 忽略超级用户
    if user_id in [int(x) for x in superusers]:
        return

    # 只处理message事件
    if matcher.type != 'message':
        return

    # 处理插件冷却
    # 冷却处理优先级: 全局>插件>群组>用户
    # 冷却限制优先级: 用户>群组>插件>全局
    plugin_name = matcher.module
    plugin = get_plugin(plugin_name)
    plugin_cool_down_list = plugin.export.get('cool_down')

    # 只有声明了__plugin_cool_down__的插件才检查冷却
    if not plugin_cool_down_list:
        return

    # 检查冷却情况
    global_check = DBCoolDownEvent.check_global_cool_down_event()
    plugin_check = DBCoolDownEvent.check_plugin_cool_down_event(plugin=plugin_name)
    group_check = DBCoolDownEvent.check_group_cool_down_event(plugin=plugin_name, group_id=group_id)
    user_check = DBCoolDownEvent.check_user_cool_down_event(plugin=plugin_name, user_id=user_id)

    # 处理全局冷却
    # 先检查是否已有全局冷却
    if plugin_check.result == 1 or group_check.result == 1 or user_check.result == 1:
        pass
    elif global_check.result == 1:
        await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{global_check.info}'))
        raise IgnoredException('全局命令冷却中')
    elif global_check.result == 0:
        pass
    else:
        logger.error(f'全局冷却事件异常! group: {group_id}, user: {user_id}, error: {global_check.info}')
    # 然后再处理命令中存在的全局冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == 'global']:
        # 若有插件、群组或用户冷却则交由其处理
        if plugin_check.result == 1 or group_check.result == 1 or user_check.result == 1:
            break

        res = check_and_set_global_cool_down(minutes=time)
        if res.result == 1:
            await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{res.info}'))
            raise IgnoredException('全局命令冷却中')
        elif res.result == 0:
            pass
        else:
            logger.error(f'全局冷却事件异常! group: {group_id}, user: {user_id}, error: {res.info}')

    # 处理插件冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == 'plugin']:
        # 若有群组或用户冷却则交由其处理
        if group_check.result == 1 or user_check.result == 1:
            break

        res = check_and_set_plugin_cool_down(minutes=time, plugin=plugin_name)
        if res.result == 1:
            await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{res.info}'))
            raise IgnoredException('插件命令冷却中')
        elif res.result == 0:
            pass
        else:
            logger.error(f'插件冷却事件异常! group: {group_id}, user: {user_id}, plugin: {plugin_name}, error: {res.info}')

    # 处理群组冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == 'group']:
        if not group_id:
            break

        # 若有用户冷却则交由其处理
        if user_check.result == 1:
            break

        res = check_and_set_group_cool_down(minutes=time, plugin=plugin_name, group_id=group_id)
        if res.result == 1:
            await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{res.info}'))
            raise IgnoredException('群组命令冷却中')
        elif res.result == 0:
            pass
        else:
            logger.error(f'群组冷却事件异常! group: {group_id}, user: {user_id}, plugin: {plugin_name}, error: {res.info}')

    # 处理用户冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == 'user']:
        if not user_id:
            break

        res = check_and_set_user_cool_down(minutes=time, plugin=plugin_name, user_id=user_id)
        if res.result == 1:
            await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{res.info}'))
            raise IgnoredException('用户命令冷却中')
        elif res.result == 0:
            pass
        else:
            logger.error(f'用户冷却事件异常! group: {group_id}, user: {user_id}, plugin: {plugin_name}, error: {res.info}')
