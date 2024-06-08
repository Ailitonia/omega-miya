"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午7:01
@FileName       : main
@Project        : nonebot2_miya
@Description    : Nhentai
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
import string
from typing import Any, Literal, Optional

from src.resource import TemporaryResource
from src.service import OmegaRequests
from src.utils.process_utils import semaphore_gather
from src.utils.zip_utils import ZipUtils

from .config import nhentai_config, nhentai_resource_config
from .exception import NhentaiNetworkError
from .model import NhentaiSearchingResult, NhentaiGalleryModel, NhentaiDownloadResult
from .helper import (
    parse_gallery_searching_result_page,
    parse_gallery_page,
    emit_preview_model_from_searching_model,
    emit_preview_model_from_gallery_model,
    generate_nhentai_preview_image
)


class Nhentai(object):
    """Nhentai"""
    _root_url: str = 'https://nhentai.net'
    _search_url: str = f'{_root_url}/search/'

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    @classmethod
    async def request_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 45
    ) -> str | bytes | None:
        """请求原始资源内容"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://nhentai.net/'})

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=nhentai_config.nhentai_cookies)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise NhentaiNetworkError(f'{response.request}, status code {response.status_code}')

        return response.content

    @classmethod
    async def download_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 60,
            folder_name: str | None = None,
            ignore_exist_file: bool = False
    ) -> TemporaryResource:
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://nhentai.net/'})

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        if folder_name is None:
            file = nhentai_resource_config.default_download_folder(original_file_name)
        else:
            file = nhentai_resource_config.default_download_folder(folder_name, original_file_name)
        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=nhentai_config.nhentai_cookies)

        return await requests.download(url=url, file=file, params=params, ignore_exist_file=ignore_exist_file)

    @classmethod
    async def search_gallery(
            cls,
            keyword: str,
            *,
            page: int = 1,
            sort: Literal['recent', 'popular-today', 'popular-week', 'popular'] = 'recent'
    ) -> NhentaiSearchingResult:
        """通过关键词搜索本子id和标题

        :param keyword: 搜索关键词
        :param page: 结果页面
        :param sort: 结果排序方式
        """
        params = {'q': keyword, 'page': page, 'sort': sort}
        searching_content = await cls.request_resource(url=cls._search_url, params=params)
        return await parse_gallery_searching_result_page(content=searching_content)

    @classmethod
    async def search_gallery_with_preview(
            cls,
            keyword: str,
            *,
            page: int = 1,
            sort: Literal['recent', 'popular-today', 'popular-week', 'popular'] = 'recent'
    ) -> TemporaryResource:
        """通过关键词搜索本子id和标题并生成预览图"""
        searching_result = await cls.search_gallery(keyword=keyword, page=page, sort=sort)
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

    async def query_gallery(self) -> NhentaiGalleryModel:
        if not isinstance(self.gallery_model, NhentaiGalleryModel):
            gallery_content = await self.request_resource(url=self.gallery_url)
            self.gallery_model = await parse_gallery_page(content=gallery_content)

        assert isinstance(self.gallery_model, NhentaiGalleryModel), 'Query gallery model failed'
        return self.gallery_model

    async def query_gallery_with_preview(self) -> TemporaryResource:
        gallery_data = await self.query_gallery()
        name = f'NhentaiGallery - {gallery_data.id} - {gallery_data.title.japanese}'
        preview_request = await emit_preview_model_from_gallery_model(gallery_name=name, model=gallery_data)
        preview_img_file = await generate_nhentai_preview_image(preview=preview_request, hold_ratio=True)
        return preview_img_file

    async def download_gallery(self, *, ignore_exist_file: bool = True) -> NhentaiDownloadResult:
        """下载所有图片到指定目录, 压缩并生成随机密码

        :param ignore_exist_file: 是否忽略已下载的文件
        """
        gallery_model = await self.query_gallery()

        # 下载目标文件夹
        folder_name = f'gallery_{gallery_model.id}'
        download_folder = nhentai_resource_config.default_download_folder(folder_name)

        # 生成下载任务序列
        download_tasks = []
        for index, page in enumerate(gallery_model.images.pages):
            match page.t:
                case 'j':
                    page_type = 'jpg'
                case 'p':
                    page_type = 'png'
                case _:
                    page_type = 'unknown'

            page_download_url = f'{self._page_resource_url}{gallery_model.media_id}/{index + 1}.{page_type}'
            # 添加下载任务
            download_tasks.append(self.download_resource(
                url=page_download_url, folder_name=folder_name, ignore_exist_file=ignore_exist_file
            ))

        # 执行下载任务
        download_result = await semaphore_gather(tasks=download_tasks, semaphore_num=10)
        for result in download_result:
            if isinstance(result, Exception):
                raise NhentaiNetworkError(f'Some page(s) download failed, {result}')

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
        zip_file = ZipUtils(file_name=f'nhentai_gallery_{gallery_model.id}.7z', folder=download_folder)
        file_list = download_folder.list_all_files()
        zip_result = await zip_file.create_7z(files=file_list, password=password_str)

        return NhentaiDownloadResult(file=zip_result, password=password_str)


__all__ = [
    'NhentaiGallery'
]
