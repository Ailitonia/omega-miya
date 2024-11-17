"""
@Author         : Ailitonia
@Date           : 2024/10/28 14:38:44
@FileName       : config.py
@Project        : omega-miya
@Description    : bilibili API 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Self
from urllib.parse import quote

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.exc import NoResultFound

from src.database import SystemSettingDAL, begin_db_session
from src.resource import TemporaryResource
from .consts import BILI_DB_SETTING_NAME


class BaseConfigModel(BaseModel):
    """Bilibili 配置基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True)

    def get_config_dict(self) -> dict[str, Any]:
        return {
            k: v for k, v in self.model_dump(by_alias=True).items()
            if v is not None
        }

    def iter_config(self) -> Generator[tuple[str, str | None], Any, None]:
        for config_name, config_value in self.model_dump(by_alias=True).items():
            yield config_name, config_value


class BilibiliLoginCookies(BaseConfigModel):
    """导出用于用户鉴权的, 包含用户登录信息的 Cookies 值"""

    bilibili_api_sessdata: str | None = Field(default=None, alias='SESSDATA')
    bilibili_api_jct: str | None = Field(default=None, alias='bili_jct')
    bilibili_api_dedeuserid: str | None = Field(default=None, alias='DedeUserID')
    bilibili_api_dedeuserid_md5: str | None = Field(default=None, alias='DedeUserID__ckMd5')
    bilibili_api_sid: str | None = Field(default=None, alias='sid')

    @field_validator('bilibili_api_sessdata', mode='after')
    @classmethod
    def quote_sessdata(cls, v: str | None) -> str | None:
        return (
            None if v is None
            else (
                v if v.find('%') != -1
                else quote(v)
            )
        )


class BilibiliCookies(BilibiliLoginCookies):
    """Bilibili API 请求所需 Cookies 值"""

    # buvid3_4 相关
    bilibili_api_buvid3: str | None = Field(default=None, alias='buvid3')
    bilibili_api_buvid4: str | None = Field(default=None, alias='buvid4')
    bilibili_api_buvid_fp: str | None = Field(default=None, alias='buvid_fp')
    bilibili_api_b_nut: str | None = Field(default=None, alias='b_nut')
    bilibili_api_uuid: str | None = Field(default=None, alias='_uuid')

    # BiliTicket 相关
    bilibili_api_web_ticket: str | None = Field(default=None, alias='bili_ticket')
    bilibili_api_web_ticket_expires: str | None = Field(default=None, alias='bili_ticket_expires')


class BilibiliAllCachedCookies(BilibiliCookies):
    """Bilibili API 相关的所有所需 Cookies 值 (包含缓存的其他临时性但不直接用于请求的参数)"""

    # localStorage 中缓存的 refresh_token
    bilibili_api_refresh_token: str | None = Field(default=None, alias='ac_time_value')

    # WBI 签名相关
    bilibili_api_wbi_img_key: str | None = Field(default=None, alias='img_key')
    bilibili_api_wbi_sub_key: str | None = Field(default=None, alias='sub_key')


@dataclass
class BilibiliLocalResourceConfig:
    # 默认的缓存资源保存路径
    default_folder: TemporaryResource = TemporaryResource('bilibili')

    def get_path(self, *args: str) -> 'TemporaryResource':
        """获取缓存路径"""
        return self.default_folder(*args)


class BilibiliAPIConfigManager:
    """bilibili API 配置"""

    __slots__ = ('_cookies_config', '_resource_config',)

    _cookies_config: 'BilibiliAllCachedCookies'
    _resource_config: 'BilibiliLocalResourceConfig'

    def __init__(self, cookies_config: 'BilibiliAllCachedCookies') -> None:
        self._cookies_config = cookies_config
        self._resource_config = BilibiliLocalResourceConfig()

    @property
    def bili_cookies(self) -> dict[str, Any]:
        """从内部缓存获取 bilibili Cookies"""
        return BilibiliCookies.model_validate(self._cookies_config.get_config_dict()).get_config_dict()

    @property
    def download_folder(self) -> 'TemporaryResource':
        """缓存下载文件目录"""
        return self.get_resource_path('download')

    def _iter_config(self) -> Generator[tuple[str, str | None], Any, None]:
        """遍历配置项"""
        return self._cookies_config.iter_config()

    def get_resource_path(self, *file_name: str) -> 'TemporaryResource':
        """获取缓存资源文件路径"""
        return self._resource_config.get_path(*file_name)

    def get_config(self, key: str, *, alias: bool = True) -> Any | None:
        """根据 alias 获取配置项"""
        if alias:
            return self._cookies_config.get_config_dict().get(key, None)
        return getattr(self._cookies_config, key, None)

    def update_config(self, **kwargs) -> None:
        """更新 bilibili Cookies 内部缓存"""
        for config_name, config_value in self._iter_config():
            kwargs.setdefault(config_name, config_value)
        self._cookies_config = BilibiliAllCachedCookies.model_validate(kwargs)

    def clear_config(self) -> None:
        """清空所有配置内容"""
        self._cookies_config = BilibiliAllCachedCookies()

    @staticmethod
    async def _save_config_to_db(dal: SystemSettingDAL, setting_key: str, value: str | None) -> None:
        if value is None:
            return
        await dal.upsert(setting_name=BILI_DB_SETTING_NAME, setting_key=setting_key, setting_value=value)

    @staticmethod
    async def _load_config_from_db(dal: SystemSettingDAL, setting_key: str) -> str | None:
        try:
            setting = await dal.query_unique(setting_name=BILI_DB_SETTING_NAME, setting_key=setting_key)
            return setting.setting_value
        except NoResultFound:
            return None

    async def save_to_database(self) -> None:
        """持久化保存用户登录 Cookies 到数据库"""
        async with begin_db_session() as session:
            dal = SystemSettingDAL(session=session)
            for config_name, config_value in self._iter_config():
                await self._save_config_to_db(dal=dal, setting_key=config_name, value=config_value)

    async def load_from_database(self) -> Self:
        """从数据库读取用户登录 Cookies"""
        async with begin_db_session() as session:
            dal = SystemSettingDAL(session=session)
            update_data = {
                config_name: await self._load_config_from_db(dal=dal, setting_key=config_name)
                for config_name, _ in self._iter_config()
            }
        self.update_config(**update_data)
        return self


try:
    bilibili_api_config = BilibiliAPIConfigManager(get_plugin_config(BilibiliAllCachedCookies))
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Bilibili 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Bilibili 配置格式验证失败, {e}')

__all__ = [
    'bilibili_api_config',
]
