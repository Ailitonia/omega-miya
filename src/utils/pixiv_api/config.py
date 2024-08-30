"""
@Author         : Ailitonia
@Date           : 2022/04/05 21:26
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Pixiv Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class PixivConfig(BaseModel):
    """Pixiv 配置"""
    pixiv_phpsessid: str | None = None

    model_config = ConfigDict(extra='ignore')

    @property
    def cookie_phpssid(self) -> dict[str, str]:
        return {'PHPSESSID': self.pixiv_phpsessid} if self.pixiv_phpsessid is not None else {}


try:
    pixiv_config = get_plugin_config(PixivConfig)
    if not pixiv_config.pixiv_phpsessid:
        logger.opt(colors=True).warning(f'<lc>Pixiv</lc> | <lr>未配置 Pixiv Cookie</lr>, <ly>部分功能可能无法正常使用</ly>')
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Pixiv 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Pixiv 配置格式验证失败, {e}')


__all__ = [
    'pixiv_config',
]
