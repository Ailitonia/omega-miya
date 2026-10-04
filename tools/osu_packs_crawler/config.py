"""
@Author         : Ailitonia
@Date           : 2025/5/18 16:18
@FileName       : config
@Project        : omega-miya
@Description    : osu! web 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.resource import TemporaryResource


class OsuWebConfig(BaseModel):
    """osu! web 配置"""
    omega_tool_osu_web_session: str | None = None

    omega_tool_osu_output_root_folder: str = Field(default='osu_packs_crawler')
    """导出曲包根目录名"""
    omega_tool_osu_pack_meta_folder_name: str = Field(default='beatmaps_pack_meta')
    """导出曲包元数据保存目录名"""
    omega_tool_osu_download_urls_folder_name: str = Field(default='download_urls')
    """导出曲包下载链接保存目录名"""

    model_config = ConfigDict(extra='ignore')

    @property
    def osu_session(self) -> dict[str, str]:
        return (
            {'osu_session': self.omega_tool_osu_web_session}
            if self.omega_tool_osu_web_session is not None
            else {}
        )

    @property
    def root_dir(self) -> TemporaryResource:
        return TemporaryResource(self.omega_tool_osu_output_root_folder)

    @property
    def meta_dir(self) -> TemporaryResource:
        return self.root_dir(self.omega_tool_osu_pack_meta_folder_name)

    @property
    def urls_dir(self) -> TemporaryResource:
        return self.root_dir(self.omega_tool_osu_download_urls_folder_name)


try:
    osu_web_config = get_plugin_config(OsuWebConfig)
    if not osu_web_config.omega_tool_osu_web_session:
        logger.opt(colors=True).debug('<lc>osu! web</lc> | <ly>未配置 osu_session Cookies</ly>')
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>osu! web 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'osu! web 配置格式验证失败, {e}')

__all__ = [
    'osu_web_config',
]
