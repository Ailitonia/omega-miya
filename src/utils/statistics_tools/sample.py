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

from .consts import STATISTICS_TOOLS_RESOURCE
from .plots import create_simple_subplots_figure

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from src.resource import TemporaryResource


def run_figure_example() -> "TemporaryResource":
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

    output_file = STATISTICS_TOOLS_RESOURCE.default_output_folder('sample.jpg')
    with output_file.open('wb') as f:
        fig.savefig(f, dpi=300, format='JPG', bbox_inches='tight')
    return output_file


def invest_test(step: int = 100, init_balance: float = 1000000.0) -> "NDArray":
    total_balance = init_balance
    rand_ar = np.random.rand(step)
    balance_ar = np.array(init_balance)
    for i in range(step):
        if rand_ar[i] >= 0.5:
            total_balance = total_balance * 0.5 + total_balance * 0.5 * 2.6
        else:
            total_balance = total_balance * 0.5
        balance_ar = np.append(balance_ar, total_balance)
    return balance_ar


def run_invest_test(step: int = 100, times: int = 10) -> "TemporaryResource":
    fig, ax = create_simple_subplots_figure(figsize=(32, 16))
    ax.set_yscale('log')
    for _ in range(times):
        ax.plot(np.arange(step + 1), invest_test(step=step))

    ax.plot(np.arange(step + 1), np.linspace(1e6, 1e6, step + 1), color='green', linestyle=':')
    ax.plot(np.arange(step + 1), np.linspace(1e5, 1e5, step + 1), color='orange', linestyle=':')
    ax.plot(np.arange(step + 1), np.linspace(1, 1, step + 1), color='red', linestyle=':')

    ax.set_xlabel('投资次数')
    ax.set_ylabel('金额')
    ax.set_title('投资-金额图表')

    output_file = STATISTICS_TOOLS_RESOURCE.default_output_folder('invest_test.jpg')
    with output_file.open('wb') as f:
        fig.savefig(f, dpi=300, format='JPG', bbox_inches='tight')
    return output_file


def coin_test(init_balance: int = 0) -> tuple["NDArray", int]:
    total_balance = init_balance
    balance_ar = np.array(init_balance)
    step = 0
    while True:
        step += 1
        total_balance -= 20
        if random.random() >= 0.5:
            total_balance += 2 ** step
            balance_ar = np.append(balance_ar, total_balance)
            break
        else:
            balance_ar = np.append(balance_ar, total_balance)

    return balance_ar, step


def run_coin_test(times: int = 10) -> "TemporaryResource":
    fig, ax = create_simple_subplots_figure(figsize=(8, 6))
    data: list[int] = [int(coin_test()[0][-1]) for _ in range(times)]

    count = {k: v for (k, v) in sorted(Counter(data).items(), key=lambda x: x[0])}
    bar = ax.bar([str(x) for x in count.keys()], [int(y) for y in count.values()])

    ax.bar_label(bar)
    ax.set_xlabel('最终金额')
    ax.set_ylabel('出现次数')
    ax.set_title('最终金额分布图表')

    output_file = STATISTICS_TOOLS_RESOURCE.default_output_folder('coin_test.jpg')
    with output_file.open('wb') as f:
        fig.savefig(f, dpi=300, format='JPG', bbox_inches='tight')
    return output_file


if __name__ == '__main__':
    run_figure_example()
    run_invest_test()
    run_coin_test()

__all__ = []
