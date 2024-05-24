"""
@Author         : Ailitonia
@Date           : 2023/10/18 23:23
@FileName       : command
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import random
from typing import Annotated

from nonebot.params import ArgStr
from nonebot.plugin import on_command

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaInterface, enable_processor_state


@on_command(
    'Roll',
    aliases={'roll'},
    handlers=[get_command_str_single_arg_parser_handler('expression')],
    priority=10,
    block=True,
    state=enable_processor_state(name='Roll', level=10),
).got('expression', prompt='请掷骰子: <骰子个数>D<骰子面数>')
async def handle_roll(expression: Annotated[str, ArgStr('expression')]):
    expression = expression.strip()
    interface = OmegaInterface()

    if re.match(r'^(\d+)[Dd](\d+)$', expression):
        # <x>d<y>
        dice_num = int(re.search(r'^(\d+)[Dd](\d+)$', expression).group(1))
        dice_side = int(re.search(r'^(\d+)[Dd](\d+)$', expression).group(2))
    elif re.match(r'^[Dd](\d+)$', expression):
        # d<x>
        dice_num = 1
        dice_side = int(re.search(r'^[Dd](\d+)$', expression).group(1))
    elif re.match(r'^\d+$', expression):
        # Any number
        dice_num = 1
        dice_side = int(expression)
    else:
        await interface.reject(f'骰子格式不对呢, 请重新输入:\n<骰子个数>D<骰子面数>')
        return

    # 加入一个趣味的机制
    if random.randint(1, 100) == 99:
        await interface.finish(f'【彩蛋】骰子之神似乎不看好你, 你掷出的骰子全部消失了')
    if dice_num > 1024 or dice_side > 1024:
        await interface.finish(f'【错误】谁没事干扔那么多骰子啊(╯°□°）╯︵ ┻━┻')
    if dice_num <= 0 or dice_side <= 0:
        await interface.finish(f'【错误】你掷出了不存在的骰子, 只有上帝知道结果是多少')
    dice_result = 0
    for i in range(dice_num):
        this_dice_result = random.choice(range(dice_side)) + 1
        dice_result += this_dice_result
    await interface.finish(f'你掷出了{dice_num}个{dice_side}面骰子。\n点数为【{dice_result}】')


__all__ = []
