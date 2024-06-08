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
from typing import Optional, Any

from lxml import etree
from nonebot.utils import run_sync

from src.resource import TemporaryResource
from src.service import OmegaRequests
from src.utils.process_utils import semaphore_gather
from src.utils.image_utils.template import generate_thumbs_preview_image

from .config import nhentai_config
from .exception import NhentaiParseError, NhentaiNetworkError
from .model import (
    NhentaiSearchingResult,
    NhentaiGalleryModel,
    NhentaiPreviewRequestModel,
    NhentaiPreviewBody,
    NhentaiPreviewModel
)


async def _request_resource(
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        timeout: int = 30
) -> bytes:
    """获取任意 nhentai 资源内容"""
    if headers is None:
        headers = OmegaRequests.get_default_headers()
        headers.update({'referer': 'https://nhentai.net/'})

    requests = OmegaRequests(timeout=timeout, headers=headers)
    response = await requests.get(url=url, params=params)
    if response.status_code != 200:
        raise NhentaiNetworkError(f'{response.request}, status code {response.status_code}')

    return response.content


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
        gallery_id = re.search(r'^/g/(\d+)/$', gallery_href).group(1)
        gallery_title = gallery_url.xpath('div[@class="caption"]').pop(0).text

        cover_image = gallery_url.xpath('img[@class="lazyload"]').pop(0)
        # cover_image_url = cover_image.attrib.get('src')
        cover_image_url = cover_image.attrib.get('data-src')

        results.append({'gallery_id': gallery_id, 'gallery_title': gallery_title, 'cover_image_url': cover_image_url})
    return NhentaiSearchingResult.parse_obj({'results': results})


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
    json_text = json_text[json_text.index('"')+1:json_text.rindex('"')]
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

    return NhentaiGalleryModel.parse_obj(gallery_page_data)


async def _request_preview_body(request: NhentaiPreviewRequestModel) -> NhentaiPreviewBody:
    """获取生成预览图中每个缩略图的数据"""
    _request_data = await _request_resource(url=request.request_url)
    return NhentaiPreviewBody(desc_text=request.desc_text, preview_thumb=_request_data)


async def _request_preview_model(
        preview_name: str,
        requests: list[NhentaiPreviewRequestModel]
) -> NhentaiPreviewModel:
    """获取生成预览图所需要的数据模型"""
    _tasks = [_request_preview_body(request) for request in requests]
    _requests_data = await semaphore_gather(tasks=_tasks, semaphore_num=30, filter_exception=True)
    _requests_data = list(_requests_data)
    count = len(_requests_data)
    return NhentaiPreviewModel(preview_name=preview_name, count=count, previews=_requests_data)


async def emit_preview_model_from_searching_model(
        searching_name: str,
        model: NhentaiSearchingResult
) -> NhentaiPreviewModel:
    """从搜索结果中获取生成预览图所需要的数据模型"""
    request_list = [
        NhentaiPreviewRequestModel(
            desc_text=f'ID: {data.gallery_id}\n{data.gallery_title[:25]}\n{data.gallery_title[25:48]}...'
            if len(data.gallery_title) > 48
            else f'ID: {data.gallery_id}\n{data.gallery_title[:25]}\n{data.gallery_title[25:]}',
            request_url=data.cover_image_url
        )
        for data in model.results
    ]
    preview_model = await _request_preview_model(preview_name=searching_name, requests=request_list)
    return preview_model


async def emit_preview_model_from_gallery_model(
        gallery_name: str,
        model: NhentaiGalleryModel,
        *,
        use_thumbnail: bool = True
) -> NhentaiPreviewModel:
    """从搜索结果中获取生成预览图所需要的数据模型"""
    def _page_type(type_: str) -> str:
        match type_:
            case 'j':
                return 'jpg'
            case 'p':
                return 'png'
            case _:
                return 'unknown'

    if use_thumbnail:
        request_list = [
            NhentaiPreviewRequestModel(desc_text=f'Page: {index + 1}', request_url=url)
            for index, url in enumerate(model.thumbs_images)
        ]
    else:
        request_list = [
            NhentaiPreviewRequestModel(
                desc_text=f'Page: {index + 1}',
                request_url=f'https://i.nhentai.net/galleries/{model.media_id}/{index + 1}.{_page_type(data.t)}'
            )
            for index, data in enumerate(model.images.pages)
        ]
    preview_model = await _request_preview_model(preview_name=gallery_name, requests=request_list)
    return preview_model


async def generate_nhentai_preview_image(
        preview: NhentaiPreviewModel,
        *,
        preview_size: tuple[int, int] = nhentai_config.default_preview_size,
        hold_ratio: bool = False,
        num_of_line: int = 6,
        limit: int = 1000
) -> TemporaryResource:
    """生成多个作品的预览图

    :param preview: 经过预处理的生成预览的数据
    :param preview_size: 单个小缩略图的尺寸
    :param hold_ratio: 是否保持缩略图原图比例
    :param num_of_line: 生成预览每一行的预览图数
    :param limit: 限制生成时加载 preview 中图片的最大值
    """
    return await generate_thumbs_preview_image(
        preview=preview,
        preview_size=preview_size,
        font_path=nhentai_config.default_font_file,
        header_color=(215, 64, 87),
        hold_ratio=hold_ratio,
        num_of_line=num_of_line,
        limit=limit,
        output_folder=nhentai_config.default_preview_img_folder
    )


__all__ = [
    'parse_gallery_searching_result_page',
    'parse_gallery_page',
    'emit_preview_model_from_searching_model',
    'emit_preview_model_from_gallery_model',
    'generate_nhentai_preview_image'
]
