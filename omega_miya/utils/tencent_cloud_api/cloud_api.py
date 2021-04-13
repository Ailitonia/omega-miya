import aiohttp
import json
import hashlib
import hmac
import datetime
from dataclasses import dataclass
from typing import Dict, Any
import nonebot

global_config = nonebot.get_driver().config
SECRET_ID = global_config.secret_id
SECRET_KEY = global_config.secret_key


class TencentCloudApi(object):
    @dataclass
    class ApiRes:
        error: bool
        info: str
        result: dict

        def success(self) -> bool:
            if not self.error:
                return True
            else:
                return False

    def __init__(self,
                 secret_id: str,
                 secret_key: str,
                 host: str):
        self.__secret_id = secret_id
        self.__secret_key = secret_key
        self.__host = host
        self.__endpoint = f'https://{host}'
        self.__service = host.split('.')[0]

        self.__headers = {
            "Content-Type": "application/json",
            "Host": self.__host
        }

        self.__request_timestamp = int(datetime.datetime.now().timestamp())
        self.__date = datetime.datetime.utcfromtimestamp(self.__request_timestamp).strftime('%Y-%m-%d')
        self.__credential_scope = f'{self.__date}/{self.__service}/tc3_request'

        sort_signed_headers = [f'{x}'.lower() for x in self.__headers.keys()]
        sort_signed_headers.sort()
        self.__signed_headers = ';'.join(sort_signed_headers)

    def __upgrade_signed_header(self,
                                action: str,
                                region: str,
                                version: str,
                                payload: Dict[str, Any]):
        self.__headers = {
            'Authorization': self.__sign_v3(payload=payload),
            'Content-Type': 'application/json',
            'Host': self.__host,
            'X-TC-Action': action,
            'X-TC-Region': region,
            'X-TC-Timestamp': str(self.__request_timestamp),
            'X-TC-Version': version
        }

    def __canonical_request(self,
                            payload: Dict[str, Any],
                            http_request_method: str = 'POST',
                            canonical_uri: str = '/',
                            canonical_query_string: str = '') -> str:
        sort_headers = [f'{x}:{y}\n'.lower() for x, y in self.__headers.items()]
        sort_headers.sort()
        canonical_headers = ''.join(sort_headers)

        payload_str = json.dumps(payload)
        hashed_request_payload = hashlib.sha256(payload_str.encode('utf-8')).hexdigest().lower()

        canonical_request = f'{http_request_method}\n' \
                            f'{canonical_uri}\n' \
                            f'{canonical_query_string}\n' \
                            f'{canonical_headers}\n' \
                            f'{self.__signed_headers}\n' \
                            f'{hashed_request_payload}'

        return canonical_request

    def __string_to_sign(self,
                         canonical_request: str,
                         algorithm: str = 'TC3-HMAC-SHA256') -> str:
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest().lower()

        string_to_sign = f'{algorithm}\n' \
                         f'{self.__request_timestamp}\n' \
                         f'{self.__credential_scope}\n' \
                         f'{hashed_canonical_request}'

        return string_to_sign

    def __sign_v3(self, payload: Dict[str, Any]) -> str:
        # 计算签名摘要函数
        def __sign(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        secret_date = __sign(f'TC3{self.__secret_key}'.encode("utf-8"), self.__date)
        secret_service = __sign(secret_date, self.__service)
        secret_signing = __sign(secret_service, "tc3_request")

        canonical_request = self.__canonical_request(payload=payload)
        string_to_sign = self.__string_to_sign(canonical_request)
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization = f'TC3-HMAC-SHA256 Credential={self.__secret_id}/{self.__credential_scope}, ' \
                        f'SignedHeaders={self.__signed_headers}, ' \
                        f'Signature={signature}'

        return authorization

    async def post_request(self, action: str, region: str, version: str, payload: Dict[str, Any]) -> ApiRes:
        self.__upgrade_signed_header(action=action, region=region, version=version, payload=payload)

        timeout_count = 0
        error_info = ''
        while timeout_count < 2:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url=self.__endpoint, json=payload, headers=self.__headers) as resp:
                        _json = await resp.json()
                return self.ApiRes(error=False, info='Success', result=_json)
            except Exception as e:
                error_info += f'{repr(e)} Occurred when trying {timeout_count + 1} with paras: {payload}\n'
            finally:
                timeout_count += 1
        else:
            error_info += f'Failed too many times with paras: {payload}'
            return self.ApiRes(error=True, info=error_info, result={})


__all__ = [
    'TencentCloudApi',
    'SECRET_ID',
    'SECRET_KEY'
]
