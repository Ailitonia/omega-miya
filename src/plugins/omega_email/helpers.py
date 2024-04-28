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

import ujson as json
from nonebot.log import logger
from nonebot.utils import run_sync

from src.resource import TemporaryResource
from src.utils.encrypt import AESEncryptStr
from src.utils.image_utils import ImageUtils

from .imap import Email, ImapMailbox


_TMP_FOLDER: TemporaryResource = TemporaryResource('receive_email')
"""已收邮件图片缓存路径"""


@run_sync
def check_mailbox(address: str, server_host: str, password: str) -> bool:
    try:
        ImapMailbox(host=server_host, address=address, password=password).check()
        return True
    except Exception as e:
        logger.error(f'OmegaEmail | Checking mailbox {address!r} failed, {e}')
        return False


@run_sync
def get_unseen_mail_data(address: str, server_host: str, password: str) -> list[Email]:
    mail = ImapMailbox(host=server_host, address=address, password=password)
    unseen_mails = mail.get_mail_list(None, 'UNSEEN')
    result = [x for x in unseen_mails]
    return result


@run_sync
def encrypt_password(plaintext: str) -> str:
    return json.dumps(list(AESEncryptStr().encrypt(plaintext)))


@run_sync
def decrypt_password(ciphertext: str) -> str:
    data = json.loads(ciphertext)
    stat, plaintext = AESEncryptStr().decrypt(data[0], data[1], data[2])
    if not stat:
        raise ValueError('Key incorrect or message corrupted')
    return plaintext


@run_sync
def _generate_mail_snapshot(mail_content: str) -> ImageUtils:
    return ImageUtils.init_from_text(text=mail_content)


async def generate_mail_snapshot(mail_content: str) -> TemporaryResource:
    image = await _generate_mail_snapshot(mail_content=mail_content)
    return await image.save(_TMP_FOLDER(f'mail_{datetime.now().strftime("%Y%m%d%H%M%S")}_{hash(mail_content)}.jpg'))


__all__ = [
    'check_mailbox',
    'get_unseen_mail_data',
    'encrypt_password',
    'decrypt_password',
    'generate_mail_snapshot'
]
