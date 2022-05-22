"""
@Author         : Ailitonia
@Date           : 2021/08/31 21:05
@FileName       : tarot.py
@Project        : nonebot2_miya 
@Description    : 塔罗插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
from nonebot import on_command, logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD

from .tarot_resources import get_tarot_resource, get_available_tarot_resource
from .utils import generate_tarot_card, get_tarot_resource_name, set_tarot_resource


# Custom plugin usage text
__plugin_custom_name__ = '塔罗牌'
__plugin_usage__ = r'''【塔罗牌】
简单的塔罗牌插件

用法:
/塔罗牌 [卡牌名]

仅限私聊或群聊中群管理员使用:
/设置塔罗牌组 [资源名]'''


# 注册事件响应器
tarot = on_command(
    'tarot',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='tarot', level=10),
    aliases={'塔罗牌', '单张塔罗牌'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@tarot.handle()
async def handle_parse_card_name(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    card_name = cmd_arg.extract_plain_text().strip()
    if card_name:
        state.update({'card_name': card_name})
    else:
        state.update({'card_name': ''})


@tarot.got('card_name', prompt='你想要看哪张塔罗牌呢?')
async def handle_para_tarot(bot: Bot, event: MessageEvent, matcher: Matcher, card_name: str = ArgStr('card_name')):
    card_name = card_name.strip()
    resource_name = await get_tarot_resource_name(bot=bot, event=event, matcher=matcher)
    card_resource = get_tarot_resource(resource_name=resource_name)
    if card_name:
        try:
            card = card_resource.pack.get_card_by_name(name=card_name)
            card_image = await generate_tarot_card(id_=card.id, resources=card_resource)
            await matcher.send(MessageSegment.image(card_image.file_uri))
        except ValueError:
            await matcher.send(f'没有找到塔罗牌: {card_name}, 该卡牌可能不在卡组中')
        except Exception as e:
            logger.error(f'Tarot | 生成塔罗牌图片失败, {e}')
            await matcher.send('生成塔罗牌图片失败了QAQ, 请稍后再试')
    else:
        try:
            card = random.choice(card_resource.pack.cards)
            # 随机正逆
            direction = random.choice([-1, 1])
            if direction == 1:
                need_upright = True
                need_reversed = False
            else:
                need_upright = False
                need_reversed = True
            # 绘制卡图
            card_image = await generate_tarot_card(
                id_=card.id,
                resources=card_resource,
                direction=direction,
                need_desc=False,
                need_upright=need_upright,
                need_reversed=need_reversed
            )
            await matcher.send(MessageSegment.image(card_image.file_uri))
        except Exception as e:
            logger.error(f'Tarot | 生成塔罗牌图片失败, {e}')
            await matcher.send('生成塔罗牌图片失败了QAQ, 请稍后再试')


set_resource = on_command(
    'SetTarotResource',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='SetTarotResource',
        level=10,
        auth_node='set_tarot_resource'
    ),
    aliases={'设置塔罗牌组', '设置塔罗牌面', '设置塔罗资源'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@set_resource.handle()
async def handle_parse_resource_name(state: T_State, matcher: Matcher, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    resource_name = cmd_arg.extract_plain_text().strip()
    if resource_name:
        state.update({'resource_name': resource_name})
    else:
        resource_msg = '\n'.join(get_available_tarot_resource())
        await matcher.send(f'当前可用的塔罗牌组有:\n\n{resource_msg}')


@set_resource.got('resource_name', prompt='请输入想要配置的塔罗牌组名称:')
async def handle_delete_user_sub(bot: Bot, event: MessageEvent, matcher: Matcher,
                                 resource_name: str = ArgStr('resource_name')):
    resource_name = resource_name.strip()
    if resource_name not in get_available_tarot_resource():
        await matcher.reject(f'{resource_name}不是可用的塔罗牌组, 重新输入:')

    setting_result = await set_tarot_resource(resource_name=resource_name, bot=bot, event=event, matcher=matcher)
    if isinstance(setting_result, Exception):
        logger.error(f"SetTarotResource | 配置塔罗资源失败, {setting_result}")
        await matcher.finish(f'设置塔罗牌组失败了QAQ, 请稍后重试或联系管理员处理')
    else:
        logger.success(f"SetTarotResource | 配置塔罗资源成功")
        await matcher.finish(f'已将塔罗牌组设置为: {resource_name}')
