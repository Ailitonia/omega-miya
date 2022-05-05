"""
@Author         : Ailitonia
@Date           : 2022/04/17 1:23
@FileName       : test.py
@Project        : nonebot2_miya
@Description    : 加密工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
from Crypto.Cipher import AES
from typing import Tuple

from .config import encrypt_config


class AESEncryptStr(object):
    def __init__(self, key: str | None = None):
        if key is None:
            key = encrypt_config.aes_key

        while len(key) % 16 != 0:
            key += '\0'
        if len(key) != 16:
            raise ValueError('Incorrect AES key length, key length should be less than 16.')
        self.__key = key.encode(encoding='utf8')

    def encrypt(self, text: str) -> Tuple[str, str, str]:
        """
        :param text: 加密文本
        :return: (nonce, ciphertext, tag)
        """
        cipher_encrypt = AES.new(self.__key, AES.MODE_EAX)
        nonce = cipher_encrypt.nonce
        data = text.encode(encoding='utf8')
        ciphertext, tag = cipher_encrypt.encrypt_and_digest(data)

        # base64处理
        nonce = base64.b64encode(nonce).decode(encoding='utf8')
        ciphertext = base64.b64encode(ciphertext).decode(encoding='utf8')
        tag = base64.b64encode(tag).decode(encoding='utf8')

        return nonce, ciphertext, tag

    def decrypt(self, nonce: str, ciphertext: str, tag: str) -> Tuple[bool, str]:
        # base64处理
        nonce = base64.b64decode(nonce.encode(encoding='utf8'))
        data = base64.b64decode(ciphertext.encode(encoding='utf8'))
        tag = base64.b64decode(tag.encode(encoding='utf8'))
        cipher_decrypt = AES.new(self.__key, AES.MODE_EAX, nonce=nonce)

        plaintext = cipher_decrypt.decrypt(data)
        try:
            cipher_decrypt.verify(tag)
            plaintext = plaintext.decode('utf8')
            return True, plaintext
        except ValueError:
            return False, ''
        except UnicodeDecodeError:
            return False, ''


__all__ = [
    'AESEncryptStr'
]
