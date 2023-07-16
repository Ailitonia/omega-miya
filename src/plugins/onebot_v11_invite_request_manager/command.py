"""
@Author         : Ailitonia
@Date           : 2021/06/09 19:10
@FileName       : command.py
@Project        : nonebot2_miya 
@Description    : 好友与群组邀请管理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
import string
from typing import Annotated

from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, CommandArg
from nonebot.plugin import on_command, on_request
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State

from nonebot.adapters.onebot.v11 import Bot, Message, FriendRequestEvent, GroupRequestEvent

from src.service import enable_processor_state


_FRIEND_ADD_VERIFY_CODE: dict[str, str] = {}
"""为好友请求分配的验证码"""


async def handle_parse_user_qq(_: Bot, state: T_State, cmd_arg: Annotated[Message, CommandArg()]):
    """首次运行时解析用户 qq 号作为命令参数"""
    user_qq = cmd_arg.extract_plain_text().strip()
    if user_qq and user_qq.isdigit():
        state.update({'user_qq': user_qq})


@on_command(
    'friend_verify_code',
    rule=to_me(),
    aliases={'好友验证码'},
    permission=SUPERUSER,
    handlers=[handle_parse_user_qq],
    priority=10,
    block=True,
    state=enable_processor_state(name='OneBotV11FriendVerifyCode', enable_processor=False)
).got('user_qq', prompt='请发送需要生成好友验证码的用户QQ号:')
async def handle_user_verify_code(_: Bot, matcher: Matcher, user_qq: Annotated[str, ArgStr('user_qq')]):
    user_qq = user_qq.strip()
    if not user_qq.isdigit():
        await matcher.reject_arg('user_qq', 'qq号应为纯数字, 请重新输入:')

    global _FRIEND_ADD_VERIFY_CODE
    verify_code = ''.join(random.sample(string.ascii_letters, k=6))
    _FRIEND_ADD_VERIFY_CODE.update({user_qq: verify_code})

    logger.success(f'FriendVerifyCode | 已为用户: {user_qq} 生成好友验证码: {verify_code}')
    await matcher.finish(f'已为用户: {user_qq} 生成好友验证码: {verify_code}')


invite_request_manager = on_request(
    priority=91,
    block=False,
    state=enable_processor_state(name='OneBotV11InviteRequestManager', enable_processor=False)
)


@invite_request_manager.handle()
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


@invite_request_manager.handle()
async def handle_group_invite(bot: Bot, event: GroupRequestEvent):
    """处理被邀请进群请求

    检查被邀请进群时邀请人是否具是好友, 若否则尝试退群
    """
    user_id = str(event.user_id)

    if event.request_type == 'group' and event.sub_type == 'invite':
        # 管理员邀请直接通过
        if user_id in bot.config.superusers:
            logger.success(f'AddInviteRequestManager | 处理邀请进群请求, 被管理员: {user_id} 邀请加入群组: {event.group_id}')
            await bot.set_group_add_request(flag=event.flag, sub_type='invite', approve=True)
            return

        # 只有是 Bot 好友的用户才可以邀请bot进入群组
        friend_list = [str(x['user_id']) for x in await bot.get_friend_list()]
        if user_id not in friend_list:
            logger.warning(f'AddInviteRequestManager | 拒绝邀请进群请求, 非好友用户: {user_id} 邀请加入群组: {event.group_id}')
            await bot.set_group_add_request(flag=event.flag, sub_type='invite', approve=False, reason='非好友')
            await bot.set_group_leave(group_id=event.group_id)
            return

        logger.success(f'AddInviteRequestManager | 处理邀请进群请求, 被用户: {user_id} 邀请加入群组: {event.group_id}')
        await bot.set_group_add_request(flag=event.flag, sub_type='invite', approve=True)


__all__ = []
