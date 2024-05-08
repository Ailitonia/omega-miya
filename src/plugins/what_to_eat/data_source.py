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
import ujson as json
from typing import Literal

from pydantic import BaseModel

from src.compat import parse_obj_as
from src.resource import StaticResource
from src.service import OmegaMessage, OmegaMessageSegment


_RESOURCE_PATH: StaticResource = StaticResource('images', 'what_to_eat')
"""本地资源路径"""
_FOOD_TYPE = Literal['早', '午', '晚', '夜']
"""菜品类型"""
_MENU_TMP: list["MenuFood"] = []
"""菜单缓存"""


class MenuFood(BaseModel):
    """菜单菜品"""
    name: str
    type: list[_FOOD_TYPE]
    img: list[str]


async def _get_menu() -> list[MenuFood]:
    """获取本地菜单资源"""
    global _MENU_TMP
    if not _MENU_TMP:
        async with _RESOURCE_PATH('index.json').async_open('r', encoding='utf8') as af:
            index = parse_obj_as(list[MenuFood], json.loads(await af.read()))
            _MENU_TMP.extend(index)
    return _MENU_TMP


async def get_random_food_msg(food_type: _FOOD_TYPE | None = None) -> OmegaMessage:
    menu = await _get_menu()
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

    img_file = _RESOURCE_PATH(random.choice(food.img))
    img_seg = OmegaMessageSegment.image(img_file.path)
    return OmegaMessageSegment.text(f'不知道吃啥的话，不如尝尝{food.name}如何？\n') + img_seg


__all__ = [
    'get_random_food_msg'
]
