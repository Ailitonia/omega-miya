"""
@Author         : Ailitonia
@Date           : 2023/11/8 22:37
@FileName       : model
@Project        : nonebot2_miya
@Description    : 工具类实现, lib-onedice 二次包装
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional

from nonebot.utils import run_sync
from onedice import RD
from pydantic import BaseModel, ConfigDict, Field


class BaseDice(BaseModel):
    """骰子数据基类"""

    model_config = ConfigDict(extra='ignore', from_attributes=True, coerce_numbers_to_str=True, frozen=True)


class DiceResult(BaseDice):
    """骰子结果"""
    origin_data_raw: str = Field(alias='originDataRaw', description='原始输入的掷骰表达式')
    origin_data: str = Field(alias='originData', description='转小写的掷骰表达式')
    result_int: Optional[int] = Field(alias='resInt', description='掷骰结果')
    result_min: Optional[int] = Field(alias='resIntMin', description='掷骰理论最小值')
    result_max: Optional[int] = Field(alias='resIntMax', description='掷骰理论最大值')
    result_detail: Optional[str] = Field(alias='resDetail', description='掷骰结果表达式')
    result_error: Optional[int] = Field(alias='resError', description='错误代码')
    custom_default: Optional[dict] = Field(alias='customDefault', description='自定义类型')
    value_map: Optional[dict] = Field(alias='valueTable', description='预设参数表')
    rule_mode: Optional[str] = Field(alias='ruleMode', description='规则模式')

    @property
    def error_message(self) -> str | None:
        match self.result_error:
            case None:
                return None
            case -1:
                return 'UNKNOWN_GENERATE_FATAL: 解析表达式时发生未知异常'
            case -2:
                return 'UNKNOWN_COMPLETE_FATAL: 计算结果时发生未知异常'
            case -3:
                return 'INPUT_RAW_INVALID: 输入表达式非法或无效'
            case -4:
                return 'INPUT_CHILD_PARA_INVALID: 输入表达式参数非法或无效'
            case -5:
                return 'INPUT_NODE_OPERATION_INVALID: 输入表达式的节点操作非法或无效'
            case -6:
                return 'NODE_OPERATION_INVALID: 计算中节点操作非法或无效'
            case -7:
                return 'NODE_STACK_EMPTY: 计算中节点堆栈为空'
            case -8:
                return 'NODE_LEFT_VAL_INVALID: 计算中节点左值非法或无效'
            case -9:
                return 'NODE_RIGHT_VAL_INVALID: 计算中节点右值非法或无效'
            case -10:
                return 'NODE_SUB_VAL_INVALID: 计算中节点子值非法或无效'
            case -11:
                return 'NODE_EXTREME_VAL_INVALID: 计算中节点极值非法或无效'
            case -12:
                return 'UNKNOWN_REPLACE_FATAL: 格式化表达式时发生未知异常'
            case _:
                return 'UNKNOWN_FATAL: 未知异常'


class RandomDice(object):
    """骰子"""
    def __init__(self, expression: str, value_map: Optional[dict[str, int]] = None):
        """
        :param expression: 掷骰表达式
        :param value_map: 预设属性/参数表
        """
        self._expression = expression
        self._value_map = value_map
        self._dice = RD(self._expression, valueTable=self._value_map)
        self.last_result: Optional[DiceResult] = None

    @run_sync
    def roll(self) -> DiceResult:
        self._dice.roll()
        self.last_result = DiceResult.model_validate(self._dice)
        return self.last_result

    @classmethod
    async def simple_roll(cls, num: int = 1, dice: int = 100) -> DiceResult:
        return await cls(f'{num}d{dice}').roll()


__all__ = [
    'DiceResult',
    'RandomDice'
]
