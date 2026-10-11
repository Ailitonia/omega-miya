"""
@Author         : Ailitonia
@Date           : 2026/10/11 23:57
@FileName       : __init__.py
@Project        : omega-miya
@Description    : 加解密便捷工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

用法:
    python bot.py --tool-execute crypto_helper:aes_encrypt
    python bot.py --tool-execute crypto_helper:aes_decrypt
    python bot.py --tool-execute crypto_helper:chacha20_encrypt
    python bot.py --tool-execute crypto_helper:chacha20_decrypt

所有参数均通过交互式输入读取, 不接受命令行参数:
    - 加密: 依次输入 key(不回显, 留空使用配置密钥) -> salt(留空使用默认值) -> 待加密明文
    - 解密: 依次输入 key(不回显, 留空使用配置密钥) -> 密文信封, 盐值自动从信封(v2 格式自描述)中提取
    - 非 tty 环境(管道/重定向)按相同顺序从 stdin 逐行读取, 可用于脚本化调用, 如:
      printf 'my-key\\nmy-salt\\nmy-content\\n' | python bot.py --tool-execute crypto_helper:aes_encrypt

安全说明:
    - 全部敏感参数经交互输入, 不进入 shell history 与 CLI 参数日志
    - 密钥输入不回显; 明文/信封在 tty 下会回显于终端, 请注意可视环境
    - 未配置 OMEGA_AES_KEY 时使用硬件派生兜底密钥, 密文不可跨机器/硬件迁移
"""

import base64
import binascii
import getpass
import sys

from src.utils.crypto import AESEncryptor, ChaCha20Encryptor

if hasattr(sys.stdout, 'reconfigure'):
    # Windows 下 stdout 默认为 GBK 等本地编码, 保证非 ASCII 内容输出到管道/重定向时编码一致
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stdin is not None and not sys.stdin.isatty() and hasattr(sys.stdin, 'reconfigure'):
    # 管道/重定向输入同样统一为 utf-8, 避免非 ASCII 参数按本地编码误解码
    sys.stdin.reconfigure(encoding='utf-8')

_DEFAULT_SALT = 'crypto_helper'
"""默认盐值"""


def _reject_args(args: tuple[str, ...]) -> None:
    """本工具不接受命令行参数, 所有参数均为交互式输入"""
    if args:
        raise ValueError('本工具所有参数均为交互式输入, 不接受命令行参数')


def _prompt(text: str, *, secret: bool = False) -> str:
    """交互式读入一行输入

    secret 且 stdin 为 tty 时使用 getpass 不回显输入; 否则提示语写入 stderr 后从 stdin 读取一行,
    非 tty 环境(管道/重定向)按行读取可用于脚本化调用
    """
    if secret and sys.stdin is not None and sys.stdin.isatty():
        try:
            return getpass.getpass(text)
        except (EOFError, OSError):
            return ''

    if sys.stderr is not None:
        # 提示语无尾随换行, 必须显式 flush, 否则行/块缓冲的 stderr 会将提示语滞留到进程退出才输出
        sys.stderr.write(text)
        sys.stderr.flush()
    if sys.stdin is None:
        return ''
    try:
        return sys.stdin.readline().rstrip('\r\n')
    except OSError:
        return ''


def _read_key() -> str | None:
    """读入密钥, 留空或读取失败时返回 None 以使用配置默认密钥"""
    key = _prompt('Input key (leave empty to use configured default key): ', secret=True)
    return key if key.strip() else None


def _extract_salt(envelope: str) -> bytes:
    """从 v2 密文信封第 3 段提取盐值"""
    segments = envelope.split(':')
    if len(segments) != 6 or segments[0] != 'v2':
        raise ValueError('密文信封格式非法, 应为 v2:{cipher}:{salt}:{nonce}:{tag}:{ciphertext} 格式')

    try:
        return base64.b64decode(segments[2], validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError('密文信封格式非法, 盐值段不是合法的 base64 文本') from e


def aes_encrypt(*args: str) -> None:
    """AES-GCM 加密, 全部参数交互式读入: key -> salt -> plaintext"""
    _reject_args(args)
    key = _read_key()
    salt = _prompt('Input salt (leave empty to use default): ') or _DEFAULT_SALT
    plaintext = _prompt('Input plaintext to encrypt: ')
    print(AESEncryptor(key, salt=salt).encrypt(plaintext))  # noqa: T201 工具结果输出到 stdout, 便于管道捕获


def aes_decrypt(*args: str) -> None:
    """AES-GCM 解密, 全部参数交互式读入: key -> envelope, 盐值自动从信封提取"""
    _reject_args(args)
    key = _read_key()
    envelope = _prompt('Input envelope to decrypt: ')
    print(AESEncryptor(key, salt=_extract_salt(envelope)).decrypt(envelope))  # noqa: T201 同上


def chacha20_encrypt(*args: str) -> None:
    """ChaCha20-Poly1305 加密, 全部参数交互式读入: key -> salt -> plaintext"""
    _reject_args(args)
    key = _read_key()
    salt = _prompt('Input salt (leave empty to use default): ') or _DEFAULT_SALT
    plaintext = _prompt('Input plaintext to encrypt: ')
    print(ChaCha20Encryptor(key, salt=salt).encrypt(plaintext))  # noqa: T201 同上


def chacha20_decrypt(*args: str) -> None:
    """ChaCha20-Poly1305 解密, 全部参数交互式读入: key -> envelope, 盐值自动从信封提取"""
    _reject_args(args)
    key = _read_key()
    envelope = _prompt('Input envelope to decrypt: ')
    print(ChaCha20Encryptor(key, salt=_extract_salt(envelope)).decrypt(envelope))  # noqa: T201 同上


__all__ = [
    'aes_decrypt',
    'aes_encrypt',
    'chacha20_decrypt',
    'chacha20_encrypt',
]
