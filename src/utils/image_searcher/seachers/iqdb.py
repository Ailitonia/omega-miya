"""
@Author         : Ailitonia
@Date           : 2022/05/08 17:04
@FileName       : iqdb.py
@Project        : nonebot2_miya 
@Description    : iqdb 识图引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from lxml import etree
from nonebot.log import logger

from src.compat import parse_obj_as
from src.exception import WebSourceException
from src.service import OmegaRequests
from ..model import ImageSearcher, ImageSearchingResult


class IqdbNetworkError(WebSourceException):
    """Iqdb 网络异常"""


class Iqdb(ImageSearcher):
    """iqdb 识图引擎"""
    _searcher_name: str = 'iqdb'
    _url: str = 'https://iqdb.org/'

    @staticmethod
    def _parser(content: str) -> list[dict]:
        """解析结果页面"""
        html = etree.HTML(content)
        # 搜索结果
        results = html.xpath('/html/body/div[@id="pages" and @class="pages"]/div/table')
        if not results:
            return []

        result = []
        for row in results:
            try:
                result_type = row.xpath('tr[1]/th').pop(0).text
                if result_type in ['Best match', 'Additional match']:  # ignore "Possible match" and "Your image
                    thumbnail = row.xpath('tr/td[@class="image"]/a/img').pop(0).attrib.get('src')
                    urls = [
                        f'https:{url}' if url.startswith('//') else url
                        for url in (x.attrib.get("href") for x in row.xpath('tr/td//a'))
                    ]
                    similarity = row.xpath('tr[last()]/td').pop(0).text
                    result.append({
                        'similarity': similarity,
                        'thumbnail': f'https://iqdb.org{thumbnail}',
                        'source': f'iqdb-{result_type}',
                        'source_urls': urls
                    })
            except (IndexError, AttributeError) as e:
                logger.debug(f'Iqdb | parse failed in row, {e}')
                continue
        return result

    async def search(self) -> list[ImageSearchingResult]:
        headers = OmegaRequests.get_default_headers()
        headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            # 'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundarySXjX8c2sLFua7bEC',
            'Cookie': 'Hm_lvt_765ecde8c11b85f1ac5f168fa6e6821f=1602471368; '
                      'Hm_lpvt_765ecde8c11b85f1ac5f168fa6e6821f=1602472300',
            'Host': 'iqdb.org',
            'Origin': 'https://iqdb.org',
            'Referer': 'https://iqdb.org/'
        })

        form_data = [
            ('MAX_FILE_SIZE', (None, '', None)),  # type: ignore
            ('service[]', (None, '1', None)),  # type: ignore
            ('service[]', (None, '2', None)),  # type: ignore
            ('service[]', (None, '3', None)),  # type: ignore
            ('service[]', (None, '4', None)),  # type: ignore
            ('service[]', (None, '5', None)),  # type: ignore
            ('service[]', (None, '6', None)),  # type: ignore
            ('service[]', (None, '11', None)),  # type: ignore
            ('service[]', (None, '13', None)),  # type: ignore
            ('file', ('', b'', 'application/octet-stream')),
            ('url', (None, self.image_url, None)),  # type: ignore
        ]

        iqdb_response = await OmegaRequests(timeout=15, headers=headers).post(url=self._url, files=form_data)
        if iqdb_response.status_code != 200:
            logger.error(f'Iqdb | IqdbNetworkError, {iqdb_response}')
            raise IqdbNetworkError(f'{iqdb_response.request}, status code {iqdb_response.status_code}')

        iqdb_search_content = OmegaRequests.parse_content_as_text(iqdb_response)

        return parse_obj_as(list[ImageSearchingResult], self._parser(content=iqdb_search_content))


__all__ = [
    'Iqdb',
]
