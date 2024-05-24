"""
@Author         : Ailitonia
@Date           : 2023/11/8 22:37
@FileName       : model
@Project        : nonebot2_miya
@Description    : 工具类实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any


class Stack(object):
    """LIFO 实现"""
    def __init__(self):
        self.items: list = []

    def is_empty(self) -> bool:
        return self.items == []

    def push(self, item: Any) -> None:
        self.items.append(item)

    def pop(self) -> Any:
        return self.items.pop()

    def peek(self) -> Any:
        return self.items[-1]

    def size(self) -> int:
        return len(self.items)


def par_checker(symbol_string: str) -> bool:
    """符号匹配"""

    def _matches(open_: str, close_: str) -> bool:
        opens = '([{'
        closers = ')]}'
        return opens.index(open_) == closers.index(close_)

    s = Stack()
    balanced = True

    for symbol in str(symbol_string):
        if not balanced:
            break

        if symbol in '(':
            s.push(symbol)
        else:
            if s.is_empty():
                balanced = False
            else:
                s.pop()

    if balanced and s.is_empty():
        return True
    else:
        return False
