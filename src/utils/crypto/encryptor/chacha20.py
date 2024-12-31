"""
@Author         : Ailitonia
@Date           : 2024/9/7 23:51
@FileName       : chacha20
@Project        : omega-miya
@Description    : ChaCha20 加密套件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
from hashlib import shake_128
from os import urandom

from Crypto.Cipher import ChaCha20, ChaCha20_Poly1305

from ..config import encrypt_config


class ChaCha20Encryptor:
    """ChaCha20 加解密工具集"""

    def __init__(self, key: str | None = None) -> None:
        if key is None:
            key = encrypt_config.omega_aes_key.get_secret_value()

        self.__key = shake_128(key.encode(encoding='utf-8')).hexdigest(ChaCha20.key_size // 2).encode(encoding='utf-8')

    @staticmethod
    def _b64_encode(content: bytes) -> str:
        return base64.b64encode(content).decode(encoding='utf-8')

    @staticmethod
    def _b64_decode(content: str) -> bytes:
        return base64.b64decode(content.encode('utf-8'))

    def chacha20_encrypt(self, plaintext: str) -> tuple[str, str]:
        """标准 ChaCha20 加密

        :return: ciphertext, nonce
        """
        plaintext_bytes = plaintext.encode('utf-8')
        nonce = urandom(12)  # Nonce must be 8/12 bytes(ChaCha20) or 24 bytes (XChaCha20)

        cipher = ChaCha20.new(key=self.__key, nonce=nonce)
        ciphertext_bytes = cipher.encrypt(plaintext_bytes)

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce)

    def chacha20_decrypt(self, ciphertext: str, nonce_text: str) -> str:
        """标准 ChaCha20 解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)

        cipher = ChaCha20.new(key=self.__key, nonce=nonce)
        plaintext_bytes = cipher.decrypt(ciphertext_bytes)

        return plaintext_bytes.decode('utf-8')

    def chacha20_poly1305_encrypt(self, plaintext: str) -> tuple[str, str, str]:
        """ChaCha20-Poly1305 加密

        :return: ciphertext, nonce, tag
        """
        plaintext_bytes = plaintext.encode('utf-8')
        nonce = urandom(12)  # Nonce must be 8, 12 or 24 bytes long

        cipher = ChaCha20_Poly1305.new(key=self.__key, nonce=nonce)
        ciphertext_bytes, tag = cipher.encrypt_and_digest(plaintext_bytes)

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce), self._b64_encode(tag)

    def chacha20_poly1305_decrypt(self, ciphertext: str, nonce_text: str, tag_text: str) -> str:
        """ChaCha20-Poly1305 解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)
        tag = self._b64_decode(tag_text)

        cipher = ChaCha20_Poly1305.new(key=self.__key, nonce=nonce)
        plaintext_bytes = cipher.decrypt_and_verify(ciphertext_bytes, tag)

        return plaintext_bytes.decode('utf-8')


__all__ = [
    'ChaCha20Encryptor',
]
