"""
@Author         : Ailitonia
@Date           : 2021/06/28 21:42
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


from nonebot import logger
from bs4 import BeautifulSoup
from omega_miya.database import Result
from omega_miya.utils.omega_plugin_utils import HttpFetcher


class ShindanMaker(object):
    ROOT_URL = 'https://cn.shindanmaker.com'
    SEARCH_URL = f'{ROOT_URL}/list/search'

    HEADERS = {'accept': '*/*',
               'accept-encoding': 'gzip, deflate',
               'accept-language': 'zh-CN,zh;q=0.9',
               'cache-control': 'max-age=0',
               'dnt': '1',
               'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
               'sec-ch-ua-mobile': '?0',
               'sec-fetch-dest': 'document',
               'sec-fetch-mode': 'navigate',
               'sec-fetch-site': 'none',
               'sec-fetch-user': '?1',
               'sec-gpc': '1',
               'upgrade-insecure-requests': '1',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/91.0.4472.124 Safari/537.36'}

    def __init__(self, maker_id: int):
        self.maker_id = maker_id

    @classmethod
    async def search(cls, keyword: str) -> Result.DictListResult:
        fetcher = HttpFetcher(timeout=10, flag='shindanmaker_search', headers=cls.HEADERS)
        html_result = await fetcher.get_text(url=cls.SEARCH_URL, params={'q': keyword})
        if html_result.error:
            return Result.DictListResult(error=True, info=f'Fetch search result failed, {html_result.info}', result=[])

        try:
            _bs = BeautifulSoup(html_result.result, 'lxml')
            all_result = _bs.find_all(name='a', attrs={'class': 'shindanLink'})
            result = []
            for item in all_result:
                _url = item.attrs['href']
                _id = int(str(_url).replace(f'{cls.ROOT_URL}/', ''))
                _name = item.get_text(strip=True)
                result.append({
                    'id': _id,
                    'url': _url,
                    'name': _name
                })
            return Result.DictListResult(error=False, info='Success', result=result)
        except Exception as e:
            logger.error(f'ShindanMaker | Parse search result failed, error: {repr(e)}')
            return Result.DictListResult(error=True, info=f'Parse search result failed', result=[])

    async def get_result(self, input_name: str) -> Result.TextResult:
        fetcher = HttpFetcher(timeout=10, flag='shindanmaker_get_token', headers=self.HEADERS)
        url = f'{self.ROOT_URL}/{self.maker_id}'

        html_result = await fetcher.get_text(url=url)
        if html_result.error:
            return Result.TextResult(error=True, info=f'Fetch shindan_maker page failed, {html_result.info}', result='')
        elif html_result.status == 404:
            return Result.TextResult(error=True, info=f'Shindan_maker page not found, 404 error', result='')

        try:
            _bs = BeautifulSoup(html_result.result, 'lxml')
            _input_form = _bs.find(name='form', attrs={'id': 'shindanForm', 'method': 'POST'})
            _token = _input_form.find(name='input', attrs={'type': 'hidden', 'name': '_token'}).attrs['value']
        except Exception as e:
            logger.error(f'ShindanMaker | Parse page token failed, error: {repr(e)}')
            return Result.TextResult(error=True, info=f'Parse page token failed', result='')

        _header = self.HEADERS.update({
            'content-type': 'application/x-www-form-urlencoded',
            'origin': self.ROOT_URL,
            'referer': f'{self.ROOT_URL}/{self.maker_id}',
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1'
        })
        fetcher = HttpFetcher(timeout=10, flag='shindanmaker_get_result', cookies=html_result.cookies, headers=_header)
        data = fetcher.FormData()
        data.add_field(name='_token', value=_token)
        data.add_field(name='shindanName', value=input_name)
        data.add_field(name='hiddenName', value='无名的X')
        maker_result = await fetcher.post_text(url=url, data=data)

        if maker_result.error:
            return Result.TextResult(
                error=True, info=f'Fetch shindan_maker result failed, {maker_result.info}', result='')

        try:
            _bs = BeautifulSoup(maker_result.result, 'lxml')
            _result = _bs.find(name='span', attrs={'id': 'shindanResult'})
            for line_break in _result.findAll(name='br'):
                line_break.replaceWith('\n')
            _result = _result.get_text()
            return Result.TextResult(error=False, info='Success', result=_result)
        except Exception as e:
            logger.error(f'ShindanMaker | Parse result page failed, error: {repr(e)}')
            return Result.TextResult(error=True, info=f'Parse result page failed', result='')
