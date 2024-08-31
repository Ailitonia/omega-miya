"""
@Author         : Ailitonia
@Date           : 2022/04/17 1:23
@FileName       : aes.py
@Project        : nonebot2_miya
@Description    : AES 加密套件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
from hashlib import shake_128
from os import urandom
from typing import Literal, Optional

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from ..config import encrypt_config


class AESEncrypter(object):
    def __init__(
            self,
            key: Optional[str] = None,
            *,
            version: Optional[Literal['AES-128', 'AES-192', 'AES-256']] = None,
    ) -> None:
        if key is None:
            key = encrypt_config.omega_aes_key.get_secret_value()

        match version:
            case 'AES-256':
                key_length = 32
            case 'AES-192':
                key_length = 24
            case 'AES-128' | _:
                key_length = 16

        self.__key = shake_128(key.encode(encoding='utf-8')).hexdigest(key_length // 2).encode(encoding='utf-8')
        self.__key_length = key_length

    @staticmethod
    def _b64_encode(content: bytes) -> str:
        return base64.b64encode(content).decode(encoding='utf-8')

    @staticmethod
    def _b64_decode(content: str) -> bytes:
        return base64.b64decode(content.encode('utf-8'))

    def ecb_encrypt(self, plaintext: str) -> str:
        """AES/ECB 模式加密

        ECB模式由于相同的明文块会产生相同的密文块, 通常不推荐用于需要高安全性的场景, 更推荐使用 CBC, CTR 或 GCM 等模式
        """
        plaintext_bytes = plaintext.encode('utf-8')
        padded_data = pad(plaintext_bytes, AES.block_size, style='pkcs7')

        cipher = AES.new(self.__key, AES.MODE_ECB)
        ciphertext_bytes = cipher.encrypt(padded_data)

        return self._b64_encode(ciphertext_bytes)

    def ecb_decrypt(self, ciphertext: str) -> str:
        """AES/ECB 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)

        cipher = AES.new(self.__key, AES.MODE_ECB)
        padded_plaintext_bytes = cipher.decrypt(ciphertext_bytes)

        plaintext_bytes = unpad(padded_plaintext_bytes, AES.block_size, style='pkcs7')

        return plaintext_bytes.decode('utf-8')

    def cfb_encrypt(self, plaintext: str, *, segment_size: int = 128) -> tuple[str, str]:
        """AES/CFB 模式加密

        :return: ciphertext, iv
        """
        plaintext_bytes = plaintext.encode('utf-8')
        iv = urandom(AES.block_size)

        cipher = AES.new(self.__key, AES.MODE_CFB, iv=iv, segment_size=segment_size)
        ciphertext_bytes = cipher.encrypt(plaintext_bytes)

        return self._b64_encode(ciphertext_bytes), self._b64_encode(iv)

    def cfb_decrypt(self, ciphertext: str, iv_text: str, *, segment_size: int = 128) -> str:
        """AES/CFB 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        iv = self._b64_decode(iv_text)

        cipher = AES.new(self.__key, AES.MODE_CFB, iv=iv, segment_size=segment_size)
        plaintext_bytes = cipher.decrypt(ciphertext_bytes)

        return plaintext_bytes.decode('utf-8')

    def cbc_encrypt(self, plaintext: str) -> tuple[str, str]:
        """AES/CBC 模式加密

        :return: ciphertext, iv
        """
        plaintext_bytes = plaintext.encode('utf-8')
        padded_data = pad(plaintext_bytes, AES.block_size, style='pkcs7')
        iv = urandom(AES.block_size)

        cipher = AES.new(self.__key, AES.MODE_CBC, iv=iv)
        ciphertext_bytes = cipher.encrypt(padded_data)

        return self._b64_encode(ciphertext_bytes), self._b64_encode(iv)

    def cbc_decrypt(self, ciphertext: str, iv_text: str) -> str:
        """AES/CBC 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        iv = self._b64_decode(iv_text)

        cipher = AES.new(self.__key, AES.MODE_CBC, iv=iv)
        padded_plaintext_bytes = cipher.decrypt(ciphertext_bytes)

        plaintext_bytes = unpad(padded_plaintext_bytes, AES.block_size, style='pkcs7')

        return plaintext_bytes.decode('utf-8')

    def ctr_encrypt(self, plaintext: str) -> tuple[str, str]:
        """AES/CTR 模式加密

        :return: ciphertext, nonce
        """
        plaintext_bytes = plaintext.encode('utf-8')
        nonce = urandom(self.__key_length // 2)

        cipher = AES.new(self.__key, AES.MODE_CTR, nonce=nonce)
        ciphertext_bytes = cipher.encrypt(plaintext_bytes)

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce)

    def ctr_decrypt(self, ciphertext: str, nonce_text: str) -> str:
        """AES/CTR 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)

        cipher = AES.new(self.__key, AES.MODE_CTR, nonce=nonce)
        plaintext_bytes = cipher.decrypt(ciphertext_bytes)

        return plaintext_bytes.decode('utf-8')

    def gcm_encrypt(self, plaintext: str) -> tuple[str, str, str]:
        """AES/GCM 模式加密

        :return: ciphertext, nonce, tag
        """
        plaintext_bytes = plaintext.encode('utf-8')
        nonce = urandom(AES.block_size)

        cipher = AES.new(self.__key, AES.MODE_GCM, nonce=nonce)
        ciphertext_bytes, tag = cipher.encrypt_and_digest(plaintext_bytes)

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce), self._b64_encode(tag)

    def gcm_decrypt(self, ciphertext: str, nonce_text: str, tag_text: str) -> str:
        """AES/GCM 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)
        tag = self._b64_decode(tag_text)

        cipher = AES.new(self.__key, AES.MODE_GCM, nonce=nonce)
        plaintext_bytes = cipher.decrypt_and_verify(ciphertext_bytes, tag)

        return plaintext_bytes.decode('utf-8')

    def eax_encrypt(self, plaintext: str) -> tuple[str, str, str]:
        """AES/EAX 模式加密

        :return: ciphertext, nonce, tag
        """
        plaintext_bytes = plaintext.encode('utf-8')
        nonce = urandom(AES.block_size)

        cipher = AES.new(self.__key, AES.MODE_EAX, nonce=nonce)
        ciphertext_bytes, tag = cipher.encrypt_and_digest(plaintext_bytes)

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce), self._b64_encode(tag)

    def eax_decrypt(self, ciphertext: str, nonce_text: str, tag_text: str) -> str:
        """AES/EAX 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)
        tag = self._b64_decode(tag_text)

        cipher = AES.new(self.__key, AES.MODE_EAX, nonce=nonce)
        plaintext_bytes = cipher.decrypt_and_verify(ciphertext_bytes, tag)

        return plaintext_bytes.decode('utf-8')


__all__ = [
    'AESEncrypter',
]
