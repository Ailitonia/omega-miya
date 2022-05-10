"""
@Author         : Ailitonia
@Date           : 2022/05/08 17:04
@FileName       : iqdb.py
@Project        : nonebot2_miya 
@Description    : iqdb 识图引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from bs4 import BeautifulSoup
from pydantic import parse_obj_as

from nonebot.log import logger

from omega_miya.web_resource import HttpFetcher
from omega_miya.exception import WebSourceException

from .model import ImageSearcher, ImageSearchingResult


class IqdbNetworkError(WebSourceException):
    """Iqdb 网络异常"""


class Iqdb(ImageSearcher):
    """iqdb 识图引擎"""
    _searcher_name: str = 'iqdb'
    _api: str = 'https://iqdb.org/'

    @staticmethod
    def _parser(content: str) -> list[dict] | None:
        """解析结果页面"""
        gallery_soup = BeautifulSoup(content, 'lxml')
        # 搜索结果
        result_div = gallery_soup.find('div', {'id': 'pages', 'class': 'pages'})
        if result_div is None:
            return None

        # 从搜索结果中解析具体每一个结果
        result_list = [x.find_all('tr') for x in result_div.find_all('div')]

        result = []
        for item in result_list:
            try:
                if item[0].get_text() == 'Best match':
                    # 第二行是匹配缩略图及链接
                    urls = '\n'.join([str(x.find('a').get('href')).strip('/') for x in item if x.find('a')])
                    img = item[1].find('img').get('src')
                    # 最后一行是相似度
                    similarity = item[-1].get_text()
                    result.append({
                        'similarity': similarity,
                        'thumbnail': f'https://iqdb.org{img}',
                        'source': f'iqdb - Best match',
                        'source_urls': [urls]
                    })
                elif item[0].get_text() == 'Additional match':
                    # 第二行是匹配缩略图及链接
                    urls = '\n'.join([str(x.find('a').get('href')).strip('/') for x in item if x.find('a')])
                    img = item[1].find('img').get('src')
                    # 最后一行是相似度
                    similarity = item[-1].get_text()
                    result.append({
                        'similarity': similarity,
                        'thumbnail': f'https://iqdb.org{img}',
                        'source': f'iqdb - Additional match',
                        'source_urls': [urls]
                    })
                elif item[0].get_text() == 'Possible match':
                    # 第二行是匹配缩略图及链接
                    urls = '\n'.join([str(x.find('a').get('href')).strip('/') for x in item if x.find('a')])
                    img = item[1].find('img').get('src')
                    # 最后一行是相似度
                    similarity = item[-1].get_text()
                    result.append({
                        'similarity': similarity,
                        'thumbnail': f'https://iqdb.org{img}',
                        'source': f'iqdb - Possible match',
                        'source_urls': [urls]
                    })
            except (KeyError, AttributeError):
                continue
        return result

    async def search(self) -> list[ImageSearchingResult]:
        headers = HttpFetcher.get_default_headers()
        headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundarycljlxd876c1ld4Zr',
            'Host': 'iqdb.org',
            'Origin': 'https://iqdb.org',
            'Referer': 'https://iqdb.org/'
        })

        data = HttpFetcher.FormData(boundary='----WebKitFormBoundarycljlxd876c1ld4Zr')
        data.add_field(name='MAX_FILE_SIZE', value='')
        for i in [1, 2, 3, 4, 5, 6, 11, 13]:
            data.add_field(name='service[]', value=str(i))
        data.add_field(name='file', value=b'', content_type='application/octet-stream', filename='')
        data.add_field(name='url', value=self.image_url)

        iqdb_result = await HttpFetcher(timeout=15).post_text(url=self._api, data=data)
        if iqdb_result.status != 200:
            logger.error(f'Iqdb | IqdbNetworkError, {iqdb_result}')
            raise IqdbNetworkError(f'IqdbNetworkError, {iqdb_result}')

        return parse_obj_as(list[ImageSearchingResult], self._parser(content=iqdb_result.result))


__all__ = [
    'Iqdb'
]
