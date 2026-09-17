"""
@Author         : Ailitonia
@Date           : 2024/9/7 23:51
@FileName       : chacha20
@Project        : omega-miya
@Description    : ChaCha20 加密套件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from os import urandom

from Crypto.Cipher import ChaCha20, ChaCha20_Poly1305

from .base import BaseEncryptor


class ChaCha20Encryptor(BaseEncryptor):
    """ChaCha20 加解密工具集"""

    _CHACHA20_NONCE_SIZE: int = 12
    _POLY1305_NONCE_SIZE: int = 12
    _POLY1305_TAG_SIZE: int = 16

    def __init__(
            self,
            key: str | None = None,
            *,
            salt: str | bytes,
    ) -> None:
        super().__init__(
            key,
            key_length=ChaCha20.key_size,
            salt=salt,
        )
        self.version = 'ChaCha20'

    def chacha20_encrypt(self, plaintext: str) -> tuple[str, str]:
        """标准 ChaCha20 加密

        :return: ciphertext, nonce
        """
        # Nonce must be 8/12 bytes(ChaCha20) or 24 bytes (XChaCha20)
        nonce = urandom(self._CHACHA20_NONCE_SIZE)

        cipher = ChaCha20.new(key=self._key, nonce=nonce)
        ciphertext_bytes = cipher.encrypt(self._encode_utf8(plaintext))

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce)

    def chacha20_decrypt(self, ciphertext: str, nonce_text: str) -> str:
        """标准 ChaCha20 解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)

        if len(nonce) not in (8, 12, 24):
            raise ValueError(f'nonce 长度必须为 8/12/24 字节之一, 实际为 {len(nonce)} 字节')

        cipher = ChaCha20.new(key=self._key, nonce=nonce)
        return self._decode_utf8(cipher.decrypt(ciphertext_bytes))

    def chacha20_poly1305_encrypt(self, plaintext: str) -> tuple[str, str, str]:
        """ChaCha20-Poly1305 加密

        :return: ciphertext, nonce, tag
        """
        nonce = urandom(self._POLY1305_NONCE_SIZE)

        cipher = ChaCha20_Poly1305.new(key=self._key, nonce=nonce)
        ciphertext_bytes, tag = cipher.encrypt_and_digest(self._encode_utf8(plaintext))

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce), self._b64_encode(tag)

    def _chacha20_poly1305_decrypt_bytes(self, ciphertext_bytes: bytes, nonce: bytes, tag: bytes) -> bytes:
        if len(nonce) != self._POLY1305_NONCE_SIZE:
            raise ValueError(f'nonce 长度必须为 {self._POLY1305_NONCE_SIZE} 字节, 实际为 {len(nonce)} 字节')
        if len(tag) != self._POLY1305_TAG_SIZE:
            raise ValueError(f'tag 长度必须为 {self._POLY1305_TAG_SIZE} 字节, 实际为 {len(tag)} 字节')

        cipher = ChaCha20_Poly1305.new(key=self._key, nonce=nonce)
        try:
            return cipher.decrypt_and_verify(ciphertext_bytes, tag)
        except ValueError as e:
            raise ValueError('认证标签校验未通过, 密文可能已被篡改或密钥错误') from e

    def chacha20_poly1305_decrypt(self, ciphertext: str, nonce_text: str, tag_text: str) -> str:
        """ChaCha20-Poly1305 解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)
        tag = self._b64_decode(tag_text)

        return self._decode_utf8(self._chacha20_poly1305_decrypt_bytes(ciphertext_bytes, nonce, tag))

    def encrypt(self, plaintext: str) -> str:
        """默认使用 ChaCha20-Poly1305 认证加密, 输出自描述信封  v1:{cipher}:{salt}:{nonce}:{tag}:{ciphertext}"""
        ciphertext, nonce, tag = self.chacha20_poly1305_encrypt(plaintext)
        salt = self._b64_encode(self._salt)

        return f'{self._ENVELOPE_VERSION}:{self.version}-Poly1305:{salt}:{nonce}:{tag}:{ciphertext}'

    def decrypt(self, envelope: str) -> str:
        """默认使用 ChaCha20-Poly1305 解密并校验 v1 认证加密信封"""
        cipher, salt, nonce, tag, ciphertext = self._unpack_envelope(envelope)

        if cipher != f'{self.version}-Poly1305':
            raise ValueError(f'密文信封内容非法, 加密算法不一致, 应为 {self.version}-Poly1305, 而不是 {cipher}')

        if salt != self._salt:
            raise ValueError('密文信封内容非法, 盐值不一致')

        return self._decode_utf8(self._chacha20_poly1305_decrypt_bytes(ciphertext, nonce, tag))


__all__ = [
    'ChaCha20Encryptor',
]
