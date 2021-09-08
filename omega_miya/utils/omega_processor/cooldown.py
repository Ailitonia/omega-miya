"""
插件命令冷却系统
使用参考例:
plugins/setu
plugin/draw
"""
from nonebot import get_plugin, get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from omega_miya.utils.omega_plugin_utils import PluginCoolDown
from omega_miya.database import DBCoolDownEvent, DBAuth, DBBot


global_config = get_driver().config
SUPERUSERS = global_config.superusers


async def preprocessor_cooldown(matcher: Matcher, bot: Bot, event: MessageEvent, state: T_State):
    """
    冷却处理 T_RunPreProcessor
    """

    group_id = getattr(event, 'group_id', None)
    user_id = event.user_id

    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        return

    # 只处理message事件
    if matcher.type != 'message':
        return

    # 处理插件冷却
    # 冷却处理优先级: 全局>插件>群组>用户
    # 冷却限制优先级: 用户>群组>插件>全局
    plugin_name = matcher.plugin_name
    plugin = get_plugin(plugin_name)
    plugin_cool_down_list = plugin.export.get('cool_down')

    # 只处理声明了__plugin_cool_down__的插件
    if not plugin_cool_down_list:
        return

    # 跳过由 got 等事件处理函数创建临时 matcher 避免冷却在命令交互中被不正常触发
    if matcher.temp:
        return

    # 处理不同bot权限
    self_bot = DBBot(self_qq=int(bot.self_id))

    # 检查用户或群组是否有skip_cd权限, 跳过冷却检查
    skip_cd_auth_node = f'{plugin_name}.{PluginCoolDown.skip_auth_node}'
    user_auth = DBAuth(self_bot=self_bot, auth_id=user_id, auth_type='user', auth_node=skip_cd_auth_node)
    user_tag_res = await user_auth.tags_info()
    if user_tag_res.result[0] == 1 and user_tag_res.result[1] == 0:
        return

    group_auth = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=skip_cd_auth_node)
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
        await bot.send(event=event, message=f'命令冷却中!\n{global_check.info}', at_sender=True)
        raise IgnoredException('全局命令冷却中')
    elif global_check.result in [0, 2]:
        pass
    else:
        logger.error(f'全局冷却事件异常! group: {group_id}, user: {user_id}, error: {global_check.info}')
    # 然后再处理命令中存在的全局冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == PluginCoolDown.global_type]:
        # 若有插件、群组或用户冷却则交由其处理
        if plugin_check.result == 1 or group_check.result == 1 or user_check.result == 1:
            break

        res = await PluginCoolDown.check_and_set_global_cool_down(minutes=time)
        if res.result == 1:
            await bot.send(event=event, message=f'命令冷却中!\n{res.info}', at_sender=True)
            raise IgnoredException('全局命令冷却中')
        elif res.result in [0, 2]:
            pass
        else:
            logger.error(f'全局冷却事件异常! group: {group_id}, user: {user_id}, error: {res.info}')

    # 处理插件冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == PluginCoolDown.plugin_type]:
        # 若有群组或用户冷却则交由其处理
        if group_check.result == 1 or user_check.result == 1:
            break

        res = await PluginCoolDown.check_and_set_plugin_cool_down(minutes=time, plugin=plugin_name)
        if res.result == 1:
            await bot.send(event=event, message=f'命令冷却中!\n{res.info}', at_sender=True)
            raise IgnoredException('插件命令冷却中')
        elif res.result in [0, 2]:
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

        res = await PluginCoolDown.check_and_set_group_cool_down(minutes=time, plugin=plugin_name, group_id=group_id)
        if res.result == 1:
            await bot.send(event=event, message=f'命令冷却中!\n{res.info}', at_sender=True)
            raise IgnoredException('群组命令冷却中')
        elif res.result in [0, 2]:
            pass
        else:
            logger.error(f'群组冷却事件异常! group: {group_id}, user: {user_id}, plugin: {plugin_name}, error: {res.info}')

    # 处理用户冷却
    for time in [x.cool_down_time for x in plugin_cool_down_list if x.type == PluginCoolDown.user_type]:
        if not user_id:
            break

        res = await PluginCoolDown.check_and_set_user_cool_down(minutes=time, plugin=plugin_name, user_id=user_id)
        if res.result == 1:
            await bot.send(event=event, message=f'命令冷却中!\n{res.info}', at_sender=True)
            raise IgnoredException('用户命令冷却中')
        elif res.result in [0, 2]:
            pass
        else:
            logger.error(f'用户冷却事件异常! group: {group_id}, user: {user_id}, plugin: {plugin_name}, error: {res.info}')


__all__ = [
    'preprocessor_cooldown'
]
