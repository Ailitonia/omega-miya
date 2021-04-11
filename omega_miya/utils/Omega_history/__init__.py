from nonebot import MatcherGroup, on_message, on_request, on_notice, logger
from nonebot.plugin import on
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from omega_miya.utils.Omega_Base import DBHistory


# 注册事件响应器, 处理MessageEvent
Message_history = MatcherGroup(type='message', priority=101, block=True)

message_history = Message_history.on_message()


@message_history.handle()
async def handle_message(bot: Bot, event: Event, state: T_State):
    try:
        message_id = event.dict().get('message_id')
        user_name = event.dict().get('sender').get('card')
        if not user_name:
            user_name = event.dict().get('sender').get('nickname')
        time = event.dict().get('time')
        self_id = event.dict().get('self_id')
        post_type = event.get_type()
        detail_type = event.dict().get(f'{event.get_type()}_type')
        sub_type = event.dict().get('sub_type')
        group_id = event.dict().get('group_id')
        user_id = event.dict().get('user_id')
        raw_data = repr(event)
        msg_data = str(event.dict().get('message'))
        new_event = DBHistory(time=time, self_id=self_id, post_type=post_type, detail_type=detail_type)
        res = await new_event.add(sub_type=sub_type, event_id=message_id, group_id=group_id, user_id=user_id,
                                  user_name=user_name, raw_data=raw_data, msg_data=msg_data)
        if res.error:
            logger.error(f'Message history recording Failed with database error: {res.info}')
    except Exception as e:
        logger.error(f'Message history recording Failed, error: {repr(e)}')


# 注册事件响应器, 处理message_sent
message_sent_history = on(type='message_sent', priority=101, block=True)


@message_sent_history.handle()
async def handle_message_sent_history(bot: Bot, event: Event, state: T_State):
    try:
        user_name = event.dict().get('sender').get('card')
        if not user_name:
            user_name = event.dict().get('sender').get('nickname')
        time = event.dict().get('time')
        self_id = event.dict().get('self_id')
        post_type = event.get_type()
        detail_type = 'self_sent'
        sub_type = 'self'
        group_id = event.dict().get('group_id')
        user_id = event.dict().get('user_id')
        raw_data = repr(event)
        msg_data = str(event.dict().get('message'))
        new_event = DBHistory(time=time, self_id=self_id, post_type=post_type, detail_type=detail_type)
        res = await new_event.add(sub_type=sub_type, group_id=group_id, user_id=user_id, user_name=user_name,
                                  raw_data=raw_data, msg_data=msg_data)
        if res.error:
            logger.error(f'Self-sent Message history recording Failed with database error: {res.info}')
    except Exception as e:
        logger.error(f'Self-sent Message history recording Failed, error: {repr(e)}')


# 注册事件响应器, 处理NoticeEvent
notice_history = on_notice(priority=101, block=True)


@notice_history.handle()
async def handle_notice(bot: Bot, event: Event, state: T_State):
    try:
        time = event.dict().get('time')
        self_id = event.dict().get('self_id')
        post_type = event.get_type()
        detail_type = event.dict().get(f'{event.get_type()}_type')
        sub_type = event.dict().get('sub_type')
        group_id = event.dict().get('group_id')
        user_id = event.dict().get('user_id')
        raw_data = repr(event)
        msg_data = str(event.dict().get('message'))
        new_event = DBHistory(time=time, self_id=self_id, post_type=post_type, detail_type=detail_type)
        res = await new_event.add(sub_type=sub_type, group_id=group_id, user_id=user_id, user_name=None,
                                  raw_data=raw_data, msg_data=msg_data)
        if res.error:
            logger.error(f'Notice history recording Failed with database error: {res.info}')
    except Exception as e:
        logger.error(f'Notice history recording Failed, error: {repr(e)}')


# 注册事件响应器, 处理RequestEvent
request_history = on_request(priority=101, block=True)


@request_history.handle()
async def handle_request(bot: Bot, event: Event, state: T_State):
    try:
        time = event.dict().get('time')
        self_id = event.dict().get('self_id')
        post_type = event.get_type()
        detail_type = event.dict().get(f'{event.get_type()}_type')
        sub_type = event.dict().get('sub_type')
        group_id = event.dict().get('group_id')
        user_id = event.dict().get('user_id')
        raw_data = repr(event)
        msg_data = str(event.dict().get('message'))
        new_event = DBHistory(time=time, self_id=self_id, post_type=post_type, detail_type=detail_type)
        res = await new_event.add(sub_type=sub_type, group_id=group_id, user_id=user_id, user_name=None,
                                  raw_data=raw_data, msg_data=msg_data)
        if res.error:
            logger.error(f'Request history recording Failed with database error: {res.info}')
    except Exception as e:
        logger.error(f'Request history recording Failed, error: {repr(e)}')
