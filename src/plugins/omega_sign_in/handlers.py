"""
@Author         : Ailitonia
@Date           : 2024/8/25 上午12:25
@FileName       : handlers
@Project        : nonebot2_miya
@Description    : 签到命令处理流程
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from datetime import datetime
from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.typing import T_State

from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment
from .config import sign_in_config
from .exception import DuplicateException, FailedException
from .helpers import generate_signin_card, get_hitokoto, get_profile_image, get_signin_top_image


async def handle_generate_sign_in_card(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        state: T_State,
) -> None:
    """处理用户签到, 生成签到卡片"""
    try:
        # 获取当前好感度信息
        await interface.entity.add_ignore_exists()
        friendship = await interface.entity.query_friendship()

        # 先检查签到状态
        check_result = await interface.entity.check_today_sign_in()
        if check_result:
            raise DuplicateException('重复签到')

        # 获取卡片头图
        try:
            top_img = await get_signin_top_image()
        except Exception as e:
            raise FailedException(f'获取签到卡片头图失败, {e}') from e

        # 尝试签到
        try:
            await interface.entity.sign_in()
        except Exception as e:
            raise FailedException(f'签到失败, {e}') from e

        # 查询连续签到时间
        total_days = await interface.entity.query_total_sign_in_days()
        continuous_days = await interface.entity.query_continuous_sign_in_day()

        # 尝试为用户增加好感度
        # 根据连签日期设置不同增幅
        if continuous_days < 7:
            base_friendship_inc = int(30 * (1 + random.gauss(0.25, 0.25)))
            currency_inc = 1 * sign_in_config.signin_plugin_base_currency
        elif continuous_days < 30:
            base_friendship_inc = int(70 * (1 + random.gauss(0.35, 0.2)))
            currency_inc = 3 * sign_in_config.signin_plugin_base_currency
        else:
            base_friendship_inc = int(110 * (1 + random.gauss(0.45, 0.15)))
            currency_inc = 5 * sign_in_config.signin_plugin_base_currency

        # 将能量值兑换为好感度
        friendship_inc = friendship.energy * sign_in_config.signin_plugin_ef_exchange_rate + base_friendship_inc
        # 增加后的好感度及硬币
        friendship_now = friendship.friendship + friendship_inc
        currency_now = friendship.currency + currency_inc

        try:
            await interface.entity.change_friendship(
                friendship=friendship_inc, currency=currency_inc, energy=(- friendship.energy)
            )
        except Exception as e:
            raise FailedException(f'增加好感度失败, {e}') from e

        nick_name = interface.get_event_user_nickname()
        user_text = f'@{nick_name} {sign_in_config.signin_plugin_friendship_alias}+{int(base_friendship_inc)} ' \
                    f'{sign_in_config.signin_plugin_currency_alias}+{int(currency_inc)}\n' \
                    f'已连续签到{continuous_days}天, 累计签到{total_days}天\n' \
                    f'已将{int(friendship.energy)}{sign_in_config.signin_plugin_energy_alias}兑换为' \
                    f'{int(friendship.energy * sign_in_config.signin_plugin_ef_exchange_rate)}' \
                    f'{sign_in_config.signin_plugin_friendship_alias}\n' \
                    f'当前{sign_in_config.signin_plugin_friendship_alias}: {int(friendship_now)}\n' \
                    f'当前{sign_in_config.signin_plugin_currency_alias}: {int(currency_now)}'

        await interface.entity.commit_session()

        try:
            sign_in_card = await generate_signin_card(
                user_id=interface.entity.entity_id, user_text=user_text, friendship=friendship_now, top_img=top_img
            )
        except Exception as e:
            raise FailedException(f'生成签到卡片失败, {e}') from e

        logger.success(f'SignIn | User({interface.entity.tid}) 签到成功')
        await interface.send_at_sender(OmegaMessageSegment.image(sign_in_card.path))
    except DuplicateException:
        # 已签到, 设置一个状态指示生成卡片中添加文字
        state.update({'_checked_sign_in_text': '今天你已经签到过了哦~'})
        logger.info(f'SignIn | User({interface.entity.tid}) 重复签到, 生成运势卡片')
        await handle_generate_fortune_card(interface=interface, state=state)
    except FailedException as e:
        logger.error(f'SignIn | User({interface.entity.tid}) 签到失败, {e}')
        await interface.send_reply('签到失败了, 请稍后再试或联系管理员处理')
    except Exception as e:
        logger.error(f'SignIn | User({interface.entity.tid}) 签到失败, 发生了预期外的错误, {e}')
        await interface.send_reply('签到失败了, 请稍后再试或联系管理员处理')


async def handle_generate_fortune_card(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        state: T_State,
) -> None:
    """处理用户重复签到及今日运势, 生成运势卡片"""
    try:
        # 获取当前好感度信息
        await interface.entity.add_ignore_exists()
        friendship = await interface.entity.query_friendship()
        nick_name = interface.get_event_user_nickname()

        # 获取一言
        try:
            hitokoto = await get_hitokoto()
        except Exception as e:
            raise FailedException(f'获取一言失败, {e}') from e

        # 获取卡片头图
        try:
            top_img = await get_signin_top_image()
        except Exception as e:
            raise FailedException(f'获取签到卡片头图失败, {e}') from e

        # 插入签到特殊文本
        pock_text = state.get('_checked_sign_in_text', None)
        user_line = f'@{nick_name}\n' if not pock_text else f'@{nick_name} {pock_text}\n'
        user_text = f'{hitokoto}\n\n' \
                    f'{user_line}' \
                    f'当前{sign_in_config.signin_plugin_friendship_alias}: {int(friendship.friendship)}\n' \
                    f'当前{sign_in_config.signin_plugin_currency_alias}: {int(friendship.currency)}'

        try:
            head_img = await get_profile_image(interface=interface)
        except Exception as e:
            logger.warning(f'获取用户头像失败, 忽略头像框绘制, {e}')
            head_img = None

        try:
            sign_in_card = await generate_signin_card(
                user_id=interface.entity.entity_id, user_text=user_text, friendship=friendship.friendship,
                top_img=top_img, draw_fortune=False, head_img=head_img
            )
        except Exception as e:
            raise FailedException(f'生成运势卡片失败, {e}') from e

        logger.success(f'SignIn | User({interface.entity.tid}) 获取运势卡片成功')
        await interface.send_at_sender(OmegaMessageSegment.image(sign_in_card.path))
    except Exception as e:
        logger.error(f'SignIn | User({interface.entity.tid}) 获取运势卡片失败, 发生了预期外的错误, {e}')
        await interface.send_reply('获取今日运势失败了, 请稍后再试或联系管理员处理')


async def handle_fix_sign_in(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        ensure: Annotated[str | None, ArgStr('sign_in_ensure')],
        state: T_State,
) -> None:
    """处理用户补签, 生成补签卡片"""
    # 检查是否收到确认消息后执行补签
    if ensure is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        fix_cost_: int | None = state.get('fix_cost')
        fix_date_text_: str | None = state.get('fix_date_text')
        fix_date_ordinal_: int | None = state.get('fix_date_ordinal')

        if (fix_cost_ is None) or (fix_date_text_ is None) or (fix_date_ordinal_ is None):
            logger.warning(f'SignIn | User({interface.entity.tid}) 补签参数异常, state: {state}')
            await interface.send_reply('补签失败了, 补签参数异常, 请稍后再试或联系管理员处理')
            return

        try:
            # 尝试补签
            await interface.entity.sign_in(sign_in_info='Fixed sign in', date_=datetime.fromordinal(fix_date_ordinal_))
            await interface.entity.change_friendship(currency=(- fix_cost_))

            # 设置一个状态指示生成卡片中添加文字
            state.update({'_checked_sign_in_text': f'已消耗{fix_cost_}{sign_in_config.signin_plugin_currency_alias}~\n'
                                                   f'成功补签了{fix_date_text_}的签到!'})
            logger.success(f'SignIn | User({interface.entity.tid}) 补签{fix_date_text_}成功')
            await handle_generate_fortune_card(interface=interface, state=state)
            await interface.entity.commit_session()
            return
        except Exception as e:
            logger.error(f'SignIn | User({interface.entity.tid}) 补签失败, 执行补签时发生了预期外的错误, {e}')
            await interface.send_reply('补签失败了, 请稍后再试或联系管理员处理')
            return
    else:
        await interface.send_reply('已取消补签')
        return

    # 未收到确认消息后则为首次触发命令执行补签检查
    try:
        # 先检查签到状态
        is_sign_in_today = await interface.entity.check_today_sign_in()
        if not is_sign_in_today:
            await interface.send_reply('你今天还没签到呢, 请先签到后再进行补签哦~')
            return

        # 获取补签的时间
        last_missing_sign_in_day = await interface.entity.query_last_missing_sign_in_day()

        fix_date_text = datetime.fromordinal(last_missing_sign_in_day).strftime('%Y年%m月%d日')
        fix_days = datetime.now().toordinal() - last_missing_sign_in_day
        base_cost = 2 * sign_in_config.signin_plugin_base_currency
        fix_cost = base_cost if fix_days <= 3 else fix_days * base_cost

        # 获取当前好感度信息
        friendship = await interface.entity.query_friendship()

        if fix_cost > friendship.currency:
            logger.info(
                f'SignIn | User({interface.entity.tid}) 未补签, {sign_in_config.signin_plugin_currency_alias}不足'
            )
            tip_msg = f'没有足够的{sign_in_config.signin_plugin_currency_alias}【{fix_cost}】进行补签, 已取消操作'
            await interface.send_reply(tip_msg)
            return

        state['fix_cost'] = fix_cost
        state['fix_date_text'] = fix_date_text
        state['fix_date_ordinal'] = last_missing_sign_in_day

    except Exception as e:
        logger.error(f'SignIn | User({interface.entity.tid}) 补签失败, 检查状态时发生了预期外的错误, {e}')
        await interface.send_reply('补签失败了, 签到状态异常, 请稍后再试或联系管理员处理')
        return

    ensure_msg = f'使用{fix_cost}{sign_in_config.signin_plugin_currency_alias}补签{fix_date_text}\n\n确认吗?\n【是/否】'
    await interface.reject_arg_reply('sign_in_ensure', ensure_msg)


__all__ = [
    'handle_generate_fortune_card',
    'handle_generate_sign_in_card',
    'handle_fix_sign_in',
]
