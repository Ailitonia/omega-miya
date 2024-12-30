"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : helpers.py
@Project        : nonebot2_miya
@Description    : 邮件处理模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import TYPE_CHECKING

from nonebot.log import logger
from nonebot.utils import run_sync
from pydantic import BaseModel, ConfigDict

from src.database import SystemSettingDAL, begin_db_session
from src.utils.crypto import AESEncryptor
from src.utils.image_utils import ImageUtils
from .consts import (
    DB_MAILBOX_ACCOUNT_SETTING_NAME,
    DB_ENTITY_SETTING_PLUGIN_NAME,
    DB_ENTITY_SETTING_MODULE_NAME,
    TMP_FOLDER
)
from .mailbox import Email, ImapMailbox

if TYPE_CHECKING:
    from src.service import OmegaMatcherInterface as OmMI
    from src.resource import TemporaryResource


class BaseMailboxModel(BaseModel):
    """邮箱数据基类"""
    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True, frozen=True)


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


async def save_mailbox(address: str, server_host: str, password: str, protocol: str, port: int) -> None:
    """向数据库写入邮箱账号数据"""
    mail_server = MailboxServer(server_host=server_host, password=password, protocol=protocol, port=port)
    async with begin_db_session() as session:
        await SystemSettingDAL(session=session).upsert(
            setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME,
            setting_key=address,
            setting_value=mail_server.model_dump_json(),
        )


async def load_mailbox(mailbox_address: str) -> MailboxAccount:
    """从数据库读取邮箱账号数据"""
    async with begin_db_session() as session:
        mailbox_server = await SystemSettingDAL(session=session).query_unique(
            setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME,
            setting_key=mailbox_address,
        )
    return MailboxAccount.model_validate({
        'address': mailbox_server.setting_key,
        'server': MailboxServer.model_validate_json(mailbox_server.setting_value),
    })


async def query_available_mailbox() -> list[MailboxAccount]:
    """从数据库读取可用邮箱账号列表"""
    async with begin_db_session() as session:
        available_mailbox = await SystemSettingDAL(session=session).query_series(
            setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME,
        )
    return [
        MailboxAccount.model_validate({
            'address': x.setting_key,
            'server': MailboxServer.model_validate_json(x.setting_value),
        })
        for x in available_mailbox
    ]


async def bind_entity_mailbox(interface: 'OmMI', mailbox_account: MailboxAccount) -> None:
    """为实体对象绑定邮箱"""
    return await interface.entity.set_auth_setting(
        module=DB_ENTITY_SETTING_MODULE_NAME,
        plugin=DB_ENTITY_SETTING_PLUGIN_NAME,
        node=mailbox_account.address,
        available=1,
        value=mailbox_account.server.model_dump_json(),
    )


async def unbind_entity_mailbox(interface: 'OmMI', mailbox_address: str) -> None:
    """为实体对象解绑邮箱"""
    return await interface.entity.set_auth_setting(
        module=DB_ENTITY_SETTING_MODULE_NAME,
        plugin=DB_ENTITY_SETTING_PLUGIN_NAME,
        node=mailbox_address,
        available=0,
        value='',
    )


async def get_entity_bound_mailbox(interface: 'OmMI') -> list[MailboxAccount]:
    """为实体对象解绑邮箱"""
    bound_mailbox = await interface.entity.query_plugin_all_auth_setting(
        module=DB_ENTITY_SETTING_MODULE_NAME,
        plugin=DB_ENTITY_SETTING_PLUGIN_NAME,
    )
    return [
        MailboxAccount.model_validate({
            'address': x.node,
            'server': MailboxServer.model_validate_json(x.value),
        })
        for x in bound_mailbox
        if (x.available == 1) and x.value
    ]


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
    unseen_mails = mail.get_mail_list(None, 'UNSEEN')
    result = [x for x in unseen_mails]
    return result


@run_sync
def encrypt_password(plaintext: str) -> str:
    return AESEncryptor().ecb_encrypt(plaintext)


@run_sync
def decrypt_password(ciphertext: str) -> str:
    return AESEncryptor().ecb_decrypt(ciphertext)


@run_sync
def _generate_mail_snapshot(mail_content: str) -> ImageUtils:
    return ImageUtils.init_from_text(text=mail_content)


async def generate_mail_snapshot(mail_content: str) -> 'TemporaryResource':
    """生成邮件快照图片"""
    image = await _generate_mail_snapshot(mail_content=mail_content)
    return await image.save(TMP_FOLDER(f'mail_{datetime.now().strftime("%Y%m%d%H%M%S")}_{hash(mail_content)}.jpg'))


__all__ = [
    'save_mailbox',
    'load_mailbox',
    'query_available_mailbox',
    'bind_entity_mailbox',
    'unbind_entity_mailbox',
    'get_entity_bound_mailbox',
    'check_mailbox',
    'get_unseen_mail_data',
    'encrypt_password',
    'decrypt_password',
    'generate_mail_snapshot',
]
