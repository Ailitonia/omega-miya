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
from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command

from src.params.handler import get_command_str_single_arg_parser_handler
from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI, OmegaMessageSegment, enable_processor_state
from .helper import generate_tarot_card, get_tarot_resource_name, set_tarot_resource
from .resources import get_tarot_resource, get_available_tarot_resource


@on_command(
    'tarot',
    aliases={'塔罗牌', '单张塔罗牌'},
    handlers=[get_command_str_single_arg_parser_handler('card_name', ensure_key=True)],
    priority=10,
    block=True,
    state=enable_processor_state(name='Tarot', level=10),
).got('card_name', prompt='你想要看哪张塔罗牌呢?')
async def handle_show_tarot(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        card_name: Annotated[str | None, ArgStr('card_name')],
) -> None:
    resource_name = await get_tarot_resource_name(interface=interface)
    card_resource = get_tarot_resource(resource_name=resource_name)

    if card_name is not None:
        card_name = card_name.strip()
        try:
            card = card_resource.pack.get_card_by_name(name=card_name)
            card_image = await generate_tarot_card(id_=card.id, resources=card_resource)
            await interface.send_reply(OmegaMessageSegment.image(card_image.path))
        except KeyError:
            await interface.send_reply(f'没有找到塔罗牌: {card_name}, 该卡牌可能不在卡组中')
        except Exception as e:
            logger.error(f'Tarot | 生成塔罗牌图片失败, {e}')
            await interface.send_reply('生成塔罗牌图片失败了QAQ, 请稍后再试')
    else:
        try:
            card = random.choice(card_resource.pack.cards)
            # 随机正逆
            direction = 1 if random.random() > 0.5 else -1
            need_upright = (direction == 1)
            need_reversed = (direction == -1)
            # 绘制卡图
            card_image = await generate_tarot_card(
                id_=card.id,
                resources=card_resource,
                direction=direction,
                need_desc=False,
                need_upright=need_upright,
                need_reversed=need_reversed
            )
            await interface.send_reply(OmegaMessageSegment.image(card_image.path))
        except Exception as e:
            logger.error(f'Tarot | 生成塔罗牌图片失败, {e}')
            await interface.send_reply('生成塔罗牌图片失败了QAQ, 请稍后再试')


@on_command(
    'set-tarot-resource',
    aliases={'设置塔罗牌组', '设置塔罗牌面', '设置塔罗资源'},
    permission=IS_ADMIN,
    handlers=[get_command_str_single_arg_parser_handler('resource_name', ensure_key=True)],
    priority=20,
    block=True,
    state=enable_processor_state(name='SetTarotResource', level=10),
).got('resource_name', prompt='请输入想要配置的塔罗牌组名称:')
async def handle_set_tarot_resource(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        resource_name: Annotated[str | None, ArgStr('resource_name')],
) -> None:
    resource_msg = '\n'.join(get_available_tarot_resource())

    if resource_name is None:
        await interface.send_reply(f'当前可用的塔罗牌组有:\n\n{resource_msg}')
        await interface.reject_reply('请输入想要配置的塔罗牌组名称:')

    resource_name = resource_name.strip()
    if resource_name not in get_available_tarot_resource():
        await interface.send_reply(f'{resource_name}不是可用的塔罗牌组, 当前可用的塔罗牌组有:\n\n{resource_msg}\n\n请确认后重试')
    else:
        try:
            await set_tarot_resource(resource_name=resource_name, interface=interface)
            logger.success(f'SetTarotResource | {interface.entity} 配置塔罗资源成功')
            await interface.send_reply(f'已将塔罗牌组配置为: {resource_name}')
        except Exception as e:
            logger.error(f'SetTarotResource | {interface.entity} 配置塔罗资源失败, {e}')
            await interface.send_reply('配置塔罗牌组失败了, 请稍后重试或联系管理员处理')


__all__ = []
