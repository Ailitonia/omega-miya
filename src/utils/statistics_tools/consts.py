"""
@Author         : Ailitonia
@Date           : 2024/8/26 10:24:10
@FileName       : consts.py
@Project        : omega-miya
@Description    : 静态资源文件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from src.resource import StaticResource, TemporaryResource


@dataclass
class StatisticsToolsResource:
    # 默认字体文件
    default_font_file: StaticResource = StaticResource('fonts', 'msyh.ttc')

    # 默认的缓存资源保存路径
    default_output_folder: TemporaryResource = TemporaryResource('statistics_tools', 'output')


STATISTICS_TOOLS_RESOURCE = StatisticsToolsResource()

__all__ = [
    'STATISTICS_TOOLS_RESOURCE',
]
