import ujson as json

from omega_miya.utils.encrypt_utils import AESEncryptStr
from omega_miya.utils.process_utils import run_sync, run_async_catching_exception

from .imap import EmailImap, Email


@run_async_catching_exception
@run_sync
def check_mailbox(address: str, server_host: str, password: str) -> bool:
    with EmailImap(host=server_host, address=address, password=password) as m:
        m.select()
    return True


@run_async_catching_exception
@run_sync
def get_unseen_mail_data(address: str, server_host: str, password: str) -> list[Email]:
    mail = EmailImap(host=server_host, address=address, password=password)
    unseen_mails = mail.get_mail_data(None, 'UNSEEN')
    result = [x for x in unseen_mails]
    return result


def encrypt_password(plaintext: str) -> str:
    return json.dumps(list(AESEncryptStr().encrypt(plaintext)))


def decrypt_password(ciphertext: str) -> str | Exception:
    try:
        data = json.loads(ciphertext)
        stat, plaintext = AESEncryptStr().decrypt(data[0], data[1], data[2])
        if not stat:
            raise ValueError('Key incorrect or message corrupted')
        result = plaintext
    except Exception as e:
        result = e
    return result


__all__ = [
    'check_mailbox',
    'get_unseen_mail_data',
    'encrypt_password',
    'decrypt_password'
]
