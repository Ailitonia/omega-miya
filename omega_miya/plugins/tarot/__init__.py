"""
@Author         : Ailitonia
@Date           : 2021/08/31 21:05
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 塔罗插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
import pathlib
from typing import Union
from nonebot import get_driver, MatcherGroup, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp.message import MessageSegment
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state
from .config import Config
from .utils import generate_tarot_card


global_config = get_driver().config
plugin_config = Config(**global_config.dict())


# Custom plugin usage text
__plugin_custom_name__ = '塔罗牌'
__plugin_usage__ = r'''【塔罗牌插件】
塔罗牌插件

**Permission**
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
/塔罗牌 [卡牌名]
/单张塔罗牌'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


Tarot = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='tarot',
        command=True,
        level=10),
    permission=GROUP,
    priority=10,
    block=True)

single_tarot = Tarot.on_command('单张塔罗牌')


@single_tarot.handle()
async def handle_single_tarot(bot: Bot, event: GroupMessageEvent, state: T_State):
    result = await handle_random_single_tarot(bot=bot, event=event, state=state)
    await single_tarot.finish(result)


para_tarot = Tarot.on_command('塔罗牌')


# 修改默认参数处理
@para_tarot.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = event.get_plaintext().strip()
    if not args:
        await para_tarot.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await para_tarot.finish('操作已取消')


@para_tarot.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = event.get_plaintext().strip()
    if not args:
        state['card_name'] = None
    else:
        state['card_name'] = args


@para_tarot.got('card_name', prompt='你想要看哪张塔罗牌呢?')
async def handle_para_tarot(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_resources = plugin_config.get_group_resources(group_id=event.group_id)
    card_name = state['card_name']
    if card_name is None:
        result = await handle_random_single_tarot(bot=bot, event=event, state=state)
        await para_tarot.finish(result)
    else:
        try:
            # 获取卡牌信息
            card = group_resources.pack.get_card_by_name(name=card_name)
            # 绘制卡图
            card_result = await generate_tarot_card(
                id_=card.id,
                resources=group_resources,
                need_desc=True,
                need_upright=True,
                need_reversed=True)

            if card_result.error:
                logger.error(f'{event.group_id}/{event.user_id} 生成塔罗牌图片失败, {card_result.info}')
                await para_tarot.send('生成塔罗牌图片失败了QAQ, 请稍后再试或联系管理员处理')
                return
            else:
                msg = MessageSegment.image(pathlib.Path(card_result.result).as_uri())
                logger.info(f'{event.group_id}/{event.user_id} 生成塔罗牌图片成功')
                await para_tarot.send(msg)
                return
        except Exception as e:
            logger.error(f'{event.group_id}/{event.user_id} 获取塔罗牌 {card_name} 信息失败, {repr(e)}')
            await para_tarot.finish(f'没有找到塔罗牌: {card_name}, 你发送的真的是卡牌名吗?')


async def handle_random_single_tarot(bot: Bot, event: GroupMessageEvent, state: T_State) -> Union[MessageSegment, str]:
    group_resources = plugin_config.get_group_resources(group_id=event.group_id)
    # 随机一张出来
    card = random.choice(group_resources.pack.cards)
    # 再随机正逆
    direction = random.choice([-1, 1])
    if direction == 1:
        need_upright = True
        need_reversed = False
    else:
        need_upright = False
        need_reversed = True
    # 绘制卡图
    card_result = await generate_tarot_card(
        id_=card.id,
        resources=group_resources,
        direction=direction,
        need_desc=False,
        need_upright=need_upright,
        need_reversed=need_reversed)

    if card_result.error:
        logger.error(f'{event.group_id}/{event.user_id} 生成塔罗牌图片失败, {card_result.info}')
        return '生成塔罗牌图片失败了QAQ, 请稍后再试或联系管理员处理'
    else:
        msg = MessageSegment.image(pathlib.Path(card_result.result).as_uri())
        logger.info(f'{event.group_id}/{event.user_id} 生成塔罗牌图片成功')
        return msg
