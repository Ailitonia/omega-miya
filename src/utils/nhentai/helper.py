"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午7:10
@FileName       : helper
@Project        : nonebot2_miya
@Description    : Nhentai 工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re

import ujson as json
from lxml import etree
from nonebot.utils import run_sync

from .exception import NhentaiParseError
from .model import NhentaiGalleryModel, NhentaiSearchingResult


class NhentaiParser:
    """Nhentai 页面解析工具集"""

    @staticmethod
    @run_sync
    def parse_gallery_searching_result_page(content: str) -> NhentaiSearchingResult:
        """解析 Nhentai gallery 搜索结果页内容

        :param content: 网页 html
        """
        html = etree.HTML(content)

        # 获取搜索结果内容主体部分
        result_container = html.xpath('/html/body//div[@class="container index-container"]').pop(0)
        galleries = result_container.xpath('div[@class="gallery"]')

        results = []
        for gallery in galleries:
            gallery_url = gallery.xpath('a[@class="cover"]').pop(0)
            gallery_href = gallery_url.attrib.get('href')
            matched_gallery_id = re.search(r'^/g/(\d+)/$', gallery_href)
            if matched_gallery_id is None:
                continue
            gallery_id = matched_gallery_id.group(1)
            gallery_title = gallery_url.xpath('div[@class="caption"]').pop(0).text

            cover_image = gallery_url.xpath('img[@class="lazyload"]').pop(0)
            # cover_image_url = cover_image.attrib.get('src')
            cover_image_url = cover_image.attrib.get('data-src')

            results.append(
                {'gallery_id': gallery_id, 'gallery_title': gallery_title, 'cover_image_url': cover_image_url})
        return NhentaiSearchingResult.model_validate({'results': results})

    @staticmethod
    @run_sync
    def parse_gallery_page(content: str) -> NhentaiGalleryModel:
        """解析 Nhentai gallery 页面内容

        :param content: 网页 html
        """
        html = etree.HTML(content)
        scripts = html.xpath('/html/body//script')

        # 提取页面 js script 中的 json 信息部分
        for script in scripts:
            script_text = script.text
            json_start = script_text.find('window._gallery')
            if json_start > 0:
                json_text = script_text[json_start:]
                json_end = json_text.find(');')
                json_text = json_text[:json_end]
                break
        else:
            raise NhentaiParseError('Parsing gallery page failed, can not found gallery json data')

        # 从单行 js 脚本中取出 json 字符串的部分
        json_text = json_text[json_text.index('"') + 1:json_text.rindex('"')]
        # 解析 json 字符串数据
        # 把字符串中的 \u 都反转义掉
        decode_json_text = json_text.encode('utf-8').decode('unicode_escape')
        gallery_page_data = json.loads(decode_json_text)

        # 解析封面图
        cover = html.xpath(
            '/html/body/div[@id="content"]/div[@class="container" and @id="bigcontainer"]/div[@id="cover"]/a/img'
        ).pop(0)
        # cover_url = cover.attrib.get('src')
        cover_url = cover.attrib.get('data-src')

        # 解析缩略图部分
        thumbnail_container = html.xpath('/html/body//div[@class="container" and @id="thumbnail-container"]').pop(0)
        thumbnail_images = thumbnail_container.xpath(
            'div[@class="thumbs"]/div[@class="thumb-container"]/a[@class="gallerythumb"]/img[@class="lazyload"]'
        )
        thumbnail_urls = [x.attrib.get('data-src') for x in thumbnail_images]

        # 更新解析结果
        gallery_page_data.update({
            'cover_image': cover_url,
            'thumbs_images': thumbnail_urls
        })

        return NhentaiGalleryModel.model_validate(gallery_page_data)


__all__ = [
    'NhentaiParser',
]
