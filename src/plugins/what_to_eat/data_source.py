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
from typing import Literal

from nonebot.log import logger
from nonebot.utils import run_sync
from pydantic import BaseModel

from src.compat import parse_json_as
from src.resource import StaticResource, TemporaryResource
from src.service import OmegaMessage, OmegaMessageSegment
from src.utils import OmegaRequests

_RESOURCE_PATH: StaticResource = StaticResource('images', 'what_to_eat')
_TMP_PATH: TemporaryResource = TemporaryResource('what_to_eat')
"""本地资源路径"""

type FoodType = Literal['早', '午', '晚', '夜']
"""菜品类型"""

_MENU_TMP: list['MenuFood'] = []
"""菜单缓存"""


class MenuFood(BaseModel):
    """菜单菜品"""
    name: str
    type: list[FoodType]
    img: list[str]


async def _get_menu() -> list[MenuFood]:
    """获取本地菜单资源"""
    global _MENU_TMP
    if not _MENU_TMP:
        async with _RESOURCE_PATH('index.json').async_open('r', encoding='utf8') as af:
            index = parse_json_as(list[MenuFood], await af.read())
            _MENU_TMP.extend(index)
        for file in _RESOURCE_PATH.path.iterdir():
            if re.search(re.compile(r'^index_addition_.+.json'), file.name):
                async with _RESOURCE_PATH(file.name).async_open('r', encoding='utf8') as af:
                    index = parse_json_as(list[MenuFood], await af.read())
                    _MENU_TMP.extend(index)
    return _MENU_TMP


async def _get_food_msg(food: MenuFood) -> OmegaMessage:
    """格式化食谱消息"""
    food_img_url = str(random.choice(food.img))
    if food_img_url.startswith(('http://', 'https://')):
        filename = OmegaRequests.hash_url_file_name(food.name, url=food_img_url)
        file = await OmegaRequests().download(url=food_img_url, file=_TMP_PATH(filename))
        img_seg = OmegaMessageSegment.image(file.path)
    else:
        img_seg = OmegaMessageSegment.image(_RESOURCE_PATH(food_img_url).path)

    return OmegaMessageSegment.text(f'不知道吃啥的话，不如尝尝{food.name}如何？\n') + img_seg


@run_sync
def _get_random_food(menu: Sequence[MenuFood], food_type: FoodType | None = None) -> MenuFood:
    """获取随机食谱"""
    match food_type:
        case '早':
            food = random.choice([food for food in menu if '早' in food.type])
        case '午':
            food = random.choice([food for food in menu if '午' in food.type])
        case '晚':
            food = random.choice([food for food in menu if '晚' in food.type])
        case '夜':
            food = random.choice([food for food in menu if '夜' in food.type])
        case _:
            food = random.choice(menu)
    return food


async def get_random_food_msg(food_type: FoodType | None = None) -> OmegaMessage | OmegaMessageSegment:
    menu = await _get_menu()
    food = await _get_random_food(menu=menu, food_type=food_type)

    try:
        msg = await _get_food_msg(food=food)
    except Exception as e:
        logger.warning(f'WhatToEat | Downloading food image failed, {e}')
        msg = OmegaMessageSegment.text(f'不知道吃啥的话，不如尝尝{food.name}如何？\n')

    return msg


__all__ = [
    'get_random_food_msg',
]
