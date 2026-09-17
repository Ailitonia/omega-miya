"""
@Author         : Ailitonia
@Date           : 2022/04/17 1:23
@FileName       : aes.py
@Project        : nonebot2_miya
@Description    : AES 加密套件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from os import urandom
from typing import Literal

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from .base import BaseEncryptor

_AES_VERSION_KEY_LENGTHS: dict[str, int] = {
    'AES-128': 16,
    'AES-192': 24,
    'AES-256': 32,
}
"""AES 版本及其对应的密钥长度"""

_ECB_REMOVED_MESSAGE = (
    'ECB 模式已弃用: 相同明文块会产生相同密文块, 会泄漏明文模式且无完整性保护, 请改用 encrypt()/decrypt() 认证加密信封'
)
"""ECB 模式移除提示信息"""


class AESEncryptor(BaseEncryptor):
    """AES 加解密工具集"""

    def __init__(
            self,
            key: str | None = None,
            *,
            salt: str | bytes,
            version: Literal['AES-128', 'AES-192', 'AES-256'] | None = None,
    ) -> None:
        if version is None:
            version = 'AES-128'

        if not isinstance(version, str) or version not in _AES_VERSION_KEY_LENGTHS:
            raise ValueError(f'不支持的 AES 版本: {version!r}, 必须为 AES-128/AES-192/AES-256 之一')

        super().__init__(
            key,
            key_length=_AES_VERSION_KEY_LENGTHS[version],
            salt=salt,
        )
        self.version = version

    @staticmethod
    def _require_exact_length(name: str, value: bytes, expected: int) -> None:
        if len(value) != expected:
            raise ValueError(f'{name} 长度必须为 {expected} 字节, 实际为 {len(value)} 字节')

    @staticmethod
    def _require_block_aligned_ciphertext(ciphertext: bytes) -> None:
        if not ciphertext or len(ciphertext) % AES.block_size != 0:
            raise ValueError(f'密文长度必须为 {AES.block_size} 字节的非零整数倍, 实际为 {len(ciphertext)} 字节')

    @staticmethod
    def _validate_segment_size(segment_size: int) -> None:
        if isinstance(segment_size, bool) or not isinstance(segment_size, int):
            raise TypeError(f'segment_size 必须为 int 类型, 而不是 {type(segment_size).__name__} 类型')
        if not 8 <= segment_size <= 128 or segment_size % 8 != 0:
            raise ValueError('segment_size 必须为 8 到 128 之间且为 8 的倍数')

    def _decrypt_padded(self, padded_plaintext: bytes, *, style: str = 'pkcs7') -> str:
        try:
            plaintext_bytes = unpad(padded_plaintext, AES.block_size, style=style)
        except ValueError as e:
            raise ValueError('填充不合法, 密文可能已损坏或密钥错误') from e
        return self._decode_utf8(plaintext_bytes)

    def ecb_encrypt(self, plaintext: str) -> str:
        """AES/ECB 模式加密 (已弃用)

        ECB模式由于相同的明文块会产生相同的密文块, 通常不推荐用于需要高安全性的场景, 更推荐使用 CBC, CTR 或 GCM 等模式
        """
        raise NotImplementedError(_ECB_REMOVED_MESSAGE)

    def ecb_decrypt(self, ciphertext: str) -> str:
        """AES/ECB 模式解密 (已弃用)"""
        raise NotImplementedError(_ECB_REMOVED_MESSAGE)

    def cfb_encrypt(self, plaintext: str, *, segment_size: int = 128) -> tuple[str, str]:
        """AES/CFB 模式加密

        :return: ciphertext, iv
        """
        self._validate_segment_size(segment_size)

        iv = urandom(AES.block_size)

        cipher = AES.new(self._key, AES.MODE_CFB, iv=iv, segment_size=segment_size)
        ciphertext_bytes = cipher.encrypt(self._encode_utf8(plaintext))

        return self._b64_encode(ciphertext_bytes), self._b64_encode(iv)

    def cfb_decrypt(self, ciphertext: str, iv_text: str, *, segment_size: int = 128) -> str:
        """AES/CFB 模式解密"""
        self._validate_segment_size(segment_size)

        ciphertext_bytes = self._b64_decode(ciphertext)
        iv = self._b64_decode(iv_text)
        self._require_exact_length('iv', iv, AES.block_size)

        cipher = AES.new(self._key, AES.MODE_CFB, iv=iv, segment_size=segment_size)
        return self._decode_utf8(cipher.decrypt(ciphertext_bytes))

    def cbc_encrypt(self, plaintext: str) -> tuple[str, str]:
        """AES/CBC 模式加密

        :return: ciphertext, iv
        """
        padded_data = pad(self._encode_utf8(plaintext), AES.block_size, style='pkcs7')
        iv = urandom(AES.block_size)

        cipher = AES.new(self._key, AES.MODE_CBC, iv=iv)
        ciphertext_bytes = cipher.encrypt(padded_data)

        return self._b64_encode(ciphertext_bytes), self._b64_encode(iv)

    def cbc_decrypt(self, ciphertext: str, iv_text: str) -> str:
        """AES/CBC 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        iv = self._b64_decode(iv_text)
        self._require_block_aligned_ciphertext(ciphertext_bytes)
        self._require_exact_length('iv', iv, AES.block_size)

        cipher = AES.new(self._key, AES.MODE_CBC, iv=iv)
        return self._decrypt_padded(cipher.decrypt(ciphertext_bytes), style='pkcs7')

    def ctr_encrypt(self, plaintext: str) -> tuple[str, str]:
        """AES/CTR 模式加密

        :return: ciphertext, nonce
        """
        nonce = urandom(12)

        cipher = AES.new(self._key, AES.MODE_CTR, nonce=nonce)
        ciphertext_bytes = cipher.encrypt(self._encode_utf8(plaintext))

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce)

    def ctr_decrypt(self, ciphertext: str, nonce_text: str) -> str:
        """AES/CTR 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)
        if not 0 < len(nonce) < AES.block_size:
            raise ValueError(f'nonce 长度必须为 1 到 {AES.block_size - 1} 字节, 实际为 {len(nonce)} 字节')

        cipher = AES.new(self._key, AES.MODE_CTR, nonce=nonce)
        return self._decode_utf8(cipher.decrypt(ciphertext_bytes))

    def gcm_encrypt(self, plaintext: str) -> tuple[str, str, str]:
        """AES/GCM 模式加密

        :return: ciphertext, nonce, tag
        """
        nonce = urandom(AES.block_size)

        cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce)
        ciphertext_bytes, tag = cipher.encrypt_and_digest(self._encode_utf8(plaintext))

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce), self._b64_encode(tag)

    def _gcm_decrypt_bytes(self, ciphertext_bytes: bytes, nonce: bytes, tag: bytes) -> bytes:
        self._require_exact_length('nonce', nonce, AES.block_size)
        self._require_exact_length('tag', tag, AES.block_size)

        cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce)
        try:
            return cipher.decrypt_and_verify(ciphertext_bytes, tag)
        except ValueError as e:
            raise ValueError('认证标签校验未通过, 密文可能已被篡改或密钥错误') from e

    def gcm_decrypt(self, ciphertext: str, nonce_text: str, tag_text: str) -> str:
        """AES/GCM 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)
        tag = self._b64_decode(tag_text)

        return self._decode_utf8(self._gcm_decrypt_bytes(ciphertext_bytes, nonce, tag))

    def eax_encrypt(self, plaintext: str) -> tuple[str, str, str]:
        """AES/EAX 模式加密

        :return: ciphertext, nonce, tag
        """
        nonce = urandom(AES.block_size)

        cipher = AES.new(self._key, AES.MODE_EAX, nonce=nonce)
        ciphertext_bytes, tag = cipher.encrypt_and_digest(self._encode_utf8(plaintext))

        return self._b64_encode(ciphertext_bytes), self._b64_encode(nonce), self._b64_encode(tag)

    def eax_decrypt(self, ciphertext: str, nonce_text: str, tag_text: str) -> str:
        """AES/EAX 模式解密"""
        ciphertext_bytes = self._b64_decode(ciphertext)
        nonce = self._b64_decode(nonce_text)
        tag = self._b64_decode(tag_text)

        self._require_exact_length('nonce', nonce, AES.block_size)
        self._require_exact_length('tag', tag, AES.block_size)

        cipher = AES.new(self._key, AES.MODE_EAX, nonce=nonce)
        try:
            plaintext_bytes = cipher.decrypt_and_verify(ciphertext_bytes, tag)
        except ValueError as e:
            raise ValueError('认证标签校验未通过, 密文可能已被篡改或密钥错误') from e

        return self._decode_utf8(plaintext_bytes)

    def encrypt(self, plaintext: str) -> str:
        """默认使用 AES-GCM 认证加密, 输出自描述信封 v1:{cipher}:{salt}:{nonce}:{tag}:{ciphertext}"""
        ciphertext, nonce, tag = self.gcm_encrypt(plaintext)
        salt = self._b64_encode(self._salt)

        return f'{self._ENVELOPE_VERSION}:{self.version}-GCM:{salt}:{nonce}:{tag}:{ciphertext}'

    def decrypt(self, envelope: str) -> str:
        """默认使用 AES-GCM 解密并校验 v1 认证加密信封"""
        cipher, salt, nonce, tag, ciphertext = self._unpack_envelope(envelope)

        if cipher != f'{self.version}-GCM':
            raise ValueError(f'密文信封内容非法, 加密算法不一致, 应为 {self.version}-GCM, 而不是 {cipher}')

        if salt != self._salt:
            raise ValueError('密文信封内容非法, 盐值不一致')

        return self._decode_utf8(self._gcm_decrypt_bytes(ciphertext, nonce, tag))


__all__ = [
    'AESEncryptor',
]
