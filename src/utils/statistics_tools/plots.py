"""
@Author         : Ailitonia
@Date           : 2024/8/26 10:33:44
@FileName       : plots.py
@Project        : omega-miya
@Description    : pyplot 图表实例创建工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import sys
from typing import TYPE_CHECKING

from matplotlib import font_manager
from matplotlib import pyplot as plt

from .consts import STATISTICS_TOOLS_RESOURCE

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from src.resource import TemporaryResource

# 添加中文字体
font_manager.fontManager.addfont(STATISTICS_TOOLS_RESOURCE.default_font_file.path)
font_manager.fontManager.addfont(STATISTICS_TOOLS_RESOURCE.alternative_font_file.path)

# 设置字体
plt.rcParams['font.family'] = ['sans-serif']
plt.rcParams['font.sans-serif'].insert(0, 'Microsoft YaHei')
plt.rcParams['font.sans-serif'].insert(1, 'FZZhengHei-EL-GBK')

# Fix RuntimeError caused by GUI needed
plt.switch_backend('agg')
if sys.platform.startswith('win'):
    plt.rcParams['axes.unicode_minus'] = False

# 启用约束布局
plt.rcParams['figure.constrained_layout.use'] = True


def get_font_names() -> list[str]:
    """获取所有已加载的字体名"""
    # (font.name, font.fname) for font in font_manager.fontManager.ttflist
    return font_manager.get_font_names()


def create_simple_figure(
        *,
        num: int | None = None,
        figsize: tuple[float, float] | None = None,
        dpi: float | None = None,
        **kwargs
) -> 'Figure':
    """Create an empty figure with no Axes"""
    fig = plt.figure(num=num, figsize=figsize, dpi=dpi, **kwargs)
    return fig


def create_simple_subplots_figure(
        *,
        figsize: tuple[float, float] | None = None,
        dpi: float | None = None,
) -> tuple['Figure', 'Axes']:
    """Create a figure with a single Axes"""
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize, dpi=dpi)
    return fig, ax


def output_figure(
        fig: 'Figure',
        output_filename: str,
        *,
        dpi: int = 300,
        format_: str = 'JPG',
        bbox_inches: str = 'tight',
        **kwargs
) -> 'TemporaryResource':
    """保存并导出生成的图表"""
    output_file = STATISTICS_TOOLS_RESOURCE.default_output_folder(output_filename)
    with output_file.open('wb') as f:
        fig.savefig(f, dpi=dpi, format=format_, bbox_inches=bbox_inches, **kwargs)
    return output_file


__all__ = [
    'create_simple_figure',
    'create_simple_subplots_figure',
    'output_figure',
]
