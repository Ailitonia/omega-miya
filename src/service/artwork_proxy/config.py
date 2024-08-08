"""
@Author         : Ailitonia
@Date           : 2024/8/4 下午7:06
@FileName       : config
@Project        : nonebot2_miya
@Description    : Artwork Proxy Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.resource import StaticResource, TemporaryResource


class ArtworkProxyPathConfig(object):
    """作品本地缓存路径配置"""
    _default_text_font_name: str = 'SourceHanSansSC-Regular.otf'
    _default_theme_font_name: str = 'fzzxhk.ttf'

    def __init__(self, base_path_name: str):
        self.__base = base_path_name

    @property
    def text_font(self) -> StaticResource:
        """默认文本字体"""
        return StaticResource('fonts', self._default_text_font_name)

    @property
    def theme_font(self) -> StaticResource:
        """默认主题字体"""
        return StaticResource('fonts', self._default_theme_font_name)

    @property
    def base_path(self) -> TemporaryResource:
        """缓存文件主目录"""
        return TemporaryResource(self.__base)

    @property
    def meta_path(self) -> TemporaryResource:
        """作品元数据文件目录"""
        return self.base_path('metadata')

    @property
    def artwork_path(self) -> TemporaryResource:
        """作品图片缓存文件目录"""
        return self.base_path('artwork')

    @property
    def preview_path(self) -> TemporaryResource:
        """生成预览图缓存文件目录"""
        return self.base_path('preview')

    @property
    def processed_path(self) -> TemporaryResource:
        """处理后图片缓存文件目录"""
        return self.base_path('processed')


__all__ = [
    'ArtworkProxyPathConfig'
]
