"""
@Author         : Ailitonia
@Date           : 2022/05/08 17:29
@FileName       : ascii2d.py
@Project        : nonebot2_miya 
@Description    : ascii2d 识图引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
from bs4 import BeautifulSoup
from pydantic import parse_obj_as

from nonebot.log import logger

from omega_miya.web_resource import HttpFetcher
from omega_miya.exception import WebSourceException

from .model import ImageSearcher, ImageSearchingResult


class Ascii2dNetworkError(WebSourceException):
    """Ascii2d 网络异常"""


class Ascii2d(ImageSearcher):
    """Ascii2d 识图引擎"""
    _searcher_name: str = 'ascii2d'
    _api: str = 'https://ascii2d.net/search/uri'

    @staticmethod
    def _parser(content: str) -> list[dict] | None:
        """解析结果页面"""
        gallery_soup = BeautifulSoup(content, 'lxml')
        # 模式
        search_mode = gallery_soup.find('h5', {'class': 'p-t-1 text-xs-center'}).get_text(strip=True)
        # 每一个搜索结果
        row = gallery_soup.find_all('div', {'class': 'row item-box'})

        result = []
        # ascii2d搜索偏差过大,pixiv及twitter结果只取第一个
        pixiv_count = 0
        twitter_count = 0
        for row_item in row:
            # 对每个搜索结果进行解析
            try:
                detail = row_item.find('div', {'class': 'detail-box gray-link'})
                is_null = detail.get_text(strip=True)
                if not is_null:
                    continue
                # 来源部分,ascii2d网页css调整大概率导致此处解析失败,调试重点关注
                source_type = detail.find('h6').find('small').get_text(strip=True)
                if source_type == 'pixiv':
                    if pixiv_count > 0:
                        break
                    else:
                        pixiv_count += 1
                elif source_type == 'twitter':
                    if twitter_count > 0:
                        break
                    else:
                        twitter_count += 1
                else:
                    continue
                source = detail.find('h6').get_text('/', strip=True)
                source_url = detail.find('h6').find('a', {'title': None, 'style': None}).get('href')

                # 预览图部分,ascii2d网页css调整大概率导致此处解析失败,调试重点关注
                preview_img_url = row_item. \
                    find('div', {'class': 'col-xs-12 col-sm-12 col-md-4 col-xl-4 text-xs-center image-box'}). \
                    find('img').get('src')

                result.append({'similarity': None,
                               'thumbnail': f'https://ascii2d.net{preview_img_url}',
                               'source': f'ascii2d - {search_mode} - {source}',
                               'source_urls': [source_url]})
            except (KeyError, AttributeError):
                continue
        return result

    async def search(self) -> list[ImageSearchingResult]:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
        fetcher = HttpFetcher(headers=headers, timeout=15)

        data = HttpFetcher.FormData()
        data.add_field(name='utf8', value='✓')
        data.add_field(name='uri', value=self.image_url)
        data.add_field(name='search', value='')

        ascii2d_redirects_result = await fetcher.post_text(url=self._api, data=data, allow_redirects=False)
        if ascii2d_redirects_result.status != 302:
            logger.error(f'Ascii2d | Ascii2dNetworkError, {ascii2d_redirects_result}')
            raise Ascii2dNetworkError(f'Ascii2dNetworkError, {ascii2d_redirects_result}')

        ascii2d_color_url: str = ascii2d_redirects_result.headers.get('Location', None)
        if not ascii2d_color_url:
            logger.error(f'Ascii2d | Ascii2dNetworkError, not found redirect url')
            raise Ascii2dNetworkError('Ascii2dNetworkError, not found redirect url')

        ascii2d_bovw_url = ascii2d_color_url.replace(r'/search/color/', r'/search/bovw/')

        color_search_task = asyncio.create_task(fetcher.get_text(url=ascii2d_color_url))
        bovw_search_task = asyncio.create_task(fetcher.get_text(url=ascii2d_bovw_url))

        color_search_result = await color_search_task
        bovw_search_result = await bovw_search_task

        if color_search_result.status != 200 and bovw_search_result != 200:
            logger.error(f'Ascii2d | Ascii2dNetworkError, get result page error')
            raise Ascii2dNetworkError('Ascii2dNetworkError, get result page error')

        parsed_result = []
        if color_search_result.status == 200:
            parsed_result.extend(self._parser(content=color_search_result.result))
        if bovw_search_result.status == 200:
            parsed_result.extend(self._parser(content=bovw_search_result.result))

        return parse_obj_as(list[ImageSearchingResult], parsed_result)
