import aiohttp
import nonebot
from asyncio.exceptions import TimeoutError as TimeoutError_
from dataclasses import dataclass
from typing import Dict, Union, Optional, Any
from nonebot import logger
from omega_miya.utils.Omega_Base import DBStatus


global_config = nonebot.get_driver().config
ENABLE_PROXY = global_config.enable_proxy
ENABLE_FORCED_PROXY = global_config.enable_forced_proxy
PROXY_ADDRESS = global_config.proxy_address
PROXY_PORT = global_config.proxy_port


class HttpFetcher(object):
    @dataclass
    class __FetcherResult:
        error: bool
        info: str
        status: int
        headers: dict

        def success(self) -> bool:
            if not self.error:
                return True
            else:
                return False

    @dataclass
    class FetcherJsonResult(__FetcherResult):
        result: dict

        def __repr__(self):
            return f'<FetcherJsonResult(' \
                   f'error={self.error}, status={self.status}, info={self.info}, result={self.result})>'

    @dataclass
    class FetcherTextResult(__FetcherResult):
        result: str

        def __repr__(self):
            return f'<FetcherTextResult(' \
                   f'error={self.error}, status={self.status}, info={self.info}, result={self.result})>'

    @dataclass
    class FetcherBytesResult(__FetcherResult):
        result: bytes

        def __repr__(self):
            return f'<FetcherBytesResult(' \
                   f'error={self.error}, status={self.status}, info={self.info}, result={self.result})>'

    @classmethod
    async def __get_proxy(cls, always_return_proxy: bool = False) -> Optional[str]:
        if always_return_proxy:
            return f'http://{PROXY_ADDRESS}:{PROXY_PORT}'

        if not all([ENABLE_PROXY, PROXY_ADDRESS, PROXY_PORT]):
            return None

        if not ENABLE_PROXY:
            return None

        # 检查proxy
        if ENABLE_FORCED_PROXY:
            return f'http://{PROXY_ADDRESS}:{PROXY_PORT}'
        else:
            proxy_status_res = await DBStatus(name='PROXY_AVAILABLE').get_status()
            if proxy_status_res.result == 1:
                return f'http://{PROXY_ADDRESS}:{PROXY_PORT}'
            else:
                return None

    def __init__(
            self,
            timeout: Union[int, float] = 10,
            attempt_limit: int = 3,
            flag: str = 'aiohttp',
            headers: Optional[Dict[str, str]] = None,
            cookies: Optional[Dict[str, str]] = None
    ):
        self.__timeout = aiohttp.ClientTimeout(total=timeout)
        self.__attempt_limit = attempt_limit
        self.__headers = headers
        self.__cookies = cookies
        self.__flag = flag

    async def get_json(
            self,
            url: str,
            params: Dict[str, str] = None,
            force_proxy: bool = False,
            **kwargs: Any) -> FetcherJsonResult:
        proxy = await self.__get_proxy(always_return_proxy=force_proxy)
        num_of_attempts = 0
        while num_of_attempts < self.__attempt_limit:
            try:
                async with aiohttp.ClientSession(timeout=self.__timeout) as session:
                    async with session.get(
                            url=url, params=params,
                            headers=self.__headers, cookies=self.__cookies, proxy=proxy, timeout=self.__timeout,
                            **kwargs
                    ) as rp:
                        result_json = await rp.json()
                        status = rp.status
                        headers = dict(rp.headers)
                    result = self.FetcherJsonResult(
                        error=False, info='Success', status=status, headers=headers, result=result_json)
                return result
            except TimeoutError_:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>TimeoutError</lr> occurred '
                    f'in <lc>get_json</lc> attempt <y>{num_of_attempts + 1}</y>.')
            except Exception as e:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>{str(e.__class__.__name__)}</lr> occurred '
                    f'in <lc>get_json</lc> attempt <y>{num_of_attempts + 1}</y>.\n<y>Error info</y>: {str(e)}')
            finally:
                num_of_attempts += 1
        else:
            logger.opt(colors=True).error(
                fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>ExceededAttemptNumberError</lr> '
                f'Failed too many times in <lc>get_json</lc>.\n'
                f'<y>url</y>: {url}\n<y>params</y>: {params}')
            return self.FetcherJsonResult(
                error=True, info='Failed too many times in get_json', status=-1, headers={}, result={})

    async def get_text(
            self,
            url: str,
            params: Dict[str, str] = None,
            force_proxy: bool = False,
            **kwargs: Any) -> FetcherTextResult:
        proxy = await self.__get_proxy(always_return_proxy=force_proxy)
        num_of_attempts = 0
        while num_of_attempts < self.__attempt_limit:
            try:
                async with aiohttp.ClientSession(timeout=self.__timeout) as session:
                    async with session.get(
                            url=url, params=params,
                            headers=self.__headers, cookies=self.__cookies, proxy=proxy, timeout=self.__timeout,
                            **kwargs
                    ) as rp:
                        result_text = await rp.text()
                        status = rp.status
                        headers = dict(rp.headers)
                    result = self.FetcherTextResult(
                        error=False, info='Success', status=status, headers=headers, result=result_text)
                return result
            except TimeoutError_:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>TimeoutError</lr> occurred '
                    f'in <lc>get_text</lc> attempt <y>{num_of_attempts + 1}</y>.')
            except Exception as e:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>{str(e.__class__.__name__)}</lr> occurred '
                    f'in <lc>get_text</lc> attempt <y>{num_of_attempts + 1}</y>.\n<y>Error info</y>: {str(e)}')
            finally:
                num_of_attempts += 1
        else:
            logger.opt(colors=True).error(
                fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>ExceededAttemptNumberError</lr> '
                f'Failed too many times in <lc>get_text</lc>.\n'
                f'<y>url</y>: {url}\n<y>params</y>: {params}')
            return self.FetcherTextResult(
                error=True, info='Failed too many times in get_text', status=-1, headers={}, result='')

    async def get_bytes(
            self,
            url: str,
            params: Dict[str, str] = None,
            force_proxy: bool = False,
            **kwargs: Any) -> FetcherBytesResult:
        proxy = await self.__get_proxy(always_return_proxy=force_proxy)
        num_of_attempts = 0
        while num_of_attempts < self.__attempt_limit:
            try:
                async with aiohttp.ClientSession(timeout=self.__timeout) as session:
                    async with session.get(
                            url=url, params=params,
                            headers=self.__headers, cookies=self.__cookies, proxy=proxy, timeout=self.__timeout,
                            **kwargs
                    ) as rp:
                        result_bytes = await rp.read()
                        status = rp.status
                        headers = dict(rp.headers)
                    result = self.FetcherBytesResult(
                        error=False, info='Success', status=status, headers=headers, result=result_bytes)
                return result
            except TimeoutError_:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>TimeoutError</lr> occurred '
                    f'in <lc>get_bytes</lc> attempt <y>{num_of_attempts + 1}</y>.')
            except Exception as e:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>{str(e.__class__.__name__)}</lr> occurred '
                    f'in <lc>get_bytes</lc> attempt <y>{num_of_attempts + 1}</y>.\n<y>Error info</y>: {str(e)}')
            finally:
                num_of_attempts += 1
        else:
            logger.opt(colors=True).error(
                fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>ExceededAttemptNumberError</lr> '
                f'Failed too many times in <lc>get_bytes</lc>.\n'
                f'<y>url</y>: {url}\n<y>params</y>: {params}')
            return self.FetcherBytesResult(
                error=True, info='Failed too many times in get_bytes', status=-1, headers={}, result=b'')

    async def post_json(
            self,
            url: str,
            params: Dict[str, str] = None,
            json: Dict[str, Any] = None,
            data: Dict[str, Any] = None,
            force_proxy: bool = False,
            **kwargs: Any) -> FetcherJsonResult:
        proxy = await self.__get_proxy(always_return_proxy=force_proxy)
        num_of_attempts = 0
        while num_of_attempts < self.__attempt_limit:
            try:
                async with aiohttp.ClientSession(timeout=self.__timeout) as session:
                    async with session.post(
                            url=url, params=params, json=json, data=data,
                            headers=self.__headers, cookies=self.__cookies, proxy=proxy, timeout=self.__timeout,
                            **kwargs
                    ) as rp:
                        result_json = await rp.json()
                        status = rp.status
                        headers = dict(rp.headers)
                    result = self.FetcherJsonResult(
                        error=False, info='Success', status=status, headers=headers, result=result_json)
                return result
            except TimeoutError_:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>TimeoutError</lr> occurred '
                    f'in <lc>post_json</lc> attempt <y>{num_of_attempts + 1}</y>.')
            except Exception as e:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>{str(e.__class__.__name__)}</lr> occurred '
                    f'in <lc>post_json</lc> attempt <y>{num_of_attempts + 1}</y>.\n<y>Error info</y>: {str(e)}')
            finally:
                num_of_attempts += 1
        else:
            logger.opt(colors=True).error(
                fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>ExceededAttemptNumberError</lr> '
                f'Failed too many times in <lc>post_json</lc>.\n'
                f'<y>url</y>: {url}\n<y>params</y>: {params}\n<y>json</y>: {json}\n<y>data</y>: {data}')
            return self.FetcherJsonResult(
                error=True, info='Failed too many times in post_json', status=-1, headers={}, result={})

    async def post_text(
            self,
            url: str,
            params: Dict[str, str] = None,
            json: Dict[str, Any] = None,
            data: Dict[str, Any] = None,
            force_proxy: bool = False,
            **kwargs: Any) -> FetcherTextResult:
        proxy = await self.__get_proxy(always_return_proxy=force_proxy)
        num_of_attempts = 0
        while num_of_attempts < self.__attempt_limit:
            try:
                async with aiohttp.ClientSession(timeout=self.__timeout) as session:
                    async with session.post(
                            url=url, params=params, json=json, data=data,
                            headers=self.__headers, cookies=self.__cookies, proxy=proxy, timeout=self.__timeout,
                            **kwargs
                    ) as rp:
                        result_text = await rp.text()
                        status = rp.status
                        headers = dict(rp.headers)
                    result = self.FetcherTextResult(
                        error=False, info='Success', status=status, headers=headers, result=result_text)
                return result
            except TimeoutError_:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>TimeoutError</lr> occurred '
                    f'in <lc>post_text</lc> attempt <y>{num_of_attempts + 1}</y>.')
            except Exception as e:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>{str(e.__class__.__name__)}</lr> occurred '
                    f'in <lc>post_text</lc> attempt <y>{num_of_attempts + 1}</y>.\n<y>Error info</y>: {str(e)}')
            finally:
                num_of_attempts += 1
        else:
            logger.opt(colors=True).error(
                fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>ExceededAttemptNumberError</lr> '
                f'Failed too many times in <lc>post_text</lc>.\n'
                f'<y>url</y>: {url}\n<y>params</y>: {params}\n<y>json</y>: {json}\n<y>data</y>: {data}')
            return self.FetcherTextResult(
                error=True, info='Failed too many times in post_text', status=-1, headers={}, result='')

    async def post_bytes(
            self,
            url: str,
            params: Dict[str, str] = None,
            json: Dict[str, Any] = None,
            data: Dict[str, Any] = None,
            force_proxy: bool = False,
            **kwargs: Any) -> FetcherBytesResult:
        proxy = await self.__get_proxy(always_return_proxy=force_proxy)
        num_of_attempts = 0
        while num_of_attempts < self.__attempt_limit:
            try:
                async with aiohttp.ClientSession(timeout=self.__timeout) as session:
                    async with session.post(
                            url=url, params=params, json=json, data=data,
                            headers=self.__headers, cookies=self.__cookies, proxy=proxy, timeout=self.__timeout,
                            **kwargs
                    ) as rp:
                        result_bytes = await rp.read()
                        status = rp.status
                        headers = dict(rp.headers)
                    result = self.FetcherBytesResult(
                        error=False, info='Success', status=status, headers=headers, result=result_bytes)
                return result
            except TimeoutError_:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>TimeoutError</lr> occurred '
                    f'in <lc>post_bytes</lc> attempt <y>{num_of_attempts + 1}</y>.')
            except Exception as e:
                logger.opt(colors=True).warning(
                    fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>{str(e.__class__.__name__)}</lr> occurred '
                    f'in <lc>post_bytes</lc> attempt <y>{num_of_attempts + 1}</y>.\n<y>Error info</y>: {str(e)}')
            finally:
                num_of_attempts += 1
        else:
            logger.opt(colors=True).error(
                fr'<Y><lw>HttpFetcher \<{self.__flag}></lw></Y> <lr>ExceededAttemptNumberError</lr> '
                f'Failed too many times in <lc>post_bytes</lc>.\n'
                f'<y>url</y>: {url}\n<y>params</y>: {params}\n<y>json</y>: {json}\n<y>data</y>: {data}')
            return self.FetcherBytesResult(
                error=True, info='Failed too many times in post_bytes', status=-1, headers={}, result=b'')
