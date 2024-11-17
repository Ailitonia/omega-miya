"""
@Author         : Ailitonia
@Date           : 2022/05/08 17:29
@FileName       : ascii2d.py
@Project        : nonebot2_miya 
@Description    : ascii2d 识图引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from lxml import etree
from nonebot.log import logger

from src.compat import parse_obj_as
from ..model import BaseImageSearcherAPI, ImageSearchingResult

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes, HeaderTypes


class Ascii2d(BaseImageSearcherAPI):
    """Ascii2d 识图引擎"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://ascii2d.net'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return True

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @staticmethod
    def _parse_search_token(content: str) -> dict[str, str]:
        """解析页面获取搜索图片 hash"""
        html = etree.HTML(content)

        csrf_param = html.xpath('/html/head/meta[@name="csrf-param"]').pop(0).attrib.get('content')
        csrf_token = html.xpath('/html/head/meta[@name="csrf-token"]').pop(0).attrib.get('content')
        return {csrf_param: csrf_token}

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
    def _parser(content: str) -> list[dict]:
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
        # ascii2d搜索偏差过大, 仅取前两个结果, 第一行是图片描述可略过
        for row in rows[1:3]:
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
        searching_page = await self._get_resource_as_text(url=self._get_root_url())
        searching_token = self._parse_search_token(content=searching_page)

        form_data = {
            'utf8': '✓',  # type: ignore
            **searching_token,  # type: ignore
            'uri': self.image_url,  # type: ignore
            'search': b''
        }

        color_response = await self._request_post(url=f'{self._get_root_url()}/search/uri', data=form_data)
        color_search_content = self._parse_content_as_text(color_response)

        image_hash = self._parse_search_hash(color_search_content)
        bovw_search_content = await self._get_resource_as_text(url=f'{self._get_root_url()}/search/bovw/{image_hash}')

        parsed_result = []
        parsed_result.extend(self._parser(content=color_search_content))
        parsed_result.extend(self._parser(content=bovw_search_content))

        return parse_obj_as(list[ImageSearchingResult], parsed_result)


__all__ = [
    'Ascii2d',
]
