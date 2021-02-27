import re
import random
from nonebot import on_command, export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import init_export
from omega_miya.utils.Omega_plugin_utils import has_command_permission, permission_level


# Custom plugin usage text
__plugin_name__ = 'roll'
__plugin_usage__ = r'''【Roll & 抽奖】
一个整合了各种roll机制的插件
更多功能待加入

**Permission**
Command & Lv.10

**Usage**
/roll <x>d<y>
/抽奖 <人数>'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)

roll = on_command('roll', rule=has_command_permission() & permission_level(level=10), aliases={'Roll'},
                  permission=GROUP, priority=10, block=True)


# 修改默认参数处理
@roll.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await roll.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await roll.finish('操作已取消')


@roll.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['roll'] = args[0]
    else:
        await roll.finish('参数错误QAQ')


@roll.got('roll', prompt='请掷骰子: <x>d<y>')
async def handle_roll(bot: Bot, event: GroupMessageEvent, state: T_State):
    _roll = state['roll']
    if re.match(r'^\d+[d]\d+$', _roll):
        dice_info = _roll.split('d')
        dice_num = int(dice_info[0])
        dice_side = int(dice_info[1])
        # 加入一个趣味的机制
        if random.randint(1, 100) == 99:
            await roll.finish(f'【彩蛋】骰子之神似乎不看好你, 你掷出的骰子全部消失了')
        if dice_num > 1000 or dice_side > 1000:
            await roll.finish(f'【错误】谁没事干扔那么多骰子啊(╯°□°）╯︵ ┻━┻')
        if dice_num <= 0 or dice_side <= 0:
            await roll.finish(f'【错误】你掷出了不存在的骰子, 只有上帝知道结果是多少')
        dice_result = 0
        for i in range(dice_num):
            this_dice_result = random.choice(range(dice_side)) + 1
            dice_result += this_dice_result
        await roll.finish(f'你掷出了{dice_num}个{dice_side}面骰子, 点数为【{dice_result}】')
    else:
        await roll.finish(f'格式不对呢, 请重新输入: /roll <x>d<y>:')


lottery = on_command('抽奖', rule=has_command_permission() & permission_level(level=10),
                     permission=GROUP, priority=10, block=True)


# 修改默认参数处理
@lottery.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await lottery.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await lottery.finish('操作已取消')


@lottery.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['lottery'] = args[0]
    else:
        await lottery.finish('参数错误QAQ')


@lottery.got('lottery', prompt='请输入抽奖人数')
async def handle_lottery(bot: Bot, event: GroupMessageEvent, state: T_State):
    _lottery = state['lottery']
    if re.match(r'^\d+$', _lottery):
        people_num = int(_lottery)

        group_member_list = await bot.call_api(api='get_group_member_list', group_id=event.group_id)
        group_user_name_list = []

        for user_info in group_member_list:
            # 用户信息
            user_nickname = user_info['nickname']
            user_group_nickmane = user_info['card']
            if not user_group_nickmane:
                user_group_nickmane = user_nickname
            group_user_name_list.append(user_group_nickmane)

        if people_num > len(group_user_name_list):
            await lottery.finish(f'【错误】抽奖人数大于群成员人数了QAQ')

        lottery_result = random.sample(group_user_name_list, k=people_num)
        msg = '【' + str.join('】\n【', lottery_result) + '】'
        await lottery.finish(f"抽奖人数: 【{people_num}】\n以下是中奖名单:\n{msg}")
    else:
        await lottery.finish(f'格式不对呢, 人数应该是数字')
