"""
@Author         : Ailitonia
@Date           : 2021/08/15 1:20
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 统计做图工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

import matplotlib.cm as cm
from matplotlib.colors import Normalize
from nonebot.utils import run_sync

from src.utils.statistics_tools import create_simple_subplots_figure, output_figure

if TYPE_CHECKING:
    from src.database.internal.statistic import CountStatisticModel
    from src.resource import TemporaryResource


async def draw_statistics(
        statistics_data: Sequence['CountStatisticModel'],
        title: str = '插件使用情况统计',
) -> 'TemporaryResource':
    """绘制插件使用统计图

    :param statistics_data: 统计信息
    :param title: 图表标题
    """

    @run_sync
    def _handle(_statistics_data: Sequence['CountStatisticModel']) -> 'TemporaryResource':
        y_name = [x.custom_name for x in _statistics_data]
        x_value = [x.call_count for x in _statistics_data]

        # 归一化数据以适用于颜色映射
        viridis = cm.get_cmap('plasma')
        norm = Normalize(vmin=min(x_value), vmax=max(x_value))

        # 绘制条形图
        fig, ax = create_simple_subplots_figure()
        bar = ax.barh(y_name, x_value, color=viridis(norm(x_value)))
        # 添加数据标签
        ax.bar_label(bar, label_type='edge')
        # 添加颜色条
        fig.colorbar(cm.ScalarMappable(norm=norm, cmap=viridis), ax=ax, orientation='horizontal')
        # 添加坐标轴标签和图表标题
        ax.set_xlabel('调用次数')
        ax.set_ylabel('插件名称')
        ax.set_title(title)

        # 导出图片
        file_name = f"statistic_{title}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.jpg"
        return output_figure(fig, file_name)

    return await _handle(_statistics_data=sorted(statistics_data, key=lambda x: x.call_count))


__all__ = [
    'draw_statistics',
]
