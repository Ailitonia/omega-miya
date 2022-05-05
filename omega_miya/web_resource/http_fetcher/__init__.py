import aiohttp
from copy import deepcopy
from typing import Iterable, Any

from omega_miya.utils.process_utils import retry, run_async_catching_exception
from omega_miya.local_resource import TmpResource

from .config import http_proxy_config
from .model import HttpFetcherJsonResult, HttpFetcherDictResult, HttpFetcherTextResult, HttpFetcherBytesResult


_default_attempt_numbers: int = 3


class HttpFetcher(object):
    _default_timeout_time: int = 10
    _default_headers: dict[str, str] = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.9',
        'dnt': '1',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/100.0.4896.75 Safari/537.36'
    }
    _http_proxy_config = http_proxy_config

    class FormData(aiohttp.FormData):
        """Patched aiohttp FormData"""
        def __init__(
                self,
                fields: Iterable[Any] = (),
                *,
                is_multipart: bool = False,
                is_processed: bool = False,
                quote_fields: bool = True,
                charset: str | None = None,
                boundary: str | None = None
        ) -> None:
            self._writer = aiohttp.multipart.MultipartWriter("form-data", boundary=boundary)
            self._fields: list = []
            self._is_multipart = is_multipart
            self._is_processed = is_processed
            self._quote_fields = quote_fields
            self._charset = charset

            if isinstance(fields, dict):
                fields = list(fields.items())
            elif not isinstance(fields, (list, tuple)):
                fields = (fields,)
            self.add_fields(*fields)

    def __init__(
            self,
            *,
            timeout: int | float | None = None,
            headers: dict[str, str] | None = None,
            cookies: dict[str, str] | None = None) -> None:

        _time_out = self._default_timeout_time if timeout is None else timeout
        _headers = self._default_headers if headers is None else headers

        self.timeout = aiohttp.ClientTimeout(total=_time_out)
        self.headers = _headers
        self.cookies = cookies

    @classmethod
    def get_default_headers(cls) -> dict[str, str]:
        return deepcopy(cls._default_headers)

    @classmethod
    @run_async_catching_exception
    async def check_proxy(cls) -> HttpFetcherBytesResult:
        return await cls(
            timeout=cls._http_proxy_config.proxy_check_timeout).get_bytes(url=cls._http_proxy_config.proxy_check_url)

    @retry(attempt_limit=_default_attempt_numbers)
    async def download_file(
            self,
            url: str,
            file: TmpResource,
            *,
            params: dict[str, str] | None = None,
            **kwargs: Any) -> HttpFetcherTextResult:
        """
        下载文件
        :param url: 链接
        :param file: 下载路径
        :param params: 请求参数
        :param kwargs: ...
        :return: 下载文件路径 file url
        """
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                    url=url,
                    params=params,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _file_bytes = await rp.read()
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies}

        async with file.async_open(mode='wb') as af:
            await af.write(_file_bytes)
            _result.update({'result': file.path.as_uri()})
        return HttpFetcherTextResult(**_result)

    @retry(attempt_limit=_default_attempt_numbers)
    async def get_json_dict(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            encoding: str | None = None,
            **kwargs: Any) -> HttpFetcherDictResult:
        """使用 get 方法获取字典类型的 Json 目标"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                    url=url,
                    params=params,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _json = await rp.json(encoding=encoding)
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies, 'result': _json}
        return HttpFetcherDictResult(**_result)

    @retry(attempt_limit=_default_attempt_numbers)
    async def get_json(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            encoding: str | None = None,
            **kwargs: Any) -> HttpFetcherJsonResult:
        """使用 get 方法获取 Json 目标"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                    url=url,
                    params=params,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _json = await rp.text(encoding=encoding)
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies, 'result': _json}
        return HttpFetcherJsonResult(**_result)

    @retry(attempt_limit=_default_attempt_numbers)
    async def get_text(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            encoding: str | None = None,
            **kwargs: Any) -> HttpFetcherTextResult:
        """使用 get 方法获取 Text 目标"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                    url=url,
                    params=params,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _text = await rp.text(encoding=encoding)
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies, 'result': _text}
        return HttpFetcherTextResult(**_result)

    @retry(attempt_limit=_default_attempt_numbers)
    async def get_bytes(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            **kwargs: Any) -> HttpFetcherBytesResult:
        """使用 get 方法获取 Bytes 目标"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                    url=url,
                    params=params,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _bytes = await rp.read()
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies, 'result': _bytes}
        return HttpFetcherBytesResult(**_result)

    @retry(attempt_limit=_default_attempt_numbers)
    async def post_json_dict(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
            data: FormData | dict[str, Any] = None,
            encoding: str | None = None,
            **kwargs: Any) -> HttpFetcherDictResult:
        """使用 post 方法获取字典类型的 Json 目标"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _json = await rp.json(encoding=encoding)
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies, 'result': _json}
        return HttpFetcherDictResult(**_result)

    @retry(attempt_limit=_default_attempt_numbers)
    async def post_json(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
            data: FormData | dict[str, Any] = None,
            encoding: str | None = None,
            **kwargs: Any) -> HttpFetcherJsonResult:
        """使用 post 方法获取 Json 目标"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _json = await rp.text(encoding=encoding)
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies, 'result': _json}
        return HttpFetcherJsonResult(**_result)

    @retry(attempt_limit=_default_attempt_numbers)
    async def post_text(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
            data: FormData | dict[str, Any] = None,
            encoding: str | None = None,
            **kwargs: Any) -> HttpFetcherTextResult:
        """使用 post 方法获取 Text 目标"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _text = await rp.text(encoding=encoding)
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies, 'result': _text}
        return HttpFetcherTextResult(**_result)

    @retry(attempt_limit=_default_attempt_numbers)
    async def post_bytes(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
            data: FormData | dict[str, Any] = None,
            **kwargs: Any) -> HttpFetcherBytesResult:
        """使用 post 方法获取 Bytes 目标"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxy=self._http_proxy_config.proxy_url,
                    timeout=self.timeout,
                    **kwargs) as rp:
                _bytes = await rp.read()
                _result = {'status': rp.status, 'headers': rp.headers, 'cookies': rp.cookies, 'result': _bytes}
        return HttpFetcherBytesResult(**_result)


__all__ = [
    'HttpFetcher',
    'HttpFetcherJsonResult',
    'HttpFetcherDictResult',
    'HttpFetcherTextResult',
    'HttpFetcherBytesResult'
]
