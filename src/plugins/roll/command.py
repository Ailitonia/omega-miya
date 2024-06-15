"""
@Author         : Ailitonia
@Date           : 2023/10/18 23:23
@FileName       : command
@Project        : nonebot2_miya
@Description    : 骰子插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import random
from datetime import timedelta
from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaInterface, enable_processor_state

from .consts import MODULE_NAME, PLUGIN_NAME, ATTR_PREFIX
from .model import RandomDice


roll = CommandGroup(
    'roll',
    priority=10,
    block=True,
    state=enable_processor_state(
        name='Roll',
        level=10
    ),
)


@roll.command(
    tuple(),
    aliases={'Roll'},
    handlers=[get_command_str_single_arg_parser_handler('expression')],
).got('expression', prompt='请掷骰子: <骰子个数>D<骰子面数>')
async def handle_roll(expression: Annotated[str, ArgStr('expression')]):
    expression = expression.strip()
    interface = OmegaInterface()
    interface.refresh_matcher_state()

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
        await interface.send_reply(f'骰子格式不对呢, 确认后请重新输入:\n<骰子个数>D<骰子面数>')
        return

    # 加入一个趣味的机制
    if random.randint(1, 100) == 99:
        await interface.send_reply(f'【彩蛋】骰子之神似乎不看好你, 你掷出的骰子全部消失了')
        return
    if dice_num > 1024 or dice_side > 1024:
        await interface.send_reply(f'【错误】谁没事干扔那么多骰子啊(╯°□°）╯︵ ┻━┻')
        return
    if dice_num <= 0 or dice_side <= 0:
        await interface.send_reply(f'【错误】你掷出了不存在的骰子, 只有上帝知道结果是多少')
        return

    dice_result = 0
    for i in range(dice_num):
        this_dice_result = random.choice(range(dice_side)) + 1
        dice_result += this_dice_result
    await interface.send_reply(f'你掷出了{dice_num}个{dice_side}面骰子。\n点数为【{dice_result}】')


@roll.command(
    'rd',
    handlers=[get_command_str_single_arg_parser_handler('expression')],
).got('expression', prompt='请掷骰子: AdB(kq)C(pb)DaE')
async def handle_rd(expression: Annotated[str, ArgStr('expression')]):
    expression = expression.strip()
    interface = OmegaInterface()
    interface.refresh_matcher_state()

    dice = RandomDice(expression=expression)
    result = dice.roll()
    if result.error_message is not None:
        logger.warning(f'Roll | 投骰异常, {result.error_message}')
        await interface.send_reply(f'掷骰异常, {result.error_message}')
        return

    if len(result.result_detail) > 1024:
        await interface.send_reply(f'你掷出了【{result.result_int}】点')
    else:
        await interface.send_reply(f'你掷出了【{result.result_int}】点\n结果为:\n{result.result_detail}')


@roll.command(
    'ra',
    handlers=[get_command_str_single_arg_parser_handler('attr')],
).got('attr', prompt='请输入需要鉴定的属性/技能名')
async def handle_ra(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface('user'))],
        attr: Annotated[str, ArgStr('attr')]
) -> None:
    attr = attr.strip()
    interface.refresh_interface_state()

    try:
        attr_node = f'{ATTR_PREFIX}{attr}'
        user_attr = await interface.entity.query_auth_setting(module=MODULE_NAME, plugin=PLUGIN_NAME, node=attr_node)
        if user_attr.value is None or not user_attr.value.isdigit():
            raise ValueError('attr value must be isdigit')
        attr_value = int(user_attr.value)
    except Exception as e:
        logger.warning(f'Roll | 查询 {interface.entity} 属性 {attr!r} 失败, {e}')
        await interface.send_reply(f'你还没有配置{attr!r}属性/技能, 或属性值异常, 请使用"/roll.rs {attr}"配置后再试')
        return

    result_int = RandomDice(expression='1d100').roll().result_int

    result_msg = '失败~'
    if result_int > 96:
        result_msg = "大失败~"
    if result_int < attr_value:
        result_msg = '成功！'
    if result_int < attr_value * 0.5:
        result_msg = '困难成功！'
    if result_int < attr_value * 0.2:
        result_msg = '极限成功！'
    if result_int < 4:
        result_msg = '大成功！！'

    await interface.send_reply(f'你对【{attr}({attr_value})】\n进行了检定=>{result_int}\n{result_msg}')
    return


@roll.command(
    'rs',
    handlers=[get_command_str_single_arg_parser_handler('attr')],
).got('attr', prompt='请输入需要随机的属性/技能名')
async def handle_rs(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface('user'))],
        attr: Annotated[str, ArgStr('attr')]
) -> None:
    attr = attr.strip()
    interface.refresh_interface_state()

    attr_node = f'{ATTR_PREFIX}{attr}'
    attr_cd_event = f'ROLL_{ATTR_PREFIX}{attr}_SETTER_COOLDOWN'

    try:
        is_expired, expired_time = await interface.entity.check_cooldown_expired(cooldown_event=attr_cd_event)
        if not is_expired:
            await interface.send_reply(f'属性{attr!r}重随冷却中!\n冷却到期: {expired_time.strftime("%Y-%m-%d %H:%M:%S")}')
            return

        set_attr = RandomDice(expression='1d100').roll().result_int
        await interface.entity.set_auth_setting(
            module=MODULE_NAME, plugin=PLUGIN_NAME, node=attr_node, available=1, value=str(set_attr)
        )
        await interface.entity.set_cooldown(cooldown_event=attr_cd_event, expired_time=timedelta(hours=6))
        await interface.entity.commit_session()

        await interface.send_reply(f'你获得了属性{attr!r}, 属性值为【{set_attr}】')
    except Exception as e:
        logger.error(f'Roll | 设置 {interface.entity} 属性 {attr!r} 失败, {e}')
        await interface.send_reply(f'配置{attr!r}属性失败了, 请稍后重试或联系管理员处理')


@roll.command('show').handle()
async def handle_show(interface: Annotated[OmegaInterface, Depends(OmegaInterface('user'))]) -> None:
    interface.refresh_interface_state()

    try:
        attrs = await interface.entity.query_plugin_all_auth_setting(module=MODULE_NAME, plugin=PLUGIN_NAME)
        attrs_msg = '\n'.join(
            f'{attr.node.removeprefix(ATTR_PREFIX)}={attr.value}'
            for attr in attrs
            if attr.node.startswith(ATTR_PREFIX)
        )
        await interface.send_reply(f'你拥有以下属性/技能:\n{attrs_msg if attrs_msg else "无"}')
    except Exception as e:
        logger.error(f'Roll | 查询 {interface.entity} 属性清单失败, {e}')
        await interface.send_reply('获取属性/技能清单失败了, 请稍后重试或联系管理员处理')


__all__ = []
