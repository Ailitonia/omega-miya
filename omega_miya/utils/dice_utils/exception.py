"""
@Author         : Ailitonia
@Date           : 2021/07/18 1:36
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


class DiceBaseException(Exception):
    pass


class CalculateException(DiceBaseException):
    """
    计算模块异常
    """
    def __init__(self, reason, expression):
        self.reason = reason
        self.expression = expression

    def __repr__(self):
        return f'<CalculateException, reason={self.reason}, expression={self.expression}>'

    def __str__(self):
        return self.__repr__()
