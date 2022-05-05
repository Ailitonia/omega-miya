"""
@Author         : Ailitonia
@Date           : 2022/04/05 17:32
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : HttpFetcher Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from typing import Literal
from pydantic import BaseModel, IPvAnyAddress, AnyHttpUrl, ValidationError


class HttpProxyConfig(BaseModel):
    """Http 代理配置"""
    enable_proxy: bool
    proxy_type: Literal['http']  # 仅支持 http 代理
    proxy_address: IPvAnyAddress
    proxy_port: int
    proxy_check_url: AnyHttpUrl
    proxy_check_timeout: int

    class Config:
        extra = "ignore"

    @property
    def proxy_url(self) -> str:
        return f'{self.proxy_type}://{self.proxy_address}:{self.proxy_port}'


try:
    http_proxy_config = HttpProxyConfig.parse_obj(get_driver().config)  # 导入并验证代理配置
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Http 代理配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Http 代理配置格式验证失败, {e}')


__all__ = [
    'http_proxy_config'
]
