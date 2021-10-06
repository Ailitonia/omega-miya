"""
@Author         : Ailitonia
@Date           : 2021/07/18 15:39
@FileName       : calculator.py
@Project        : nonebot2_miya 
@Description    : 简易计算器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import on_command, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state
from omega_miya.utils.dice_utils import BaseCalculator
from omega_miya.utils.dice_utils.exception import CalculateException


# Custom plugin usage text
__plugin_custom_name__ = '计算器'
__plugin_usage__ = r'''【简易计算器】
只能计算加减乘除和乘方!

**Permission**
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
/计算器 [算式]'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
calculator = on_command(
    'Calculator',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='calculator',
        command=True,
        level=10),
    aliases={'calculator', '计算器', '计算'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=10,
    block=True)


# 修改默认参数处理
@calculator.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await calculator.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await calculator.finish('操作已取消')


@calculator.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['expression'] = args[0]
    else:
        await calculator.finish('参数错误QAQ')


@calculator.got('expression', prompt='请输入你想要计算的算式(只支持加减乘除和乘方):')
async def handle_calculator(bot: Bot, event: MessageEvent, state: T_State):
    expression = state['expression']
    if len(expression) >= 128:
        logger.warning(f'Calculator | 超过长度限制的算式: {expression}')
        await calculator.finish('算式太长了QAQ')

    try:
        result = await BaseCalculator(expression=expression).aio_std_calculate()
    except CalculateException as e:
        logger.warning(f'Calculator | 计算失败, error: {repr(e)}')
        await calculator.finish(f'计算失败QAQ, {e.reason}')
        return
    except Exception as e:
        logger.error(f'Calculator | 计算失败, error: {repr(e)}')
        await calculator.finish(f'计算失败QAQ，也许算式超出计算范围了')
        return
    await calculator.finish(f'{expression}的计算结果是:\n\n{result}')
