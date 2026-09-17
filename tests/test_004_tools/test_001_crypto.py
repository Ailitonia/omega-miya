"""
@Author         : Ailitonia
@Date           : 2026/9/17 21:30
@FileName       : test_001_crypto
@Project        : omega-miya
@Description    : 加密工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
from typing import TYPE_CHECKING, Any

import pytest
from Crypto.Cipher import AES, ChaCha20

if TYPE_CHECKING:
    from src.utils.crypto import AESEncryptor, ChaCha20Encryptor

TEST_KEY = 'unit-test-key-0123456789abcdef'
OTHER_KEY = 'another-unit-test-key-9876543210'
TEST_SALT = 'unit-test-salt'

AES_VERSIONS = [('AES-128', 16), ('AES-192', 24), ('AES-256', 32)]

BLOCK_SIZE = 16
HEX_CHARS = frozenset('0123456789abcdef')

PLAINTEXTS = ['', 'a', 'A' * 15, 'A' * 16, 'A' * 17, 'A' * 1000, '中文测试', '🔐🔑', 'line1\nline2\t"quote"']
PLAINTEXT_IDS = [
    'empty', 'one-char', 'block-minus-1', 'one-block', 'block-plus-1', 'long', 'chinese', 'emoji', 'escape',
]

AES_MODES = ['cfb', 'cbc', 'ctr', 'gcm', 'eax']

# 异常信息片段, 用于 pytest.raises 的 match 校验
_MSG_B64 = '不是合法的 base64'
_MSG_KEY_LENGTH = '长度必须'
_MSG_VERSION = '不支持的 AES 版本'
_MSG_KEY_ALGORITHM = '不支持的密钥长度'
_MSG_ENVELOPE = '密文信封格式非法'
_MSG_ENVELOPE_CONTENT = '密文信封内容非法'
_MSG_TAG = '认证标签校验未通过'
_MSG_PADDING = '填充不合法'
_MSG_UTF8 = '不是合法的 utf-8 文本'
_MSG_SEGMENT_SIZE = 'segment_size 必须'
_MSG_EMPTY_KEY = '不能为空'
_MSG_KEY_TYPE = '必须为 str 类型'
_MSG_SECRET_TYPE = 'secret 必须为 str 类型'
_MSG_KEY_LENGTH_TYPE = 'key_length 必须为 int 类型'
_MSG_SALT_TYPE = 'salt 必须为 str/bytes 类型或为 None'


def _utf8_length(text: str) -> int:
    return len(text.encode(encoding='utf-8'))


def _padded_length(text: str, block_size: int = BLOCK_SIZE) -> int:
    """PKCS7 填充后的长度, 明文为整块时也会补一整个块"""
    return (_utf8_length(text) // block_size + 1) * block_size


def _flip_b64_byte(content: str, index: int) -> str:
    """翻转 base64 内容解码后指定字节的最低位"""
    raw = bytearray(base64.b64decode(content))
    raw[index] ^= 0x01
    return base64.b64encode(bytes(raw)).decode()


def _call_outcome(func: Any, *args: Any, **kwargs: Any) -> tuple[bool, Any]:
    """执行调用, 返回 (是否成功, 结果或异常对象)"""
    try:
        return True, func(*args, **kwargs)
    except Exception as e:
        return False, e


def _assert_decrypt_never_returns(func: Any, expected_plaintext: str) -> None:
    """断言解密要么报错, 要么得到与原文不同的结果

    无完整性校验的模式(ECB/CBC/CFB/CTR/ChaCha20)无法保证检出篡改或密钥错误,
    只能用"不会还原出原文"来描述其行为边界
    """
    succeeded, outcome = _call_outcome(func)
    if succeeded:
        assert outcome != expected_plaintext
    else:
        assert isinstance(outcome, ValueError)


# 加密实例构造需执行 PBKDF2 (600k 迭代), 实例构造后不可变, 统一使用 module 作用域共享
@pytest.fixture(scope='module')
def aes128() -> 'AESEncryptor':
    """AES-128 加密实例"""
    from src.utils.crypto import AESEncryptor

    return AESEncryptor(key=TEST_KEY, salt=TEST_SALT, version='AES-128')


@pytest.fixture(scope='module')
def aes192() -> 'AESEncryptor':
    """AES-192 加密实例"""
    from src.utils.crypto import AESEncryptor

    return AESEncryptor(key=TEST_KEY, salt=TEST_SALT, version='AES-192')


@pytest.fixture(scope='module')
def aes256() -> 'AESEncryptor':
    """AES-256 加密实例"""
    from src.utils.crypto import AESEncryptor

    return AESEncryptor(key=TEST_KEY, salt=TEST_SALT, version='AES-256')


@pytest.fixture(scope='module')
def aes_default() -> 'AESEncryptor':
    """未指定版本(默认 AES-128)的加密实例"""
    from src.utils.crypto import AESEncryptor

    return AESEncryptor(key=TEST_KEY, salt=TEST_SALT)


@pytest.fixture(scope='module')
def aes_other() -> 'AESEncryptor':
    """使用其他密钥的 AES-128 加密实例"""
    from src.utils.crypto import AESEncryptor

    return AESEncryptor(key=OTHER_KEY, salt=TEST_SALT)


@pytest.fixture(scope='module')
def aes_alt_salt() -> 'AESEncryptor':
    """使用其他盐值的 AES-128 加密实例"""
    from src.utils.crypto import AESEncryptor

    return AESEncryptor(key=TEST_KEY, salt='alt-unit-test-salt')


@pytest.fixture(scope='module')
def chacha20() -> 'ChaCha20Encryptor':
    """ChaCha20 加密实例"""
    from src.utils.crypto import ChaCha20Encryptor

    return ChaCha20Encryptor(key=TEST_KEY, salt=TEST_SALT)


@pytest.fixture(scope='module')
def chacha_other() -> 'ChaCha20Encryptor':
    """使用其他密钥的 ChaCha20 加密实例"""
    from src.utils.crypto import ChaCha20Encryptor

    return ChaCha20Encryptor(key=OTHER_KEY, salt=TEST_SALT)


class TestModuleContract:
    """模块导出契约测试"""

    def test_package_exports(self):
        import src.utils.crypto

        assert src.utils.crypto.__all__ == ['AESEncryptor', 'ChaCha20Encryptor']

    def test_encryptor_exports(self):
        import src.utils.crypto.encryptor

        expected = ['AESEncryptor', 'BaseEncryptor', 'ChaCha20Encryptor', 'derive_key']
        assert src.utils.crypto.encryptor.__all__ == expected

    def test_package_reexports_same_objects(self):
        import src.utils.crypto
        from src.utils.crypto.encryptor import AESEncryptor, ChaCha20Encryptor

        assert src.utils.crypto.AESEncryptor is AESEncryptor
        assert src.utils.crypto.ChaCha20Encryptor is ChaCha20Encryptor

    def test_encryptors_share_base_class(self):
        from src.utils.crypto.encryptor import AESEncryptor, BaseEncryptor, ChaCha20Encryptor

        assert issubclass(AESEncryptor, BaseEncryptor)
        assert issubclass(ChaCha20Encryptor, BaseEncryptor)

    def test_base_encryptor_envelope_requires_implementation(self):
        from src.utils.crypto.encryptor import BaseEncryptor

        with pytest.raises(TypeError, match="Can't instantiate abstract class BaseEncryptor"):
            BaseEncryptor(key=TEST_KEY, key_length=16, salt=TEST_SALT)

    def test_encryptor_key_is_not_readable_from_repr(self, aes128):
        assert TEST_KEY not in repr(aes128)
        assert repr(aes128).startswith('AESEncryptor(')


class TestKeyDerivation:
    """密钥派生与 AES 版本解析测试"""

    @pytest.mark.parametrize('key_length', [16, 24, 32])
    def test_derive_key_returns_requested_length(self, key_length: int):
        from src.utils.crypto.encryptor import derive_key

        key, _salt = derive_key(TEST_KEY, key_length, salt=TEST_SALT)

        assert len(key) == key_length

    @pytest.mark.parametrize('key_length', [0, 1, 15, 17, 31, 33, 64])
    def test_derive_key_rejects_unsupported_length(self, key_length: int):
        from src.utils.crypto.encryptor import derive_key

        with pytest.raises(ValueError, match=_MSG_KEY_ALGORITHM):
            derive_key(TEST_KEY, key_length, salt=TEST_SALT)

    def test_derive_key_is_deterministic(self):
        from src.utils.crypto.encryptor import derive_key

        assert derive_key(TEST_KEY, 32, salt=TEST_SALT) == derive_key(TEST_KEY, 32, salt=TEST_SALT)

    def test_derive_key_varies_with_secret(self):
        from src.utils.crypto.encryptor import derive_key

        assert derive_key(TEST_KEY, 32, salt=TEST_SALT)[0] != derive_key(OTHER_KEY, 32, salt=TEST_SALT)[0]

    def test_derive_key_varies_with_length(self):
        from src.utils.crypto.encryptor import derive_key

        keys = {derive_key(TEST_KEY, length, salt=TEST_SALT)[0] for length in (16, 24, 32)}
        assert len(keys) == 3

    def test_str_and_bytes_salt_are_equivalent(self):
        from src.utils.crypto.encryptor import derive_key

        assert derive_key(TEST_KEY, 32, salt='unit-test-salt') == derive_key(TEST_KEY, 32, salt=b'unit-test-salt')

    def test_short_salt_is_padded_to_16_bytes(self):
        from src.utils.crypto.encryptor import derive_key

        _key, salt = derive_key(TEST_KEY, 32, salt='abc')

        assert salt == b'abc' + b'\x00' * 13

    def test_exact_16_byte_salt_is_unchanged(self):
        from src.utils.crypto.encryptor import derive_key

        _key, salt = derive_key(TEST_KEY, 32, salt=b'A' * 16)

        assert salt == b'A' * 16

    def test_long_salt_is_not_truncated(self):
        from src.utils.crypto.encryptor import derive_key

        _key, salt = derive_key(TEST_KEY, 32, salt=b'A' * 40)

        assert salt == b'A' * 40

    def test_salt_influences_derived_key(self):
        from src.utils.crypto.encryptor import derive_key

        assert derive_key(TEST_KEY, 32, salt='salt-a')[0] != derive_key(TEST_KEY, 32, salt='salt-b')[0]

    def test_omitted_salt_is_random_per_call(self):
        from src.utils.crypto.encryptor import derive_key

        first_key, first_salt = derive_key(TEST_KEY, 32)
        second_key, second_salt = derive_key(TEST_KEY, 32)

        assert first_salt != second_salt
        assert len(first_salt) == 16
        assert len(second_salt) == 16

    def test_key_derivation_uses_full_entropy_bytes(self):
        from src.utils.crypto.encryptor import derive_key

        assert not set(derive_key(TEST_KEY, 32, salt=TEST_SALT)[0]) <= set(b'0123456789abcdef')

    @pytest.mark.parametrize('invalid_secret', [b'bytes-secret', 123, 12.5, None, ['secret']])
    def test_non_str_secret_is_rejected(self, invalid_secret: Any):
        from src.utils.crypto.encryptor import derive_key

        with pytest.raises(TypeError, match=_MSG_SECRET_TYPE):
            derive_key(invalid_secret, 32, salt=TEST_SALT)

    @pytest.mark.parametrize('invalid_length', ['16', 16.0, True, False, None, [16]])
    def test_non_int_key_length_is_rejected(self, invalid_length: Any):
        from src.utils.crypto.encryptor import derive_key

        with pytest.raises(TypeError, match=_MSG_KEY_LENGTH_TYPE):
            derive_key(TEST_KEY, invalid_length, salt=TEST_SALT)

    @pytest.mark.parametrize(
        ('invalid_salt', 'type_name'),
        [(123, 'int'), (12.5, 'float'), (True, 'bool'), (['x'], 'list')],
    )
    def test_non_str_bytes_salt_is_rejected(self, invalid_salt: Any, type_name: str):
        from src.utils.crypto.encryptor import derive_key

        with pytest.raises(TypeError, match=f'{_MSG_SALT_TYPE}, 而不是 {type_name} 类型'):
            derive_key(TEST_KEY, 32, salt=invalid_salt)

    def test_instance_keys_match_derive_key(self, aes128, aes192, aes256, chacha20):
        from src.utils.crypto.encryptor import derive_key

        assert aes128._key == derive_key(TEST_KEY, 16, salt=TEST_SALT)[0]
        assert aes192._key == derive_key(TEST_KEY, 24, salt=TEST_SALT)[0]
        assert aes256._key == derive_key(TEST_KEY, 32, salt=TEST_SALT)[0]
        assert chacha20._key == derive_key(TEST_KEY, 32, salt=TEST_SALT)[0]

    def test_instance_salt_is_normalized(self, aes128, chacha20):
        assert aes128._salt == TEST_SALT.encode(encoding='utf-8').ljust(16, b'\x00')
        assert chacha20._salt == TEST_SALT.encode(encoding='utf-8').ljust(16, b'\x00')

    def test_default_version_is_aes_128(self, aes_default):
        assert aes_default.version == 'AES-128'
        assert aes_default.key_length == 16

    def test_explicit_version_is_recorded(self, aes128, aes192, aes256, chacha20):
        assert aes128.version == 'AES-128'
        assert aes192.version == 'AES-192'
        assert aes256.version == 'AES-256'
        assert chacha20.version == 'ChaCha20'

    @pytest.mark.parametrize(
        'invalid_version',
        ['AES-999', 'aes-256', 'AES128', 'AES-64', '', 'AES-256 ', 128, 256, True, 16.0, b'AES-128'],
    )
    def test_unsupported_version_is_rejected(self, invalid_version: Any):
        from src.utils.crypto import AESEncryptor

        with pytest.raises(ValueError, match=_MSG_VERSION):
            AESEncryptor(key=TEST_KEY, salt=TEST_SALT, version=invalid_version)

    def test_salt_is_required_on_aes_encryptor(self):
        from src.utils.crypto import AESEncryptor

        with pytest.raises(TypeError, match='salt'):
            AESEncryptor(key=TEST_KEY)

    def test_salt_is_required_on_chacha20_encryptor(self):
        from src.utils.crypto import ChaCha20Encryptor

        with pytest.raises(TypeError, match='salt'):
            ChaCha20Encryptor(key=TEST_KEY)

    @pytest.mark.parametrize('invalid_key', [b'bytes-key', 123, 12.5, ['key']])
    def test_non_str_key_is_rejected(self, invalid_key: Any):
        from src.utils.crypto import AESEncryptor, ChaCha20Encryptor

        with pytest.raises(TypeError, match=_MSG_KEY_TYPE):
            AESEncryptor(key=invalid_key, salt=TEST_SALT)

        with pytest.raises(TypeError, match=_MSG_KEY_TYPE):
            ChaCha20Encryptor(key=invalid_key, salt=TEST_SALT)

    def test_none_key_falls_back_to_global_config(self):
        from src.utils.crypto import AESEncryptor
        from src.utils.crypto.config import encrypt_config
        from src.utils.crypto.encryptor import derive_key

        config_key = encrypt_config.omega_aes_key.get_secret_value()

        assert AESEncryptor(salt=TEST_SALT)._key == derive_key(config_key, 16, salt=TEST_SALT)[0]


class TestEncryptConfig:
    """加密配置测试"""

    def test_default_key_is_hardware_derived(self):
        from src.utils.crypto.config import EncryptConfig, generate_aes_key_by_hardware

        config = EncryptConfig()
        assert config.omega_aes_key.get_secret_value() == generate_aes_key_by_hardware().get_secret_value()

    def test_hardware_key_is_stable_within_process(self):
        from src.utils.crypto.config import generate_aes_key_by_hardware

        assert generate_aes_key_by_hardware().get_secret_value() == generate_aes_key_by_hardware().get_secret_value()

    def test_hardware_key_is_sha256_hexdigest(self):
        from src.utils.crypto.config import generate_aes_key_by_hardware

        secret = generate_aes_key_by_hardware().get_secret_value()
        assert len(secret) == 64
        assert set(secret.lower()) <= HEX_CHARS

    def test_explicit_key_is_kept_and_masked(self):
        from src.utils.crypto.config import EncryptConfig

        config = EncryptConfig(omega_aes_key=TEST_KEY)
        assert config.omega_aes_key.get_secret_value() == TEST_KEY
        assert TEST_KEY not in repr(config)
        assert TEST_KEY not in str(config)

    @pytest.mark.parametrize('empty_key', ['', ' ', '   ', '\t', '\n', ' \t\n '])
    def test_empty_key_is_rejected(self, empty_key: str):
        from src.utils.crypto.config import EncryptConfig

        with pytest.raises(ValueError, match=_MSG_EMPTY_KEY):
            EncryptConfig(omega_aes_key=empty_key)

    def test_short_key_is_accepted_with_warning(self):
        from src.utils.crypto.config import EncryptConfig

        # 不设硬性长度下限: 下游可能已用短密钥加密了存量数据, 此处仅记录告警
        assert EncryptConfig(omega_aes_key='short-key').omega_aes_key.get_secret_value() == 'short-key'

    @pytest.mark.parametrize('invalid_key', [123, True, ['key'], {'key': 'value'}])
    def test_non_str_key_is_rejected(self, invalid_key: Any):
        from pydantic import ValidationError

        from src.utils.crypto.config import EncryptConfig

        with pytest.raises(ValidationError):
            EncryptConfig(omega_aes_key=invalid_key)

    def test_encryptor_reads_key_from_global_config(self, monkeypatch: pytest.MonkeyPatch):
        from pydantic import SecretStr

        from src.utils.crypto import AESEncryptor, ChaCha20Encryptor
        from src.utils.crypto.config import encrypt_config
        from src.utils.crypto.encryptor import derive_key

        monkeypatch.setattr(encrypt_config, 'omega_aes_key', SecretStr('monkeypatched-secret'))

        assert AESEncryptor(salt=TEST_SALT)._key == derive_key('monkeypatched-secret', 16, salt=TEST_SALT)[0]
        assert ChaCha20Encryptor(salt=TEST_SALT)._key == derive_key('monkeypatched-secret', 32, salt=TEST_SALT)[0]


class TestBase64Codec:
    """base64 编解码测试"""

    @pytest.mark.parametrize('content', [b'', b'\x00', b'\xff\xfe\x00', b'hello world', bytes(range(256))])
    def test_roundtrip(self, content: bytes):
        from src.utils.crypto import AESEncryptor

        assert AESEncryptor._b64_decode(AESEncryptor._b64_encode(content)) == content

    def test_encode_returns_str(self):
        from src.utils.crypto import AESEncryptor

        assert isinstance(AESEncryptor._b64_encode(b'hello'), str)

    def test_empty_string_decodes_to_empty_bytes(self):
        from src.utils.crypto import AESEncryptor

        assert AESEncryptor._b64_decode('') == b''

    @pytest.mark.parametrize(
        'invalid',
        [
            '!!!!', 'QUJD!', 'QUJ', 'a', 'ab', 'abc',
            '====', '=', 'QUJD==', 'QUJD===', ' QUJD', 'QUJD ', '中文', 'QUJD\n',
        ],
    )
    def test_invalid_content_is_rejected(self, invalid: str):
        from src.utils.crypto import AESEncryptor

        with pytest.raises(ValueError, match=_MSG_B64):
            AESEncryptor._b64_decode(invalid)

    @pytest.mark.parametrize('invalid', [b'QUJD', 123, None])
    def test_non_str_content_is_rejected(self, invalid: Any):
        from src.utils.crypto import AESEncryptor

        with pytest.raises(TypeError, match=_MSG_KEY_TYPE):
            AESEncryptor._b64_decode(invalid)


class TestAESECBRemoved:
    """AES/ECB 模式已彻底移除"""

    def test_ecb_encrypt_raises_not_implemented(self, aes128):
        with pytest.raises(NotImplementedError, match='ECB'):
            aes128.ecb_encrypt('secret')

    def test_ecb_decrypt_raises_not_implemented(self, aes128):
        with pytest.raises(NotImplementedError, match='ECB'):
            aes128.ecb_decrypt('QUJD')

    @pytest.mark.parametrize('invalid_input', [None, b'bytes', 123, '', '\ud800'])
    def test_ecb_methods_reject_any_input(self, aes128, invalid_input: Any):
        # 移除检查先于一切输入校验: 任何输入都直接 NotImplementedError
        with pytest.raises(NotImplementedError):
            aes128.ecb_encrypt(invalid_input)

        with pytest.raises(NotImplementedError):
            aes128.ecb_decrypt(invalid_input)


class TestAESCFB:
    """AES/CFB 模式测试"""

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_roundtrip(self, aes128, plaintext: str):
        ciphertext, iv = aes128.cfb_encrypt(plaintext)
        assert aes128.cfb_decrypt(ciphertext, iv) == plaintext

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_ciphertext_length_equals_plaintext_length(self, aes128, plaintext: str):
        # 流密码模式不做填充
        ciphertext, _iv = aes128.cfb_encrypt(plaintext)
        assert len(base64.b64decode(ciphertext)) == _utf8_length(plaintext)

    def test_iv_is_block_sized_and_unique(self, aes128):
        ivs = {aes128.cfb_encrypt('x')[1] for _ in range(20)}
        assert len(ivs) == 20
        assert all(len(base64.b64decode(iv)) == BLOCK_SIZE for iv in ivs)

    @pytest.mark.parametrize('segment_size', [8, 16, 32, 64, 128])
    def test_valid_segment_size_roundtrip(self, aes128, segment_size: int):
        ciphertext, iv = aes128.cfb_encrypt('segmented plaintext', segment_size=segment_size)
        assert aes128.cfb_decrypt(ciphertext, iv, segment_size=segment_size) == 'segmented plaintext'

    def test_default_segment_size_is_128(self, aes128):
        ciphertext, iv = aes128.cfb_encrypt('default segment')
        assert aes128.cfb_decrypt(ciphertext, iv, segment_size=128) == 'default segment'

    @pytest.mark.parametrize('segment_size', [0, 7, 9, 15, 17, 129, 136, -8])
    def test_invalid_segment_size_is_rejected(self, aes128, segment_size: int):
        with pytest.raises(ValueError, match=_MSG_SEGMENT_SIZE):
            aes128.cfb_encrypt('plaintext', segment_size=segment_size)

    @pytest.mark.parametrize('segment_size', [0, 7, 136])
    def test_invalid_segment_size_is_rejected_on_decrypt(self, aes128, segment_size: int):
        ciphertext, iv = aes128.cfb_encrypt('plaintext')

        with pytest.raises(ValueError, match=_MSG_SEGMENT_SIZE):
            aes128.cfb_decrypt(ciphertext, iv, segment_size=segment_size)

    @pytest.mark.parametrize('segment_size', [True, False, 8.0, '128', None])
    def test_non_int_segment_size_is_rejected(self, aes128, segment_size: Any):
        with pytest.raises(TypeError):
            aes128.cfb_encrypt('plaintext', segment_size=segment_size)

    def test_mismatched_segment_size_never_returns_plaintext(self, aes128):
        ciphertext, iv = aes128.cfb_encrypt('secret', segment_size=128)

        _assert_decrypt_never_returns(lambda: aes128.cfb_decrypt(ciphertext, iv, segment_size=8), 'secret')

    def test_tampered_ciphertext_is_not_detected(self, aes128):
        # CFB 没有完整性校验: 篡改只会得到被改写的明文, 不会报错
        ciphertext, iv = aes128.cfb_encrypt('secret')
        assert aes128.cfb_decrypt(_flip_b64_byte(ciphertext, 0), iv) == 'recret'

    def test_wrong_iv_is_not_detected(self, aes128):
        ciphertext, _iv = aes128.cfb_encrypt('secret payload')

        _assert_decrypt_never_returns(lambda: aes128.cfb_decrypt(ciphertext, _flip_b64_byte(_iv, 0)), 'secret payload')

    @pytest.mark.parametrize('iv_bytes', [b'', b'short', b'A' * 15, b'A' * 17])
    def test_wrong_iv_length_is_rejected(self, aes128, iv_bytes: bytes):
        ciphertext, _iv = aes128.cfb_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            aes128.cfb_decrypt(ciphertext, base64.b64encode(iv_bytes).decode())

    def test_wrong_key_does_not_return_plaintext(self, aes128, aes_other):
        ciphertext, iv = aes128.cfb_encrypt('top-secret-value')

        _assert_decrypt_never_returns(lambda: aes_other.cfb_decrypt(ciphertext, iv), 'top-secret-value')


class TestAESCBC:
    """AES/CBC 模式测试"""

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_roundtrip(self, aes128, plaintext: str):
        ciphertext, iv = aes128.cbc_encrypt(plaintext)
        assert aes128.cbc_decrypt(ciphertext, iv) == plaintext

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_ciphertext_length_is_padded_to_block(self, aes128, plaintext: str):
        ciphertext, _iv = aes128.cbc_encrypt(plaintext)
        assert len(base64.b64decode(ciphertext)) == _padded_length(plaintext)

    def test_iv_is_block_sized_and_unique(self, aes128):
        ivs = {aes128.cbc_encrypt('x')[1] for _ in range(20)}
        assert len(ivs) == 20
        assert all(len(base64.b64decode(iv)) == BLOCK_SIZE for iv in ivs)

    def test_same_plaintext_produces_different_ciphertext(self, aes128):
        assert aes128.cbc_encrypt('same-secret')[0] != aes128.cbc_encrypt('same-secret')[0]

    def test_tampered_ciphertext_never_returns_plaintext(self, aes128):
        ciphertext, iv = aes128.cbc_encrypt('A' * 32)

        _assert_decrypt_never_returns(lambda: aes128.cbc_decrypt(_flip_b64_byte(ciphertext, -1), iv), 'A' * 32)

    def test_wrong_iv_never_returns_plaintext(self, aes128):
        ciphertext, iv = aes128.cbc_encrypt('secret payload')

        _assert_decrypt_never_returns(lambda: aes128.cbc_decrypt(ciphertext, _flip_b64_byte(iv, 0)), 'secret payload')

    @pytest.mark.parametrize('iv_bytes', [b'', b'short', b'A' * 15, b'A' * 17])
    def test_wrong_iv_length_is_rejected(self, aes128, iv_bytes: bytes):
        ciphertext, _iv = aes128.cbc_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            aes128.cbc_decrypt(ciphertext, base64.b64encode(iv_bytes).decode())

    @pytest.mark.parametrize('ciphertext_bytes', [1, 15, 17, 31])
    def test_ciphertext_not_block_aligned_is_rejected(self, aes128, ciphertext_bytes: int):
        _ciphertext, iv = aes128.cbc_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            aes128.cbc_decrypt(base64.b64encode(b'A' * ciphertext_bytes).decode(), iv)

    def test_empty_ciphertext_is_rejected(self, aes128):
        _ciphertext, iv = aes128.cbc_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            aes128.cbc_decrypt('', iv)

    def test_invalid_padding_is_rejected(self, aes128):
        ciphertext, _iv = aes128.cbc_encrypt('secret')

        # 篡改整块密文使解密结果不可能为合法 PKCS7 填充
        with pytest.raises(ValueError, match=_MSG_PADDING):
            aes128.cbc_decrypt(_flip_b64_byte(ciphertext, 0), _flip_b64_byte(_iv, 0))

    def test_invalid_base64_is_rejected(self, aes128):
        _ciphertext, iv = aes128.cbc_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_B64):
            aes128.cbc_decrypt('!!!!', iv)

    def test_wrong_key_does_not_return_plaintext(self, aes128, aes_other):
        ciphertext, iv = aes128.cbc_encrypt('top-secret-value')

        _assert_decrypt_never_returns(lambda: aes_other.cbc_decrypt(ciphertext, iv), 'top-secret-value')


class TestAESCTR:
    """AES/CTR 模式测试"""

    @pytest.mark.parametrize(('version', 'key_length'), AES_VERSIONS)
    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_roundtrip_all_versions(self, version: str, key_length: int, plaintext: str):
        # 审计 H1 回归: nonce 长度曾与密钥长度绑定, AES-256 下 CTR 会直接抛出 Nonce is too long
        from src.utils.crypto import AESEncryptor

        encryptor = AESEncryptor(key=TEST_KEY, salt=TEST_SALT, version=version)
        ciphertext, nonce = encryptor.ctr_encrypt(plaintext)

        assert len(encryptor._key) == key_length
        assert encryptor.ctr_decrypt(ciphertext, nonce) == plaintext

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_ciphertext_length_equals_plaintext_length(self, aes128, plaintext: str):
        ciphertext, _nonce = aes128.ctr_encrypt(plaintext)
        assert len(base64.b64decode(ciphertext)) == _utf8_length(plaintext)

    def test_nonce_is_12_bytes_and_unique(self, aes128):
        nonces = {aes128.ctr_encrypt('x')[1] for _ in range(20)}
        assert len(nonces) == 20
        assert all(len(base64.b64decode(nonce)) == 12 for nonce in nonces)

    @pytest.mark.parametrize('nonce_length', [1, 8, 12, 15])
    def test_nonce_shorter_than_block_is_supported(self, aes128, nonce_length: int):
        # 直接使用指定长度 nonce 构造密文, 验证解密侧不再把 nonce 长度限制在单一取值
        nonce = bytes(range(nonce_length))
        cipher = AES.new(aes128._key, AES.MODE_CTR, nonce=nonce)
        ciphertext = base64.b64encode(cipher.encrypt(b'hello')).decode()

        assert aes128.ctr_decrypt(ciphertext, base64.b64encode(nonce).decode()) == 'hello'

    @pytest.mark.parametrize('nonce_length', [0, 16, 17, 24])
    def test_nonce_not_shorter_than_block_is_rejected(self, aes128, nonce_length: int):
        ciphertext, _nonce = aes128.ctr_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            aes128.ctr_decrypt(ciphertext, base64.b64encode(b'A' * nonce_length).decode())

    def test_tampered_ciphertext_is_not_detected(self, aes128):
        # CTR 没有完整性校验: 篡改只会得到被改写的明文, 不会报错
        ciphertext, nonce = aes128.ctr_encrypt('secret')
        assert aes128.ctr_decrypt(_flip_b64_byte(ciphertext, 0), nonce) == 'recret'

    def test_wrong_nonce_is_not_detected(self, aes128):
        ciphertext, nonce = aes128.ctr_encrypt('secret payload')

        _assert_decrypt_never_returns(
            lambda: aes128.ctr_decrypt(ciphertext, _flip_b64_byte(nonce, 0)), 'secret payload'
        )

    def test_wrong_key_does_not_return_plaintext(self, aes128, aes_other):
        ciphertext, nonce = aes128.ctr_encrypt('top-secret-value')

        _assert_decrypt_never_returns(lambda: aes_other.ctr_decrypt(ciphertext, nonce), 'top-secret-value')


class TestAESAuthenticatedModes:
    """AES/GCM 与 AES/EAX 认证加密模式测试"""

    @pytest.fixture(params=['gcm', 'eax'])
    def mode(self, request: pytest.FixtureRequest) -> str:
        """认证加密模式名"""
        return request.param

    @staticmethod
    def _encrypt(encryptor: 'AESEncryptor', mode: str, plaintext: str) -> tuple[str, str, str]:
        return getattr(encryptor, f'{mode}_encrypt')(plaintext)

    @staticmethod
    def _decrypt(encryptor: 'AESEncryptor', mode: str, encrypted: tuple[str, str, str]) -> str:
        return getattr(encryptor, f'{mode}_decrypt')(*encrypted)

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_roundtrip(self, aes128, mode: str, plaintext: str):
        assert self._decrypt(aes128, mode, self._encrypt(aes128, mode, plaintext)) == plaintext

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_ciphertext_length_equals_plaintext_length(self, aes128, mode: str, plaintext: str):
        ciphertext, _nonce, _tag = self._encrypt(aes128, mode, plaintext)
        assert len(base64.b64decode(ciphertext)) == _utf8_length(plaintext)

    def test_nonce_and_tag_sizes(self, aes128, mode: str):
        _ciphertext, nonce, tag = self._encrypt(aes128, mode, 'secret')
        assert len(base64.b64decode(nonce)) == BLOCK_SIZE
        assert len(base64.b64decode(tag)) == BLOCK_SIZE

    def test_nonce_is_unique(self, aes128, mode: str):
        nonces = {self._encrypt(aes128, mode, 'x')[1] for _ in range(20)}
        assert len(nonces) == 20

    def test_same_plaintext_produces_different_ciphertext(self, aes128, mode: str):
        assert self._encrypt(aes128, mode, 'same-secret')[0] != self._encrypt(aes128, mode, 'same-secret')[0]

    @pytest.mark.parametrize('index', [0, 1, 2])
    def test_tampered_component_is_rejected(self, aes128, mode: str, index: int):
        encrypted = list(self._encrypt(aes128, mode, 'secret'))
        encrypted[index] = _flip_b64_byte(encrypted[index], 0)

        with pytest.raises(ValueError, match=_MSG_TAG):
            self._decrypt(aes128, mode, tuple(encrypted))

    def test_wrong_key_is_rejected(self, aes128, aes_other, mode: str):
        encrypted = self._encrypt(aes128, mode, 'secret')

        with pytest.raises(ValueError, match=_MSG_TAG):
            self._decrypt(aes_other, mode, encrypted)

    def test_tag_with_wrong_length_is_rejected(self, aes128, mode: str):
        # 标签长度由实现固定为 16 字节, 避免接受被截断的认证标签
        ciphertext, nonce, _tag = self._encrypt(aes128, mode, 'secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            getattr(aes128, f'{mode}_decrypt')(ciphertext, nonce, base64.b64encode(b'A' * 8).decode())

    def test_nonce_with_wrong_length_is_rejected(self, aes128, mode: str):
        ciphertext, _nonce, tag = self._encrypt(aes128, mode, 'secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            getattr(aes128, f'{mode}_decrypt')(ciphertext, base64.b64encode(b'A' * 12).decode(), tag)


class TestEnvelopeEncryption:
    """认证加密信封 (`encrypt` / `decrypt`) 测试"""

    @pytest.fixture(params=['aes', 'chacha20'], scope='module')
    def encryptor(self, request: pytest.FixtureRequest, aes128, chacha20) -> Any:
        """加密实例, 分别覆盖 AES-GCM 与 ChaCha20-Poly1305"""
        return aes128 if request.param == 'aes' else chacha20

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_roundtrip(self, encryptor: Any, plaintext: str):
        assert encryptor.decrypt(encryptor.encrypt(plaintext)) == plaintext

    def test_envelope_is_self_describing(self, encryptor: Any):
        from src.utils.crypto import AESEncryptor

        segments = encryptor.encrypt('secret').split(':')
        assert len(segments) == 6
        assert segments[0] == 'v1'
        assert segments[1] == ('AES-128-GCM' if isinstance(encryptor, AESEncryptor) else 'ChaCha20-Poly1305')
        # 密文段长度与明文一致 (认证加密不填充), 且必须是合法 base64
        assert len(base64.b64decode(segments[5], validate=True)) == len('secret')

    def test_salt_segment_encodes_normalized_salt(self, encryptor: Any):
        segments = encryptor.encrypt('secret').split(':')
        assert base64.b64decode(segments[2]) == encryptor._salt
        assert encryptor._salt == TEST_SALT.encode(encoding='utf-8').ljust(16, b'\x00')

    def test_envelope_nonce_and_tag_length(self, encryptor: Any):
        from src.utils.crypto import AESEncryptor

        segments = encryptor.encrypt('secret').split(':')
        expected_nonce_length = BLOCK_SIZE if isinstance(encryptor, AESEncryptor) else 12
        assert len(base64.b64decode(segments[3])) == expected_nonce_length
        assert len(base64.b64decode(segments[4])) == BLOCK_SIZE

    def test_same_plaintext_produces_different_envelope(self, encryptor: Any):
        assert len({encryptor.encrypt('same-secret') for _ in range(20)}) == 20

    @pytest.mark.parametrize('index', [3, 4, 5])
    def test_tampered_nonce_tag_ciphertext_is_rejected(self, encryptor: Any, index: int):
        segments = encryptor.encrypt('secret').split(':')
        segments[index] = _flip_b64_byte(segments[index], 0)

        with pytest.raises(ValueError, match=_MSG_TAG):
            encryptor.decrypt(':'.join(segments))

    def test_tampered_cipher_segment_is_rejected(self, encryptor: Any):
        # 算法标识段被篡改: 解密侧直接拒绝, 不进入标签校验
        segments = encryptor.encrypt('secret').split(':')
        segments[1] = 'AES-256-GCM' if segments[1] == 'AES-128-GCM' else 'AES-128-GCM'

        with pytest.raises(ValueError, match=_MSG_ENVELOPE_CONTENT):
            encryptor.decrypt(':'.join(segments))

    def test_tampered_salt_segment_is_rejected(self, encryptor: Any):
        # 盐值段被篡改: 与实例盐不一致, 直接拒绝
        segments = encryptor.encrypt('secret').split(':')
        segments[2] = _flip_b64_byte(segments[2], 0)

        with pytest.raises(ValueError, match=_MSG_ENVELOPE_CONTENT):
            encryptor.decrypt(':'.join(segments))

    @pytest.mark.parametrize(
        'envelope',
        ['', 'v1', 'v1:a', 'v1:a:b', 'v1:a:b:c', 'v1:a:b:c:d', 'v1:a:b:c:d:e:f', 'plain-text', 'V1:a:b:c:d:e'],
    )
    def test_malformed_envelope_is_rejected(self, encryptor: Any, envelope: str):
        with pytest.raises(ValueError, match=_MSG_ENVELOPE):
            encryptor.decrypt(envelope)

    def test_invalid_base64_segment_is_rejected(self, encryptor: Any):
        with pytest.raises(ValueError, match=_MSG_B64):
            encryptor.decrypt('v1:AES-128-GCM:!!!!:QUJD:QUJD:QUJD')

    def test_unknown_cipher_identifier_is_rejected(self, encryptor: Any):
        with pytest.raises(ValueError, match=_MSG_ENVELOPE_CONTENT):
            encryptor.decrypt('v1:DES-CBC:QUJD:QUJD:QUJD:QUJD')

    def test_wrong_key_is_rejected(self, encryptor: Any, aes_other, chacha_other):
        from src.utils.crypto import AESEncryptor

        envelope = encryptor.encrypt('secret')
        other = aes_other if isinstance(encryptor, AESEncryptor) else chacha_other

        with pytest.raises(ValueError, match=_MSG_TAG):
            other.decrypt(envelope)

    @pytest.mark.parametrize('invalid', [b'v1:a:b:c:d:e', 123, None, ['v1:a:b:c:d:e']])
    def test_non_str_envelope_is_rejected(self, encryptor: Any, invalid: Any):
        with pytest.raises(TypeError, match=_MSG_KEY_TYPE):
            encryptor.decrypt(invalid)


class TestChaCha20:
    """ChaCha20 模式测试"""

    def test_key_length_is_32_bytes(self, chacha20):
        assert len(chacha20._key) == 32

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_roundtrip(self, chacha20, plaintext: str):
        ciphertext, nonce = chacha20.chacha20_encrypt(plaintext)
        assert chacha20.chacha20_decrypt(ciphertext, nonce) == plaintext

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_ciphertext_length_equals_plaintext_length(self, chacha20, plaintext: str):
        ciphertext, _nonce = chacha20.chacha20_encrypt(plaintext)
        assert len(base64.b64decode(ciphertext)) == _utf8_length(plaintext)

    def test_nonce_is_12_bytes_and_unique(self, chacha20):
        nonces = {chacha20.chacha20_encrypt('x')[1] for _ in range(20)}
        assert len(nonces) == 20
        assert all(len(base64.b64decode(nonce)) == 12 for nonce in nonces)

    @pytest.mark.parametrize('nonce_length', [8, 12, 24])
    def test_supported_nonce_lengths_are_decryptable(self, chacha20, nonce_length: int):
        # 24 字节 nonce 即 XChaCha20, 本类不会生成, 但解密侧兼容
        nonce = bytes(range(nonce_length))
        cipher = ChaCha20.new(key=chacha20._key, nonce=nonce)
        ciphertext = base64.b64encode(cipher.encrypt(b'hello')).decode()

        assert chacha20.chacha20_decrypt(ciphertext, base64.b64encode(nonce).decode()) == 'hello'

    @pytest.mark.parametrize('nonce_length', [0, 1, 11, 13, 16, 32])
    def test_unsupported_nonce_lengths_are_rejected(self, chacha20, nonce_length: int):
        ciphertext, _nonce = chacha20.chacha20_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            chacha20.chacha20_decrypt(ciphertext, base64.b64encode(b'A' * nonce_length).decode())

    def test_tampered_ciphertext_is_not_detected(self, chacha20):
        # 标准 ChaCha20 没有完整性校验: 篡改只会得到被改写的明文, 不会报错
        ciphertext, nonce = chacha20.chacha20_encrypt('secret')
        assert chacha20.chacha20_decrypt(_flip_b64_byte(ciphertext, 0), nonce) == 'recret'

    def test_wrong_nonce_is_not_detected(self, chacha20):
        ciphertext, nonce = chacha20.chacha20_encrypt('secret payload')

        _assert_decrypt_never_returns(
            lambda: chacha20.chacha20_decrypt(ciphertext, _flip_b64_byte(nonce, 0)), 'secret payload'
        )

    def test_wrong_key_does_not_return_plaintext(self, chacha20, chacha_other):
        ciphertext, nonce = chacha20.chacha20_encrypt('top-secret-value')

        _assert_decrypt_never_returns(lambda: chacha_other.chacha20_decrypt(ciphertext, nonce), 'top-secret-value')

    def test_undecodable_decrypt_result_is_rejected(self, chacha20):
        # 流密码 keystream 可预测: 利用已知明文构造解密后必然为非法 utf-8 的密文
        plaintext = 'abcd'
        ciphertext, nonce = chacha20.chacha20_encrypt(plaintext)
        keystream = bytes(a ^ b for a, b in zip(base64.b64decode(ciphertext), plaintext.encode(encoding='utf-8')))
        bad_ciphertext = bytes(a ^ b for a, b in zip(b'\x80\x81\x82\x83', keystream))

        with pytest.raises(ValueError, match=_MSG_UTF8):
            chacha20.chacha20_decrypt(base64.b64encode(bad_ciphertext).decode(), nonce)


class TestChaCha20Poly1305:
    """ChaCha20-Poly1305 认证加密模式测试"""

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_roundtrip(self, chacha20, plaintext: str):
        ciphertext, nonce, tag = chacha20.chacha20_poly1305_encrypt(plaintext)
        assert chacha20.chacha20_poly1305_decrypt(ciphertext, nonce, tag) == plaintext

    @pytest.mark.parametrize('plaintext', PLAINTEXTS, ids=PLAINTEXT_IDS)
    def test_ciphertext_length_equals_plaintext_length(self, chacha20, plaintext: str):
        ciphertext, _nonce, _tag = chacha20.chacha20_poly1305_encrypt(plaintext)
        assert len(base64.b64decode(ciphertext)) == _utf8_length(plaintext)

    def test_nonce_and_tag_sizes(self, chacha20):
        _ciphertext, nonce, tag = chacha20.chacha20_poly1305_encrypt('secret')
        assert len(base64.b64decode(nonce)) == 12
        assert len(base64.b64decode(tag)) == BLOCK_SIZE

    @pytest.mark.parametrize('index', [0, 1, 2])
    def test_tampered_component_is_rejected(self, chacha20, index: int):
        encrypted = list(chacha20.chacha20_poly1305_encrypt('secret'))
        encrypted[index] = _flip_b64_byte(encrypted[index], 0)

        with pytest.raises(ValueError, match=_MSG_TAG):
            chacha20.chacha20_poly1305_decrypt(*encrypted)

    def test_wrong_key_is_rejected(self, chacha20, chacha_other):
        encrypted = chacha20.chacha20_poly1305_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_TAG):
            chacha_other.chacha20_poly1305_decrypt(*encrypted)

    def test_tag_with_wrong_length_is_rejected(self, chacha20):
        ciphertext, nonce, _tag = chacha20.chacha20_poly1305_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            chacha20.chacha20_poly1305_decrypt(ciphertext, nonce, base64.b64encode(b'A' * 8).decode())

    def test_nonce_with_wrong_length_is_rejected(self, chacha20):
        ciphertext, _nonce, tag = chacha20.chacha20_poly1305_encrypt('secret')

        with pytest.raises(ValueError, match=_MSG_KEY_LENGTH):
            chacha20.chacha20_poly1305_decrypt(ciphertext, base64.b64encode(b'A' * 16).decode(), tag)


class TestCrossKeyIsolation:
    """密钥、盐与版本隔离测试"""

    @pytest.mark.parametrize('mode', AES_MODES)
    def test_wrong_key_never_returns_plaintext(self, aes128, aes_other, mode: str):
        plaintext = 'multi block top-secret-value ' * 3
        encrypted = getattr(aes128, f'{mode}_encrypt')(plaintext)
        args = (encrypted,) if isinstance(encrypted, str) else encrypted

        _assert_decrypt_never_returns(lambda: getattr(aes_other, f'{mode}_decrypt')(*args), plaintext)

    @pytest.mark.parametrize('mode', AES_MODES)
    def test_cross_version_never_returns_plaintext(self, aes128, aes256, mode: str):
        plaintext = 'multi block top-secret-value ' * 3
        encrypted = getattr(aes256, f'{mode}_encrypt')(plaintext)
        args = (encrypted,) if isinstance(encrypted, str) else encrypted

        _assert_decrypt_never_returns(lambda: getattr(aes128, f'{mode}_decrypt')(*args), plaintext)

    def test_derived_keys_differ_across_versions(self):
        from src.utils.crypto.encryptor import derive_key

        keys = {derive_key(TEST_KEY, key_length, salt=TEST_SALT)[0] for key_length in (16, 24, 32)}
        assert len(keys) == 3

    def test_envelope_cross_version_is_rejected(self, aes128, aes256):
        # 信封携带算法标识, AES-256 信封不能被 AES-128 实例解密
        with pytest.raises(ValueError, match=_MSG_ENVELOPE_CONTENT):
            aes128.decrypt(aes256.encrypt('secret'))

    def test_envelope_cross_algorithm_is_rejected(self, aes128, chacha20):
        with pytest.raises(ValueError, match=_MSG_ENVELOPE_CONTENT):
            chacha20.decrypt(aes128.encrypt('secret'))

        with pytest.raises(ValueError, match=_MSG_ENVELOPE_CONTENT):
            aes128.decrypt(chacha20.encrypt('secret'))

    def test_envelope_salt_mismatch_is_rejected(self, aes128, aes_alt_salt):
        # 同密钥不同盐的实例不能解密对方信封
        with pytest.raises(ValueError, match=_MSG_ENVELOPE_CONTENT):
            aes_alt_salt.decrypt(aes128.encrypt('secret'))


class TestUnsupportedInput:
    """入参类型与长度校验测试"""

    @pytest.mark.parametrize('mode', AES_MODES)
    @pytest.mark.parametrize('invalid_plaintext', [None, b'bytes', 123, ['list'], {'key': 'value'}])
    def test_non_str_plaintext_is_rejected(self, aes128, mode: str, invalid_plaintext: Any):
        with pytest.raises(TypeError, match=_MSG_KEY_TYPE):
            getattr(aes128, f'{mode}_encrypt')(invalid_plaintext)

    @pytest.mark.parametrize('invalid_plaintext', [None, b'bytes', 123, ['list']])
    def test_non_str_plaintext_is_rejected_by_envelope(self, aes128, invalid_plaintext: Any):
        with pytest.raises(TypeError, match=_MSG_KEY_TYPE):
            aes128.encrypt(invalid_plaintext)

    @pytest.mark.parametrize('mode', AES_MODES)
    def test_lone_surrogate_plaintext_is_rejected(self, aes128, mode: str):
        with pytest.raises(ValueError, match='无法使用 utf-8 编码'):
            getattr(aes128, f'{mode}_encrypt')('\ud800')

    def test_lone_surrogate_plaintext_is_rejected_by_envelope(self, aes128):
        with pytest.raises(ValueError, match='无法使用 utf-8 编码'):
            aes128.encrypt('\ud800')

    @pytest.mark.parametrize('mode', AES_MODES)
    @pytest.mark.parametrize('invalid_ciphertext', [None, b'QUJD', 123, ['QUJD']])
    def test_non_str_ciphertext_is_rejected(self, aes128, mode: str, invalid_ciphertext: Any):
        encrypted = getattr(aes128, f'{mode}_encrypt')('secret')
        args = (encrypted,) if isinstance(encrypted, str) else encrypted
        invalid_args = (invalid_ciphertext,) + args[1:]

        with pytest.raises(TypeError, match=_MSG_KEY_TYPE):
            getattr(aes128, f'{mode}_decrypt')(*invalid_args)

    @pytest.mark.parametrize('mode', AES_MODES)
    def test_invalid_base64_ciphertext_is_rejected(self, aes128, mode: str):
        encrypted = getattr(aes128, f'{mode}_encrypt')('secret')
        args = (encrypted,) if isinstance(encrypted, str) else encrypted

        with pytest.raises(ValueError, match=_MSG_B64):
            getattr(aes128, f'{mode}_decrypt')('!!!!', *args[1:])

    def test_undecodable_decrypt_result_is_rejected(self, aes128):
        # 流密码 keystream 可预测: 利用已知明文构造解密后必然为非法 utf-8 的密文
        plaintext = 'abcd'
        ciphertext, nonce = aes128.ctr_encrypt(plaintext)
        keystream = bytes(a ^ b for a, b in zip(base64.b64decode(ciphertext), plaintext.encode(encoding='utf-8')))
        bad_ciphertext = bytes(a ^ b for a, b in zip(b'\x80\x81\x82\x83', keystream))

        with pytest.raises(ValueError, match=_MSG_UTF8):
            aes128.ctr_decrypt(base64.b64encode(bad_ciphertext).decode(), nonce)


class TestAuditRegression:
    """针对历轮审计发现问题的定向回归测试"""

    def test_ctr_supports_aes_256(self, aes256):
        # 审计 H1: 旧实现取 nonce = key_length // 2 字节, AES-256 下 nonce 等于分组长度, CTR 必然失败
        ciphertext, nonce = aes256.ctr_encrypt('multi block plaintext ' * 4)

        assert len(base64.b64decode(nonce)) < BLOCK_SIZE
        assert aes256.ctr_decrypt(ciphertext, nonce) == 'multi block plaintext ' * 4

    def test_base64_decoding_is_strict(self):
        # 审计 M3: 旧实现使用宽松模式, '!!!!' 会被静默解码为空字节串
        from src.utils.crypto import AESEncryptor

        with pytest.raises(ValueError, match=_MSG_B64):
            AESEncryptor._b64_decode('!!!!')

    def test_unsupported_aes_version_is_not_silently_downgraded(self):
        # 审计 M2: 旧实现会把一切无法识别的版本静默当作 AES-128
        from src.utils.crypto import AESEncryptor

        with pytest.raises(ValueError, match=_MSG_VERSION):
            AESEncryptor(key=TEST_KEY, salt=TEST_SALT, version='AES-999')

    def test_empty_config_key_is_rejected(self):
        # 审计 H3: 旧实现接受空密钥, 并派生出所有部署共用的固定密钥
        from src.utils.crypto.config import EncryptConfig

        with pytest.raises(ValueError, match=_MSG_EMPTY_KEY):
            EncryptConfig(omega_aes_key='')

    def test_key_derivation_uses_full_entropy(self):
        # 审计 M1: 旧实现的密钥是十六进制文本, 每字节只有 4 bit 熵
        from src.utils.crypto.encryptor import derive_key

        assert not set(derive_key(TEST_KEY, 32, salt=TEST_SALT)[0]) <= set(b'0123456789abcdef')

    def test_authenticated_envelope_is_available(self, aes128):
        # 审计 H2: 存量密文使用无认证的 ECB, 现提供自带完整性且自描述的默认接口
        envelope = aes128.encrypt('mailbox-password')
        segments = envelope.split(':')

        assert segments[0] == 'v1'
        assert segments[1] == 'AES-128-GCM'

        segments[5] = _flip_b64_byte(segments[5], 0)

        with pytest.raises(ValueError, match=_MSG_TAG):
            aes128.decrypt(':'.join(segments))

    def test_salt_type_error_names_actual_type(self):
        # 审计 N1: salt 类型校验错误消息曾引用错误变量, 恒报 "int 类型"
        from src.utils.crypto.encryptor import derive_key

        with pytest.raises(TypeError, match=f'{_MSG_SALT_TYPE}, 而不是 int 类型'):
            derive_key(TEST_KEY, 32, salt=123)

        with pytest.raises(TypeError, match=f'{_MSG_SALT_TYPE}, 而不是 list 类型'):
            derive_key(TEST_KEY, 32, salt=['x'])

    def test_config_failure_fails_fast_in_subprocess(self):
        # 空密钥配置使宿主进程在模块导入期快速失败 (fail-fast 约定), 只能在子进程中复现
        import os
        import subprocess
        import sys
        from pathlib import Path

        script = (
            'import importlib.util\n'
            'import nonebot\n'
            'nonebot.init()\n'
            "spec = importlib.util.spec_from_file_location('probe_config', 'src/utils/crypto/config.py')\n"
            'module = importlib.util.module_from_spec(spec)\n'
            'spec.loader.exec_module(module)\n'
        )
        project_root = Path(__file__).resolve().parents[2]

        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True,
            cwd=project_root,
            env={**os.environ, 'OMEGA_AES_KEY': '', 'PYTHONIOENCODING': 'utf-8'},
        )

        assert result.returncode != 0
