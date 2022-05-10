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
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11.message import Message
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from .calculator import Calculator, CalculateException


# Custom plugin usage text
__plugin_custom_name__ = '计算器'
__plugin_usage__ = r'''【简易计算器】
只能计算加减乘除和乘方!

用法:
/计算 [算式]'''


# 注册事件响应器
calculator = on_command(
    'calculator',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='calculator', level=10),
    aliases={'计算', '计算器'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@calculator.handle()
async def handle_parse_expression(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    expression = cmd_arg.extract_plain_text().strip()
    if expression:
        state.update({'expression': expression})


@calculator.got('expression', prompt='请输入你想要计算的算式(只支持加减乘除和乘方):')
async def handle_calculator(expression: str = ArgStr('expression')):
    expression = expression.strip()
    if len(expression) >= 128:
        logger.warning(f'Calculator | 超过长度限制的算式: {expression}')
        await calculator.finish('算式太长了QAQ')

    try:
        result = await Calculator(expression=expression).async_std_calculate()
    except CalculateException as e:
        logger.warning(f'Calculator | 计算失败, error: {repr(e)}')
        await calculator.finish(f'计算失败QAQ, {e.reason}')
        return
    except Exception as e:
        logger.error(f'Calculator | 计算失败, error: {repr(e)}')
        await calculator.finish(f'计算失败QAQ，也许算式超出计算范围了')
        return
    await calculator.finish(f'{expression}的计算结果是:\n\n{result}')
