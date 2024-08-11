"""
@Author         : Ailitonia
@Date           : 2022/04/11 19:12
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Bilibili Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.exc import NoResultFound

from src.database import SystemSettingDAL, begin_db_session
from src.resource import TemporaryResource


class BilibiliConfig(BaseModel):
    """Bilibili 配置

    - bili_sessdata: 浏览器 Cookies 中的 SESSDATA 字段值. Defaults to None.
    - bili_jct: 浏览器 Cookies 中的 bili_jct 字段值. Defaults to None.
    - bili_buvid3: 浏览器 Cookies 中的 BUVID3 字段值. Defaults to None.
    - bili_dedeuserid: 浏览器 Cookies 中的 DedeUserID 字段值. Defaults to None.
    - bili_ac_time_value: 浏览器 Cookies 中的 ac_time_value 字段值. Defaults to None.
    """
    bili_sessdata: str | None = None
    bili_jct: str | None = None
    bili_buvid3: str | None = None
    bili_dedeuserid: str | None = None
    bili_ac_time_value: str | None = None

    _cookies_cache: dict | None = None

    model_config = ConfigDict(extra="ignore", coerce_numbers_to_str=True)

    @property
    def bili_cookies(self) -> dict[str, Any]:
        sessdata = (
            None
            if self.bili_sessdata is None
            else self.bili_sessdata if self.bili_sessdata.find("%") != -1 else quote(self.bili_sessdata)
        )

        cookies = {
            "SESSDATA": sessdata,
            "buvid3": self.bili_buvid3,
            "bili_jct": self.bili_jct,
            "ac_time_value": self.bili_ac_time_value,
        }
        if self.bili_dedeuserid:
            cookies.update({"DedeUserID": self.bili_dedeuserid})

        return cookies

    def update_bili_cookies(self, **kwargs) -> dict[str, str]:
        if self._cookies_cache is not None and not kwargs:
            return self._cookies_cache

        cookies = self.bili_cookies
        for key, value in kwargs.items():
            if key not in cookies and value is not None:
                cookies[key] = value

        self._cookies_cache = cookies
        return cookies

    def clear_cookies_cache(self) -> None:
        self._cookies_cache = None

    def clear_cookies_config(self) -> None:
        self.bili_sessdata = None
        self.bili_jct = None
        self.bili_buvid3 = None
        self.bili_dedeuserid = None
        self.bili_ac_time_value = None

    def clear_all(self) -> None:
        self.clear_cookies_config()
        self.clear_cookies_cache()

    @staticmethod
    async def _save_config_to_db(dal: SystemSettingDAL, setting_name: str, value: str | None) -> None:
        if value is None:
            return
        try:
            setting = await dal.query_unique(setting_name=setting_name)
            await dal.update(id_=setting.id, setting_value=value)
        except NoResultFound:
            await dal.add(setting_name=setting_name, setting_value=value)

    @staticmethod
    async def _load_config_from_db(dal: SystemSettingDAL, setting_name: str) -> str | None:
        try:
            setting = await dal.query_unique(setting_name=setting_name)
            return setting.setting_value
        except NoResultFound:
            return None

    async def save_to_database(self) -> None:
        async with begin_db_session() as session:
            dal = SystemSettingDAL(session=session)
            await self._save_config_to_db(dal=dal, setting_name='bili_sessdata', value=self.bili_sessdata)
            await self._save_config_to_db(dal=dal, setting_name='bili_jct', value=self.bili_jct)
            await self._save_config_to_db(dal=dal, setting_name='bili_buvid3', value=self.bili_buvid3)
            await self._save_config_to_db(dal=dal, setting_name='bili_dedeuserid', value=self.bili_dedeuserid)
            await self._save_config_to_db(dal=dal, setting_name='bili_ac_time_value', value=self.bili_ac_time_value)

    async def load_from_database(self) -> "BilibiliConfig":
        async with begin_db_session() as session:
            dal = SystemSettingDAL(session=session)
            bili_sessdata = await self._load_config_from_db(dal=dal, setting_name='bili_sessdata')
            if bili_sessdata is not None:
                self.bili_sessdata = bili_sessdata

            bili_jct = await self._load_config_from_db(dal=dal, setting_name='bili_jct')
            if bili_jct is not None:
                self.bili_jct = bili_jct

            bili_buvid3 = await self._load_config_from_db(dal=dal, setting_name='bili_buvid3')
            if bili_buvid3 is not None:
                self.bili_buvid3 = bili_buvid3

            bili_dedeuserid = await self._load_config_from_db(dal=dal, setting_name='bili_dedeuserid')
            if bili_dedeuserid is not None:
                self.bili_dedeuserid = bili_dedeuserid

            bili_ac_time_value = await self._load_config_from_db(dal=dal, setting_name='bili_ac_time_value')
            if bili_ac_time_value is not None:
                self.bili_ac_time_value = bili_ac_time_value

        return self


@dataclass
class BilibiliLocalResourceConfig:
    # 默认的缓存资源保存路径
    default_tmp_folder: TemporaryResource = TemporaryResource('bilibili')
    default_download_folder: TemporaryResource = default_tmp_folder('download')


try:
    bilibili_resource_config = BilibiliLocalResourceConfig()
    bilibili_config = get_plugin_config(BilibiliConfig)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Bilibili 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Bilibili 配置格式验证失败, {e}')


__all__ = [
    'bilibili_config',
    'bilibili_resource_config'
]
