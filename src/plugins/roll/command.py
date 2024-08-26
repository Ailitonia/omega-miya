"""
@Author         : Ailitonia
@Date           : 2023/10/18 23:23
@FileName       : command
@Project        : nonebot2_miya
@Description    : 骰子插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
import re
from datetime import timedelta
from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.database import AuthSettingDAL
from src.params.handler import get_command_str_single_arg_parser_handler, get_set_default_state_handler
from src.service import OmegaMatcherInterface as OmMI, enable_processor_state
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
async def handle_roll(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        expression: Annotated[str, ArgStr('expression')],
) -> None:
    expression = expression.strip()

    if (matched := re.match(r'^(\d+)[Dd](\d+)$', expression)) is not None:
        # <x>d<y>
        dice_num = int(matched.group(1))
        dice_side = int(matched.group(2))
    elif (matched := re.match(r'^[Dd](\d+)$', expression)) is not None:
        # d<x>
        dice_num = 1
        dice_side = int(matched.group(1))
    elif re.match(r'^\d+$', expression):
        # Any number
        dice_num = 1
        dice_side = int(expression)
    else:
        await interface.finish_reply(f'骰子格式不对呢, 确认后请重新输入:\n<骰子个数>D<骰子面数>')

    # 加入一个趣味的机制
    if random.randint(1, 100) == 99:
        await interface.finish_reply(f'【彩蛋】骰子之神似乎不看好你, 你掷出的骰子全部消失了')
    if dice_num > 1024 or dice_side > 1024:
        await interface.finish_reply(f'【错误】谁没事干扔那么多骰子啊(╯°□°）╯︵ ┻━┻')
    if dice_num <= 0 or dice_side <= 0:
        await interface.finish_reply(f'【错误】你掷出了不存在的骰子, 只有上帝知道结果是多少')

    dice_result = 0
    for i in range(dice_num):
        this_dice_result = random.choice(range(dice_side)) + 1
        dice_result += this_dice_result
    await interface.finish_reply(f'你掷出了{dice_num}个{dice_side}面骰子。\n点数为【{dice_result}】')


@roll.command(
    'rd',
    handlers=[get_command_str_single_arg_parser_handler('expression')],
).got('expression', prompt='请掷骰子: AdB(kq)C(pb)DaE')
async def handle_roll_dice(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        expression: Annotated[str, ArgStr('expression')],
) -> None:
    expression = expression.strip()

    dice = RandomDice(expression=expression)
    result = await dice.roll()
    if result.error_message is not None:
        logger.warning(f'Roll | 投骰异常, {result.error_message}')
        await interface.finish_reply(f'掷骰异常, {result.error_message}, 请稍后重试')

    if not result.result_detail or len(result.result_detail) > 1024:
        await interface.finish_reply(f'你掷出了【{result.result_int}】点')
    else:
        await interface.finish_reply(f'你掷出了【{result.result_int}】点\n结果为:\n{result.result_detail}')


@roll.command(
    'ra',
    handlers=[get_command_str_single_arg_parser_handler('attr')],
).got('attr', prompt='请输入需要鉴定的属性/技能名')
async def handle_roll_attr(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        attr: Annotated[str, ArgStr('attr')],
) -> None:
    attr = attr.strip()

    try:
        attr_node = f'{ATTR_PREFIX}{attr}'
        user_attr = await interface.entity.query_auth_setting(module=MODULE_NAME, plugin=PLUGIN_NAME, node=attr_node)
        if user_attr.value is None or not user_attr.value.isdigit():
            raise ValueError('attr value must be isdigit')
        attr_value = int(user_attr.value)
    except Exception as e:
        logger.warning(f'Roll | 查询 {interface.entity} 属性 {attr!r} 失败, {e}')
        await interface.finish_reply(f'你还没有配置{attr!r}属性/技能, 或属性值异常, 请使用"/roll.rs {attr}"配置后再试')

    roll_result = await RandomDice.simple_roll(1, 100)
    if roll_result.result_int is None or roll_result.error_message is not None:
        logger.warning(f'Roll | 投骰异常, {roll_result.error_message}')
        await interface.finish_reply('掷骰异常, 请稍后重试')

    result_msg = '失败~'
    if roll_result.result_int > 96:
        result_msg = "大失败~"
    if roll_result.result_int < attr_value:
        result_msg = '成功！'
    if roll_result.result_int < attr_value * 0.5:
        result_msg = '困难成功！'
    if roll_result.result_int < attr_value * 0.2:
        result_msg = '极限成功！'
    if roll_result.result_int < 4:
        result_msg = '大成功！！'

    await interface.finish_reply(
        f'你对【{attr}({attr_value})】\n进行了检定, 1D100=>{roll_result.result_int}\n{result_msg}')


@roll.command(
    'rs',
    handlers=[get_command_str_single_arg_parser_handler('attr')],
).got('attr', prompt='请输入需要随机的属性/技能名')
async def handle_roll_set_attr(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        attr: Annotated[str, ArgStr('attr')],
) -> None:
    attr = attr.strip()
    attr_node = f'{ATTR_PREFIX}{attr}'
    attr_cd_event = f'ROLL_{ATTR_PREFIX}{attr}_SETTER_COOLDOWN'

    try:
        is_expired, expired_time = await interface.entity.check_cooldown_expired(cooldown_event=attr_cd_event)
        if not is_expired:
            await interface.send_reply(f'属性{attr!r}重随冷却中!\n冷却到期: {expired_time.strftime("%Y-%m-%d %H:%M:%S")}')
            return

        roll_result = await RandomDice.simple_roll(1, 100)
        if roll_result.result_int is None:
            raise RuntimeError(f'掷骰异常, {roll_result.error_message}')

        await interface.entity.set_auth_setting(
            module=MODULE_NAME, plugin=PLUGIN_NAME, node=attr_node, available=1, value=str(roll_result.result_int)
        )
        await interface.entity.set_cooldown(cooldown_event=attr_cd_event, expired_time=timedelta(hours=6))
        await interface.entity.commit_session()

        await interface.send_reply(f'你获得了{attr!r}属性/技能, 属性/技能值为【{roll_result.result_int}】')
    except Exception as e:
        logger.error(f'Roll | 设置 {interface.entity} 属性 {attr!r} 失败, {e}')
        await interface.send_reply(f'随机获取{attr!r}属性/技能失败了, 请稍后重试或联系管理员处理')


@roll.command(
    'rc',
    handlers=[get_command_str_single_arg_parser_handler('attr')],
).got('attr', prompt='请输入需要移除的属性/技能名')
async def handle_roll_clear_attr(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        auth_dal: Annotated[AuthSettingDAL, Depends(AuthSettingDAL.dal_dependence)],
        attr: Annotated[str, ArgStr('attr')],
) -> None:
    attr = attr.strip()
    attr_node = f'{ATTR_PREFIX}{attr}'

    try:
        exist_attr = await interface.entity.query_auth_setting(module=MODULE_NAME, plugin=PLUGIN_NAME, node=attr_node)
        await auth_dal.delete(id_=exist_attr.id)
        await auth_dal.commit_session()

        await interface.send_reply(f'你移除了{attr!r}属性/技能')
    except Exception as e:
        logger.error(f'Roll | 移除 {interface.entity} 属性 {attr!r} 失败, {e}')
        await interface.send_reply(f'移除{attr!r}属性/技能失败了, 可能是你还没有配置{attr!r}属性/技能, 或属性值异常')


@roll.command(
    'rca',
    handlers=[get_set_default_state_handler('ensure', value=None)],
).got('ensure')
async def handle_roll_clear_all_attr(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        auth_dal: Annotated[AuthSettingDAL, Depends(AuthSettingDAL.dal_dependence)],
        ensure: Annotated[str | None, ArgStr('ensure')],
) -> None:
    if ensure is None:
        ensure_msg = f'即将移除你所有的属性/技能\n\n确认吗?\n【是/否】'
        await interface.reject_arg_reply('ensure', ensure_msg)
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        exist_attrs = await interface.entity.query_plugin_all_auth_setting(module=MODULE_NAME, plugin=PLUGIN_NAME)
        for attrs in exist_attrs:
            if attrs.node.startswith(ATTR_PREFIX):
                await auth_dal.delete(id_=attrs.id)
        await auth_dal.commit_session()

        removed_attrs = [x.node.removeprefix(ATTR_PREFIX) for x in exist_attrs if x.node.startswith(ATTR_PREFIX)]
        await interface.finish_reply(f'你移除了{", ".join(removed_attrs)!r}属性/技能')
    else:
        await interface.finish_reply('已取消操作')


@roll.command('show').handle()
async def handle_show_attr(interface: Annotated[OmMI, Depends(OmMI.depend('user'))]) -> None:
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
