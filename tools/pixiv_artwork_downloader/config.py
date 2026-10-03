"""
@Author         : Ailitonia
@Date           : 2026/10/3 19:05
@FileName       : config
@Project        : omega-miya
@Description    : pixiv_artwork_downloader 工具配置项
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, Field, ValidationError

from src.resource import AnyResource, BaseResource, TemporaryResource


class PixivArtworkDownloaderConfig(BaseModel):
    """Pixiv 下载工具配置"""

    omega_tool_pixiv_download_root_folder: str | None = Field(default=None)
    """下载根目录 (应当为完整地址)"""
    omega_tool_pixiv_download_save_folder_name: str | None = Field(default=None)
    """下载作品保存文件目录名"""
    omega_tool_pixiv_download_artists_folder_name: str | None = Field(default=None)
    """下载用户作品保存文件目录名"""
    omega_tool_pixiv_download_favorites_folder_name: str | None = Field(default=None)
    """下载收藏作品保存文件目录名"""

    @property
    def root_dir(self) -> BaseResource:
        if self.omega_tool_pixiv_download_root_folder is None:
            return TemporaryResource('pixiv_artwork_downloader')

        root_dir = AnyResource(self.omega_tool_pixiv_download_root_folder)
        root_dir.raise_not_dir()
        return root_dir

    @property
    def save_dir(self) -> BaseResource:
        return self.root_dir(self.omega_tool_pixiv_download_save_folder_name or 'download')

    @property
    def artists_dir(self) -> BaseResource:
        return self.root_dir(self.omega_tool_pixiv_download_artists_folder_name or 'artists')

    @property
    def favorites_dir(self) -> BaseResource:
        return self.root_dir(self.omega_tool_pixiv_download_favorites_folder_name or 'favorites')


try:
    downloader_config = get_plugin_config(PixivArtworkDownloaderConfig)
    _ = downloader_config.root_dir
except (ValidationError, ValueError) as e:
    import sys

    logger.opt(colors=True).critical(f'<lc>PixivArtworkDownloader</lc> | 配置格式验证失败, 错误信息:\n{e}')
    sys.exit(f'PixivArtworkDownloader 配置格式验证失败, {e}')

__all__ = [
    'downloader_config',
]
