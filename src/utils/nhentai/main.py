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
from typing import TYPE_CHECKING, Literal, Sequence

from src.exception import WebSourceException
from src.utils.common_api import BaseCommonAPI
from src.utils.image_utils.template import generate_thumbs_preview_image
from src.utils.process_utils import semaphore_gather
from src.utils.zip_utils import ZipUtils
from .config import nhentai_config, nhentai_resource_config
from .helper import NhentaiParser
from .model import (
    NhentaiDownloadResult,
    NhentaiGalleryModel,
    NhentaiPreviewRequestModel,
    NhentaiPreviewBody,
    NhentaiPreviewModel,
    NhentaiSearchingResult,
)

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes, HeaderTypes
    from src.resource import TemporaryResource


class BaseNhentai(BaseCommonAPI):
    """Nhentai 基类"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://nhentai.net'

    @classmethod
    def _get_search_url(cls) -> str:
        return f'{cls._get_root_url()}/search/'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> "HeaderTypes":
        headers = cls._get_omega_requests_default_headers()
        headers.update({'referer': 'https://nhentai.net/'})
        return headers

    @classmethod
    def _get_default_cookies(cls) -> "CookieTypes":
        return nhentai_config.nhentai_cookies

    @classmethod
    async def download_resource(
            cls,
            url: str,
            *,
            folder_name: str | None = None,
            ignore_exist_file: bool = False
    ) -> "TemporaryResource":
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=nhentai_resource_config.default_download_folder,
            url=url,
            subdir=folder_name,
            ignore_exist_file=ignore_exist_file
        )

    @classmethod
    async def _request_preview_body(cls, request: NhentaiPreviewRequestModel) -> NhentaiPreviewBody:
        """获取生成预览图中每个缩略图的数据"""
        _request_data = await cls._get_resource_as_bytes(url=request.request_url)
        return NhentaiPreviewBody(desc_text=request.desc_text, preview_thumb=_request_data)

    @classmethod
    async def _request_preview_model(
            cls,
            preview_name: str,
            requests: Sequence[NhentaiPreviewRequestModel]
    ) -> NhentaiPreviewModel:
        """获取生成预览图所需要的数据模型"""
        _tasks = [cls._request_preview_body(request) for request in requests]
        _requests_data = await semaphore_gather(tasks=_tasks, semaphore_num=30, filter_exception=True)
        _requests_data = list(_requests_data)
        count = len(_requests_data)
        return NhentaiPreviewModel.model_validate({
            'preview_name': preview_name,
            'count': count,
            'previews': _requests_data
        })

    @classmethod
    async def emit_preview_model_from_searching_model(
            cls,
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
        return await cls._request_preview_model(preview_name=searching_name, requests=request_list)

    @classmethod
    async def emit_preview_model_from_gallery_model(
            cls,
            gallery_name: str,
            model: NhentaiGalleryModel,
            *,
            use_thumbnail: bool = True
    ) -> NhentaiPreviewModel:
        """从作品信息中获取生成预览图所需要的数据模型"""

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
                NhentaiPreviewRequestModel.model_validate({
                    'desc_text': f'Page: {index + 1}',
                    'request_url': f'https://i.nhentai.net/galleries/{model.media_id}/{index + 1}.{_page_type(data.t)}'
                })
                for index, data in enumerate(model.images.pages)
            ]
        return await cls._request_preview_model(preview_name=gallery_name, requests=request_list)

    @classmethod
    async def generate_nhentai_preview_image(
            cls,
            preview: NhentaiPreviewModel,
            *,
            preview_size: tuple[int, int] = nhentai_resource_config.default_preview_size,
            hold_ratio: bool = False,
            num_of_line: int = 6,
            limit: int = 1000
    ) -> "TemporaryResource":
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
            font_path=nhentai_resource_config.default_font_file,
            header_color=(215, 64, 87),
            hold_ratio=hold_ratio,
            num_of_line=num_of_line,
            limit=limit,
            output_folder=nhentai_resource_config.default_preview_img_folder
        )


class Nhentai(BaseNhentai):
    """Nhentai 主站"""

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
        searching_content = await cls._get_resource_as_text(url=cls._get_search_url(), params=params)
        return await NhentaiParser.parse_gallery_searching_result_page(content=searching_content)

    @classmethod
    async def search_gallery_with_preview(
            cls,
            keyword: str,
            *,
            page: int = 1,
            sort: Literal['recent', 'popular-today', 'popular-week', 'popular'] = 'recent'
    ) -> "TemporaryResource":
        """通过关键词搜索本子id和标题并生成预览图"""
        searching_result = await cls.search_gallery(keyword=keyword, page=page, sort=sort)
        name = f'Searching - {keyword} - Page {page}'
        preview_request = await cls.emit_preview_model_from_searching_model(searching_name=name, model=searching_result)
        preview_img_file = await cls.generate_nhentai_preview_image(preview=preview_request, hold_ratio=True)
        return preview_img_file


class NhentaiGallery(Nhentai):
    """NhentaiGallery"""

    def __init__(self, gallery_id: int):
        self.gallery_id = gallery_id
        self.gallery_url = f'{self._get_root_url()}/g/{gallery_id}/'

        # 实例缓存
        self.gallery_model: NhentaiGalleryModel | None = None

    def __repr__(self):
        return f'<{self.__class__.__name__}(gallery_id={self.gallery_id})>'

    @classmethod
    def _get_page_resource_url(cls) -> str:
        return 'https://i.nhentai.net/galleries/'

    async def query_gallery(self) -> NhentaiGalleryModel:
        if not isinstance(self.gallery_model, NhentaiGalleryModel):
            gallery_content = await self._get_resource_as_text(url=self.gallery_url)
            self.gallery_model = await NhentaiParser.parse_gallery_page(content=gallery_content)

        if not isinstance(self.gallery_model, NhentaiGalleryModel):
            raise TypeError('Query gallery model failed')
        return self.gallery_model

    async def query_gallery_with_preview(self) -> "TemporaryResource":
        gallery_data = await self.query_gallery()
        name = f'NhentaiGallery - {gallery_data.id} - {gallery_data.title.japanese}'
        preview_request = await self.emit_preview_model_from_gallery_model(gallery_name=name, model=gallery_data)
        preview_img_file = await self.generate_nhentai_preview_image(preview=preview_request, hold_ratio=True)
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

            page_download_url = f'{self._get_page_resource_url()}{gallery_model.media_id}/{index + 1}.{page_type}'
            # 添加下载任务
            download_tasks.append(self.download_resource(
                url=page_download_url, folder_name=folder_name, ignore_exist_file=ignore_exist_file
            ))

        # 执行下载任务
        download_result = await semaphore_gather(tasks=download_tasks, semaphore_num=10)
        for result in download_result:
            if isinstance(result, WebSourceException):
                raise WebSourceException(result.status_code, f'Some page(s) download failed') from result
            elif isinstance(result, Exception):
                raise WebSourceException(404, f'Some page(s) download failed, {result}') from result

        # 生成包含本子原始信息的文件
        manifest_path = download_folder('manifest.json')
        async with manifest_path.async_open('w', encoding='utf8') as af:
            await af.write(gallery_model.model_dump_json())

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
    'Nhentai',
    'NhentaiGallery',
]
