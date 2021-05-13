from nonebot import get_driver
from omega_miya.utils.Omega_plugin_utils import HttpFetcher, PicEncoder
from omega_miya.utils.Omega_Base import Result


__GLOBAL_CONFIG = get_driver().config
BILI_SESSDATA = __GLOBAL_CONFIG.bili_sessdata
BILI_CSRF = __GLOBAL_CONFIG.bili_csrf
BILI_UID = __GLOBAL_CONFIG.bili_uid


class BiliRequestUtils(object):
    HEADERS = {'accept': 'application/json, text/plain, */*',
               'accept-encoding': 'gzip, deflate',
               'accept-language': 'zh-CN,zh;q=0.9',
               'dnt': '1',
               'origin': 'https://www.bilibili.com',
               'referer': 'https://www.bilibili.com/',
               'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
               'sec-ch-ua-mobile': '?0',
               'sec-fetch-dest': 'empty',
               'sec-fetch-mode': 'cors',
               'sec-fetch-site': 'same-site',
               'sec-gpc': '1',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/89.0.4389.114 Safari/537.36'
               }

    @classmethod
    def get_bili_uid(cls):
        return BILI_UID

    @classmethod
    def get_bili_csrf(cls):
        return BILI_CSRF

    @classmethod
    def get_bili_sessdata(cls):
        return BILI_SESSDATA

    @classmethod
    def get_cookies(cls) -> Result.DictResult:
        cookies = {}
        if BILI_SESSDATA and BILI_CSRF:
            cookies.update({'SESSDATA': BILI_SESSDATA})
            cookies.update({'bili_jct': BILI_CSRF})
            return Result.DictResult(error=False, info='Success', result=cookies)
        else:
            return Result.DictResult(error=True, info='None', result=cookies)

    async def verify_cookies(self) -> Result.TextResult:
        cookies_result = self.get_cookies()
        if cookies_result.error:
            return Result.TextResult(error=True, info='No cookies configs', result='')

        cookies_verify_url = 'https://api.bilibili.com/x/web-interface/nav'
        cookies = cookies_result.result
        fetcher = HttpFetcher(timeout=10, flag='bilibili_live_monitor', headers=self.HEADERS, cookies=cookies)
        result = await fetcher.get_json(url=cookies_verify_url)

        if result.success():
            code = result.result.get('code')
            data = dict(result.result.get('data'))
            if code == 0 and data.get('isLogin'):
                uname = data.get('uname')
                mid = data.get('mid')
                if mid == BILI_UID:
                    return Result.TextResult(error=False, info='Success login', result=uname)
                else:
                    return Result.TextResult(error=True, info='Logged user UID does not match', result=uname)
            else:
                return Result.TextResult(error=True, info='Not login', result='')
        else:
            return Result.TextResult(error=True, info=result.info, result='')

    @classmethod
    # 图片转base64
    async def pic_2_base64(cls, url: str) -> Result.TextResult:
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/89.0.4389.114 Safari/537.36',
                   'origin': 'https://www.bilibili.com',
                   'referer': 'https://www.bilibili.com/'}

        fetcher = HttpFetcher(
            timeout=30, attempt_limit=2, flag='bilibili_live_monitor_get_image', headers=headers)
        bytes_result = await fetcher.get_bytes(url=url)
        if bytes_result.error:
            return Result.TextResult(error=True, info='Image download failed', result='')

        encode_result = PicEncoder.bytes_to_b64(image=bytes_result.result)

        if encode_result.success():
            return Result.TextResult(error=False, info='Success', result=encode_result.result)
        else:
            return Result.TextResult(error=True, info=encode_result.info, result='')


__all__ = [
    'BiliRequestUtils'
]
