"""
@Author         : Ailitonia
@Date           : 2021/06/09 19:10
@FileName       : __init__.py
@Project        : nonebot2_miya 
@Description    : 好友邀请与群组邀请管理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
import string
from typing import Dict
from nonebot import on_request, on_command, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, FriendRequestEvent, GroupRequestEvent
from omega_miya.database import DBBot
from omega_miya.utils.omega_plugin_utils import init_export, MessageDecoder, PermissionChecker


# 为好友请求分配验证码
FRIEND_ADD_VERIFY_CODE: Dict[int, str] = {}


# Custom plugin usage text
__plugin_custom_name__ = '好友和群组请求管理'
__plugin_usage__ = r'''【Omega 好友和群组请求管理】
处理加好友请求和加群、退群请求

以下命令均需要@机器人
**Usage**
**SuperUser Only**
/好友验证'''


# 声明本插件额外可配置的权限节点
__plugin_auth_node__ = [
    'allow_invite_group'
]


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
generate_verify_code = on_command('FriendVerifyCode', rule=to_me(), aliases={'加好友', '好友验证'},
                                  permission=SUPERUSER, priority=10, block=True)


# 修改默认参数处理
@generate_verify_code.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).lower().strip()
    if not args:
        await generate_verify_code.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await generate_verify_code.finish('操作已取消')


@generate_verify_code.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    all_at_qq = MessageDecoder(message=event.get_message()).get_all_at_qq()
    if len(all_at_qq) == 1:
        state['user_id'] = all_at_qq[0]
    elif len(all_at_qq) > 1:
        await generate_verify_code.finish('每次只能为一个用户生成验证码QAQ')


@generate_verify_code.got('user_id', prompt='请发送你想要生成验证码的用户qq号:')
async def handle_verify_code(bot: Bot, event: MessageEvent, state: T_State):
    try:
        user_id = int(state['user_id'])
    except ValueError:
        await generate_verify_code.finish('输入的不是合法的qq号QAQ')
        return

    global FRIEND_ADD_VERIFY_CODE
    verify_code = ''.join(random.sample(string.ascii_letters, k=6))
    FRIEND_ADD_VERIFY_CODE.update({user_id: verify_code})
    await generate_verify_code.finish(f'已为用户: {user_id} 生成好友验证码: {verify_code}')


# 注册事件响应器
add_and_invite_request = on_request(priority=100)


# 处理加好友申请
@add_and_invite_request.handle()
async def handle_friend_request(bot: Bot, event: FriendRequestEvent, state: T_State):
    global FRIEND_ADD_VERIFY_CODE
    user_id = event.user_id
    comment = event.comment

    # 加好友验证消息
    try:
        verify_code = FRIEND_ADD_VERIFY_CODE.pop(user_id)
    except KeyError:
        await bot.set_friend_add_request(flag=event.flag, approve=False)
        logger.warning(f'已拒绝用户: {user_id} 的好友申请, 该用户没有生成有效的验证码')
        return

    if verify_code == comment:
        await bot.set_friend_add_request(flag=event.flag, approve=True)
        logger.info(f'已同意用户: {user_id} 的好友申请, 验证通过')
    else:
        await bot.set_friend_add_request(flag=event.flag, approve=False)
        logger.warning(f'已拒绝用户: {user_id} 的好友申请, 验证码验证失败')


# 处理被邀请进群
@add_and_invite_request.handle()
async def handle_group_invite(bot: Bot, event: GroupRequestEvent, state: T_State):
    self_id = event.self_id
    user_id = event.user_id
    group_id = event.group_id
    sub_type = event.sub_type
    detail_type = event.request_type
    if detail_type == 'group' and sub_type == 'invite':
        # 只有具备相应权限节点的用户才可以邀请bot进入群组
        permission_check_result = await PermissionChecker(self_bot=DBBot(self_qq=self_id)).check_auth_node(
            auth_id=user_id, auth_type='user', auth_node='omega_invite_manager.allow_invite_group'
        )
        if permission_check_result == 1:
            await bot.set_group_add_request(flag=event.flag, sub_type='invite', approve=True)
            logger.info(f'已处理邀请进群请求, 被用户: {user_id} 邀请加入群组: {group_id}.')
        else:
            await bot.set_group_add_request(flag=event.flag, sub_type='invite', approve=False, reason='没有邀请权限')
            logger.warning(f'已拒绝邀请进群请求, 非授权用户: {user_id} 试图邀请加入群组: {group_id}.')
