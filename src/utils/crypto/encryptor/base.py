"""
@Author         : Ailitonia
@Date           : 2026/9/17 19:30
@FileName       : base.py
@Project        : omega-miya
@Description    : 加密套件基类与密钥派生
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import base64
import binascii
import re
from hashlib import pbkdf2_hmac
from os import urandom
from typing import Literal

from ..config import encrypt_config

_B64_PATTERN = re.compile(rb'[A-Za-z0-9+/]*={0,2}')
"""base64 编码匹配模式"""
_PURPOSE_PATTERN = re.compile(r'[A-Za-z0-9-]+')
"""派生用途标识匹配模式, 限定字符集以保证域分离框架分隔无歧义"""
_KDF_DOMAIN_PREFIX = b'omega-miya-kdf|v2|'
"""KDF 域分离框架前缀"""
_SUPPORTED_KEY_LENGTHS = (16, 24, 32,)
"""支持的密钥长度"""


def derive_key(
        secret: str,
        key_length: int,
        *,
        purpose: str,
        salt: str | bytes | None = None,
) -> tuple[bytes, bytes]:
    """从密钥口令派生指定长度的加密密钥

    派生时将用途标识与目标密钥长度混入 KDF 盐值实现域分离, 不同用途/长度的派生密钥相互独立

    :param secret: 密钥口令
    :param key_length: 目标密钥长度, 仅支持 16/24/32 字节
    :param purpose: 派生用途标识, 仅允许字母/数字/连字符, 如 AES-256 / ChaCha20
    :param salt: 盐值, 原样使用不做填充, 留空则随机生成
    :raises TypeError: secret/purpose 不为 str 或 key_length 不为 int
    :raises ValueError: secret 为空或仅含空白字符, purpose 含非法字符, salt 为空, 或 key_length 不为 16/24/32 之一
    :return: 派生密钥, 盐值
    """
    if not isinstance(secret, str):
        raise TypeError(f'secret 必须为 str 类型, 而不是 {type(secret).__name__} 类型')
    if not secret.strip():
        raise ValueError('secret 不能为空或仅包含空白字符')
    if isinstance(key_length, bool) or not isinstance(key_length, int):
        raise TypeError(f'key_length 必须为 int 类型, 而不是 {type(key_length).__name__} 类型')
    if key_length not in _SUPPORTED_KEY_LENGTHS:
        raise ValueError(f'不支持的密钥长度: {key_length}, 长度必须为 16/24/32 字节之一')
    if not isinstance(purpose, str):
        raise TypeError(f'purpose 必须为 str 类型, 而不是 {type(purpose).__name__} 类型')
    if _PURPOSE_PATTERN.fullmatch(purpose) is None:
        raise ValueError(f'purpose 仅允许非空的字母/数字/连字符组合, 而不是 {purpose!r}')
    if (salt is not None) and (not isinstance(salt, (str, bytes))):
        raise TypeError(f'salt 必须为 str/bytes 类型或为 None, 而不是 {type(salt).__name__} 类型')

    secret_bytes = secret.encode(encoding='utf-8')

    if salt is None:
        salt_bytes = urandom(16)
    elif isinstance(salt, str):
        if not salt.strip():
            raise ValueError('salt 不能为空或仅包含空白字符')
        salt_bytes = salt.encode(encoding='utf-8')
    else:
        if not salt:
            raise ValueError('salt 不能为空')
        salt_bytes = salt

    domain = _KDF_DOMAIN_PREFIX + purpose.encode(encoding='ascii') + b'|' + str(key_length).encode() + b'|'
    kdf_salt = domain + salt_bytes

    return pbkdf2_hmac('sha256', secret_bytes, kdf_salt, 600_000, dklen=key_length), salt_bytes


class BaseEncryptor(abc.ABC):
    """加密器基类, 提供密钥派生、严格 base64 编解码与认证加密信封的公共实现

    Version: 加密信封格式
    - v2 -> {version}:{cipher}:{salt}:{nonce}:{tag}:{ciphertext}

    v2 信封绑定 PBKDF2-HMAC-SHA256 (600_000 迭代) + 域分离 (purpose 与 key_length 混入 KDF 盐值)
    + 盐原样使用 + AES-GCM 96-bit nonce; 变更上述任一参数必须升级信封版本并保持旧版本可解密;
    v1 (无域分离, 盐 null 填充, GCM 16 字节 nonce) 已废弃
    """

    _ENVELOPE_VERSION: Literal['v2'] = 'v2'
    """加密信封版本值"""

    def __init__(
            self,
            key: str | None = None,
            *,
            key_length: int,
            salt: str | bytes,
            purpose: str,
    ) -> None:
        if key is None:
            key = encrypt_config.omega_aes_key.get_secret_value()
        if not isinstance(key, str):
            raise TypeError(f'key 必须为 str 类型, 而不是 {type(key).__name__} 类型')

        self._key, self._salt = derive_key(secret=key, key_length=key_length, purpose=purpose, salt=salt)
        self.key_length = key_length

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(key_length={self.key_length})'

    @staticmethod
    def _b64_encode(content: bytes) -> str:
        return base64.b64encode(content).decode(encoding='utf-8')

    @staticmethod
    def _b64_decode(content: str) -> bytes:
        if not isinstance(content, str):
            raise TypeError(f'content 必须为 str 类型, 而不是 {type(content).__name__} 类型')

        try:
            encoded = content.encode(encoding='utf-8')
        except UnicodeEncodeError as e:
            raise ValueError('content 不是合法的 base64 文本') from e

        if len(encoded) % 4 != 0 or _B64_PATTERN.fullmatch(encoded) is None:
            raise ValueError('content 不是合法的 base64 文本')

        try:
            return base64.b64decode(encoded, validate=True)
        except binascii.Error as e:
            raise ValueError('content 不是合法的 base64 文本') from e

    @staticmethod
    def _encode_utf8(text: str) -> bytes:
        if not isinstance(text, str):
            raise TypeError(f'text 必须为 str 类型, 而不是 {type(text).__name__} 类型')
        try:
            return text.encode(encoding='utf-8')
        except UnicodeEncodeError as e:
            raise ValueError(f'无法使用 utf-8 编码明文文本: {e}') from e

    @staticmethod
    def _decode_utf8(data: bytes) -> str:
        try:
            return data.decode(encoding='utf-8')
        except UnicodeDecodeError as e:
            raise ValueError(f'解码结果不是合法的 utf-8 文本: {e}') from e

    @classmethod
    def _unpack_envelope(cls, envelope: str) -> tuple[str, bytes, bytes, bytes, bytes]:
        """解析 v2 认证加密信封, 返回 (cipher, salt, nonce, tag, ciphertext)"""
        if not isinstance(envelope, str):
            raise TypeError(f'envelope 必须为 str 类型, 而不是 {type(envelope).__name__} 类型')

        segments = envelope.split(':')
        if len(segments) != 6 or segments[0] != cls._ENVELOPE_VERSION:
            raise ValueError(
                '密文信封格式非法, 应为 v2:{cipher}:{salt}:{nonce}:{tag}:{ciphertext} 格式'
            )

        cipher = segments[1]
        salt = cls._b64_decode(segments[2])
        nonce = cls._b64_decode(segments[3])
        tag = cls._b64_decode(segments[4])
        ciphertext = cls._b64_decode(segments[5])
        return cipher, salt, nonce, tag, ciphertext

    @abc.abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """认证加密, 输出自描述信封 v2:{cipher}:{salt}:{nonce}:{tag}:{ciphertext}"""
        raise NotImplementedError

    @abc.abstractmethod
    def decrypt(self, envelope: str) -> str:
        """解密并校验 v2 认证加密信封"""
        raise NotImplementedError


__all__ = [
    'BaseEncryptor',
    'derive_key',
]
