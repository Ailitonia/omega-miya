"""
@Author         : Ailitonia
@Date           : 2024/12/30 16:54:04
@FileName       : consts.py
@Project        : omega-miya
@Description    : 邮件插件常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from src.resource import TemporaryResource

DB_MAILBOX_ACCOUNT_SETTING_NAME: Literal['omega_email_mailbox'] = 'omega_email_mailbox'
"""数据库存放邮箱账号系统配置项名称"""
DB_ENTITY_SETTING_MODULE_NAME: Literal['omega_email'] = 'omega_email'
DB_ENTITY_SETTING_PLUGIN_NAME: Literal['omega_email_mailbox_bind'] = 'omega_email_mailbox_bind'
"""实体对象配置项名称"""
EMAIL_PASSWORD_ENCRYPT_SALT: Literal['0x656D61696C'] = '0x656D61696C'
"""邮箱密码加密盐值"""
EMAIL_TMP_FOLDER: TemporaryResource = TemporaryResource('receive_email')
"""已收邮件图片缓存路径"""


__all__ = [
    'DB_MAILBOX_ACCOUNT_SETTING_NAME',
    'DB_ENTITY_SETTING_MODULE_NAME',
    'DB_ENTITY_SETTING_PLUGIN_NAME',
    'EMAIL_PASSWORD_ENCRYPT_SALT',
    'EMAIL_TMP_FOLDER',
]
