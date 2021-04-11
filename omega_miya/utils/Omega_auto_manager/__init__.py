from nonebot import on_request, on_notice, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import MessageSegment, Message
from nonebot.adapters.cqhttp.event import FriendRequestEvent, GroupRequestEvent, GroupIncreaseNoticeEvent
from omega_miya.utils.Omega_Base import DBGroup

# 注册事件响应器
add_and_invite_request = on_request(priority=100)


# 处理加好友申请
@add_and_invite_request.handle()
async def handle_friend_request(bot: Bot, event: FriendRequestEvent, state: T_State):
    user_id = event.user_id
    detail_type = event.request_type
    comment = event.comment
    if detail_type == 'friend' and comment == 'Miya好萌好可爱':
        await bot.call_api('set_friend_add_request', flag=event.flag, approve=True)
        logger.info(f'已同意用户: {user_id} 的好友申请')
    elif detail_type == 'friend':
        await bot.call_api('set_friend_add_request', flag=event.flag, approve=False)
        logger.info(f'已拒绝用户: {user_id} 的好友申请')


# 处理被邀请进群
@add_and_invite_request.handle()
async def handle_group_invite(bot: Bot, event: GroupRequestEvent, state: T_State):
    user_id = event.user_id
    group_id = event.group_id
    sub_type = event.sub_type
    detail_type = event.request_type
    if detail_type == 'group' and sub_type == 'invite':
        await bot.call_api('set_group_add_request', flag=event.flag, sub_type='invite', approve=True)
        logger.info(f'已处理群组请求, 被用户: {user_id} 邀请加入群组: {group_id}.')


# 注册事件响应器, 新增群成员
group_increase = on_notice(priority=100)


@group_increase.handle()
async def handle_group_increase(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    user_id = event.user_id
    group_id = event.group_id
    detail_type = event.notice_type
    group_c_permission_res = await DBGroup(group_id=group_id).permission_command()
    if detail_type == 'group_increase' and group_c_permission_res.result == 1:
        # 发送欢迎消息
        at_seg = MessageSegment.at(user_id=user_id)
        msg = f'{at_seg}欢迎新朋友～\n进群请先看群公告～\n一起愉快地聊天吧!'
        await bot.send(event=event, message=Message(msg))
        logger.info(f'群组: {group_id}, 有新用户: {user_id} 进群')
