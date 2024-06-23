"""
@Author         : Ailitonia
@Date           : 2024/5/26 下午7:44
@FileName       : config
@Project        : nonebot2_miya
@Description    : 18Comic Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import TemporaryResource


class Comic18Config(BaseModel):
    """Comic18 配置"""
    comic18_cookie_avs: str | None = None

    model_config = ConfigDict(extra="ignore")

    @property
    def cookies(self) -> dict[str, str] | None:
        return {'AVS': self.comic18_cookie_avs} if self.comic18_cookie_avs is not None else None


@dataclass
class Comic18LocalResourceConfig:
    # 默认的缓存资源保存路径
    default_preview_folder: TemporaryResource = TemporaryResource('comic18', 'preview')
    default_download_folder: TemporaryResource = TemporaryResource('comic18', 'download')


try:
    comic18_resource_config = Comic18LocalResourceConfig()
    comic18_config = get_plugin_config(Comic18Config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Comic18 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Comic18 配置格式验证失败, {e}')


__all__ = [
    'comic18_config',
    'comic18_resource_config'
]
