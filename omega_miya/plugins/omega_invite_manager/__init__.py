"""
@Author         : Ailitonia
@Date           : 2021/06/09 19:10
@FileName       : omega_invite_manager.py
@Project        : nonebot2_miya 
@Description    : 好友与群组邀请管理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
import string
from nonebot import on_request, on_command, logger
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import FriendRequestEvent, GroupRequestEvent
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import InternalBotUser
from omega_miya.service import init_processor_state
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.message_tools import MessageTools


# Custom plugin usage text
__plugin_custom_name__ = '好友和群组请求管理'
__plugin_usage__ = r'''【OmegaInviteManager 好友和群组请求管理插件】
处理加好友请求和加群、退群请求

用法:
/好友验证码 [用户qq]
/允许邀请进群 [用户qq]
/禁止邀请进群 [用户qq]

说明:
以上命令均只允许管理员使用,
"好友验证码"命令会为指定用户生成一段验证码, 该用户在验证消息中输入该验证码可让 bot 通过好友验证
"允许邀请进群"命令会为指定用户分配邀请 bot 进群的权限, 若该用户是 bot 的好友且具备该权限, 则 bot 会自动同意用户的邀请进群请求
"禁止邀请进群"命令会移除指定用户的邀请 bot 进群的权限, 若 bot 被无该权限的用户邀请进群, 则会自动退群'''


_FRIEND_ADD_VERIFY_CODE: dict[str, str] = {}
"""为好友请求分配的验证码"""
_ALLOW_INVITE_GROUP_PERMISSION: str = 'allow_invite_into_group'
"""允许邀请 bot 加群的权限节点名称"""


async def handle_parse_user_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析用户 qq 作为命令参数"""
    user_id = cmd_arg.extract_plain_text().strip()
    if user_id:
        state.update({'user_id': user_id})

    at_list = MessageTools(message=cmd_arg).get_all_at_qq()
    if at_list:
        state.update({'user_id': str(at_list[0])})


friend_verify_code = on_command(
    'FriendVerifyCode',
    rule=to_me(),
    state=init_processor_state(name='FriendVerifyCode', enable_processor=False),
    aliases={'好友验证码'},
    permission=SUPERUSER,
    priority=10,
    block=True
)
friend_verify_code.handle()(handle_parse_user_id)


@friend_verify_code.got('user_id', prompt='请发送你想要生成验证码的用户qq号:')
async def handle_user_verify_code(user_id: str = ArgStr('user_id')):
    user_id = user_id.strip()
    if not user_id.isdigit():
        await friend_verify_code.reject('qq号应为纯数字, 请重新输入:')

    global _FRIEND_ADD_VERIFY_CODE
    verify_code = ''.join(random.sample(string.ascii_letters, k=6))
    _FRIEND_ADD_VERIFY_CODE.update({user_id: verify_code})
    logger.success(f'FriendVerifyCode | 已为用户: {user_id} 生成好友验证码: {verify_code}')
    await friend_verify_code.finish(f'已为用户: {user_id} 生成好友验证码: {verify_code}')


allow_invite_group = on_command(
    'AllowInviteGroup',
    rule=to_me(),
    state=init_processor_state(name='AllowInviteGroup', enable_processor=False),
    aliases={'允许邀请进群'},
    permission=SUPERUSER,
    priority=10,
    block=True
)
allow_invite_group.handle()(handle_parse_user_id)


@allow_invite_group.got('user_id', prompt='请发送允许邀请进群的用户qq号:')
async def handle_allow_user_invite(bot: Bot, matcher: Matcher, user_id: str = ArgStr('user_id')):
    user_id = user_id.strip()
    if not user_id.isdigit():
        await matcher.reject('qq号应为纯数字, 请重新输入:')

    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    user = InternalBotUser(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=user_id)
    permission_result = await run_async_catching_exception(user.set_auth_setting)(
        module=module_name, plugin=plugin_name, node=_ALLOW_INVITE_GROUP_PERMISSION, available=1)

    if isinstance(permission_result, Exception) or permission_result.error:
        logger.error(f'AllowInviteGroup | 为用户: {user_id} 配置邀请权限失败, {permission_result}')
        await matcher.finish(f'为用户: {user_id} 配置邀请权限失败, 详情请查看日志')
    else:
        logger.success(f'AllowInviteGroup | 为用户: {user_id} 配置邀请权限成功')
        await matcher.finish(f'为用户: {user_id} 配置邀请权限成功')


deny_invite_group = on_command(
    'DenyInviteGroup',
    rule=to_me(),
    state=init_processor_state(name='DenyInviteGroup', enable_processor=False),
    aliases={'禁止邀请进群'},
    permission=SUPERUSER,
    priority=10,
    block=True
)
deny_invite_group.handle()(handle_parse_user_id)


@deny_invite_group.got('user_id', prompt='请发送禁止邀请进群的用户qq号:')
async def handle_allow_user_invite(bot: Bot, matcher: Matcher, user_id: str = ArgStr('user_id')):
    user_id = user_id.strip()
    if not user_id.isdigit():
        await matcher.reject('qq号应为纯数字, 请重新输入:')

    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    user = InternalBotUser(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=user_id)
    permission_result = await run_async_catching_exception(user.set_auth_setting)(
        module=module_name, plugin=plugin_name, node=_ALLOW_INVITE_GROUP_PERMISSION, available=0)

    if isinstance(permission_result, Exception) or permission_result.error:
        logger.error(f'AllowInviteGroup | 为用户: {user_id} 配置邀请权限失败, {permission_result}')
        await matcher.finish(f'移除用户: {user_id} 邀请权限失败, 详情请查看日志')
    else:
        logger.success(f'AllowInviteGroup | 为用户: {user_id} 配置邀请权限成功')
        await matcher.finish(f'移除用户: {user_id} 邀请权限成功')


add_invite_request_manager = on_request(
    state=init_processor_state(name='AddInviteRequestManager', enable_processor=False),
    priority=90,
    block=False
)


@add_invite_request_manager.handle()
async def handle_friend_request(bot: Bot, event: FriendRequestEvent):
    """处理加好友申请"""
    global _FRIEND_ADD_VERIFY_CODE
    user_id = str(event.user_id)
    comment = event.comment

    # 加好友验证消息
    try:
        verify_code = _FRIEND_ADD_VERIFY_CODE.pop(user_id)
    except KeyError:
        logger.warning(f'AddInviteRequestManager | 拒绝用户: {user_id} 的好友申请, 该用户没有生成有效的验证码')
        await bot.set_friend_add_request(flag=event.flag, approve=False)
        return

    if verify_code == comment:
        logger.success(f'AddInviteRequestManager | 同意用户: {user_id} 的好友申请, 验证通过')
        await bot.set_friend_add_request(flag=event.flag, approve=True)
    else:
        logger.warning(f'AddInviteRequestManager | 拒绝用户: {user_id} 的好友申请, 验证码验证失败')
        await bot.set_friend_add_request(flag=event.flag, approve=False)


@add_invite_request_manager.handle()
async def handle_group_invite(bot: Bot, event: GroupRequestEvent, matcher: Matcher):
    """处理被邀请进群请求

    在小群、好友等情况下邀请进群是不需要同意的, 这里检查被邀请进群时邀请人是否具有相应的权限, 若无权限则尝试退群
    """
    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name

    user_id = str(event.user_id)
    group_id = str(event.group_id)

    sub_type = event.sub_type
    request_type = event.request_type
    gocq_bot = GoCqhttpBot(bot=bot)

    if request_type == 'group' and sub_type == 'invite':
        # 管理员邀请直接通过
        if user_id in bot.config.superusers:
            logger.success(f'AddInviteRequestManager | 处理邀请进群请求, 被管理员: {user_id} 邀请加入群组: {group_id}')
            await run_async_catching_exception(gocq_bot.set_group_add_request)(
                flag=event.flag, sub_type='invite', approve=True)
            return

        # 只有是 bot 好友且具备相应权限节点的用户才可以邀请bot进入群组
        is_friend = await run_async_catching_exception(gocq_bot.is_friend)(user_id=user_id)
        if isinstance(is_friend, Exception) or not is_friend:
            logger.warning(f'AddInviteRequestManager | 拒绝邀请进群请求, 非好友用户: {user_id} 试图邀请加入群组: {group_id}')
            await run_async_catching_exception(gocq_bot.set_group_add_request)(
                flag=event.flag, sub_type='invite', approve=False, reason='非好友')
            await run_async_catching_exception(gocq_bot.set_group_leave)(group_id=group_id)
            return

        user = InternalBotUser(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=user_id)
        permission_result = await run_async_catching_exception(user.check_auth_setting)(
            module=module_name, plugin=plugin_name, node=_ALLOW_INVITE_GROUP_PERMISSION)

        if isinstance(permission_result, Exception) or not permission_result:
            logger.warning(f'AddInviteRequestManager | 拒绝邀请进群请求, 非授权用户: {user_id} 试图邀请加入群组: {group_id}')
            await run_async_catching_exception(gocq_bot.set_group_add_request)(
                flag=event.flag, sub_type='invite', approve=False, reason='没有邀请权限')
            await run_async_catching_exception(gocq_bot.set_group_leave)(group_id=group_id)
        else:
            logger.success(f'AddInviteRequestManager | 处理邀请进群请求, 被用户: {user_id} 邀请加入群组: {group_id}')
            await run_async_catching_exception(gocq_bot.set_group_add_request)(
                flag=event.flag, sub_type='invite', approve=True)
