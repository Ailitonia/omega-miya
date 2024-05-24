"""
@Author         : Ailitonia
@Date           : 2023/10/18 23:30
@FileName       : dice
@Project        : nonebot2_miya
@Description    : 骰子工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
import random
import re
from pydantic import BaseModel
from typing import List, Literal, Union

from src.exception import PluginException


class DiceException(PluginException):
    """骰子异常"""


class CalculateException(DiceException):
    """骰子计算异常"""
    def __init__(self, reason, expression):
        self.reason = reason
        self.expression = expression

    def __repr__(self):
        return f'<CalculateException, reason={self.reason}, expression={self.expression}>'


class Operator(BaseModel):
    """运算符"""
    operator: Literal['^', '*', '/', '+', '-']
    priority: int


class Operation(BaseModel):
    """运算基类"""
    operator: Operator
    left: int
    right: int

    def __str__(self) -> str:
        return f'Operation(expression={self.exp})'

    @property
    def exp(self) -> str:
        return f'{self.left}{self.operator}{self.right}'

    def calc(self) -> int:
        match self.operator.operator:
            case '^':
                return self.left ** self.right
            case '*':
                return self.left * self.right
            case '/':
                return self.left // self.right
            case '+':
                return self.left + self.right
            case '*':
                return self.left - self.right
            case _:
                raise CalculateException(f'operator {self.operator.operator!r} not support', self.exp)


class DiceToolMixin(abc.ABC):
    """骰子基础工具混入混入基类"""


class CalculateTool(DiceToolMixin):

    @staticmethod
    def _prepare_exp(expression: str) -> str:
        """预处理运算公式"""
        # 移除空白字符
        _expression = re.sub(r'\s', '', expression)
        # 替换中文符号
        _expression = re.sub(r'（', '(', _expression)
        _expression = re.sub(r'）', ')', _expression)
        # 替换运算符
        _expression = re.sub(r'[xX×]', '*', _expression)
        _expression = re.sub(r'[÷]', '/', _expression)
        return _expression

    @classmethod
    def _calculate_sequence(
            cls, calculate_sequence: List[Union[str, int, float]]) -> List[Union[str, int, float]]:
        """对拆分后的基本算式执行分步运算"""
        # 处理运算
        if '^' in calculate_sequence:
            # 处理乘方
            for _index, _obj in reversed(list(enumerate(calculate_sequence))):
                # 乘方需要从后向前匹配, 发现乘方则直接进行运算并返回
                if _obj == '^':
                    num_back = float(calculate_sequence.pop(_index + 1))
                    # 移除运算符
                    calculate_sequence.pop(_index)
                    num_front = float(calculate_sequence.pop(_index - 1))
                    if num_front >= cls._power_limit or num_back >= cls._power_limit:
                        raise CalculateException('单步运算算数大小超过限制上限', f'{num_front}, {num_back}')
                    result = num_front ** num_back
                    calculate_sequence.insert(_index - 1, result)
                    return calculate_sequence
        elif '*' in calculate_sequence or '/' in calculate_sequence:
            # 处理乘除法
            for _index, _obj in enumerate(calculate_sequence):
                # 从前向后匹配, 发现乘除法则直接进行运算并返回
                if _obj == '*':
                    num_back = float(calculate_sequence.pop(_index + 1))
                    # 移除运算符
                    calculate_sequence.pop(_index)
                    num_front = float(calculate_sequence.pop(_index - 1))
                    if num_front >= cls._multi_limit or num_back >= cls._multi_limit:
                        raise CalculateException('单步运算算数大小超过限制上限', f'{num_front}, {num_back}')
                    result = num_front * num_back
                    calculate_sequence.insert(_index - 1, result)
                    return calculate_sequence
                elif _obj == '/':
                    num_back = float(calculate_sequence.pop(_index + 1))
                    # 移除运算符
                    calculate_sequence.pop(_index)
                    num_front = float(calculate_sequence.pop(_index - 1))
                    if num_front >= cls._multi_limit or num_back >= cls._multi_limit:
                        raise CalculateException('单步运算算数大小超过限制上限', f'{num_front}, {num_back}')
                    result = num_front / num_back
                    calculate_sequence.insert(_index - 1, result)
                    return calculate_sequence
        elif '+' in calculate_sequence or '-' in calculate_sequence:
            # 处理加减法
            for _index, _obj in enumerate(calculate_sequence):
                # 从前向后匹配, 发现加减法则直接进行运算并返回
                if _obj == '+':
                    num_back = float(calculate_sequence.pop(_index + 1))
                    # 移除运算符
                    calculate_sequence.pop(_index)
                    num_front = float(calculate_sequence.pop(_index - 1))
                    if num_front >= cls._add_limit or num_back >= cls._add_limit:
                        raise CalculateException('单步运算算数大小超过限制上限', f'{num_front}, {num_back}')
                    result = num_front + num_back
                    calculate_sequence.insert(_index - 1, result)
                    return calculate_sequence
                elif _obj == '-':
                    num_back = float(calculate_sequence.pop(_index + 1))
                    # 移除运算符
                    calculate_sequence.pop(_index)
                    num_front = float(calculate_sequence.pop(_index - 1))
                    if num_front >= cls._add_limit or num_back >= cls._add_limit:
                        raise CalculateException('单步运算算数大小超过限制上限', f'{num_front}, {num_back}')
                    result = num_front - num_back
                    calculate_sequence.insert(_index - 1, result)
                    return calculate_sequence
        else:
            # 运算序列中已经没有运算符, 直接返回结果
            if len(calculate_sequence) == 1:
                return calculate_sequence
            else:
                raise CalculateException('执行分步运算错误, 非预期的结果', calculate_sequence)

    @classmethod
    def _calculate_exp(cls, expression: str) -> int:
        """解析并运算不含括号的简单运算"""
        # 移除空白字符
        expression = re.sub(r'\s', '', expression)
        # 移除首尾括号
        expression = expression.lstrip('(').rstrip(')')

        # 判断运算符合法
        if re.search(r'[^+\-*/^.\d]', expression):
            raise CalculateException('非法算式, 包含运算符之外的字符', expression)

        # 拆分所有运算符
        cal_seq: List[Union[str, int, float]] = [x for x in re.split(r'([+\-*/^])', expression) if x]
        if re.match(r'[+*/^]', cal_seq[0]) or re.match(r'[+\-*/^]', cal_seq[-1]):
            raise CalculateException('非法算式, 算式首尾出现运算符', expression)

        # 处理负数
        for _index, _obj in enumerate(cal_seq):
            # 负号在第一位
            if _obj == '-' and _index == 0 and re.match(r'^-?\d+?(\.\d+?)?$', str(cal_seq[_index + 1])):
                num = float(cal_seq.pop(_index + 1))
                cal_seq.pop(_index)
                cal_seq.insert(_index, -num)
            # 负号在中间
            elif _obj == '-' and re.match(r'^[+\-*/^]$', str(cal_seq[_index - 1])) and re.match(
                    r'^-?\d+?(\.\d+?)?$', str(cal_seq[_index + 1])):
                num = float(cal_seq.pop(_index + 1))
                cal_seq.pop(_index)
                cal_seq.insert(_index, -num)

        # 负数处理完后再次判断运算符合法
        for _index, _obj in enumerate(cal_seq):
            if re.match(r'^[+\-*/^]$', str(_obj)) and re.match(r'^[+\-*/^]$', str(cal_seq[_index - 1])):
                raise CalculateException('非法算式, 包含连续的运算符', expression)

        # 分步循环执行运算
        while len(cal_seq) != 1:
            cal_seq = cls.__handle_sequence_calculate(cal_seq)
        return int(cal_seq[0])

    def calculate(self, expression: str) -> int:
        """解析并运算"""
        _expression = self._prepare_exp(expression=expression)
        # 从最内层括号开始依次执行运算
        while inner_par := re.search(r'(\([+\-*/^.\d]+?\))', _expression):
            inner_cal_result = self._calculate_exp(inner_par.group())
            # 处理括号前 a(x+y) 的简写形式
            if re.match(r'.*\d$', _expression[:inner_par.start()]):
                _expression = f'{_expression[:inner_par.start()]}*{inner_cal_result}{_expression[inner_par.end():]}'
            else:
                _expression = f'{_expression[:inner_par.start()]}{inner_cal_result}{_expression[inner_par.end():]}'
        # 括号遍历完后执行最外层运算
        return self._calculate_exp(_expression)


class RandomTool(DiceToolMixin):

    @staticmethod
    def random(min_: int, max_: int):
        """该方法实现自定义随机数生成函数，可通过继承后重写来完成随机数算法的修改"""
        return random.randint(min_, max_)


class SimpleDice(BaseModel):
    """基础骰子"""
    num: int = 1
    side: int = 100


__all__ = [
    'Calculator',
    'CalculateException'
]