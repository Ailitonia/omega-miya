"""
@Author         : Ailitonia
@Date           : 2024/11/5 16:48:00
@FileName       : web_ticket.py
@Project        : omega-miya
@Description    : BiliTicket 令牌
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import hashlib
import hmac
import time


def hmac_sha256(key: str, message: str) -> str:
    """使用 HMAC-SHA256 算法对给定的消息进行散列

    :param key: 密钥
    :param message: 要加密的消息
    :return: 加密后的哈希值
    """

    encoded_key = key.encode(encoding='utf-8')
    encoded_message = message.encode(encoding='utf-8')

    # 使用 HMAC-SHA256 计算哈希值并转换为十六进制字符串
    hmac_obj = hmac.new(encoded_key, encoded_message, hashlib.sha256)
    return hmac_obj.digest().hex()


def create_gen_web_ticket_params(bili_jct: str | None = None) -> dict[str, str]:
    """生成请求 BiliTicket 的参数"""
    timestamp = int(time.time())
    hex_sign = hmac_sha256('XgwSnGZ1p', f'ts{timestamp}')

    return {
        'key_id': 'ec02',
        'hexsign': hex_sign,
        'context[ts]': f'{timestamp}',
        'csrf': '' if bili_jct is None else bili_jct
    }


__all__ = [
    'create_gen_web_ticket_params',
]
