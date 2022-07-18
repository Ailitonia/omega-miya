"""
@Author         : Ailitonia
@Date           : 2021/07/17 1:29
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 轻量化签到插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
from typing import Union
from datetime import datetime
from nonebot import get_driver
from nonebot.log import logger
from nonebot.plugin import MatcherGroup, on_notice, PluginMetadata
from nonebot.message import handle_event
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent, PokeNotifyEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.params import ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch import GuildMessageEvent, GUILD
from omega_miya.database import EventEntityHelper
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.utils.rule import group_has_permission_level
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.exception import PluginException

from .config import sign_in_config, sign_local_resource_config
from .utils import get_head_image, get_hitokoto, generate_signin_card


__plugin_meta__ = PluginMetadata(
    name="签到",
    description="【OmegaSignIn 签到插件】\n"
                "签到插件\n"
                "好感度系统基础支持",
    usage="/签到\n"
          "/今日运势|今日人品\n"
          "/好感度|我的好感\n"
          "/一言\n\n"
          "可使用双击头像戳一戳触发",
    config=sign_in_config.__class__,
    extra={"author": "Ailitonia"},
)


_COMMAND_START: set[str] = get_driver().config.command_start
_DEFAULT_COMMAND_START: str = list(_COMMAND_START)[0] if _COMMAND_START else ''
"""默认的命令头"""


class SignInException(PluginException):
    """签到异常基类"""


class DuplicateException(SignInException):
    """重复签到"""


class FailedException(SignInException):
    """签到失败"""


SignIn = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='SignIn', level=20, auth_node='sign_in', echo_processor_result=False),
    permission=GROUP | GUILD,
    priority=20,
    block=True
)


command_sign_in = SignIn.on_command('sign_in', aliases={'签到'})
command_fix_sign_in = SignIn.on_command('fix_sign_in', aliases={'补签'})
command_fortune_today = SignIn.on_command('fortune_today', aliases={'今日运势', '今日人品', '一言', '好感度', '我的好感'})


poke_sign_in = on_notice(
    rule=to_me() & group_has_permission_level(level=20),
    state=init_processor_state(name='PokeSignIn', echo_processor_result=False),
    priority=50,
    block=False
)


@poke_sign_in.handle()
async def handle_command_sign_in(bot: Bot, event: PokeNotifyEvent):
    # 获取戳一戳用户身份
    sender_data = await GoCqhttpBot(bot=bot).get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    sender = {
        'user_id': event.user_id,
        'nickname': sender_data.nickname,
        'sex': sender_data.sex,
        'age': sender_data.age,
        'card': sender_data.card,
        'area': sender_data.area,
        'level': sender_data.level,
        'role': sender_data.role,
        'title': sender_data.title
    }
    # 从 PokeNotifyEvent 构造一个 GroupMessageEvent
    msg = f'{_DEFAULT_COMMAND_START}签到'
    event_ = GroupMessageEvent.parse_obj({
                    'time': event.time,
                    'self_id': event.self_id,
                    'post_type': 'message',
                    'sub_type': 'normal',
                    'user_id': event.user_id,
                    'group_id': event.group_id,
                    'message_type': 'group',
                    'message_id': hash(repr(event)),
                    'message': Message(msg),
                    'raw_message': msg,
                    'font': 0,
                    'sender': sender
                })
    # 签到及异常通过事件分发后交由签到函数处理
    await handle_event(bot=bot, event=event_)
    logger.debug(f'SignIn | {event.group_id}/{event.user_id}, 通过戳一戳发起了签到请求')


@command_sign_in.handle()
async def handle_command_sign_in(bot: Bot, event: GroupMessageEvent | GuildMessageEvent, state: T_State):
    msg = await handle_sign_in(bot=bot, event=event, state=state)
    await command_sign_in.finish(msg, at_sender=True)


@command_fortune_today.handle()
async def handle_command_fortune_today(bot: Bot, event: GroupMessageEvent | GuildMessageEvent, state: T_State):
    msg = await handle_fortune(bot=bot, event=event, state=state)
    await command_fortune_today.finish(msg, at_sender=True)


if sign_in_config.signin_enable_regex_matcher:
    regex_sign_in = SignIn.on_regex(r'^签到$')
    regex_fortune_today = SignIn.on_regex(r'^(今日(运势|人品)|一言|好感度|我的好感)$')

    @regex_sign_in.handle()
    async def handle_regex_sign_in(bot: Bot, event: GroupMessageEvent | GuildMessageEvent, state: T_State):
        msg = await handle_sign_in(bot=bot, event=event, state=state)
        await regex_sign_in.finish(msg, at_sender=True)

    @regex_fortune_today.handle()
    async def handle_regex_fortune_today(bot: Bot, event: GroupMessageEvent | GuildMessageEvent, state: T_State):
        msg = await handle_fortune(bot=bot, event=event, state=state)
        await regex_fortune_today.finish(msg, at_sender=True)


@command_fix_sign_in.handle()
async def handle_command_fix_sign_in_check(bot: Bot, event: GroupMessageEvent | GuildMessageEvent, state: T_State):
    user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
    # 先检查签到状态
    check_result = await run_async_catching_exception(user.check_today_sign_in)()
    if isinstance(check_result, Exception):
        logger.error(f'SignIn | User({user.tid}) 补签失败, 签到状态异常, {check_result}')
        await command_fix_sign_in.finish('补签失败了QAQ, 签到状态异常, 请稍后再试或联系管理员处理', at_sender=True)
    elif not check_result:
        # 未签到
        await command_fix_sign_in.finish('你今天还没签到呢, 请先签到后再进行补签哦~', at_sender=True)

    # 获取补签的时间
    fix_date_result = await run_async_catching_exception(user.query_last_missing_sign_in_day)()
    if isinstance(fix_date_result, Exception):
        logger.error(f'SignIn | User({user.tid}) 补签失败, 获取补签日期失败, {fix_date_result}')
        await command_fix_sign_in.finish('补签失败了QAQ, 签到状态异常, 请稍后再试或联系管理员处理', at_sender=True)

    fix_date = datetime.fromordinal(fix_date_result).strftime('%Y年%m月%d日')
    fix_days = datetime.now().toordinal() - fix_date_result
    base_cost = 2 * sign_in_config.signin_base_currency
    fix_cost = base_cost if fix_days <= 3 else fix_days * base_cost

    # 获取当前好感度信息
    friendship = await run_async_catching_exception(user.get_friendship_model)()
    if isinstance(friendship, Exception):
        logger.error(f'SignIn | User({user.tid}) 补签失败, 用户无好感度信息, {friendship}')
        await command_fix_sign_in.finish('补签失败了QAQ, 没有你的签到信息, 请先尝试签到后再补签', at_sender=True)

    if fix_cost > friendship.currency:
        logger.info(f'SignIn | User({user.tid}) 补签失败, 用户{sign_in_config.signin_currency_alias}不足')
        tip_msg = f'没有足够的{sign_in_config.signin_currency_alias}【{fix_cost}】进行补签QAQ'
        await command_fix_sign_in.finish(tip_msg, at_sender=True)

    state['fix_cost'] = fix_cost
    state['fix_date'] = fix_date
    state['fix_date_ordinal'] = fix_date_result

    await command_fix_sign_in.send(f'使用{fix_cost}{sign_in_config.signin_currency_alias}补签{fix_date}', at_sender=True)


@command_fix_sign_in.got('check', prompt='确认吗?\n【是/否】')
async def handle_command_fix_sign_in_check(bot: Bot, event: GroupMessageEvent | GuildMessageEvent, state: T_State,
                                           check: str = ArgStr('check')):
    fix_cost: int = state['fix_cost']
    fix_date: str = state['fix_date']
    fix_date_ordinal: int = state['fix_date_ordinal']
    check = check.strip()

    if check != '是':
        await command_fix_sign_in.finish('那就不补签了哦~', at_sender=True)

    user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
    currency_result = await run_async_catching_exception(user.add_friendship)(currency=(- fix_cost))
    if isinstance(currency_result, Exception):
        logger.error(f'SignIn | User({user.tid}) 补签失败, '
                     f'{sign_in_config.signin_currency_alias}更新失败, {currency_result}')
        await command_fix_sign_in.finish('补签失败了QAQ, 请稍后再试或联系管理员处理', at_sender=True)

    # 尝试签到
    sign_in_result = await run_async_catching_exception(user.sign_in)(sign_in_info='Fixed sign in',
                                                                      date_=datetime.fromordinal(fix_date_ordinal))
    if isinstance(sign_in_result, Exception):
        logger.error(f'SignIn | User({user.tid}) 补签失败, 尝试签到失败, {sign_in_result}')
        await command_fix_sign_in.finish('补签失败了QAQ, 请尝试先签到后再试或联系管理员处理', at_sender=True)

    # 设置一个状态指示生成卡片中添加文字
    state.update({'_checked_sign_in_text': f'已消耗{fix_cost}{sign_in_config.signin_currency_alias}~\n'
                                           f'成功补签了{fix_date}的签到!'})
    msg = await handle_fortune(bot=bot, event=event, state=state)
    logger.info(f'SignIn | User({user.tid}), 补签成功')
    await command_fix_sign_in.finish(msg, at_sender=True)


async def handle_sign_in(bot: Bot, event: MessageEvent, state: T_State) -> Union[Message, MessageSegment, str]:
    """处理生成签到卡片"""
    user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
    try:
        # 获取当前好感度信息
        friendship = await run_async_catching_exception(user.get_friendship_model)()
        if isinstance(friendship, Exception):
            # 大多数情况是用户第一次发言, 需要新建用户 entity
            await user.add_only(entity_name=event.sender.nickname, related_entity_name=event.sender.nickname)
            friendship = await user.get_friendship_model()

        # 先检查签到状态
        check_result = await user.check_today_sign_in()
        if check_result:
            # 已签到
            raise DuplicateException('重复签到')

        # 尝试签到
        sign_in_result = await user.sign_in()
        if sign_in_result.error:
            raise FailedException(f'签到失败, {sign_in_result.info}')

        # 查询连续签到时间
        continuous_days = await user.query_continuous_sign_in_day()

        # 尝试为用户增加好感度
        # 根据连签日期设置不同增幅
        if continuous_days < 7:
            base_friendship_inc = int(30 * (1 + random.gauss(0.25, 0.25)))
            currency_inc = 1 * sign_in_config.signin_base_currency
        elif continuous_days < 30:
            base_friendship_inc = int(70 * (1 + random.gauss(0.35, 0.2)))
            currency_inc = 3 * sign_in_config.signin_base_currency
        else:
            base_friendship_inc = int(110 * (1 + random.gauss(0.45, 0.15)))
            currency_inc = 5 * sign_in_config.signin_base_currency

        # 将能量值兑换为好感度
        friendship_inc = friendship.energy * sign_in_config.signin_ef_exchange_rate + base_friendship_inc
        # 增加后的好感度及硬币
        friendship_now = friendship.friend_ship + friendship_inc
        currency_now = friendship.currency + currency_inc

        add_friendship_result = await user.add_friendship(friend_ship=friendship_inc, currency=currency_inc,
                                                          energy=(- friendship.energy))
        if add_friendship_result.error:
            raise FailedException(f'增加好感度失败, {add_friendship_result.info}')

        nick_name = event.sender.card if event.sender.card else event.sender.nickname
        user_text = f'@{nick_name} {sign_in_config.signin_friendship_alias}+{int(base_friendship_inc)} ' \
                    f'{sign_in_config.signin_currency_alias}+{int(currency_inc)}\n' \
                    f'已连续签到{continuous_days}天\n' \
                    f'已将{int(friendship.energy)}{sign_in_config.signin_energy_alias}兑换为' \
                    f'{int(friendship.energy * sign_in_config.signin_ef_exchange_rate)}' \
                    f'{sign_in_config.signin_friendship_alias}\n' \
                    f'当前{sign_in_config.signin_friendship_alias}: {int(friendship_now)}\n' \
                    f'当前{sign_in_config.signin_currency_alias}: {int(currency_now)}'

        sign_in_card_result = await generate_signin_card(user_id=event.user_id, user_text=user_text, fav=friendship_now)
        if isinstance(sign_in_card_result, Exception):
            raise FailedException(f'生成签到卡片失败, {sign_in_card_result}')

        msg = MessageSegment.image(sign_in_card_result.file_uri)
        logger.success(f'SignIn | User({user.tid}) 签到成功')
        return msg
    except DuplicateException as e:
        # 已签到, 设置一个状态指示生成卡片中添加文字
        state.update({'_checked_sign_in_text': '今天你已经签到过了哦~'})
        msg = await handle_fortune(bot=bot, event=event, state=state)
        logger.info(f'SignIn | User({user.tid}) 重复签到, 生成运势卡片, {e}')
        return msg
    except FailedException as e:
        msg = MessageSegment.at(event.user_id) + '签到失败了QAQ, 请稍后再试或联系管理员处理'
        logger.error(f'SignIn | User({user.tid}) 签到失败, {e}')
        return msg
    except Exception as e:
        msg = MessageSegment.at(event.user_id) + '签到失败了QAQ, 请稍后再试或联系管理员处理'
        logger.error(f'SignIn | User({user.tid}) 签到失败, 发生了预期外的错误, {e}')
        return msg


async def handle_fortune(bot: Bot, event: MessageEvent, state: T_State) -> Union[Message, MessageSegment, str]:
    """处理生成运势卡片"""
    user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
    try:
        # 获取当前好感度信息
        friendship = await run_async_catching_exception(user.get_friendship_model)()
        if isinstance(friendship, Exception):
            # 应付那些用户第一次发言就要看好感度的, 新建用户 entity
            await user.add_only(entity_name=event.sender.nickname, related_entity_name=event.sender.nickname)
            friendship = await user.get_friendship_model()

        nick_name = event.sender.card if event.sender.card else event.sender.nickname

        # 获取一言
        hitokoto = await get_hitokoto()

        # 插入签到特殊文本
        pock_text = state.get('_checked_sign_in_text', None)
        user_line = f'@{nick_name}\n' if not pock_text else f'@{nick_name} {pock_text}\n'
        user_text = f'{hitokoto}\n\n' \
                    f'{user_line}' \
                    f'当前{sign_in_config.signin_friendship_alias}: {int(friendship.friend_ship)}\n' \
                    f'当前{sign_in_config.signin_currency_alias}: {int(friendship.currency)}'

        head_img = await get_head_image(bot=bot, event=event)
        head_img = head_img if not isinstance(head_img, Exception) else None

        sign_in_card_result = await generate_signin_card(user_id=event.user_id, user_text=user_text, fortune_do=False,
                                                         fav=friendship.friend_ship, head_img=head_img)
        if isinstance(sign_in_card_result, Exception):
            raise FailedException(f'生成运势卡片失败, {sign_in_card_result}')

        msg = MessageSegment.image(sign_in_card_result.file_uri)
        logger.info(f'SignIn | User({user.tid}) 获取运势卡片成功')
        return msg
    except Exception as e:
        msg = MessageSegment.at(event.user_id) + '获取今日运势失败了QAQ, 请稍后再试或联系管理员处理'
        logger.error(f'SignIn | User({user.tid}) 获取运势卡片失败, 发生了预期外的错误, {e}')
        return msg
