"""
@Author         : Ailitonia
@Date           : 2024/4/6 14:28
@FileName       : base
@Project        : nonebot2_miya
@Description    : tencent cloud api 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from src.utils import OmegaRequests
from ..config import tencent_cloud_config


class BaseTencentCloudAPI:
    """腾讯云 API 基类"""

    __slots__ = (
        '_secret_id',
        '_secret_key',
        '_host',
        '_endpoint',
        '_service',
        '_headers',
        '_request_timestamp',
        '_date',
        '_credential_scope',
        '_signed_headers',
    )

    _headers: dict[str, Any]
    _request_timestamp: int
    _date: str
    _credential_scope: str
    _signed_headers: str

    def __init__(
            self,
            host: str,
            *,
            secret_id: str | None = None,
            secret_key: str | None = None
    ):
        self._secret_id = tencent_cloud_config.tencent_cloud_secret_id if secret_id is None else secret_id
        self._secret_key = tencent_cloud_config.tencent_cloud_secret_key if secret_key is None else secret_key

        self._host = host
        self._endpoint = f'https://{host}'
        self._service = host.split('.')[0]

    def __upgrade_signed_header(
            self,
            action: str,
            region: str,
            version: str,
            payload: dict[str, Any]
    ) -> None:
        # 初始化请求时间戳
        self._request_timestamp = int(datetime.now().timestamp())
        self._date = datetime.fromtimestamp(self._request_timestamp, tz=UTC).strftime('%Y-%m-%d')
        self._credential_scope = f'{self._date}/{self._service}/tc3_request'

        # 生成签名 Headers 内容
        self._headers = {
            'Content-Type': 'application/json',
            'Host': self._host,
            'X-TC-Action': action,
            'X-TC-Language': 'zh-CN',
            'X-TC-Region': region,
            'X-TC-Timestamp': str(self._request_timestamp),
            'X-TC-Version': version,
        }
        self._signed_headers = ';'.join(sorted(x.lower() for x in self._headers.keys()))

        # 执行 Headers 签名
        self._headers.update({
            'Authorization': self.__sign_v3(payload=payload),
        })

    def __canonical_request(
            self,
            payload: dict[str, Any],
            *,
            http_request_method: str = 'POST',
            canonical_uri: str = '/',
            canonical_query_string: str = ''
    ) -> str:
        """签名步骤 1: 拼接规范请求串"""
        canonical_headers = ''.join(sorted(f'{x}:{y}\n'.lower() for x, y in self._headers.items()))
        hashed_request_payload = hashlib.sha256(json.dumps(payload).encode('utf-8')).hexdigest().lower()

        return (
            f'{http_request_method}\n'
            f'{canonical_uri}\n'
            f'{canonical_query_string}\n'
            f'{canonical_headers}\n'
            f'{self._signed_headers}\n'
            f'{hashed_request_payload}'
        )

    def __string_to_sign(
            self,
            canonical_request: str,
            *,
            algorithm: str = 'TC3-HMAC-SHA256'
    ) -> str:
        """签名步骤 2: 拼接待签名字符串"""
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest().lower()

        return (
            f'{algorithm}\n'
            f'{self._request_timestamp}\n'
            f'{self._credential_scope}\n'
            f'{hashed_canonical_request}'
        )

    def __sign_v3(self, payload: dict[str, Any]) -> str:
        """步骤 3: 计算签名摘要"""

        def __sign(key: bytes | bytearray, msg: str) -> bytes:
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        secret_date = __sign(f'TC3{self._secret_key}'.encode(), self._date)
        secret_service = __sign(secret_date, self._service)
        secret_signing = __sign(secret_service, 'tc3_request')

        canonical_request = self.__canonical_request(payload=payload)
        string_to_sign = self.__string_to_sign(canonical_request)
        signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        return (
            f'TC3-HMAC-SHA256 Credential={self._secret_id}/{self._credential_scope}, '
            f'SignedHeaders={self._signed_headers}, '
            f'Signature={signature}'
        )

    async def _post_request(
            self,
            action: str,
            region: str,
            version: str,
            payload: dict[str, Any]
    ) -> Any:
        """计算请求签名并发送 api 请求"""
        self.__upgrade_signed_header(action=action, region=region, version=version, payload=payload)
        response = await OmegaRequests(timeout=10, headers=self._headers).post(url=self._endpoint, json=payload)
        return OmegaRequests.parse_content_as_json(response)


__all__ = [
    'BaseTencentCloudAPI',
]
