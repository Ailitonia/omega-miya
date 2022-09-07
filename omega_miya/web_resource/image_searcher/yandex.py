"""
@Author         : Ailitonia
@Date           : 2022/08/20 18:47
@FileName       : yandex.py
@Project        : nonebot2_miya 
@Description    : yandex 识图引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from bs4 import BeautifulSoup
from pydantic import parse_obj_as

from nonebot.log import logger

from omega_miya.web_resource import HttpFetcher
from omega_miya.exception import WebSourceException

from .model import ImageSearcher, ImageSearchingResult


class YandexNetworkError(WebSourceException):
    """yandex 网络异常"""


class Yandex(ImageSearcher):
    """yandex 识图引擎"""
    _searcher_name: str = 'yandex'
    _api: str = 'https://yandex.com/images/search'

    @staticmethod
    def _parser(content: str) -> list[dict] | None:
        """解析结果页面"""
        gallery_soup = BeautifulSoup(content, 'lxml')
        # 定位到相似图片区域
        container = gallery_soup.find(name='section',
                                      attrs={'class': 'CbirSection CbirSection_decorated CbirSites CbirSites_infinite'})

        container_title = container.find(name='div', attrs={'class': 'CbirSection-Title'}).get_text()
        if container_title != 'Sites containing information about the image':
            logger.error('Yandex | Css style change, unable to locate page element')
            return None

        image_result_container = container.find(name='div', attrs={'class': 'CbirSites-Items'})
        if not image_result_container:
            return None

        image_results = image_result_container.find_all(name='div', attrs={'class': 'CbirSites-Item'})
        result = []
        for item in image_results:
            try:
                title_info = item.find(name='div', attrs={'class': 'CbirSites-ItemTitle'})
                title_href = title_info.find(name='a', attrs={'target': '_blank', 'class': 'Link Link_view_default'})
                source_text = title_href.get_text()
                source_text = source_text if len(source_text) <= 20 else f'{source_text[:20]}...'

                thumbnail_info = item.find(name='div', attrs={'class': 'CbirSites-ItemThumb'})
                thumbnail_href = thumbnail_info.find(name='a', attrs={'target': '_blank'})
                thumbnail_url_elm = thumbnail_href.find(name='img', attrs={'class': 'MMImage Thumb-Image'})
                thumbnail_url = thumbnail_url_elm.attrs.get('src')
                thumbnail_url = f'https:{thumbnail_url}' if thumbnail_url else None

                result.append({'similarity': None,
                               'thumbnail': thumbnail_url,
                               'source': f'Yandex - {source_text}',
                               'source_urls': [title_href.attrs.get('href'), thumbnail_href.attrs.get('href')]})
            except (KeyError, AttributeError):
                continue
        return result

    async def search(self) -> list[ImageSearchingResult]:
        headers = HttpFetcher.get_default_headers()
        headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Host': 'yandex.com',
            'Origin': 'https://yandex.com/images',
            'Referer': 'https://yandex.com/images/'
        })

        params = {'rpt': 'imageview', 'url': self.image_url}
        yandex_result = await HttpFetcher(timeout=15).get_text(url=self._api, params=params)
        if yandex_result.status != 200:
            logger.error(f'Yandex | YandexNetworkError, {yandex_result}')
            raise YandexNetworkError(f'YandexNetworkError, {yandex_result}')

        return parse_obj_as(list[ImageSearchingResult], self._parser(content=yandex_result.result)[:8])


__all__ = [
    'Yandex'
]
