"""
@Author         : Ailitonia
@Date           : 2022/04/14 23:22
@FileName       : file.py
@Project        : nonebot2_miya 
@Description    : Onebot File Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base_model import BaseOnebotModel


class RecordFile(BaseOnebotModel):
    """语音文件"""
    file: str


class ImageFile(BaseOnebotModel):
    """图片文件"""
    file: str


class CanSendImage(BaseOnebotModel):
    """是否可以发送图片"""
    yes: bool


class CanSendRecord(BaseOnebotModel):
    """是否可以发送语音"""
    yes: bool


class Cookies(BaseOnebotModel):
    """Cookies"""
    cookies: str


class CSRF(BaseOnebotModel):
    """CSRF Token"""
    token: int


class Credentials(BaseOnebotModel):
    """Cookies 和 CSRF Token"""
    cookies: str
    csrf_token: int


class Status(BaseOnebotModel):
    """运行状态"""
    online: bool
    good: bool

    class Config:
        extra = 'allow'


class VersionInfo(BaseOnebotModel):
    """版本信息"""
    app_name: str
    app_version: str
    protocol_version: str

    class Config:
        extra = 'allow'


__all__ = [
    'RecordFile',
    'ImageFile',
    'CanSendImage',
    'CanSendRecord',
    'Cookies',
    'CSRF',
    'Credentials',
    'Status',
    'VersionInfo'
]
