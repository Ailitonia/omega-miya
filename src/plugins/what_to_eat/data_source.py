"""
@Author         : Ailitonia
@Date           : 2022/05/10 18:43
@FileName       : model.py
@Project        : nonebot2_miya
@Description    : What to eat model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from nonebot.log import logger
from pydantic import BaseModel

from src.compat import parse_json_as
from src.resource import StaticResource, TemporaryResource
from src.service import OmegaMessage, OmegaMessageSegment
from src.utils import OmegaRequests, semaphore_gather

if TYPE_CHECKING:
    from src.service import OmegaMatcherInterface as OmMI


_RESOURCE_PATH: StaticResource = StaticResource('images', 'what_to_eat')
_TMP_PATH: TemporaryResource = TemporaryResource('what_to_eat')
"""本地资源路径"""

type FoodType = Literal['早', '午', '晚', '夜']
"""菜品类型"""

_MENU_TMP: list['MenuFood'] = []
"""菜单缓存"""
_TYPE_MENU_TMP: dict[FoodType, list['MenuFood']] = {}
"""分类菜单缓存"""

_MSG_PREFIX: list[str] = [
    '不知道吃啥的话，不如尝尝这些吧~',
    '根据今天的好天气，为你推荐这些好吃的~',
    '还在纠结吃啥吗？不如试试这些~',
    '想尝试点新东西吗？这里有你的新选择~',
    '每一餐都是新的冒险，不如试试这些~',
]
"""消息前缀清单"""


class MenuFood(BaseModel):
    """菜单菜品"""
    name: str
    type: list[FoodType]
    img: list[str]


async def _init_menu() -> None:
    """初始化本地菜单资源"""
    menu_data = []
    async with _RESOURCE_PATH('index.json').async_open('r', encoding='utf8') as af:
        index = parse_json_as(list[MenuFood], await af.read())
        menu_data.extend(index)
    for file in _RESOURCE_PATH.iter_current_files():
        if re.search(re.compile(r'^index_addition_.+.json$'), file.name):
            async with file.async_open('r', encoding='utf8') as af:
                index = parse_json_as(list[MenuFood], await af.read())
                menu_data.extend(index)

    _MENU_TMP.extend(menu_data)
    _TYPE_MENU_TMP.update({
        '早': [food for food in _MENU_TMP if '早' in food.type],
        '午': [food for food in _MENU_TMP if '早' in food.type],
        '晚': [food for food in _MENU_TMP if '早' in food.type],
        '夜': [food for food in _MENU_TMP if '早' in food.type],
    })
    logger.debug(f'WhatToEat | Init menu completed, total: {len(_MENU_TMP)}')


async def _get_menu_random_food(food_type: FoodType | None = None, num: int = 3) -> list[MenuFood]:
    """初始化本地菜单资源, 获取随机食谱"""
    if not _MENU_TMP or not _TYPE_MENU_TMP:
        await _init_menu()

    if food_type is None:
        return random.sample(list(_MENU_TMP), k=num)
    else:
        return random.sample(list(_TYPE_MENU_TMP[food_type]), k=num)


async def _get_food_msg(food: MenuFood) -> OmegaMessage:
    """获取食谱内容"""
    food_img_url = str(random.choice(food.img))
    if food_img_url.startswith(('http://', 'https://')):
        filename = OmegaRequests.hash_url_file_name(food.name, url=food_img_url)
        file = await OmegaRequests().download(url=food_img_url, file=_TMP_PATH(filename), ignore_exist_file=True)
        img_seg = OmegaMessageSegment.image(await file.get_hosting_path())
    else:
        img_seg = OmegaMessageSegment.image(await _RESOURCE_PATH(food_img_url).get_hosting_path())

    return OmegaMessageSegment.text(f'【{food.name}】\n') + img_seg


async def _format_menu_msg(foods: Sequence[MenuFood]) -> OmegaMessage:
    """批量格式化食谱消息"""
    output_msg = OmegaMessage(random.choice(_MSG_PREFIX))

    messages = await semaphore_gather([_get_food_msg(x) for x in foods], semaphore_num=3, filter_exception=True)
    for msg in messages:
        output_msg += OmegaMessageSegment.text('\n') + msg

    return output_msg


async def get_random_food_msg(food_type: FoodType | None = None) -> OmegaMessage:
    """获取随机食谱并生成消息"""
    foods = await _get_menu_random_food(food_type=food_type)
    return await _format_menu_msg(foods=foods)


async def send_random_food_msg(interface: 'OmMI', food_type: FoodType | None = None) -> None:
    """获取随机食谱并发送消息"""
    try:
        msg = await get_random_food_msg(food_type=food_type)
        await interface.send_reply(msg)
    except Exception as e:
        logger.error(f'WhatToEat | 获取菜单失败, {e}')
        await interface.send_reply('获取菜单失败了, 请稍后再试')


__all__ = [
    'get_random_food_msg',
    'send_random_food_msg',
]
