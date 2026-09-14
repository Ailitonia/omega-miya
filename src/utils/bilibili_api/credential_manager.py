"""
@Author         : Ailitonia
@Date           : 2026/9/13 15:34
@FileName       : credential_manager
@Project        : omega-miya
@Description    : bilibili API 凭据管理器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Generator
from typing import Any, Self
from urllib.parse import quote, unquote

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import NoResultFound

from src.database import SystemSettingDAL
from .consts import BILI_API_SETTING_NAME


class _BaseCredential(BaseModel):
    """bilibili API 凭据基类"""

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


class BilibiliLoginCookiesData(_BaseCredential):
    """导出用于用户鉴权的, 包含用户登录信息的 Cookies 值"""

    bilibili_api_sessdata: str | None = Field(default=None, alias='SESSDATA')
    bilibili_api_jct: str | None = Field(default=None, alias='bili_jct')
    bilibili_api_dedeuserid: str | None = Field(default=None, alias='DedeUserID')
    bilibili_api_dedeuserid_md5: str | None = Field(default=None, alias='DedeUserID__ckMd5')
    bilibili_api_sid: str | None = Field(default=None, alias='sid')

    # buvid3_4 相关
    bilibili_api_buvid3: str | None = Field(default=None, alias='buvid3')
    bilibili_api_buvid4: str | None = Field(default=None, alias='buvid4')
    bilibili_api_buvid_fp: str | None = Field(default=None, alias='buvid_fp')
    bilibili_api_b_nut: str | None = Field(default=None, alias='b_nut')
    bilibili_api_uuid: str | None = Field(default=None, alias='_uuid')

    # BiliTicket 相关
    bilibili_api_web_ticket: str | None = Field(default=None, alias='bili_ticket')
    bilibili_api_web_ticket_expires: str | None = Field(default=None, alias='bili_ticket_expires')

    @field_validator('bilibili_api_sessdata', mode='after')
    @classmethod
    def quote_sessdata(cls, v: str | None) -> str | None:
        # 先解码再编码, 对原始值与已编码值均幂等, 含非法 % 序列的原始值也能被正确编码
        return None if v is None else quote(unquote(v))


class BilibiliCookiesData(BilibiliLoginCookiesData):
    """Bilibili API 相关的所有所需 Cookies 值 (包含缓存的其他临时性但不直接用于请求的参数)"""

    # localStorage 中缓存的 refresh_token
    bilibili_api_refresh_token: str | None = Field(default=None, alias='ac_time_value')

    # WBI 签名相关
    bilibili_api_wbi_img_key: str | None = Field(default=None, alias='img_key')
    bilibili_api_wbi_sub_key: str | None = Field(default=None, alias='sub_key')


class _BilibiliCredentialManager:
    """bilibili API 凭据管理器"""

    __slots__ = ('_cookies_data',)

    def __init__(self, cookies_data: 'BilibiliCookiesData | None' = None) -> None:
        self._cookies_data: BilibiliCookiesData = cookies_data or BilibiliCookiesData()

    @property
    def cookies(self) -> dict[str, Any]:
        """导出全量 cookies 内容"""
        return self._cookies_data.as_dict

    @property
    def login_cookies(self) -> dict[str, Any]:
        """导出登录用 cookies 内容"""
        return BilibiliLoginCookiesData.model_validate(self.cookies).as_dict

    def get_cookie(self, key: str, *, alias: bool = True) -> Any | None:
        if alias:
            return self.cookies.get(key, None)
        return getattr(self._cookies_data, key, None)

    def update_cookies(self, **kwargs: Any) -> None:
        for config_name, config_value in self._cookies_data.iter_items:
            kwargs.setdefault(config_name, config_value)
        self._cookies_data = BilibiliCookiesData.model_validate(kwargs)

    def replace_cookies(self, cookies_data: BilibiliCookiesData) -> None:
        """一次性全量替换 Cookies 数据

        同步赋值, 单事件循环内对并发读取天然原子, 用于刷新流程"先算后换"的最终提交
        """
        self._cookies_data = cookies_data

    def clear_cookies(self) -> None:
        self._cookies_data = BilibiliCookiesData()

    async def rebuild_to_database(self) -> None:
        """持久化保存全量 Cookies 到数据库, 移除所有现有数据并重建"""
        async with SystemSettingDAL.create() as dal:
            exist_configs = await dal.query_series(setting_name=BILI_API_SETTING_NAME)
            for config in exist_configs:
                await dal.delete(setting_name=BILI_API_SETTING_NAME, setting_key=config.setting_key)

            for config_name, config_value in self._cookies_data.iter_items:
                if config_value is None:
                    continue
                await dal.add_update_exist(
                    setting_name=BILI_API_SETTING_NAME,
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
                    setting_name=BILI_API_SETTING_NAME,
                    setting_key=config_name,
                    setting_value=config_value,
                )

    async def load_from_database(self) -> Self:
        """从数据库读取 Cookies 并全量加载到实例"""
        update_data: dict[str, Any] = {}

        async with SystemSettingDAL.create() as dal:
            for config_name, _ in self._cookies_data.iter_items:
                try:
                    setting = await dal.query_unique(setting_name=BILI_API_SETTING_NAME, setting_key=config_name)
                    update_data[config_name] = setting.setting_value
                except NoResultFound:
                    update_data[config_name] = None

        self.clear_cookies()
        self.update_cookies(**update_data)
        return self


BILIBILI_CREDENTIAL_MANAGER = _BilibiliCredentialManager()
"""全局 bilibili API 凭据管理器"""

__all__ = [
    'BILIBILI_CREDENTIAL_MANAGER',
    'BilibiliCookiesData',
    'BilibiliLoginCookiesData',
]
