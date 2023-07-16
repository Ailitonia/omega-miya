"""
@Author         : Ailitonia
@Date           : 2022/04/14 23:22
@FileName       : file.py
@Project        : nonebot2_miya 
@Description    : OneBot File Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base_model import BaseOneBotModel


class RecordFile(BaseOneBotModel):
    """语音文件"""
    file: str


class ImageFile(BaseOneBotModel):
    """图片文件"""
    file: str


class CanSendImage(BaseOneBotModel):
    """是否可以发送图片"""
    yes: bool


class CanSendRecord(BaseOneBotModel):
    """是否可以发送语音"""
    yes: bool


class Cookies(BaseOneBotModel):
    """Cookies"""
    cookies: str


class CSRF(BaseOneBotModel):
    """CSRF Token"""
    token: int


class Credentials(BaseOneBotModel):
    """Cookies 和 CSRF Token"""
    cookies: str
    csrf_token: int


class Status(BaseOneBotModel):
    """运行状态"""
    online: bool
    good: bool

    class Config:
        extra = 'allow'


class VersionInfo(BaseOneBotModel):
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
