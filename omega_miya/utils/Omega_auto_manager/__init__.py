from nonebot import on_request, on_notice, logger
from nonebot.typing import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_Base import DBGroup

# 注册事件响应器, 处理加好友申请
friend_request = on_request(priority=100)


@friend_request.handle()
async def handle_friend_request(bot: Bot, event: Event, state: dict):
    if event.detail_type == 'friend' and event.raw_event.get('comment') == 'Miya好萌好可爱':
        await bot.call_api('set_friend_add_request', flag=event.raw_event.get('flag'), approve=True)
        logger.info(f'已同意用户: {event.user_id} 的好友申请')
    elif event.detail_type == 'friend':
        await bot.call_api('set_friend_add_request', flag=event.raw_event.get('flag'), approve=False)
        logger.info(f'已拒绝用户: {event.user_id} 的好友申请')


# 注册事件响应器, 处理被邀请进群
group_invite = on_request(priority=100)


@group_invite.handle()
async def handle_group_invite(bot: Bot, event: Event, state: dict):
    if event.detail_type == 'group' and event.sub_type == 'invite':
        await bot.call_api('set_group_add_request', flag=event.raw_event.get('flag'), sub_type='invite', approve=True)
        logger.info(f'已处理群组请求, 被用户: {event.user_id} 邀请加入群组: {event.group_id}.')


# 注册事件响应器, 新增群成员
group_increase = on_notice(priority=100)


@group_increase.handle()
async def handle_group_increase(bot: Bot, event: Event, state: dict):
    if event.detail_type == 'group_increase' and DBGroup(group_id=event.group_id).permission_command().result == 1:
        # 发送欢迎消息
        at_seg = MessageSegment.at(user_id=event.user_id)
        msg = f'{at_seg}欢迎新朋友～\n进群请先看群公告~\n想知道我的用法请发送/help'
        await bot.send(event=event, message=msg)
        logger.info(f'群组: {event.group_id}, 有新用户: {event.user_id} 进群')
