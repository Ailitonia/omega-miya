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
from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError
from omega_miya.local_resource import LocalResource, TmpResource


class SignInConfig(BaseModel):
    """签到插件配置"""
    # 是否启用正则匹配matcher
    # 如果 bot 配置了命令前缀, 但需要额外响应无前缀的 "签到" 等消息, 请将本选项设置为 True
    # 如果 bot 没有配置命令前缀或空白前缀, 请将本选项设置为 False, 避免重复响应
    signin_enable_regex_matcher: bool = True

    # 是否启用自动下载签到头图的定时任务
    # 会大幅增加 pixiv 缓存文件量, 硬盘空间小于 10G 请谨慎开启
    signin_enable_preparing_scheduler: bool = False

    # 相关数值显示命令
    signin_friendship_alias: str = '好感度'
    signin_energy_alias: str = '能量值'
    signin_currency_alias: str = '硬币'

    # 能量值与好感度的兑换比例 公式为(能量值 * 兑换比 = 好感度)
    signin_ef_exchange_rate: float = 0.25
    # 每日首次签到获取的基础硬币数 同时也是补签所需硬币的倍率基数
    signin_base_currency: int = 5

    # 是否启用求签事件导入 api
    signin_enable_fortune_import_api: bool = False

    class Config:
        extra = "ignore"


@dataclass
class SignLocalResourceConfig:
    """签到插件文件配置"""
    # 默认内置的静态资源文件路径
    default_font_folder: LocalResource = LocalResource('fonts')
    default_font: LocalResource = default_font_folder('SourceHanSansSC-Regular.otf')
    default_bold_font: LocalResource = default_font_folder('SourceHanSansSC-Heavy.otf')
    default_level_font: LocalResource = default_font_folder('pixel.ttf')
    default_footer_font: LocalResource = default_font_folder('fzzxhk.ttf')
    # 默认的缓存资源保存路径
    default_save_folder: TmpResource = TmpResource('sign_in')

    # 求签事件资源路径
    default_fortune_event: LocalResource = LocalResource('docs', 'fortune', 'event.json')
    tmp_fortune_event: TmpResource = TmpResource('fortune', 'event.json')
    fortune_event_import_file: TmpResource = TmpResource('fortune', 'fortune_event_import.xlsx')


try:
    sign_local_resource_config = SignLocalResourceConfig()
    sign_in_config = SignInConfig.parse_obj(get_driver().config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>SignIn 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'SignIn 插件格式验证失败, {e}')


__all__ = [
    'sign_in_config',
    'sign_local_resource_config'
]
