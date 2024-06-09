"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午6:55
@FileName       : config
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource


class NhentaiConfig(BaseModel):
    """Nhentai 配置"""
    nhentai_csrftoken: str | None = None
    nhentai_sessionid: str | None = None

    model_config = ConfigDict(extra="ignore")

    @property
    def nhentai_cookies(self) -> dict[str, str] | None:
        if self.nhentai_csrftoken is not None and self.nhentai_sessionid is not None:
            return {'csrftoken': self.nhentai_csrftoken, 'sessionid': self.nhentai_sessionid}
        else:
            return None


@dataclass
class NhentaiResourceConfig:
    """Nhentai 配置"""
    # 默认字体文件
    default_font_file: StaticResource = StaticResource('fonts', 'fzzxhk.ttf')
    # 默认的下载文件路径
    default_download_folder: TemporaryResource = TemporaryResource('nhentai', 'download')
    # 预览图生成路径
    default_preview_img_folder: TemporaryResource = TemporaryResource('nhentai', 'preview')
    default_preview_size: tuple[int, int] = (224, 327)  # 默认预览图缩略图大小


try:
    nhentai_resource_config = NhentaiResourceConfig()
    nhentai_config = get_plugin_config(NhentaiConfig)
    if not nhentai_config.nhentai_cookies:
        logger.opt(colors=True).debug(f'<lc>Nhentai</lc> | <ly>未配置 Nhentai Cookies</ly>')
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Nhentai 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Nhentai 配置格式验证失败, {e}')


__all__ = [
    'nhentai_config',
    'nhentai_resource_config'
]
