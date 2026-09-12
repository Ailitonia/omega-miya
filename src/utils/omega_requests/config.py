"""
@Author         : Ailitonia
@Date           : 2022/04/05 17:32
@FileName       : config.py
@Project        : nonebot2_miya
@Description    : HttpFetcher Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from copy import deepcopy
from ipaddress import IPv4Address
from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, ValidationError

from .types import Timeout, TimeoutTypes


class OmegaRequestsConfig(BaseModel):
    """OmegaRequests 配置"""

    # 代理配置
    omega_requests_enable_proxy: bool = Field(default=False)
    omega_requests_proxy_type: Literal['http'] = Field(default='http')  # 仅支持 http 代理
    omega_requests_proxy_address: IPvAnyAddress = Field(default=IPv4Address('127.0.0.1'))
    omega_requests_proxy_port: int = Field(default=1081)

    # 默认请求参数
    omega_requests_default_retry_limit: int = Field(default=3, ge=1)  # 最大总尝试次数, 至少发起一次请求
    omega_requests_default_timeout: TimeoutTypes = Field(default=Timeout(total=30, connect=10, read=20))
    omega_requests_default_headers: dict[str, str] = Field(default={
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN,zh;q=0.9',
        'dnt': '1',
        'sec-ch-ua': '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/152.0.0.0 Safari/537.36',
    })

    model_config = ConfigDict(extra='ignore')

    @property
    def default_retry_limit(self) -> int:
        return self.omega_requests_default_retry_limit

    @property
    def default_timeout(self) -> TimeoutTypes:
        return deepcopy(self.omega_requests_default_timeout)

    @property
    def default_headers(self) -> dict[str, str]:
        return deepcopy(self.omega_requests_default_headers)

    @property
    def proxy_url(self) -> str | None:
        if self.omega_requests_enable_proxy:
            return (
                f'{self.omega_requests_proxy_type}://'
                f'{self.omega_requests_proxy_address}:{self.omega_requests_proxy_port}'
            )
        return None


try:
    omega_requests_config = get_plugin_config(OmegaRequestsConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>OmegaRequests 配置验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'OmegaRequests 配置验证失败, {e}')


__all__ = [
    'omega_requests_config'
]
