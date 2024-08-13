"""
@Author         : Ailitonia
@Date           : 2024/4/25 上午12:35
@FileName       : config
@Project        : nonebot2_miya
@Description    : shindan maker config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class ShindanMakerPluginConfig(BaseModel):
    """ShindanMaker 插件配置"""
    # 站点类型
    shindan_maker_plugin_domain_version: Literal['default', 'cn'] = 'cn'

    model_config = ConfigDict(extra='ignore')

    @property
    def root_url(self) -> str:
        return self._get_root_url()

    def _get_root_url(self) -> str:
        """获取对应版本网站 url"""
        match self.shindan_maker_plugin_domain_version:
            case 'cn':
                return 'https://cn.shindanmaker.com'
            case 'default' | _:
                return 'https://shindanmaker.com'


try:
    shindan_maker_plugin_config = get_plugin_config(ShindanMakerPluginConfig)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>ShindanMaker 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'ShindanMaker 插件配置格式验证失败, {e}')


__all__ = [
    'shindan_maker_plugin_config'
]
