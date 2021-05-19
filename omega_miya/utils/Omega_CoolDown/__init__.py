"""
插件命令冷却系统
使用参考例:
plugins/setu
plugin/draw
"""
from nonebot import get_plugin, get_driver, logger
from nonebot.adapters.cqhttp import MessageSegment, Message
from nonebot.exception import IgnoredException
from nonebot.message import run_preprocessor
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from omega_miya.utils.Omega_plugin_utils import \
    check_and_set_global_cool_down, check_and_set_plugin_cool_down, \
    check_and_set_group_cool_down, check_and_set_user_cool_down, PluginCoolDown
from omega_miya.utils.Omega_Base import DBCoolDownEvent, DBAuth


@run_preprocessor
async def handle_plugin_cooldown(matcher: Matcher, bot: Bot, event: MessageEvent, state: T_State):
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

    # 只处理声明了__plugin_cool_down__的插件
    if not plugin_cool_down_list:
        return

    # 跳过由 got 等事件处理函数创建临时 matcher 避免冷却在命令交互中被不正常触发
    if matcher.temp:
        return

    # 检查用户或群组是否有skip_cd权限, 跳过冷却检查
    skip_cd_auth_node = f'{plugin_name}.{PluginCoolDown.skip_auth_node}'
    user_auth = DBAuth(auth_id=user_id, auth_type='user', auth_node=skip_cd_auth_node)
    user_tag_res = await user_auth.tags_info()
    if user_tag_res.result[0] == 1 and user_tag_res.result[1] == 0:
        return

    group_auth = DBAuth(auth_id=group_id, auth_type='group', auth_node=skip_cd_auth_node)
    group_tag_res = await group_auth.tags_info()
    if group_tag_res.result[0] == 1 and group_tag_res.result[1] == 0:
        return

    # 检查冷却情况
    global_check = await DBCoolDownEvent.check_global_cool_down_event()
    plugin_check = await DBCoolDownEvent.check_plugin_cool_down_event(plugin=plugin_name)
    group_check = await DBCoolDownEvent.check_group_cool_down_event(plugin=plugin_name, group_id=group_id)
    user_check = await DBCoolDownEvent.check_user_cool_down_event(plugin=plugin_name, user_id=user_id)

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
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == PluginCoolDown.global_type]:
        # 若有插件、群组或用户冷却则交由其处理
        if plugin_check.result == 1 or group_check.result == 1 or user_check.result == 1:
            break

        res = await check_and_set_global_cool_down(minutes=time)
        if res.result == 1:
            await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{res.info}'))
            raise IgnoredException('全局命令冷却中')
        elif res.result == 0:
            pass
        else:
            logger.error(f'全局冷却事件异常! group: {group_id}, user: {user_id}, error: {res.info}')

    # 处理插件冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == PluginCoolDown.plugin_type]:
        # 若有群组或用户冷却则交由其处理
        if group_check.result == 1 or user_check.result == 1:
            break

        res = await check_and_set_plugin_cool_down(minutes=time, plugin=plugin_name)
        if res.result == 1:
            await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{res.info}'))
            raise IgnoredException('插件命令冷却中')
        elif res.result == 0:
            pass
        else:
            logger.error(f'插件冷却事件异常! group: {group_id}, user: {user_id}, plugin: {plugin_name}, error: {res.info}')

    # 处理群组冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == PluginCoolDown.group_type]:
        if not group_id:
            break

        # 若有用户冷却则交由其处理
        if user_check.result == 1:
            break

        res = await check_and_set_group_cool_down(minutes=time, plugin=plugin_name, group_id=group_id)
        if res.result == 1:
            await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{res.info}'))
            raise IgnoredException('群组命令冷却中')
        elif res.result == 0:
            pass
        else:
            logger.error(f'群组冷却事件异常! group: {group_id}, user: {user_id}, plugin: {plugin_name}, error: {res.info}')

    # 处理用户冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == PluginCoolDown.user_type]:
        if not user_id:
            break

        res = await check_and_set_user_cool_down(minutes=time, plugin=plugin_name, user_id=user_id)
        if res.result == 1:
            await bot.send(event=event, message=Message(f'{MessageSegment.at(user_id=user_id)}命令冷却中!\n{res.info}'))
            raise IgnoredException('用户命令冷却中')
        elif res.result == 0:
            pass
        else:
            logger.error(f'用户冷却事件异常! group: {group_id}, user: {user_id}, plugin: {plugin_name}, error: {res.info}')
