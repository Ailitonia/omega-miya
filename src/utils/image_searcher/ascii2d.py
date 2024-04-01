"""
@Author         : Ailitonia
@Date           : 2022/05/08 17:29
@FileName       : ascii2d.py
@Project        : nonebot2_miya 
@Description    : ascii2d 识图引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from lxml import etree
from nonebot.log import logger

from src.compat import parse_obj_as
from src.exception import WebSourceException
from src.service import OmegaRequests

from .model import ImageSearcher, ImageSearchingResult


class Ascii2dNetworkError(WebSourceException):
    """Ascii2d 网络异常"""


class Ascii2d(ImageSearcher):
    """Ascii2d 识图引擎"""
    _searcher_name: str = 'ascii2d'
    _url: str = 'https://ascii2d.net/search'

    @staticmethod
    def _parse_search_hash(content: str) -> str:
        """解析页面获取搜索图片 hash"""
        html = etree.HTML(content)

        # 定位到搜索图片 hash
        image_hash = html.xpath(
            '/html/body/div[@class="container"]/div[@class="row"]//div[@class="row item-box"]//div[@class="hash"]'
        ).pop(0).text
        return image_hash

    @staticmethod
    def _parser(content: str) -> list[dict] | None:
        """解析结果页面"""
        html = etree.HTML(content)
        # 搜索模式
        search_mode = html.xpath(
            '/html/body/div[@class="container"]/div[@class="row"]/div[1]/h5[@class="p-t-1 text-xs-center"]'
        ).pop(0).text

        # 每一个搜索结果
        rows = html.xpath(
            '/html/body/div[@class="container"]/div[@class="row"]/div[1]/div[@class="row item-box"]'
        )

        result = []
        # ascii2d搜索偏差过大, 仅取前三个结果, 第一行是图片描述可略过
        for row in rows[1:4]:
            # 对每个搜索结果进行解析
            try:
                detail = row.xpath(
                    'div[@class="col-xs-12 col-sm-12 col-md-8 col-xl-8 info-box"]/div[@class="detail-box gray-link"]/h6'
                ).pop(0)

                # 来源部分
                source_type = detail.xpath('small').pop(0).text.strip()
                source_url = detail.xpath('a[1]').pop(0).attrib.get('href')
                source_ref = '/'.join(x.text.strip() for x in detail.xpath('a'))

                # 预览图部分
                preview_img_url = row.xpath(
                    'div[@class="col-xs-12 col-sm-12 col-md-4 col-xl-4 text-xs-center image-box"]/img'
                ).pop(0).attrib.get('src')

                result.append({
                    'similarity': None,
                    'thumbnail': f'https://ascii2d.net{preview_img_url}',
                    'source': f'ascii2d-{search_mode}-{source_type}-{source_ref}',
                    'source_urls': [source_url]
                })
            except (IndexError, AttributeError) as e:
                logger.debug(f'Ascii2d | parse failed in row, {e}')
                continue
        return result

    async def search(self) -> list[ImageSearchingResult]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'
        }

        form_data = {
            'utf8': '✓',  # type: ignore
            'uri': self.image_url,  # type: ignore
            'search': b''
        }

        color_response = await OmegaRequests(headers=headers, timeout=15).post(url=f'{self._url}/uri', files=form_data)
        if color_response.status_code != 200:
            logger.error(f'Ascii2d | Ascii2dNetworkError, color searching failed, {color_response}')
            raise Ascii2dNetworkError(f'{color_response.request}, status code {color_response.status_code}')

        color_search_content = OmegaRequests.parse_content_text(color_response)
        image_hash = self._parse_search_hash(color_search_content)

        bovw_url = f'{self._url}/bovw/{image_hash}'
        bovw_response = await OmegaRequests(headers=headers, timeout=10).get(url=bovw_url)
        if bovw_response.status_code != 200:
            logger.error(f'Ascii2d | Ascii2dNetworkError, bovw searching failed, {bovw_response}')
            raise Ascii2dNetworkError(f'{bovw_response.request}, status code {bovw_response.status_code}')

        bovw_search_content = OmegaRequests.parse_content_text(bovw_response)

        parsed_result = []
        parsed_result.extend(self._parser(content=color_search_content))
        parsed_result.extend(self._parser(content=bovw_search_content))

        return parse_obj_as(list[ImageSearchingResult], parsed_result)
