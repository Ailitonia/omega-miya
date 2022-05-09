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
    enable_proxy: bool = False
    proxy_type: Literal['http'] = 'http'  # 仅支持 http 代理
    proxy_address: IPvAnyAddress = '127.0.0.1'
    proxy_port: int = 1081
    proxy_check_url: AnyHttpUrl = 'https://www.google.com'
    proxy_check_timeout: int = 5

    class Config:
        extra = "ignore"

    @property
    def proxy_url(self) -> str | None:
        if self.enable_proxy:
            proxy = f'{self.proxy_type}://{self.proxy_address}:{self.proxy_port}'
        else:
            proxy = None
        return proxy


try:
    http_proxy_config = HttpProxyConfig.parse_obj(get_driver().config)  # 导入并验证代理配置
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Http 代理配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Http 代理配置格式验证失败, {e}')


__all__ = [
    'http_proxy_config'
]
