"""
@Author         : Ailitonia
@Date           : 2022/04/05 21:26
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Pixiv Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError
from omega_miya.local_resource import LocalResource, TmpResource


class PixivConfig(BaseModel):
    """Pixiv 配置"""
    pixiv_phpsessid: str | None = None

    class Config:
        extra = "ignore"

    @property
    def cookie_phpssid(self) -> dict[str, str] | None:
        return {'PHPSESSID': self.pixiv_phpsessid} if self.pixiv_phpsessid is not None else None


@dataclass
class PixivLocalResourceConfig:
    # pixiv module 需要的相关配置参数, 不要随便乱改
    # 默认内置的静态资源文件路径
    default_font_name: str = 'SourceHanSansSC-Regular.otf'
    default_font_folder: LocalResource = LocalResource('fonts')
    default_font_file: LocalResource = default_font_folder(default_font_name)
    default_preview_font: LocalResource = default_font_folder('fzzxhk.ttf')
    # 默认的缓存资源保存路径
    default_artwork_folder: TmpResource = TmpResource('pixiv', 'artwork')
    default_download_folder: TmpResource = TmpResource('pixiv', 'download')
    default_ugoira_gif_folder: TmpResource = TmpResource('pixiv', 'ugoira_gif')
    # 图片绘制相关参数
    default_preview_img_folder: TmpResource = TmpResource('pixiv', 'preview')
    default_preview_size: tuple[int, int] = (250, 250)  # 默认预览图缩略图大小
    user_searching_card_ratio: float = 6.75  # 注意这里的图片长宽比会直接影响到排版 不要随便改
    user_searching_card_num: int = 8  # 图中绘制的画师搜索结果数量限制


try:
    pixiv_resource_config = PixivLocalResourceConfig()
    pixiv_config = PixivConfig.parse_obj(get_driver().config)
    if not pixiv_config.pixiv_phpsessid:
        logger.opt(colors=True).warning(f'<lc>Pixiv</lc> | <lr>未配置 Pixiv Cookie</lr>, <ly>部分功能可能无法正常使用</ly>')
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Pixiv 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Pixiv 配置格式验证失败, {e}')


__all__ = [
    'pixiv_config',
    'pixiv_resource_config'
]
