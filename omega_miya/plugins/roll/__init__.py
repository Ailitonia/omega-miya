"""
@Author         : Ailitonia
@Date           : 2021/12/24 11:09
@FileName       : roll.py
@Project        : nonebot2_miya
@Description    : Roll
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
import random
from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD
from omega_miya.onebot_api import GoCqhttpBot


__plugin_meta__ = PluginMetadata(
    name="Roll",
    description="【骰子插件】\n"
                "各种姿势的掷骰子\n"
                "选择困难症患者福音",
    usage="/roll <x>d<y>\n"
          "/抽奖 <人数>\n"
          "/帮我选 [选项1 选项2 ...]",
    extra={"author": "Ailitonia"},
)


_ALL_LOTTERY_NUM: int = 50
"""限制抽奖的最大人数"""


roll = on_command(
    'Roll',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='roll', level=10, cool_down=10),
    aliases={'roll'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@roll.handle()
async def handle_parse_expression(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    expression = cmd_arg.extract_plain_text().strip()
    if expression:
        state.update({'expression': expression})


@roll.got('expression', prompt='请掷骰子: <骰子个数>D<骰子面数>')
async def handle_roll(expression: str = ArgStr('expression')):
    expression = expression.strip()

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
        await roll.reject(f'骰子格式不对呢, 请重新输入:\n<骰子个数>D<骰子面数>')
        return

    # 加入一个趣味的机制
    if random.randint(1, 100) == 99:
        await roll.finish(f'【彩蛋】骰子之神似乎不看好你, 你掷出的骰子全部消失了')
    if dice_num > 1024 or dice_side > 1024:
        await roll.finish(f'【错误】谁没事干扔那么多骰子啊(╯°□°）╯︵ ┻━┻')
    if dice_num <= 0 or dice_side <= 0:
        await roll.finish(f'【错误】你掷出了不存在的骰子, 只有上帝知道结果是多少')
    dice_result = 0
    for i in range(dice_num):
        this_dice_result = random.choice(range(dice_side)) + 1
        dice_result += this_dice_result
    await roll.finish(f'你掷出了{dice_num}个{dice_side}面骰子。\n点数为【{dice_result}】')


lottery = on_command(
    'lottery',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='lottery', level=10, cool_down=30),
    aliases={'抽奖'},
    permission=GROUP,
    priority=10,
    block=True
)


@lottery.handle()
async def handle_parse_num(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    num = cmd_arg.extract_plain_text().strip()
    if num:
        state.update({'num': num})
    else:
        state.update({'num': '1'})


@lottery.got('num', prompt='请输入抽奖人数:')
async def handle_lottery(bot: Bot, event: GroupMessageEvent, num: str = ArgStr('num')):
    num = num.strip()
    if not num.isdigit():
        await lottery.reject(f'抽奖人数应当是一个正整数, 请重新输入:')

    num = int(num)
    gocq_bot = GoCqhttpBot(bot=bot)
    group_member_list = await gocq_bot.get_group_member_list(group_id=event.group_id)
    group_user_name_list = [x.card if x.card else x.nickname for x in group_member_list]
    if num > len(group_user_name_list) or num > _ALL_LOTTERY_NUM or num < 1:
        await lottery.finish(f'抽奖人数超过群总人数或超出抽奖上限了QAQ')
    lottery_result = random.sample(group_user_name_list, k=num)

    send_msg = f'抽奖人数: 【{num}】\n以下是中奖名单:\n【' + '】\n【'.join(lottery_result) + '】'
    await lottery.finish(send_msg)


help_choice = on_command(
    'help_choice',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='help_choice', level=10, cool_down=10),
    aliases={'帮我选', '选择困难症'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@help_choice.handle()
async def handle_parse_choices(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    choices = cmd_arg.extract_plain_text().strip()
    if choices:
        state.update({'choices': choices})


@help_choice.got('choices', prompt='有啥选项, 发来我帮你选~')
async def handle_help_choices(choices: str = ArgStr('choices')):
    choices = choices.strip().split()
    if not choices:
        await help_choice.finish('你什么选项都没告诉我, 怎么帮你选OwO')
    result = random.choice(choices)
    result_text = f'''帮你从“{'”，“'.join(choices)}”中选择了：\n\n“{result}”'''
    await help_choice.finish(result_text, at_sender=True)
