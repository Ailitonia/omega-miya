"""
@Author         : Ailitonia
@Date           : 2021/08/15 1:20
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 统计做图工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import sys
from datetime import datetime
from io import BytesIO
from matplotlib import font_manager
from matplotlib import pyplot as plt

from nonebot.utils import run_sync

from src.database.internal.statistic import CountStatisticModel
from src.resource import StaticResource, TemporaryResource


_DEFAULT_FONT: StaticResource = StaticResource('fonts', 'fzzxhk.ttf')
"""默认使用字体"""
_TMP_STATISTIC_PATH: TemporaryResource = TemporaryResource('statistic')
"""生成统计图临时文件路径"""


# 添加资源文件中字体
font_manager.fontManager.addfont(_DEFAULT_FONT.resolve_path)


async def draw_statistics(
        statistics_data: list[CountStatisticModel],
        title: str = '插件使用统计'
) -> TemporaryResource:
    """绘制插件使用统计图

    :param statistics_data: 统计信息
    :param title: 图表标题
    """

    @run_sync
    def _handle(statistics_data_: list[CountStatisticModel]) -> bytes:
        plt.switch_backend('agg')  # Fix RuntimeError caused by GUI needed
        plt.rcParams['font.sans-serif'] = ['FZZhengHei-EL-GBK']
        if sys.platform.startswith('win'):
            plt.rcParams['axes.unicode_minus'] = False

        # 绘制条形图
        _bar_c = plt.barh([x.custom_name for x in statistics_data_], [x.call_count for x in statistics_data_])
        plt.bar_label(_bar_c, label_type='edge')
        plt.title(title)

        # 导出图片
        with BytesIO() as bf:
            plt.savefig(bf, dpi=300, format='JPG', bbox_inches='tight')
            img_bytes = bf.getvalue()
        plt.clf()
        return img_bytes

    image_content = await _handle(statistics_data_=statistics_data)
    image_file_name = f"statistic_{title}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"
    save_file = _TMP_STATISTIC_PATH(image_file_name)
    async with save_file.async_open('wb') as af:
        await af.write(image_content)
    return save_file


__all__ = [
    'draw_statistics'
]
