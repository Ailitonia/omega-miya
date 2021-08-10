"""
@Author         : Ailitonia
@Date           : 2021/07/18 1:28
@FileName       : dice.py
@Project        : nonebot2_miya 
@Description    : 掷骰核心
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import random
import asyncio
from typing import List, Dict
from dataclasses import dataclass


class BaseDice(object):
    """
    骰子基类, 模拟真实骰子
    """
    def __init__(self, num: int = 1, side: int = 100):
        self.__num: int = num  # 骰子个数
        self.__side: int = side  # 骰子面数
        self.__result: int = -1  # 掷骰结果
        self.__index: int = -1  # 掷骰子次数索引
        self.__all_result: Dict[int, List[int]] = {}  # 记录全部掷骰历史

    @property
    def result(self) -> int:  # 本次掷骰点数总和
        return self.__result

    @property
    def index(self) -> int:
        return self.__index

    @property
    def count(self) -> int:
        return self.__index + 1

    @property
    def full_result(self) -> List[int]:  # 本次掷骰具体详情
        if self.count > 0:
            return self.__all_result[self.index]
        else:
            return []

    @property
    def all_result(self) -> Dict[int, List[int]]:  # 历史所有掷骰结果详情
        return self.__all_result

    def dice(self) -> int:
        """
        标准掷骰
        :return: int, 本次掷骰点数总和
        """
        self.__index += 1
        result: List[int] = []

        for i in range(self.__num):
            this_dice_result = random.choice(range(self.__side)) + 1
            result.append(this_dice_result)

        self.__result = sum(result)
        self.__all_result.update({self.__index: result})

        return self.result

    async def aio_dice(self) -> int:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.dice)
        return result


class ParseDice(object):
    """
    掷骰表达式解析与执行
    """
    @dataclass
    class ParsedExpression:
        num: int  # 骰子个数
        side: int  # 骰子面数
        check: bool  # 是否检定
        hidden: bool  # 是否暗骰

    @dataclass
    class DiceResult:
        num: int  # 骰子个数
        side: int  # 骰子面数
        hidden: bool  # 是否暗骰
        __result_L: List[int]  # 本次掷骰全部骰子点数的列表

        @property
        def sum(self) -> int:
            return sum(self.__result_L)  # 本次掷骰全部骰子点数之和

    def __init__(self, expression: str):
        self.__raw_expression = expression
        self.__is_parsed: bool = False

    def __parse(self):
        pass


__all__ = [
    'BaseDice'
]
