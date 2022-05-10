import json
import hashlib
import hmac
import datetime
from typing import Any

from omega_miya.web_resource.http_fetcher import HttpFetcher, HttpFetcherDictResult

from .config import tencent_cloud_config


class TencentCloudApi(object):
    """腾讯云 Api"""
    def __init__(
            self,
            host: str,
            *,
            secret_id: str | None = None,
            secret_key: str | None = None):
        self._secret_id = tencent_cloud_config.tencent_cloud_secret_id if secret_id is None else secret_id
        self._secret_key = tencent_cloud_config.tencent_cloud_secret_key if secret_key is None else secret_key

        self._host = host
        self._endpoint = f'https://{host}'
        self._service = host.split('.')[0]
        self._headers = {
            "Content-Type": "application/json",
            "Host": self._host
        }

        self._request_timestamp = int(datetime.datetime.now().timestamp())
        self._date = datetime.datetime.utcfromtimestamp(self._request_timestamp).strftime('%Y-%m-%d')
        self._credential_scope = f'{self._date}/{self._service}/tc3_request'

        sort_signed_headers = [f'{x}'.lower() for x in self._headers.keys()]
        sort_signed_headers.sort()
        self._signed_headers = ';'.join(sort_signed_headers)

    def __upgrade_signed_header(self,
                                action: str,
                                region: str,
                                version: str,
                                payload: dict[str, Any]):
        self._headers.update({
            'Authorization': self.__sign_v3(payload=payload),
            'Content-Type': 'application/json',
            'Host': self._host,
            'X-TC-Action': action,
            'X-TC-Region': region,
            'X-TC-Timestamp': str(self._request_timestamp),
            'X-TC-Version': version
        })

    def __canonical_request(self,
                            payload: dict[str, Any],
                            http_request_method: str = 'POST',
                            canonical_uri: str = '/',
                            canonical_query_string: str = '') -> str:
        sort_headers = [f'{x}:{y}\n'.lower() for x, y in self._headers.items()]
        sort_headers.sort()
        canonical_headers = ''.join(sort_headers)

        payload_str = json.dumps(payload)
        hashed_request_payload = hashlib.sha256(payload_str.encode('utf-8')).hexdigest().lower()

        canonical_request = f'{http_request_method}\n' \
                            f'{canonical_uri}\n' \
                            f'{canonical_query_string}\n' \
                            f'{canonical_headers}\n' \
                            f'{self._signed_headers}\n' \
                            f'{hashed_request_payload}'

        return canonical_request

    def __string_to_sign(self,
                         canonical_request: str,
                         algorithm: str = 'TC3-HMAC-SHA256') -> str:
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest().lower()

        string_to_sign = f'{algorithm}\n' \
                         f'{self._request_timestamp}\n' \
                         f'{self._credential_scope}\n' \
                         f'{hashed_canonical_request}'

        return string_to_sign

    def __sign_v3(self, payload: dict[str, Any]) -> str:
        # 计算签名摘要函数
        def __sign(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        secret_date = __sign(f'TC3{self._secret_key}'.encode("utf-8"), self._date)
        secret_service = __sign(secret_date, self._service)
        secret_signing = __sign(secret_service, "tc3_request")

        canonical_request = self.__canonical_request(payload=payload)
        string_to_sign = self.__string_to_sign(canonical_request)
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization = f'TC3-HMAC-SHA256 Credential={self._secret_id}/{self._credential_scope}, ' \
                        f'SignedHeaders={self._signed_headers}, ' \
                        f'Signature={signature}'

        return authorization

    async def post_request(
            self, action: str, region: str, version: str, payload: dict[str, Any]) -> HttpFetcherDictResult:
        self.__upgrade_signed_header(action=action, region=region, version=version, payload=payload)

        fetcher = HttpFetcher(timeout=10, headers=self._headers)
        result = await fetcher.post_json_dict(url=self._endpoint, json=payload)
        return result


__all__ = [
    'TencentCloudApi'
]
