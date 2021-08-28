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
from nonebot import MatcherGroup, logger, get_driver
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp.message import Message, MessageSegment
from omega_miya.utils.omega_plugin_utils import init_export, init_permission_state
from omega_miya.database import DBUser
from .config import Config
from .utils import scheduler, get_hitokoto, generate_sign_in_card


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
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
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
/签到
/今日运势
/今日人品
/一言'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__, __plugin_auth_node__)


SignIn = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='sign_in',
        command=True,
        level=20,
        auth_node='basic'),
    permission=GROUP,
    priority=20,
    block=True)

command_sign_in = SignIn.on_command('sign_in', aliases={'签到'})
regex_sign_in = SignIn.on_regex(r'^签到$')
command_fortune_today = SignIn.on_command('fortune_today', aliases={'今日运势', '今日人品', '一言'})
regex_fortune_today = SignIn.on_regex(r'^(今日(运势|人品)|一言)$')


@command_sign_in.handle()
async def handle_command_sign_in(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = await handle_sign_in(bot=bot, event=event, state=state)
    await command_sign_in.finish(msg)


@regex_sign_in.handle()
async def handle_regex_sign_in(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = await handle_sign_in(bot=bot, event=event, state=state)
    await regex_sign_in.finish(msg)


@command_fortune_today.handle()
async def handle_command_fortune_today(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = await handle_fortune(bot=bot, event=event, state=state)
    await command_fortune_today.finish(msg)


@regex_fortune_today.handle()
async def handle_regex_fortune_today(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = await handle_fortune(bot=bot, event=event, state=state)
    await regex_fortune_today.finish(msg)


async def handle_sign_in(bot: Bot, event: GroupMessageEvent, state: T_State) -> Union[Message, MessageSegment, str]:
    user = DBUser(user_id=event.user_id)
    try:
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

        # 获取当前好感度信息
        favorability_status_result = await user.favorability_status()
        if favorability_status_result.error:
            raise FailedException(f'获取好感度信息失败, {favorability_status_result}')
        status, mood, favorability, energy, currency, response_threshold = favorability_status_result.result

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
        # 增加后的好感度
        favorability_ = favorability + favorability_inc

        favorability_result = await user.favorability_add(favorability=favorability_inc, currency=currency_inc,
                                                          energy=(- energy))
        if favorability_result.error and favorability_result.info == 'NoResultFound':
            favorability_result = await user.favorability_reset(favorability=favorability_inc, currency=currency_inc)
        if favorability_result.error:
            raise FailedException(f'增加好感度失败, {favorability_result.info}')

        nick_name = event.sender.card if event.sender.card else event.sender.nickname
        user_text = f'@{nick_name} {FAVORABILITY_ALIAS}+{int(favorability_inc_)} ' \
                    f'{CURRENCY_ALIAS}+{int(currency_inc)}\n' \
                    f'已连续签到{continuous_days}天\n' \
                    f'已将{int(energy)}{ENERGY_ALIAS}兑换为{int(energy * EF_EXCHANGE_RATE)}{FAVORABILITY_ALIAS}\n' \
                    f'当前{FAVORABILITY_ALIAS}: {int(favorability_)}\n' \
                    f'当前{CURRENCY_ALIAS}: {int(currency)}'

        sign_in_card_result = await generate_sign_in_card(user_id=event.user_id, user_text=user_text, fav=favorability_)
        if sign_in_card_result.error:
            raise FailedException(f'生成签到卡片失败, {sign_in_card_result.info}')

        msg = MessageSegment.image(pathlib.Path(sign_in_card_result.result).as_uri())
        logger.info(f'{event.group_id}/{event.user_id} 签到成功')
        return msg
    except DuplicateException as e:
        msg = Message(MessageSegment.at(event.user_id)).append('你今天已经签到过了, 请明天再来吧~')
        logger.info(f'{event.group_id}/{event.user_id} 重复签到, {str(e)}')
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

        user_text = f'{hitokoto_result.result}\n\n' \
                    f'@{nick_name}\n' \
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
