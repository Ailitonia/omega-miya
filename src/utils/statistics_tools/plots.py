"""
@Author         : Ailitonia
@Date           : 2024/8/26 10:33:44
@FileName       : plots.py
@Project        : omega-miya
@Description    : pyplot 图表实例创建工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import math
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from matplotlib import cm, colormaps, font_manager
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from nonebot import logger

from .config import statistics_tools_config

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from src.resource import TemporaryResource

# 添加中文字体
if statistics_tools_config.default_font.is_file:
    font_manager.fontManager.addfont(statistics_tools_config.default_font.path)
else:
    logger.warning(
        f'statistics_tools 默认字体文件不存在: {statistics_tools_config.default_font.resolve_path}, 已跳过注册'
    )
if statistics_tools_config.alternative_font.is_file:
    font_manager.fontManager.addfont(statistics_tools_config.alternative_font.path)
else:
    logger.warning(
        f'statistics_tools 备用字体文件不存在: {statistics_tools_config.alternative_font.resolve_path}, 已跳过注册'
    )

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


def _validate_output_filename(output_filename: str) -> None:
    """校验输出文件名必须为纯文件名, 不允许包含路径分隔符、目录穿越片段或绝对路径"""
    if not output_filename or Path(output_filename).name != output_filename:
        raise ValueError(f'invalid output filename: {output_filename!r}, expected a plain file name')


def _validate_output_format(fig: 'Figure', format_: str) -> None:
    """校验导出格式为当前画布支持的图片格式 (大小写不敏感)"""
    supported = fig.canvas.get_supported_filetypes()
    if format_.lower() not in supported:
        raise ValueError(f'unsupported output format: {format_!r}, supported: {sorted(supported)}')


def _format_bar_value(value: float) -> str:
    """将数值格式化为条形图标签文本, 整数值不带小数点"""
    if value == int(value):
        return str(int(value))
    return f'{value:.4f}'.rstrip('0').rstrip('.')


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


def create_dict_data_figure(
        data: dict[str, float],
        *,
        title: str | None = None,
        xlabel: str = '数值',
        ylabel: str = '名称',
        sort: Literal['desc', 'asc', 'keep'] = 'desc',
        colorbar: bool = True,
        cmap_name: str = 'plasma',
        figsize: tuple[float, float] | None = None,
        dpi: float | None = None,
) -> tuple['Figure', 'Axes']:
    """绘制 dict[str, float] 结构化数据的水平条形图 (含数值标签与颜色映射)

    :param data: 名称到数值的映射
    :param title: 图表标题, 缺省时不设置标题
    :param xlabel: x 轴标签
    :param ylabel: y 轴标签
    :param sort: 排序方式, 'desc' 按值自上而下从大到小, 'asc' 自上而下从小到大, 'keep' 保持传入顺序
    :param colorbar: 是否添加颜色条, 全部数值相等时忽略
    :param cmap_name: 颜色映射名称
    :param figsize: 画布尺寸, 缺省时高度按数据条目数自适应
    :param dpi: 画布分辨率
    :raises ValueError: data 为空或包含非有限数值 (NaN/Inf)
    """
    if not data:
        raise ValueError('data must not be empty')
    if not all(isinstance(v, (int, float)) for v in data.values()):
        raise ValueError('data values must be int or float')
    if not all(math.isfinite(v) for v in data.values()):
        raise ValueError('data values must be finite')

    items = list(data.items())
    if sort == 'desc':
        # barh 自下而上绘制, 升序排列使最大值展示在顶部
        items.sort(key=lambda x: x[1])
    elif sort == 'asc':
        items.sort(key=lambda x: x[1], reverse=True)

    y_names = [name for name, _ in items]
    x_values = [float(value) for _, value in items]

    if figsize is None:
        figsize = (12.8, 0.6 * len(items) + 2.4)

    fig, ax = create_simple_subplots_figure(figsize=figsize, dpi=dpi)

    cmap = colormaps[cmap_name]
    vmin, vmax = min(x_values), max(x_values)
    if vmin == vmax:
        # 全部数值相等时归一化分母为零, 退化为固定颜色
        bar_colors = cmap(0.7)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)
        bar_colors = cmap(norm(x_values))

    bar = ax.barh(y_names, x_values, color=bar_colors)
    ax.bar_label(bar, labels=[_format_bar_value(v) for v in x_values], label_type='edge')
    if colorbar and vmin != vmax:
        fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation='horizontal')

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title is not None:
        ax.set_title(title)

    return fig, ax


def draw_dict_data(
        data: dict[str, float],
        output_filename: str,
        *,
        title: str | None = None,
        xlabel: str = '数值',
        ylabel: str = '名称',
        sort: Literal['desc', 'asc', 'keep'] = 'desc',
        colorbar: bool = True,
        cmap_name: str = 'plasma',
        figsize: tuple[float, float] | None = None,
        dpi: float | None = None,
        output_dpi: int = 300,
) -> 'TemporaryResource':
    """一步到位绘制 dict[str, float] 结构化数据并导出为图片文件, 参数说明见 create_dict_data_figure"""
    fig, _ = create_dict_data_figure(
        data,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        sort=sort,
        colorbar=colorbar,
        cmap_name=cmap_name,
        figsize=figsize,
        dpi=dpi,
    )
    return output_figure(fig, output_filename, dpi=output_dpi)


def output_figure(
        fig: 'Figure',
        output_filename: str,
        *,
        dpi: int = 300,
        format_: str = 'JPG',
        bbox_inches: str = 'tight',
        **kwargs
) -> 'TemporaryResource':
    """保存并导出生成的图表

    无论保存成功与否, 最终都会关闭并释放 Figure 实例;
    文件名或格式校验失败时直接抛出 ValueError 且不接管 Figure 实例

    :raises ValueError: output_filename 不是合法的纯文件名, 或 format_ 不是画布支持的导出格式
    """
    _validate_output_filename(output_filename)
    _validate_output_format(fig, format_)
    output_file = statistics_tools_config.default_output_folder(output_filename)
    try:
        with output_file.open('wb') as f:
            fig.savefig(f, dpi=dpi, format=format_, bbox_inches=bbox_inches, **kwargs)
    except Exception as e:
        logger.warning(f'导出图表失败, output: {output_file.resolve_path}, error: {e!r}')
        raise
    finally:
        plt.close(fig)
    return output_file


__all__ = [
    'create_dict_data_figure',
    'create_simple_figure',
    'create_simple_subplots_figure',
    'draw_dict_data',
    'output_figure',
]
