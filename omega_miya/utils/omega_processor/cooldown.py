"""
插件命令冷却系统
使用参考例:
plugins/setu
plugin/draw
"""
from typing import Optional, List
from nonebot import get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from omega_miya.utils.omega_plugin_utils import PluginCoolDown
from omega_miya.database import DBCoolDownEvent, DBAuth, DBBot


global_config = get_driver().config
SUPERUSERS = global_config.superusers

# 是否在用户交互中提示全局冷却状态
# 强烈建议将此选项保持为 False, 以避免非交互类插件触发
NOTICE_GLOBAL_COOLDOWN: bool = False


async def preprocessor_cooldown(matcher: Matcher, bot: Bot, event: MessageEvent, state: T_State):
    """
    冷却处理 T_RunPreProcessor
    处理冷却优先级: 全局用户 > 全局群组 > 插件用户 > 插件群组
    """

    group_id = getattr(event, 'group_id', None)
    user_id = event.user_id

    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        return

    # 获取插件及 matcher 信息
    plugin_name: str = matcher.plugin_name
    matcher_default_state = matcher.state
    matcher_cool_down: Optional[List[PluginCoolDown]] = matcher_default_state.get('_cool_down', None)
    enable_cool_down_check: bool = matcher_default_state.get('_enable_cool_down_check', True)

    # 跳过声明了不处理冷却的 matcher
    if not enable_cool_down_check:
        return

    # 跳过由 got 等事件处理函数创建临时 matcher 避免冷却在命令交互中被不正常触发
    if matcher.temp:
        return

    # 处理全局冷却
    # 设计上只有专用的管理员命令能设置全局冷却, 单插件不允许设置全局冷却, 因此这里只做检验不做更新
    # skip_cd 权限针对插件, 全局冷却优先级高于该权限, 优先处理
    # 检查全局用户冷却
    global_user_check = await DBCoolDownEvent.check_global_user_cool_down_event(user_id=user_id)
    if global_user_check.success() and global_user_check.result == 1:
        if NOTICE_GLOBAL_COOLDOWN:
            await bot.send(event=event, message=f'用户冷却中!\n{global_user_check.info}', at_sender=True)
        logger.info(f'CoolDown | 全局用户冷却中, user: {user_id}, {global_user_check.info}')
        raise IgnoredException('全局用户冷却中')
    elif global_user_check.success() and global_user_check.result in [0, 2]:
        pass
    else:
        logger.error(f'CoolDown | 全局用户冷却事件异常, user: {user_id}, {global_user_check}')

    # 检查全局群组冷却
    if group_id is not None:
        global_group_check = await DBCoolDownEvent.check_global_group_cool_down_event(group_id=group_id)
        if global_group_check.success() and global_group_check.result == 1:
            if NOTICE_GLOBAL_COOLDOWN:
                await bot.send(event=event, message=f'群组冷却中!\n{global_group_check.info}', at_sender=True)
            logger.info(f'CoolDown | 全局群组冷却中, group: {group_id}, {global_group_check.info}')
            raise IgnoredException('全局用户冷却中')
        elif global_group_check.success() and global_group_check.result in [0, 2]:
            pass
        else:
            logger.error(f'CoolDown | 全局群组冷却事件异常, user: {user_id}, {global_group_check}')

    # 处理插件冷却
    # 跳过未声明冷却的 matcher
    if not matcher_cool_down:
        return

    # 检查用户或群组是否有skip_cd权限, 跳过冷却检查, 处理不同bot权限
    self_bot = DBBot(self_qq=int(bot.self_id))
    skip_cd_auth_node = f'{plugin_name}.{PluginCoolDown.skip_auth_node}'

    # 检查用户 skip_cd 权限
    user_auth = DBAuth(self_bot=self_bot, auth_id=user_id, auth_type='user', auth_node=skip_cd_auth_node)
    user_tag_res = await user_auth.tags_info()
    if user_tag_res.result[0] == 1 and user_tag_res.result[1] == 0:
        return

    # 检查群组 skip_cd 权限
    group_auth = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=skip_cd_auth_node)
    group_tag_res = await group_auth.tags_info()
    if group_tag_res.result[0] == 1 and group_tag_res.result[1] == 0:
        return

    # 所有处理的冷却以该类型声明的第一个为准
    user_cool_down_l = [x for x in matcher_cool_down if x.type == PluginCoolDown.user_type]
    user_cool_down = user_cool_down_l[0] if user_cool_down_l else None

    group_cool_down_l = [x for x in matcher_cool_down if x.type == PluginCoolDown.group_type]
    group_cool_down = group_cool_down_l[0] if group_cool_down_l else None

    # 先过一个群组 cd 检查, 避免用户无 cd 而群组有 cd 时还会再给用户加 cd 的情况
    if (group_cool_down is not None) and (group_id is not None):
        check_group_cd = True
        group_cool_down_check = await DBCoolDownEvent.check_group_cool_down_event(plugin=plugin_name, group_id=group_id)
        if group_cool_down_check.success() and group_cool_down_check.result == 1:
            # 群组现在有 cd, 跳过用户的 cd 检查
            check_user_cd = False
        else:
            check_user_cd = True
    else:
        # 无 group_id 或未声明群组冷却则不更新群组冷却
        check_group_cd = False
        check_user_cd = True
    if user_cool_down is None:
        # 没有声明用户冷却的情况
        check_user_cd = False

    # 检查并处理插件用户冷却
    if check_user_cd:
        user_cool_down_result = await PluginCoolDown.check_and_set_user_cool_down(
            plugin=plugin_name, user_id=user_id, seconds=user_cool_down.cool_down_time)
        if user_cool_down_result.success() and user_cool_down_result.result == 1:
            await bot.send(event=event, message=f'该命令正在用户冷却中!\n{user_cool_down_result.info}', at_sender=True)
            raise IgnoredException('插件用户冷却中')
        elif user_cool_down_result.success() and user_cool_down_result.result == 0:
            pass
        else:
            logger.error(f'CoolDown | 插件用户冷却事件异常, user: {user_id}, {user_cool_down_result}')
            pass

    # 检查并处理插件群组冷却
    if check_group_cd:
        group_cool_down_result = await PluginCoolDown.check_and_set_group_cool_down(
            plugin=plugin_name, group_id=group_id, seconds=group_cool_down.cool_down_time)
        if group_cool_down_result.success() and group_cool_down_result.result == 1:
            await bot.send(event=event, message=f'该命令正在群组冷却中!\n{group_cool_down_result.info}', at_sender=True)
            raise IgnoredException('插件群组冷却中')
        elif group_cool_down_result.success() and group_cool_down_result.result == 0:
            pass
        else:
            logger.error(f'CoolDown | 插件群组冷却事件异常, group:{group_id}, {group_cool_down_result}')
            pass


__all__ = [
    'preprocessor_cooldown'
]
