"""
@Author         : Ailitonia
@Date           : 2023/7/9 1:09
@FileName       : command
@Project        : nonebot2_miya
@Description    : 签到命令
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver
from nonebot.adapters.onebot.v11.bot import Bot as OneBotV11Bot
from nonebot.adapters.onebot.v11.event import (
    PokeNotifyEvent as OneBotV11PokeNotifyEvent,
    GroupMessageEvent as OneBotV11GroupMessageEvent,
    PrivateMessageEvent as OneBotV11PrivateMessageEvent
)
from nonebot.adapters.onebot.v11.message import Message as OneBotV11Message
from nonebot.log import logger
from nonebot.message import handle_event
from nonebot.plugin import MatcherGroup, on_notice
from nonebot.rule import to_me

from src.params.handler import get_command_str_single_arg_parser_handler
from src.params.rule import event_has_permission_level
from src.service import enable_processor_state
from .config import sign_in_config
from .handlers import handle_generate_fortune_card, handle_generate_sign_in_card, handle_fix_sign_in

_COMMAND_START: set[str] = get_driver().config.command_start
_DEFAULT_COMMAND_START: str = list(_COMMAND_START)[0] if _COMMAND_START else ''
"""默认的命令头"""


sign_in = MatcherGroup(
    type='message',
    priority=10,
    block=True,
    state=enable_processor_state(name='OmegaSignIn', level=20, auth_node='sign_in', echo_processor_result=False),
)

sign_in.on_command('签到', handlers=[handle_generate_sign_in_card])
sign_in.on_command('老黄历', aliases={'好感度', '一言'}, handlers=[handle_generate_fortune_card])


if sign_in_config.signin_plugin_enable_regex_matcher:
    sign_in.on_fullmatch(('签到',), handlers=[handle_generate_sign_in_card])
    sign_in.on_fullmatch(('老黄历', '今日运势', '一言', '好感度',), handlers=[handle_generate_fortune_card])


sign_in.on_command(
    '补签',
    handlers=[get_command_str_single_arg_parser_handler('sign_in_ensure', ensure_key=True)]
).got('sign_in_ensure')(handle_fix_sign_in)


# 针对 OneBot V11 的戳一戳事件进行特殊处理
@on_notice(
    rule=to_me() & event_has_permission_level(level=20),
    state=enable_processor_state(name='OmegaPokeSignIn', echo_processor_result=False),
    priority=11,
    block=False
).handle()
async def handle_poke_sign_in(bot: OneBotV11Bot, event: OneBotV11PokeNotifyEvent):
    # 获取戳一戳用户身份
    if event.group_id is None:
        sender_data = await bot.get_stranger_info(user_id=event.user_id)
    else:
        sender_data = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)

    sender = {
        'user_id': event.user_id,
        'nickname': sender_data.get('nickname'),
        'sex': sender_data.get('sex'),
        'age': sender_data.get('age'),
        'card': sender_data.get('card'),
        'area': sender_data.get('area'),
        'level': sender_data.get('level'),
        'role': sender_data.get('role'),
        'title': sender_data.get('title')
    }

    # 从 PokeNotifyEvent 构造一个 MessageEvent
    msg = f'{_DEFAULT_COMMAND_START}签到'
    event_t = OneBotV11PrivateMessageEvent if event.group_id is None else OneBotV11GroupMessageEvent
    message_type = 'private' if event.group_id is None else 'group'
    event_ = event_t.model_validate(
        {
            'time': event.time,
            'self_id': event.self_id,
            'post_type': 'message',
            'sub_type': 'normal',
            'user_id': event.user_id,
            'group_id': event.group_id,
            'message_type': message_type,
            'message_id': hash(repr(event)),
            'message': OneBotV11Message(msg),
            'raw_message': msg,
            'font': 0,
            'sender': sender
        }
    )
    # 签到及异常通过事件分发后交由签到函数处理
    logger.debug(f'SignIn | QQ Group({event.group_id})/User({event.user_id}), 通过戳一戳发起了签到请求')
    await handle_event(bot=bot, event=event_)


__all__ = []
