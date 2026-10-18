"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : helpers.py
@Project        : nonebot2_miya
@Description    : 邮件处理模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING

from nonebot.log import logger
from nonebot.utils import run_sync
from pydantic import BaseModel, ConfigDict

from src.database.internal.system_setting import SystemSetting, SystemSettingDAL
from src.utils.crypto import AESEncryptor
from src.utils.image_utils import ImageEffectProcessor, ImageLoader
from .consts import (
    DB_ENTITY_SETTING_MODULE_NAME,
    DB_ENTITY_SETTING_PLUGIN_NAME,
    DB_MAILBOX_ACCOUNT_SETTING_NAME,
    EMAIL_PASSWORD_ENCRYPT_SALT,
    EMAIL_TMP_FOLDER,
)
from .mailbox import Email, ImapMailbox

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.service import OmegaMatcherInterface

_EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
"""邮箱地址校验正则"""


class BaseMailboxModel(BaseModel):
    """邮箱数据基类"""
    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, frozen=True)


class MailboxServer(BaseMailboxModel):
    """邮箱账号数据"""
    server_host: str
    password: str
    protocol: str
    port: int


class MailboxAccount(BaseMailboxModel):
    """数据库存储的邮箱账号数据"""
    address: str
    server: MailboxServer


def is_valid_email_address(email_address: str) -> bool:
    if not email_address or len(email_address) > 254:
        return False
    local = email_address.split('@')[0]
    if len(local) > 64:
        return False
    return _EMAIL_RE.match(email_address) is not None


@run_sync
def _encrypt_password(plaintext: str) -> str:
    return AESEncryptor(salt=EMAIL_PASSWORD_ENCRYPT_SALT).encrypt(plaintext=plaintext)


@run_sync
def _decrypt_password(envelope: str) -> str:
    return AESEncryptor(salt=EMAIL_PASSWORD_ENCRYPT_SALT).decrypt(envelope=envelope)


async def save_mailbox_into_database(
        address: str,
        server_host: str,
        password: str,
        protocol: str,
        port: int,
) -> SystemSetting:
    """向数据库写入邮箱账号数据"""
    if not is_valid_email_address(address):
        raise ValueError(f'Invalid email address: {address!r}')

    encrypted_password = await _encrypt_password(password)
    mail_server = MailboxServer(server_host=server_host, password=encrypted_password, protocol=protocol, port=port)
    async with SystemSettingDAL.create() as dal:
        email_setting = await dal.add_update_exist(
            setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME,
            setting_key=address,
            setting_value=mail_server.model_dump_json(),
        )
    return email_setting


async def load_mailbox_from_database(mailbox_address: str) -> MailboxAccount | None:
    """从数据库读取邮箱账号数据"""
    try:
        async with SystemSettingDAL.create() as dal:
            mailbox_setting = await dal.query_unique(
                setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME,
                setting_key=mailbox_address,
            )
    except Exception as e:
        logger.error(f'OmegaEmail | Load mailbox {mailbox_address!r} failed, {e}, '
                     f'若为旧版本数据需使用内置工具重新导入')
        return None

    try:
        mailbox_server = MailboxServer.model_validate_json(mailbox_setting.setting_value)
        password = await _decrypt_password(mailbox_server.password)
        return MailboxAccount.model_validate({
            'address': mailbox_setting.setting_key,
            'server': {
                'server_host': mailbox_server.server_host,
                'password': password,
                'protocol': mailbox_server.protocol,
                'port': mailbox_server.port,
            }
        })
    except Exception as e:
        logger.error(f'OmegaEmail | Parse mailbox {mailbox_address!r} failed, {e}, '
                     f'若为旧版本数据需使用内置工具重新导入')
        return None


async def query_available_mailbox_address() -> list[str]:
    """从数据库读取可用邮箱账号列表"""
    async with SystemSettingDAL.create() as dal:
        available_mailbox = await dal.query_series(setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME)
    return [x.setting_key for x in available_mailbox]


async def bind_entity_mailbox(interface: 'OmegaMatcherInterface', mailbox_address: str) -> None:
    """为实体对象绑定邮箱"""
    async with interface.create_current_entity_session() as entity:
        await entity.set_auth_setting(
            module=DB_ENTITY_SETTING_MODULE_NAME,
            plugin=DB_ENTITY_SETTING_PLUGIN_NAME,
            node=mailbox_address,
            available=1,
            value={'bound_email': mailbox_address},
        )


async def unbind_entity_mailbox(interface: 'OmegaMatcherInterface', mailbox_address: str) -> None:
    """为实体对象解绑邮箱"""
    async with interface.create_current_entity_session() as entity:
        await entity.set_auth_setting(
            module=DB_ENTITY_SETTING_MODULE_NAME,
            plugin=DB_ENTITY_SETTING_PLUGIN_NAME,
            node=mailbox_address,
            available=0,
            value={},
    )


async def query_entity_bound_mailbox(interface: 'OmegaMatcherInterface') -> list[str]:
    """查询实体对象已绑定的邮箱账号列表"""
    async with interface.create_current_entity_session() as entity:
        bound_mailbox = await entity.query_plugin_all_auth_setting(
            module=DB_ENTITY_SETTING_MODULE_NAME,
            plugin=DB_ENTITY_SETTING_PLUGIN_NAME,
        )
    return [x.node for x in bound_mailbox if (x.available == 1)]


@run_sync
def check_mailbox(address: str, server_host: str, password: str) -> bool:
    """检查邮箱状态"""
    try:
        ImapMailbox(host=server_host, address=address, password=password).check()
        return True
    except Exception as e:
        logger.error(f'OmegaEmail | Checking mailbox {address!r} failed, {e}')
        return False


@run_sync
def get_unseen_mail_data(address: str, server_host: str, password: str) -> list[Email]:
    """获取未读邮件列表"""
    mail = ImapMailbox(host=server_host, address=address, password=password)
    return mail.get_mail_list(None, 'UNSEEN')


@run_sync
def _generate_mail_snapshot(mail_content: str) -> ImageEffectProcessor:
    return ImageEffectProcessor(ImageLoader.init_from_text(text=mail_content))


async def generate_mail_snapshot(mail_content: str) -> 'TemporaryResource':
    """生成邮件快照图片"""
    image = await _generate_mail_snapshot(mail_content=mail_content)
    file_name = f'mail_{datetime.now().strftime("%Y%m%d%H%M%S")}_{hash(mail_content)}.jpg'
    return await image.save(EMAIL_TMP_FOLDER(file_name), format_='JPEG')


__all__ = [
    'bind_entity_mailbox',
    'check_mailbox',
    'generate_mail_snapshot',
    'get_unseen_mail_data',
    'is_valid_email_address',
    'load_mailbox_from_database',
    'query_available_mailbox_address',
    'query_entity_bound_mailbox',
    'save_mailbox_into_database',
    'unbind_entity_mailbox',
]
