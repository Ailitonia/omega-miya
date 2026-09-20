"""
@Author         : Ailitonia
@Date           : 2024/8/26 10:53:19
@FileName       : sample.py
@Project        : omega-miya
@Description    : 示范用例
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from collections import Counter
from typing import TYPE_CHECKING

import numpy as np

from .plots import create_simple_subplots_figure, output_figure

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from src.resource import TemporaryResource


def run_figure_example() -> 'TemporaryResource':
    x = np.linspace(0, 2, 100)  # Sample data.

    # Note that even in the OO-style, we use `.pyplot.figure` to create the Figure.
    fig, ax = create_simple_subplots_figure(figsize=(5, 2.7))
    ax.plot(x, x, label='linear')  # Plot some data on the axes.
    ax.plot(x, x ** 2, label='quadratic')  # Plot more data on the axes...
    ax.plot(x, x ** 3, label='cubic')  # ... and some more.
    ax.set_xlabel('x label')  # Add an x-label to the axes.
    ax.set_ylabel('y label')  # Add a y-label to the axes.
    ax.set_title('Simple Plot')  # Add a title to the axes.
    ax.legend()  # Add a legend.

    return output_figure(fig, 'sample.jpg')


def invest_test(step: int = 100, init_balance: float = 1000000.0, seed: int | None = None) -> 'NDArray':
    rng = np.random.default_rng(seed)
    rand_ar = rng.random(step)
    # 单步胜率乘数 0.5 + 0.5 * 2.6 = 1.8, 败率乘数 0.5, 余额为初始余额乘逐项乘累积积
    multipliers = np.where(rand_ar >= 0.5, 1.8, 0.5)
    balance_ar = np.concatenate(([init_balance], init_balance * np.cumprod(multipliers)))
    return balance_ar


def run_invest_test(step: int = 100, times: int = 10, seed: int | None = None) -> 'TemporaryResource':
    fig, ax = create_simple_subplots_figure(figsize=(32, 16))
    ax.set_yscale('log')
    for i in range(times):
        ax.plot(np.arange(step + 1), invest_test(step=step, seed=None if seed is None else seed + i))

    x_axis = np.arange(step + 1)
    ax.plot(x_axis, np.full(step + 1, 1e6), color='green', linestyle=':')
    ax.plot(x_axis, np.full(step + 1, 1e5), color='orange', linestyle=':')
    ax.plot(x_axis, np.full(step + 1, 1), color='red', linestyle=':')

    ax.set_xlabel('投资次数')
    ax.set_ylabel('金额')
    ax.set_title('投资-金额图表')

    return output_figure(fig, 'invest_test.jpg')


def coin_test(init_balance: int = 0, seed: int | None = None) -> tuple['NDArray', int]:
    rng = random.Random(seed)
    total_balance = init_balance
    balance_list: list[float] = [init_balance]
    step = 0
    while True:
        step += 1
        total_balance -= 20
        if rng.random() >= 0.5:
            total_balance += 2 ** step
            balance_list.append(total_balance)
            break
        else:
            balance_list.append(total_balance)

    return np.array(balance_list), step


def run_coin_test(times: int = 10, seed: int | None = None) -> 'TemporaryResource':
    fig, ax = create_simple_subplots_figure(figsize=(8, 6))
    data: list[int] = [int(coin_test(seed=None if seed is None else seed + i)[0][-1]) for i in range(times)]

    count = dict(sorted(Counter(data).items(), key=lambda x: x[0]))
    bar = ax.bar([str(x) for x in count.keys()], [int(y) for y in count.values()])

    ax.bar_label(bar)
    ax.set_xlabel('最终金额')
    ax.set_ylabel('出现次数')
    ax.set_title('最终金额分布图表')

    return output_figure(fig, 'coin_test.jpg')


if __name__ == '__main__':
    run_figure_example()
    run_invest_test()
    run_coin_test()

__all__ = []
