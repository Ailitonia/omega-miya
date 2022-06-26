"""
@Author         : Ailitonia
@Date           : 2022/04/10 21:50
@FileName       : nhentai.py
@Project        : nonebot2_miya
@Description    : Nhentai
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from typing import Literal
from dataclasses import dataclass

from omega_miya.local_resource import TmpResource
from omega_miya.web_resource import HttpFetcher
from omega_miya.utils.process_utils import run_sync, semaphore_gather
from omega_miya.utils.zip_utils import ZipUtils

from .config import nhentai_config
from .exception import NhentaiParseError, NhentaiNetworkError
from .model import NhentaiSearchingResult, NhentaiGalleryModel
from .helper import (parse_gallery_searching_result_page, parse_gallery_page,
                     emit_preview_model_from_searching_model, generate_nhentai_preview_image)


@dataclass
class NhentaiDownloadResult:
    """Nhentai 下载结果信息"""
    file: TmpResource
    password: str


class Nhentai(object):
    """Nhentai"""
    _root_url: str = 'https://nhentai.net/'
    _search_url: str = 'https://nhentai.net/search/'
    _default_headers = HttpFetcher.get_default_headers()
    _default_headers.update({'referer': 'https://nhentai.net/'})

    _fetcher = HttpFetcher(timeout=45, headers=_default_headers)

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    @classmethod
    async def search_gallery(
            cls,
            keyword: str,
            *,
            page: int = 1,
            sort: Literal['recent', 'popular-today', 'popular-week', 'popular'] = 'recent') -> NhentaiSearchingResult:
        """通过关键词搜索本子id和标题

        :param keyword: 搜索关键词
        :param page: 结果页面
        :param sort: 结果排序方式
        """
        params = {'q': keyword, 'page': page, 'sort': sort}
        searching_result = await cls._fetcher.get_text(url=cls._search_url, params=params)
        if searching_result.status != 200:
            raise NhentaiNetworkError(f'NhentaiNetworkError, status code {searching_result.status}')
        # 解析页面
        searching_result = await run_sync(parse_gallery_searching_result_page)(content=searching_result.result)
        return searching_result

    @classmethod
    async def search_gallery_with_preview(
            cls,
            keyword: str,
            *,
            page: int = 1,
            sort: Literal['recent', 'popular-today', 'popular-week', 'popular'] = 'recent') -> TmpResource:
        """通过关键词搜索本子id和标题并生成预览图"""
        searching_result = await cls.search_gallery(keyword=keyword, page=page, sort=sort)
        if not searching_result.results:
            raise NhentaiNetworkError(f'No result found, keyword={keyword}, page={page}')
        name = f'Searching - {keyword} - Page {page}'
        preview_request = await emit_preview_model_from_searching_model(searching_name=name, model=searching_result)
        preview_img_file = await generate_nhentai_preview_image(preview=preview_request, hold_ratio=True)
        return preview_img_file


class NhentaiGallery(Nhentai):
    """NhentaiGallery"""
    _page_resource_url: str = 'https://i.nhentai.net/galleries/'

    def __init__(self, gallery_id: int):
        self.gallery_id = gallery_id
        self.gallery_url = f'{self._root_url}/g/{gallery_id}/'

        # 实例缓存
        self.gallery_model: NhentaiGalleryModel | None = None

    def __repr__(self):
        return f'<{self.__class__.__name__}(gallery_id={self.gallery_id})>'

    async def get_gallery_model(self) -> NhentaiGalleryModel:
        if not isinstance(self.gallery_model, NhentaiGalleryModel):
            gallery_result = await self._fetcher.get_text(url=self.gallery_url)
            if gallery_result.status != 200:
                raise NhentaiNetworkError(f'NhentaiNetworkError, status code {gallery_result.status}')
            # 解析页面
            self.gallery_model = await run_sync(parse_gallery_page)(content=gallery_result.result)

        assert isinstance(self.gallery_model, NhentaiGalleryModel), 'Query gallery model failed'
        return self.gallery_model

    async def download(self, *, force_cover: bool = False) -> NhentaiDownloadResult:
        """下载所有图片到指定目录, 压缩并生成随机密码

        :param force_cover: 是否覆盖已下载的文件
        """
        gallery_model = await self.get_gallery_model()

        # 下载目标文件夹
        download_folder = nhentai_config.default_download_folder(f'gallery_{gallery_model.id}')

        # 生成下载任务序列
        download_tasks = []
        for index, page in enumerate(gallery_model.images.pages):
            match page.t:
                case 'j':
                    page_type = 'jpg'
                case 'p':
                    page_type = 'png'
                case _:
                    raise NhentaiParseError('Unknown page type')
            page_download_url = f'{self._page_resource_url}{gallery_model.media_id}/{index + 1}.{page_type}'
            page_file_name = f'{index + 1}.{page_type}'
            page_file = download_folder(page_file_name)
            # 检测文件是否已经存在避免重复下载
            if not force_cover and page_file.path.exists() and page_file.path.is_file():
                continue
            # 添加下载任务
            download_tasks.append(
                self._fetcher.download_file(url=page_download_url, file=page_file)
            )
        # 执行下载任务
        download_result = await semaphore_gather(tasks=download_tasks, semaphore_num=10)
        for result in download_result:
            if isinstance(result, BaseException):
                raise NhentaiNetworkError(f'Some page(s) download failed, error: {result}')
            elif result.status != 200:
                raise NhentaiNetworkError(f'Some page(s) download failed, status: {result.status}')

        # 生成包含本子原始信息的文件
        manifest_path = download_folder('manifest.json')
        async with manifest_path.async_open('w', encoding='utf8') as af:
            await af.write(gallery_model.json())

        # 生成一段随机字符串改变打包后压缩文件的hash
        rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=1024))
        rand_file = download_folder('mask')
        async with rand_file.async_open('w', encoding='utf8') as af:
            await af.write(rand_str)

        # 生成压缩包随机密码
        password_str = ''.join(random.sample(string.ascii_letters + string.digits, k=8))
        password_file = download_folder('password')
        async with password_file.async_open('w', encoding='utf8') as af:
            await af.write(password_str)

        # 打包
        zip_file = ZipUtils(file_name=f'nhentai_gallery_{gallery_model.id}.7z')
        file_list = download_folder.list_all_files()
        zip_result = await zip_file.create_7z(files=file_list, password=password_str)

        return NhentaiDownloadResult(file=zip_result, password=password_str)


__all__ = [
    'NhentaiGallery'
]
