from nonebot import on_message, on_request, on_notice, logger
from nonebot.typing import Bot, Event
from omega_miya.utils.Omega_Base import DBHistory


# 注册事件响应器, 处理MessageEvent
message_history = on_message(priority=101, block=True)


@message_history.handle()
async def handle_message(bot: Bot, event: Event, state: dict):
    try:
        user_name = event.sender.get('card')
        if not user_name:
            user_name = event.sender.get('nickname')
        time = int(event.time)
        self_id = int(event.self_id)
        post_type = str(event.type)
        detail_type = str(event.detail_type)
        sub_type = str(event.sub_type)
        group_id = int(event.group_id)
        user_id = int(event.user_id)
        raw_data = str(event.raw_message)
        msg_data = str(event.message)
        new_event = DBHistory(time=time, self_id=self_id, post_type=post_type, detail_type=detail_type)
        new_event.add(sub_type=sub_type, group_id=group_id, user_id=user_id, user_name=user_name,
                      raw_data=raw_data, msg_data=msg_data)
    except Exception as e:
        logger.error(f'Message history recording Failed, error: {repr(e)}')


# 注册事件响应器, 处理NoticeEvent
notice_history = on_notice(priority=101, block=True)


@notice_history.handle()
async def handle_notice(bot: Bot, event: Event, state: dict):
    try:
        time = int(event.time)
        self_id = int(event.self_id)
        post_type = str(event.type)
        detail_type = str(event.detail_type)
        sub_type = str(event.sub_type)
        group_id = int(event.group_id)
        user_id = int(event.user_id)
        raw_data = repr(event.raw_event)
        msg_data = str(event.message)
        new_event = DBHistory(time=time, self_id=self_id, post_type=post_type, detail_type=detail_type)
        new_event.add(sub_type=sub_type, group_id=group_id, user_id=user_id, user_name=None,
                      raw_data=raw_data, msg_data=msg_data)
    except Exception as e:
        logger.error(f'Notice history recording Failed, error: {repr(e)}')


# 注册事件响应器, 处理RequestEvent
request_history = on_request(priority=101, block=True)


@request_history.handle()
async def handle_request(bot: Bot, event: Event, state: dict):
    try:
        time = int(event.time)
        self_id = int(event.self_id)
        post_type = str(event.type)
        detail_type = str(event.detail_type)
        sub_type = str(event.sub_type)
        group_id = int(event.group_id)
        user_id = int(event.user_id)
        raw_data = repr(event.raw_event)
        msg_data = str(event.message)
        new_event = DBHistory(time=time, self_id=self_id, post_type=post_type, detail_type=detail_type)
        new_event.add(sub_type=sub_type, group_id=group_id, user_id=user_id, user_name=None,
                      raw_data=raw_data, msg_data=msg_data)
    except Exception as e:
        logger.error(f'Request history recording Failed, error: {repr(e)}')
