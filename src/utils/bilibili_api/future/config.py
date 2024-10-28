"""
@Author         : Ailitonia
@Date           : 2024/10/28 14:38:44
@FileName       : config.py
@Project        : omega-miya
@Description    : bilibili API 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from typing import Any, Self
from urllib.parse import quote

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
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


class BilibiliLoginCookies(BaseConfigModel):
    """导出用于用户鉴权的, 包含用户登录信息的 Cookies 值"""

    bilibili_api_sessdata: str | None = Field(default=None, alias='SESSDATA')
    bilibili_api_jct: str | None = Field(default=None, alias='bili_jct')
    bilibili_api_dedeuserid: str | None = Field(default=None, alias='DedeUserID')
    bilibili_api_refresh_token: str | None = Field(default=None, alias='ac_time_value')

    @field_validator('bilibili_api_sessdata', mode='after')
    @classmethod
    def quote_sessdata(cls, v: str | None) -> str | None:
        return (
            None if v is None
            else (
                v if v.find("%") != -1
                else quote(v)
            )
        )


class BilibiliCookies(BilibiliLoginCookies):
    """Bilibili API 请求所需 Cookies 值"""

    bilibili_api_buvid3: str | None = Field(default=None, alias='buvid3')
    bilibili_api_buvid4: str | None = Field(default=None, alias='buvid4')
    bilibili_api_buvid_fp: str | None = Field(default=None, alias='buvid_fp')
    bilibili_api_uuid: str | None = Field(default=None, alias='_uuid')


class BilibiliAPIConfig(BilibiliCookies):
    """bilibili API 配置"""

    cookies_cache: BilibiliCookies = Field(default_factory=BilibiliCookies)

    @model_validator(mode='before')
    @classmethod
    def init_cookies_cache(cls, values):
        """初始化内部缓存"""
        values.update({"cookies_cache": values})
        return values

    @property
    def bili_cookies(self) -> dict[str, Any]:
        """从内部缓存获取 bilibili Cookies"""
        return self.cookies_cache.get_config_dict()

    def update_cookies_cache(self, **kwargs) -> None:
        """更新 bilibili Cookies 内部缓存"""
        kwargs.setdefault('SESSDATA', self.bilibili_api_sessdata)
        kwargs.setdefault('bili_jct', self.bilibili_api_jct)
        kwargs.setdefault('DedeUserID', self.bilibili_api_dedeuserid)
        kwargs.setdefault('ac_time_value', self.bilibili_api_refresh_token)
        kwargs.setdefault('buvid3', self.bilibili_api_buvid3)
        kwargs.setdefault('buvid4', self.bilibili_api_buvid4)
        kwargs.setdefault('buvid_fp', self.bilibili_api_buvid_fp)
        kwargs.setdefault('_uuid', self.bilibili_api_uuid)

        self.cookies_cache = BilibiliCookies.model_validate(kwargs)

    def clear_cookies_cache(self) -> None:
        """清空内部缓存"""
        self.cookies_cache = BilibiliCookies()

    def clear_all(self) -> None:
        """清空所有配置内容"""
        for field_name in self.model_fields.keys():
            if field_name == 'cookies_cache':
                continue
            setattr(self, field_name, None)
        self.clear_cookies_cache()

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
            await self._save_config_to_db(dal=dal, setting_key='SESSDATA', value=self.bilibili_api_sessdata)
            await self._save_config_to_db(dal=dal, setting_key='bili_jct', value=self.bilibili_api_jct)
            await self._save_config_to_db(dal=dal, setting_key='DedeUserID', value=self.bilibili_api_dedeuserid)
            await self._save_config_to_db(dal=dal, setting_key='ac_time_value', value=self.bilibili_api_refresh_token)

    async def load_from_database(self) -> Self:
        """从数据库读取用户登录 Cookies"""
        async with begin_db_session() as session:
            dal = SystemSettingDAL(session=session)
            self.bilibili_api_sessdata = await self._load_config_from_db(dal=dal, setting_key='SESSDATA')
            self.bilibili_api_jct = await self._load_config_from_db(dal=dal, setting_key='bili_jct')
            self.bilibili_api_dedeuserid = await self._load_config_from_db(dal=dal, setting_key='DedeUserID')
            self.bilibili_api_refresh_token = await self._load_config_from_db(dal=dal, setting_key='ac_time_value')

        self.update_cookies_cache()
        return self


@dataclass
class BilibiliAPILocalResourceConfig:
    # 默认的缓存资源保存路径
    default_tmp_folder: TemporaryResource = TemporaryResource('bilibili')
    default_download_folder: TemporaryResource = default_tmp_folder('download')


try:
    bilibili_api_resource_config = BilibiliAPILocalResourceConfig()
    bilibili_api_config = get_plugin_config(BilibiliAPIConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Bilibili 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Bilibili 配置格式验证失败, {e}')

__all__ = [
    'bilibili_api_config',
    'bilibili_api_resource_config',
]
