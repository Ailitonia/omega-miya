"""
@Author         : Ailitonia
@Date           : 2022/04/10 22:09
@FileName       : helper.py
@Project        : nonebot2_miya 
@Description    : Nhentai 工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import ujson as json
from bs4 import BeautifulSoup

from omega_miya.local_resource import TmpResource
from omega_miya.web_resource import HttpFetcher
from omega_miya.utils.process_utils import semaphore_gather
from omega_miya.utils.image_utils import generate_thumbs_preview_image

from .config import nhentai_config
from .model import (NhentaiSearchingResult, NhentaiGalleryModel,
                    NhentaiPreviewRequestModel, NhentaiPreviewBody, NhentaiPreviewModel)
from .exception import NhentaiParseError, NhentaiNetworkError


async def _get_nhentai_resource(url: str, *, params: dict | None = None) -> bytes:
    """获取任意 nhentai 资源内容"""
    _default_headers = HttpFetcher.get_default_headers()
    _default_headers.update({'referer': 'https://nhentai.net/'})

    _file_fetcher = HttpFetcher(timeout=30, headers=_default_headers)
    _content = await _file_fetcher.get_bytes(url=url, params=params)
    if _content.status != 200:
        raise NhentaiNetworkError(f'NhentaiNetworkError, status code {_content.status}')
    return _content.result


def parse_gallery_searching_result_page(content: str) -> NhentaiSearchingResult:
    """使用 bs4 解析 Nhentai gallery 搜索结果页内容

    :param content: 网页 html
    """
    search_page_bs = BeautifulSoup(content, 'lxml')
    # 获取搜索结果内容主体部分
    result_container = search_page_bs.find(name='div', attrs={'class': 'container index-container'})
    gallerys = result_container.find_all(name='div', attrs={'class': 'gallery'})

    results = []
    for gallery in gallerys:
        gallery_title = gallery.find(name='div', attrs={'class': 'caption'}).get_text(strip=True)
        gallery_id = gallery.find(name='a', attrs={'class': 'cover'}).attrs.get('href')
        gallery_id = re.search(r'^/g/(\d+)/$', gallery_id).group(1)
        cover_image_url = gallery.find(name='img', attrs={'class': 'lazyload', 'title': None}).attrs.get('data-src')
        results.append({'gallery_id': gallery_id, 'gallery_title': gallery_title, 'cover_image_url': cover_image_url})
    return NhentaiSearchingResult.parse_obj({'results': results})


def parse_gallery_page(content: str) -> NhentaiGalleryModel:
    """使用 bs4 解析 Nhentai gallery 页面内容

    :param content: 网页 html
    """
    gallery_page_bs = BeautifulSoup(content, 'lxml')
    # 获取搜索结果内容主体部分
    scripts = gallery_page_bs.find(name='body').find_all(name='script')

    # 提取页面 js script 中的 json 信息部分
    for script in scripts:
        script_text = script.get_text()
        json_start = script_text.find('window._gallery')
        if json_start > 0:
            json_text = script_text[json_start:]
            json_end = json_text.find('\n')
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
    return NhentaiGalleryModel.parse_obj(gallery_page_data)


async def _request_preview_body(request: NhentaiPreviewRequestModel) -> NhentaiPreviewBody:
    """获取生成预览图中每个缩略图的数据"""
    _request_data = await _get_nhentai_resource(url=request.request_url)
    return NhentaiPreviewBody(desc_text=request.desc_text, preview_thumb=_request_data)


async def _request_preview_model(
        preview_name: str,
        requests: list[NhentaiPreviewRequestModel]) -> NhentaiPreviewModel:
    """获取生成预览图所需要的数据模型"""
    _tasks = [_request_preview_body(request) for request in requests]
    _requests_data = await semaphore_gather(tasks=_tasks, semaphore_num=30, filter_exception=True)
    _requests_data = list(_requests_data)
    count = len(_requests_data)
    return NhentaiPreviewModel(preview_name=preview_name, count=count, previews=_requests_data)


async def emit_preview_model_from_searching_model(
        searching_name: str, model: NhentaiSearchingResult) -> NhentaiPreviewModel:
    """从搜索结果中获取生成预览图所需要的数据模型"""
    request_list = [
        NhentaiPreviewRequestModel(
            desc_text=f'ID: {data.gallery_id}\n{data.gallery_title[:25]}\n{data.gallery_title[25:48]}...',
            request_url=data.cover_image_url)
        for data in model.results]
    preview_model = await _request_preview_model(preview_name=searching_name, requests=request_list)
    return preview_model


async def generate_nhentai_preview_image(
        preview: NhentaiPreviewModel,
        *,
        preview_size: tuple[int, int] = nhentai_config.default_preview_size,
        hold_ratio: bool = False,
        num_of_line: int = 6,
        limit: int = 1000) -> TmpResource:
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
    'generate_nhentai_preview_image'
]
