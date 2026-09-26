"""
@Author         : Ailitonia
@Date           : 2026/9/25 22:38
@FileName       : credential_manager
@Project        : omega-miya
@Description    : weibo API 凭据管理器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Generator
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import NoResultFound

from src.database import SystemSettingDAL
from .consts import WEIBO_API_SETTING_NAME


class _BaseCredential(BaseModel):
    """weibo API 凭据基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True)

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            k: v for k, v in self.model_dump(by_alias=True).items()
            if v is not None
        }

    @property
    def iter_items(self) -> Generator[tuple[str, str | None], Any, None]:
        yield from self.model_dump(by_alias=True).items()


class WeiboCookiesData(_BaseCredential):
    """Weibo API 相关的所有所需 Cookies 值 (访客及登录凭据)"""

    # 访客/登录会话相关
    weibo_api_sub: str | None = Field(default=None, alias='SUB')
    weibo_api_subp: str | None = Field(default=None, alias='SUBP')
    weibo_api_sup: str | None = Field(default=None, alias='SUP')

    # 登录态相关
    weibo_api_scf: str | None = Field(default=None, alias='SCF')
    weibo_api_alf: str | None = Field(default=None, alias='ALF')
    weibo_api_sso_login_state: str | None = Field(default=None, alias='SSOLoginState')
    weibo_api_sso_info: str | None = Field(default=None, alias='sso_info')
    weibo_api_un: str | None = Field(default=None, alias='un')

    # 风控校验相关
    weibo_api_tid: str | None = Field(default=None, alias='tid')
    weibo_api_xsrf_token: str | None = Field(default=None, alias='XSRF-TOKEN')
    weibo_api_t_wm: str | None = Field(default=None, alias='_T_WM')
    weibo_api_mlogin: str | None = Field(default=None, alias='MLOGIN')
    weibo_api_m_weibocn_params: str | None = Field(default=None, alias='M_WEIBOCN_PARAMS')


class _WeiboCredentialManager:
    """weibo API 凭据管理器"""

    __slots__ = ('_cookies_data',)

    def __init__(self, cookies_data: 'WeiboCookiesData | None' = None) -> None:
        self._cookies_data: WeiboCookiesData = cookies_data or WeiboCookiesData()

    @property
    def cookies(self) -> dict[str, Any]:
        """导出全量 cookies 内容"""
        return self._cookies_data.as_dict

    def get_cookie(self, key: str, *, alias: bool = True) -> Any | None:
        if alias:
            return self.cookies.get(key, None)
        return getattr(self._cookies_data, key, None)

    def update_cookies(self, **kwargs: Any) -> None:
        for config_name, config_value in self._cookies_data.iter_items:
            kwargs.setdefault(config_name, config_value)
        self._cookies_data = WeiboCookiesData.model_validate(kwargs)

    def replace_cookies(self, cookies_data: WeiboCookiesData) -> None:
        """一次性全量替换 Cookies 数据

        同步赋值, 单事件循环内对并发读取天然原子, 用于刷新流程"先算后换"的最终提交
        """
        self._cookies_data = cookies_data

    def clear_cookies(self) -> None:
        self._cookies_data = WeiboCookiesData()

    async def rebuild_to_database(self) -> None:
        """持久化保存全量 Cookies 到数据库, 移除所有现有数据并重建"""
        async with SystemSettingDAL.create() as dal:
            exist_configs = await dal.query_series(setting_name=WEIBO_API_SETTING_NAME)
            for config in exist_configs:
                await dal.delete(setting_name=WEIBO_API_SETTING_NAME, setting_key=config.setting_key)

            for config_name, config_value in self._cookies_data.iter_items:
                if config_value is None:
                    continue
                await dal.add_update_exist(
                    setting_name=WEIBO_API_SETTING_NAME,
                    setting_key=config_name,
                    setting_value=config_value,
                )

    async def save_to_database(self) -> None:
        """持久化保存全量 Cookies 到数据库, 不主动移除 None 值或过期值, 失效值导致的失败或异常由业务层处理"""
        async with SystemSettingDAL.create() as dal:
            for config_name, config_value in self._cookies_data.iter_items:
                if config_value is None:
                    continue
                await dal.add_update_exist(
                    setting_name=WEIBO_API_SETTING_NAME,
                    setting_key=config_name,
                    setting_value=config_value,
                )

    async def load_from_database(self) -> Self:
        """从数据库读取 Cookies 并全量加载到实例"""
        update_data: dict[str, Any] = {}

        async with SystemSettingDAL.create() as dal:
            for config_name, _ in self._cookies_data.iter_items:
                try:
                    setting = await dal.query_unique(setting_name=WEIBO_API_SETTING_NAME, setting_key=config_name)
                    update_data[config_name] = setting.setting_value
                except NoResultFound:
                    update_data[config_name] = None

        self.clear_cookies()
        self.update_cookies(**update_data)
        return self


WEIBO_CREDENTIAL_MANAGER = _WeiboCredentialManager()
"""全局 weibo API 凭据管理器"""

__all__ = [
    'WEIBO_CREDENTIAL_MANAGER',
    'WeiboCookiesData',
]
