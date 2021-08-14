"""
@Author         : Ailitonia
@Date           : 2021/07/17 1:29
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 轻量化签到插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import CommandGroup, logger, get_driver
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.omega_plugin_utils import init_export, init_permission_state
from omega_miya.database import DBUser
from .config import Config


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
FAVORABILITY_ALIAS = plugin_config.favorability_alias
ENERGY_ALIAS = plugin_config.energy_alias
CURRENCY_ALIAS = plugin_config.currency_alias


class SignInException(Exception):
    pass


class DuplicateException(SignInException):
    pass


class FailedException(SignInException):
    pass


# Custom plugin usage text
__plugin_name__ = '签到'
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
/签到'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


SignIn = CommandGroup(
    'SignIn',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='sign_in',
        command=True,
        level=10,
        auth_node='basic'),
    permission=GROUP,
    priority=10,
    block=True)

sign_in = SignIn.command('sign_in', aliases={'签到'})


@sign_in.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
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

        # 尝试为用户增加好感度
        if continuous_days < 7:
            favorability_inc = 10
            currency_inc = 1
        elif continuous_days < 30:
            favorability_inc = 30
            currency_inc = 2
        else:
            favorability_inc = 50
            currency_inc = 5

        favorability_result = await user.favorability_add(favorability=favorability_inc, currency=currency_inc)
        if favorability_result.error and favorability_result.info == 'NoResultFound':
            favorability_result = await user.favorability_reset(favorability=favorability_inc, currency=currency_inc)
        if favorability_result.error:
            raise FailedException(f'增加好感度失败, {favorability_result.info}')

        # 获取当前好感度信息
        favorability_status_result = await user.favorability_status()
        if favorability_status_result.error:
            raise FailedException(f'获取好感度信息失败, {favorability_status_result}')

        status, mood, favorability, energy, currency, response_threshold = favorability_status_result.result

        msg = f'签到成功! {FAVORABILITY_ALIAS}+{favorability_inc}, {CURRENCY_ALIAS}+{currency_inc}!\n\n' \
              f'你已连续签到{continuous_days}天\n' \
              f'当前{FAVORABILITY_ALIAS}: {favorability}\n' \
              f'当前{CURRENCY_ALIAS}: {currency}'
        logger.info(f'{event.group_id}/{event.user_id} 签到成功')
        await sign_in.finish(msg)
    except DuplicateException as e:
        logger.info(f'{event.group_id}/{event.user_id} 重复签到, {str(e)}')
        await sign_in.finish('你今天已经签到过了, 请明天再来吧~')
    except FailedException as e:
        logger.error(f'{event.group_id}/{event.user_id} 签到失败, {str(e)}')
        await sign_in.finish('签到失败了QAQ, 请稍后再试或联系管理员处理')
