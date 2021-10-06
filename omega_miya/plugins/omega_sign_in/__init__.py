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
import pathlib
from typing import Union
from nonebot import MatcherGroup, on_notice, logger, get_driver
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent, PokeNotifyEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp.message import Message, MessageSegment
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state, OmegaRules
from omega_miya.database import DBUser
from .config import Config
from .utils import scheduler, get_hitokoto, generate_sign_in_card


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ENABLE_REGEX_MATCHER = plugin_config.enable_regex_matcher
FAVORABILITY_ALIAS = plugin_config.favorability_alias
ENERGY_ALIAS = plugin_config.energy_alias
CURRENCY_ALIAS = plugin_config.currency_alias
EF_EXCHANGE_RATE = plugin_config.ef_exchange_rate


class SignInException(Exception):
    pass


class DuplicateException(SignInException):
    pass


class FailedException(SignInException):
    pass


# Custom plugin usage text
__plugin_custom_name__ = '签到'
__plugin_usage__ = r'''【Omega 签到插件】
轻量化签到插件
好感度系统基础支持
仅限群聊使用

**Permission**
Command & Lv.20
or AuthNode

**AuthNode**
basic

**Usage**
/签到
/今日运势(今日人品)
/好感度(我的好感)
/一言

可使用戳一戳触发'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


SignIn = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='sign_in',
        command=True,
        level=20),
    permission=GROUP,
    priority=20,
    block=True)


command_sign_in = SignIn.on_command('sign_in', aliases={'签到'})
command_fortune_today = SignIn.on_command('fortune_today', aliases={'今日运势', '今日人品', '一言', '好感度', '我的好感'})


poke_sign_in = on_notice(
    rule=to_me() & OmegaRules.has_group_command_permission() & OmegaRules.has_level_or_node(20, 'omega_sign_in.basic'),
    priority=50,
    block=False
)


@poke_sign_in.handle()
async def handle_command_sign_in(bot: Bot, event: PokeNotifyEvent, state: T_State):
    # 获取戳一戳用户身份
    sender_ = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    sender = {
        'user_id': event.user_id,
        'nickname': sender_.get('nickname', ''),
        'sex': sender_.get('sex', ''),
        'age': sender_.get('age', 0),
        'card': sender_.get('card', ''),
        'area': sender_.get('area', ''),
        'level': sender_.get('level', ''),
        'role': sender_.get('role', ''),
        'title': sender_.get('title', '')
    }
    # 从 PokeNotifyEvent 构造一个 GroupMessageEvent
    event_ = GroupMessageEvent(**{
                    'time': event.time,
                    'self_id': event.self_id,
                    'post_type': 'message',
                    'sub_type': 'normal',
                    'user_id': event.user_id,
                    'group_id': event.group_id,
                    'message_type': 'group',
                    'message_id': hash(repr(event)),
                    'message': Message('签到'),
                    'raw_message': '签到',
                    'font': 0,
                    'sender': sender
                })
    user = DBUser(user_id=event.user_id)
    # 先检查签到状态
    check_result = await user.sign_in_check_today()
    if check_result.result == 1:
        # 已签到
        # 设置一个状态指示生成卡片中添加文字
        state.update({'_checked_sign_in_text': '今天你已经签到过了哦~'})
        msg = await handle_fortune(bot=bot, event=event_, state=state)
        logger.info(f'{event.group_id}/{event.user_id}, 重复签到, 通过戳一戳获取了运势卡片')
        await poke_sign_in.finish(msg)
    else:
        # 未签到及异常交由签到函数处理
        msg = await handle_sign_in(bot=bot, event=event_, state=state)
        logger.info(f'{event.group_id}/{event.user_id}, 通过戳一戳进行了签到')
        await poke_sign_in.finish(msg)


@command_sign_in.handle()
async def handle_command_sign_in(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = await handle_sign_in(bot=bot, event=event, state=state)
    await command_sign_in.finish(msg)


@command_fortune_today.handle()
async def handle_command_fortune_today(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = await handle_fortune(bot=bot, event=event, state=state)
    await command_fortune_today.finish(msg)


if ENABLE_REGEX_MATCHER:
    regex_sign_in = SignIn.on_regex(r'^签到$')
    regex_fortune_today = SignIn.on_regex(r'^(今日(运势|人品)|一言|好感度|我的好感)$')

    @regex_sign_in.handle()
    async def handle_regex_sign_in(bot: Bot, event: GroupMessageEvent, state: T_State):
        msg = await handle_sign_in(bot=bot, event=event, state=state)
        await regex_sign_in.finish(msg)

    @regex_fortune_today.handle()
    async def handle_regex_fortune_today(bot: Bot, event: GroupMessageEvent, state: T_State):
        msg = await handle_fortune(bot=bot, event=event, state=state)
        await regex_fortune_today.finish(msg)


async def handle_sign_in(bot: Bot, event: GroupMessageEvent, state: T_State) -> Union[Message, MessageSegment, str]:
    user = DBUser(user_id=event.user_id)
    try:
        # 获取当前好感度信息
        favorability_status_result = await user.favorability_status()
        if favorability_status_result.error and favorability_status_result.info == 'NoResultFound':
            # 没有好感度记录的要重置
            reset_favorability_result = await user.favorability_reset()
            if reset_favorability_result.error:
                raise FailedException(f'Sign-in add User {event.user_id} Failed, '
                                      f'init user favorability status failed, {reset_favorability_result.info}')
            favorability_status_result = await user.favorability_status()
        elif favorability_status_result.error and favorability_status_result.info == 'User not exist':
            # 没有用户的要先新增用户
            user_add_result = await user.add(nickname=event.sender.nickname)
            if user_add_result.error:
                raise FailedException(f'Sign-in add User {event.user_id} Failed, '
                                      f'add user to database failed, {user_add_result.info}')
            # 新增了用户后同样要重置好感度记录
            reset_favorability_result = await user.favorability_reset()
            if reset_favorability_result.error:
                raise FailedException(f'Sign-in add User {event.user_id} Failed, '
                                      f'init user favorability status failed, {reset_favorability_result.info}')
            favorability_status_result = await user.favorability_status()
        if favorability_status_result.error:
            raise FailedException(f'获取好感度信息失败, {favorability_status_result}')
        status, mood, favorability, energy, currency, response_threshold = favorability_status_result.result

        # 尝试签到
        sign_in_result = await user.sign_in()
        if sign_in_result.error:
            raise FailedException(f'签到失败, {sign_in_result.info}')
        elif sign_in_result.result == 1:
            raise DuplicateException('重复签到')

        # 查询连续签到时间
        sign_in_c_d_result = await user.sign_in_continuous_days()
        if sign_in_c_d_result.error:
            raise FailedException(f'查询连续签到时间失败, {sign_in_c_d_result.info}')
        continuous_days = sign_in_c_d_result.result

        # 尝试为用户增加好感度
        # 根据连签日期设置不同增幅
        if continuous_days < 7:
            favorability_inc_ = int(10 * (1 + random.gauss(0.25, 0.25)))
            currency_inc = 1
        elif continuous_days < 30:
            favorability_inc_ = int(30 * (1 + random.gauss(0.35, 0.2)))
            currency_inc = 3
        else:
            favorability_inc_ = int(50 * (1 + random.gauss(0.45, 0.15)))
            currency_inc = 5
        # 将能量值兑换为好感度
        favorability_inc = energy * EF_EXCHANGE_RATE + favorability_inc_
        # 增加后的好感度及硬币
        favorability_ = favorability + favorability_inc
        currency_ = currency + currency_inc

        favorability_result = await user.favorability_add(favorability=favorability_inc, currency=currency_inc,
                                                          energy=(- energy))
        if favorability_result.error:
            raise FailedException(f'增加好感度失败, {favorability_result.info}')

        nick_name = event.sender.card if event.sender.card else event.sender.nickname
        user_text = f'@{nick_name} {FAVORABILITY_ALIAS}+{int(favorability_inc_)} ' \
                    f'{CURRENCY_ALIAS}+{int(currency_inc)}\n' \
                    f'已连续签到{continuous_days}天\n' \
                    f'已将{int(energy)}{ENERGY_ALIAS}兑换为{int(energy * EF_EXCHANGE_RATE)}{FAVORABILITY_ALIAS}\n' \
                    f'当前{FAVORABILITY_ALIAS}: {int(favorability_)}\n' \
                    f'当前{CURRENCY_ALIAS}: {int(currency_)}'

        sign_in_card_result = await generate_sign_in_card(user_id=event.user_id, user_text=user_text, fav=favorability_)
        if sign_in_card_result.error:
            raise FailedException(f'生成签到卡片失败, {sign_in_card_result.info}')

        msg = MessageSegment.image(pathlib.Path(sign_in_card_result.result).as_uri())
        logger.info(f'{event.group_id}/{event.user_id} 签到成功')
        return msg
    except DuplicateException as e:
        # 已签到
        # 设置一个状态指示生成卡片中添加文字
        state.update({'_checked_sign_in_text': '今天你已经签到过了哦~'})
        msg = await handle_fortune(bot=bot, event=event, state=state)
        logger.info(f'{event.group_id}/{event.user_id} 重复签到, 生成运势卡片, {str(e)}')
        return msg
    except FailedException as e:
        msg = Message(MessageSegment.at(event.user_id)).append('签到失败了QAQ, 请稍后再试或联系管理员处理')
        logger.error(f'{event.group_id}/{event.user_id} 签到失败, {str(e)}')
        return msg
    except Exception as e:
        msg = Message(MessageSegment.at(event.user_id)).append('签到失败了QAQ, 请稍后再试或联系管理员处理')
        logger.error(f'{event.group_id}/{event.user_id} 签到失败, 发生了预期外的错误, {str(e)}')
        return msg


async def handle_fortune(bot: Bot, event: GroupMessageEvent, state: T_State) -> Union[Message, MessageSegment, str]:
    user = DBUser(user_id=event.user_id)
    try:
        # 获取当前好感度信息
        favorability_status_result = await user.favorability_status()
        if favorability_status_result.error or not favorability_status_result.result:
            logger.info(f'{event.group_id}/{event.user_id} 尚未签到或无好感度信息, {favorability_status_result}')
            status, mood, favorability, energy, currency, response_threshold = ('', 0, 0, 0, 0, 0)
        else:
            status, mood, favorability, energy, currency, response_threshold = favorability_status_result.result

        nick_name = event.sender.card if event.sender.card else event.sender.nickname

        # 获取一言
        hitokoto_result = await get_hitokoto()
        if hitokoto_result.error:
            raise FailedException(f'获取一言失败, {hitokoto_result}')

        # 插入poke签到特殊文本
        pock_text = state.get('_checked_sign_in_text', None)
        user_line = f'@{nick_name}\n' if not pock_text else f'@{nick_name} {pock_text}\n'
        user_text = f'{hitokoto_result.result}\n\n' \
                    f'{user_line}' \
                    f'当前{FAVORABILITY_ALIAS}: {int(favorability)}\n' \
                    f'当前{CURRENCY_ALIAS}: {int(currency)}'

        sign_in_card_result = await generate_sign_in_card(
            user_id=event.user_id, user_text=user_text, fav=favorability, fortune_do=False)
        if sign_in_card_result.error:
            raise FailedException(f'生成运势卡片失败, {sign_in_card_result.info}')

        msg = MessageSegment.image(pathlib.Path(sign_in_card_result.result).as_uri())
        logger.info(f'{event.group_id}/{event.user_id} 获取运势卡片成功')
        return msg
    except Exception as e:
        msg = Message(MessageSegment.at(event.user_id)).append('获取今日运势失败了QAQ, 请稍后再试或联系管理员处理')
        logger.error(f'{event.group_id}/{event.user_id} 获取运势卡片失败, 发生了预期外的错误, {str(e)}')
        return msg
