"""
@Author         : Ailitonia
@Date           : 2021/07/17 2:04
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource
from src.service.artwork_collection import ALLOW_ARTWORK_ORIGIN


class SignInConfig(BaseModel):
    """签到插件配置"""
    # 是否启用正则匹配matcher
    # 如果 bot 配置了命令前缀, 但需要额外响应无前缀的 "签到" 等消息, 请将本选项设置为 True
    # 如果 bot 没有配置命令前缀或空白前缀, 请将本选项设置为 False, 避免重复响应
    signin_plugin_enable_full_matcher: bool = True

    # 签到头图图库来源, 可配置: pixiv, danbooru, gelbooru, konachan, yandere, local
    # 特别的: 当配置为 `None` 时, 代表从所有的来源随机获取
    # 配置后需要数据库里面有图才能正常获取到
    signin_plugin_top_image_origin: ALLOW_ARTWORK_ORIGIN | None = 'pixiv'

    # 相关数值显示命令
    signin_plugin_friendship_alias: str = '好感度'
    signin_plugin_energy_alias: str = '能量值'
    signin_plugin_currency_alias: str = '硬币'

    # 能量值与好感度的兑换比例 公式为(能量值 * 兑换比 = 好感度)
    signin_plugin_ef_exchange_rate: float = 0.5
    # 每日首次签到获取的基础硬币数 同时也是补签所需硬币的倍率基数
    signin_plugin_base_currency: int = 5

    model_config = ConfigDict(extra='ignore')


@dataclass
class SignLocalResourceConfig:
    """签到插件文件配置"""
    # 默认内置的静态资源文件路径
    default_font_folder: StaticResource = StaticResource('fonts')
    default_font: StaticResource = default_font_folder('SourceHanSansSC-Regular.otf')
    default_bold_font: StaticResource = default_font_folder('SourceHanSansSC-Heavy.otf')
    default_level_font: StaticResource = default_font_folder('pixel.ttf')
    default_footer_font: StaticResource = default_font_folder('fzzxhk.ttf')

    # 默认生成的缓存资源保存路径
    default_save_folder: TemporaryResource = TemporaryResource('sign_in')

    # 求签事件资源路径
    default_fortune: StaticResource = StaticResource('docs', 'fortune', 'event.json')
    addition_fortune: TemporaryResource = TemporaryResource('fortune', 'event.json')


try:
    sign_local_resource_config = SignLocalResourceConfig()
    sign_in_config = get_plugin_config(SignInConfig)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>OmegaSignIn 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'OmegaSignIn 插件配置格式验证失败, {e}')


__all__ = [
    'sign_in_config',
    'sign_local_resource_config',
]
