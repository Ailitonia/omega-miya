"""
@Author         : Ailitonia
@Date           : 2025/4/29 11:29:13
@FileName       : config.py
@Project        : omega-miya
@Description    : statistics_tools 模块配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource


class StatisticsToolsConfig(BaseModel):
    # 字体文件
    statistics_tools_default_font_name: str = 'msyh.ttc'
    statistics_tools_alternative_font_name: str = 'fzzxhk.ttf'
    # 默认缓存资源保存路径
    statistics_tools_default_output_folder_name: str = 'statistics_tools'

    model_config = ConfigDict(extra='ignore')

    @property
    def default_font(self) -> StaticResource:
        return StaticResource('fonts', self.statistics_tools_default_font_name)

    @property
    def alternative_font(self) -> StaticResource:
        return StaticResource('fonts', self.statistics_tools_alternative_font_name)

    @property
    def default_output_folder(self) -> TemporaryResource:
        """生成图片保存路径"""
        return TemporaryResource(self.statistics_tools_default_output_folder_name, 'output')


try:
    statistics_tools_config = get_plugin_config(StatisticsToolsConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>StatisticsTools 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'StatisticsTools 配置格式验证失败, {e}')

__all__ = [
    'statistics_tools_config',
]
