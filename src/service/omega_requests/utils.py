"""
@Author         : Ailitonia
@Date           : 2022/12/10 20:30
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Omega requests handler utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Optional

from nonebot import get_plugin_config, logger
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class CloudflareClearanceModel(BaseModel):
    model_config = ConfigDict(extra='ignore')


class DomainCloudflareClearanceCookies(CloudflareClearanceModel):
    cf_clearance: str
    cf_bm: Optional[str] = Field(None, alias='__cf_bm')
    cflb: Optional[str] = Field(None, alias='__cflb')


class DomainCloudflareClearanceHeaders(CloudflareClearanceModel):
    user_agent: Optional[str] = Field(None, alias='User-Agent')


class DomainCloudflareClearance(CloudflareClearanceModel):
    """网站的 Cloudflare Clearance cookie 内容"""
    domain: str
    cookies: DomainCloudflareClearanceCookies
    headers: DomainCloudflareClearanceHeaders

    def get_cookies(self) -> dict[str, Any]:
        return {k: v for k, v in self.cookies.model_dump(by_alias=True).items() if v is not None}

    def get_headers(self) -> dict[str, Any]:
        return {k: v for k, v in self.headers.model_dump(by_alias=True).items() if v is not None}


class CloudflareClearanceConfig(CloudflareClearanceModel):
    """Cloudflare Clearance 配置"""
    cloudflare_clearance_config: list[DomainCloudflareClearance] = []

    @property
    def _config_map(self) -> dict[str, DomainCloudflareClearance]:
        return {config.domain: config for config in self.cloudflare_clearance_config}

    def get_domain_config(self, domain: str) -> DomainCloudflareClearance | None:
        if (domain_config := self._config_map.get(domain, None)) is None:
            return None

        return domain_config

    def get_url_config(self, url: str) -> DomainCloudflareClearance | None:
        domain = TypeAdapter(AnyHttpUrl).validate_python(url).host
        return self.get_domain_config(domain=domain)


try:
    cloudflare_clearance_config = get_plugin_config(CloudflareClearanceConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Cloudflare Clearance 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Cloudflare Clearance 配置格式验证失败, {e}')


__all__ = [
    'cloudflare_clearance_config',
]
