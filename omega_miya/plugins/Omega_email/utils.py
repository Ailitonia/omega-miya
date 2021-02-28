import asyncio
import nonebot
import json
from omega_miya.utils.Omega_Base import DBEmail, Result
from omega_miya.utils.Omega_plugin_utils import AESEncryptStr
from .imap import EmailImap


global_config = nonebot.get_driver().config
AES_KEY = global_config.aes_key


async def check_mailbox(address: str, server_host: str, password: str) -> Result:
    def __check_mailbox() -> Result:
        try:
            with EmailImap(host=server_host, address=address, password=password) as m:
                m.select()
            __result = Result(error=False, info='Success', result=0)
        except Exception as e:
            __result = Result(error=True, info=f'Login Failed: {repr(e)}', result=-1)

        return __result

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __check_mailbox)

    return result


async def get_unseen_mail_info(address: str, server_host: str, password: str) -> Result:
    def __get_unseen_mail_info() -> Result:
        try:
            mail = EmailImap(host=server_host, address=address, password=password)
            unseen_mails = mail.get_mail_info(None, 'UNSEEN')
            res = []
            for email in unseen_mails:
                DBEmail(mail_hash=email.hash).add(date=email.date, header=email.header, sender=email.sender,
                                                  to=email.to, body=email.body, html=email.html)

                res.append(email)
            __result = Result(error=False, info='Success', result=res)
        except Exception as e:
            __result = Result(error=True, info=repr(e), result=[])
        return __result

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __get_unseen_mail_info)

    return result


def encrypt_password(plaintext: str) -> str:
    encryptor = AESEncryptStr(key=AES_KEY)
    return json.dumps(list(encryptor.encrypt(plaintext)))


def decrypt_password(ciphertext: str) -> Result:
    encryptor = AESEncryptStr(key=AES_KEY)
    try:
        data = json.loads(ciphertext)
        stat, plaintext = encryptor.decrypt(data[0], data[1], data[2])
        if stat:
            return Result(error=False, info='Success', result=plaintext)
        else:
            return Result(error=True, info='Key incorrect or message corrupted', result=plaintext)
    except Exception as e:
        return Result(error=True, info=f'Ciphertext parse error: {repr(e)}', result='')
