"""
@Author         : Ailitonia
@Date           : 2022/04/10 21:25
@FileName       : config.py
@Project        : nonebot2_miya
@Description    : ZipUtils config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import zipfile

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import TemporaryResource


class ZipUtilsConfig(BaseModel):
    """ZipUtils 配置"""
    zip_utils_default_zip_compression: int = zipfile.ZIP_STORED

    # 默认缓存资源保存路径
    zip_utils_default_output_folder_name: str = 'zip_utils'

    model_config = ConfigDict(extra='ignore')

    @property
    def default_output_folder(self) -> TemporaryResource:
        return TemporaryResource(self.zip_utils_default_output_folder_name)


try:
    zip_utils_config = get_plugin_config(ZipUtilsConfig)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>ZipUtils 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'ZipUtils 配置格式验证失败, {e}')


__all__ = [
    'zip_utils_config',
]
