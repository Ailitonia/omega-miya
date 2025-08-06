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
from nonebot.utils import run_sync

from src.compat import parse_obj_as
from src.resource import BaseResource
from ..config import image_searcher_config
from ..model import BaseImageSearcherAPI, ImageSearchingResult

if TYPE_CHECKING:
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes, Response


class Ascii2d(BaseImageSearcherAPI):
    """Ascii2d 识图引擎"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        # the website `https://ascii2d.net` has enabled Cloudflare verification.
        # It can only be used through a mirror site.
        # Currently, there is a usable instance `https://ascii2d.obfs.dev`.
        return (
            'https://ascii2d.net'
            if image_searcher_config.image_searcher_ascii2d_alternative_url is None
            else image_searcher_config.image_searcher_ascii2d_alternative_url.removesuffix('/')
        )

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'PostmanRuntime/7.29.0'}

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @staticmethod
    @run_sync
    def _parse_search_token(content: str) -> dict[str, str]:
        """解析页面获取搜索图片 hash"""
        html = etree.HTML(content)

        csrf_param = html.xpath('/html/head/meta[@name="csrf-param"]').pop(0).attrib.get('content')
        csrf_token = html.xpath('/html/head/meta[@name="csrf-token"]').pop(0).attrib.get('content')
        return {csrf_param: csrf_token}

    @staticmethod
    @run_sync
    def _parse_search_hash(content: str) -> str:
        """解析页面获取搜索图片 hash"""
        html = etree.HTML(content)

        # 定位到搜索图片 hash
        image_hash = html.xpath(
            '/html/body/div[@class="container"]/div[@class="row"]//div[@class="row item-box"]//div[@class="hash"]'
        ).pop(0).text
        return image_hash

    @classmethod
    @run_sync
    def _parser(cls, content: str) -> list[dict]:
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
                    'thumbnail': (
                        preview_img_url
                        if preview_img_url is None or preview_img_url.startswith('http')
                        else f'{cls._get_root_url().removesuffix("/")}/{preview_img_url.removeprefix("/")}'
                    ),
                    'source': f'ascii2d-{search_mode}-{source_type}-{source_ref}',
                    'source_urls': [source_url]
                })
            except (IndexError, AttributeError) as e:
                logger.debug(f'Ascii2d | parse failed in row, {e}')
                continue
        return result

    @classmethod
    async def _handle_color_search_result(cls, color_search_response: 'Response') -> list[ImageSearchingResult]:
        """解析颜色搜索并处理后续特征搜索"""
        color_search_content = cls._parse_content_as_text(color_search_response)

        image_hash = await cls._parse_search_hash(color_search_content)
        bovw_search_content = await cls._get_resource_as_text(url=f'{cls._get_root_url()}/search/bovw/{image_hash}')

        parsed_result = []
        parsed_result.extend(await cls._parser(content=color_search_content))
        parsed_result.extend(await cls._parser(content=bovw_search_content))

        return parse_obj_as(list[ImageSearchingResult], parsed_result)

    @classmethod
    async def _search_local_image(cls, image: BaseResource) -> list[ImageSearchingResult]:
        with image.open('rb') as f:
            files = {
                'file': (image.name, f, 'application/octet-stream'),
            }
            color_response = await cls._request_post(url=f'{cls._get_root_url()}/search/file',
                                                     files=files)  # type: ignore
        return await cls._handle_color_search_result(color_search_response=color_response)

    @classmethod
    async def _search_bytes_image(cls, image: bytes) -> list[ImageSearchingResult]:
        files = {
            'file': ('blob', image, 'application/octet-stream'),
        }
        color_response = await cls._request_post(url=f'{cls._get_root_url()}/search/file', files=files)  # type: ignore
        return await cls._handle_color_search_result(color_search_response=color_response)

    @classmethod
    async def _search_url_image(cls, image: str) -> list[ImageSearchingResult]:
        searching_page = await cls._get_resource_as_text(url=cls._get_root_url())
        searching_token = await cls._parse_search_token(content=searching_page)

        form_data = {
            'utf8': '✓',  # type: ignore
            **searching_token,  # type: ignore
            'uri': image,  # type: ignore
            'search': b''
        }

        color_response = await cls._request_post(url=f'{cls._get_root_url()}/search/uri', data=form_data)
        return await cls._handle_color_search_result(color_search_response=color_response)


__all__ = [
    'Ascii2d',
]
