"""
@Author         : Ailitonia
@Date           : 2024/5/26 下午7:49
@FileName       : main
@Project        : nonebot2_miya
@Description    : 18Comic
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
import string
from typing import Any, Literal, Optional

from nonebot.log import logger

from src.resource import TemporaryResource
from src.service import OmegaRequests
from src.utils.image_utils.template import generate_thumbs_preview_image
from src.utils.process_utils import semaphore_gather
from src.utils.zip_utils import ZipUtils

from .config import comic18_config, comic18_resource_config
from .exception import Comic18NetworkError
from .helper import Comic18Parser, Comic18ImgOps
from .model import (
    AlbumData,
    AlbumPage,
    AlbumPageContent,
    AlbumsResult,
    AlbumPackResult,
    Comic18PreviewBody,
    Comic18PreviewModel,
    Comic18PreviewRequestModel,
)


class _BaseComic18(object):
    """18Comic 基类"""
    __root_url: Optional[str] = None

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    async def get_root_url(
            cls,
            *,
            type_: Literal['300', '301', '302', '303', '304', '305', '306', '307', '308'] = '300'
    ) -> str:
        """获取主站地址

        - 导航地址: https://jmcmomic.github.io/
        - 仓库: https://github.com/jmcmomic/jmcmomic.github.io
        """
        if cls.__root_url is None:
            go_url = f'https://raw.githubusercontent.com/jmcmomic/jmcmomic.github.io/main/go/{type_}.html'
            go_response = await OmegaRequests().get(go_url)
            if go_response.status_code != 200:
                raise Comic18NetworkError(f'{go_response.request}, status code {go_response.status_code}')
            cls.__root_url = Comic18Parser.parse_root_url(content=go_response.content)

        return cls.__root_url

    @classmethod
    async def request_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 30
    ) -> str | bytes | None:
        """请求原始资源内容"""
        if headers is None:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
            headers.update({'referer': url})

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=comic18_config.cookies)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise Comic18NetworkError(f'{response.request}, status code {response.status_code}')

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
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
            headers.update({'referer': url})

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        if folder_name is None:
            file = comic18_resource_config.default_download_folder(original_file_name)
        else:
            file = comic18_resource_config.default_download_folder(folder_name, original_file_name)

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=comic18_config.cookies)

        return await requests.download(url=url, file=file, params=params, ignore_exist_file=ignore_exist_file)


class Comic18(_BaseComic18):
    """18Comic 主站功能"""

    def __init__(self, album_id: int):
        self.aid = album_id

        # 实例缓存
        self.album_data: AlbumData | None = None

    @classmethod
    async def query_albums_list(
            cls,
            page: Optional[int] = None,
            type_: Optional[Literal['another', 'doujin', 'hanman', 'meiman', 'short', 'single']] = None,
            time: Optional[Literal['a', 't', 'w', 'm']] = None,
            order: Optional[Literal['mr', 'mv', 'mp', 'md', 'tr', 'tf']] = None,
    ) -> list[AlbumsResult]:
        """获取分类漫画

        :param page: 分类页数
        :param type_: 分类类型, another其他, doujin同人本, hanman韩漫, meiman美漫, short短篇, single单行本, None默认全部
        :param time: 时间范围, a全部, t今天, w本周, m本月, 默认全部
        :param order: 结果排序, mr最新(most recent), mv最多点击(most view), mp最多图片(most page), md最多评论, tr最高评分, tf最多爱心
        """
        root_url = await cls.get_root_url()
        url = f'{root_url}/albums'
        if type_ is not None:
            url = f'{url}/{type_}'

        params = {}
        if page is not None:
            params.update({'page': page})
        if time is not None:
            params.update({'t': time})
        if order is not None:
            params.update({'o': order})

        content = await cls.request_resource(url=url, params=params)

        return await Comic18Parser(root_url=root_url).parse_query_albums_result_page(content=content)

    @classmethod
    async def query_albums_list_with_preview(
            cls,
            page: Optional[int] = None,
            type_: Optional[Literal['another', 'doujin', 'hanman', 'meiman', 'short', 'single']] = None,
            time: Optional[Literal['a', 't', 'w', 'm']] = None,
            order: Optional[Literal['mr', 'mv', 'mp', 'md', 'tr', 'tf']] = None,
    ) -> TemporaryResource:
        """获取分类漫画并生成预览图"""
        result = await cls.query_albums_list(page=page, type_=type_, time=time, order=order)
        name = f'AlbumsList - {type_} - Page {page}'
        preview = await cls._emit_preview_model_from_searching_data(searching_name=name, searching_data=result)
        return await cls._generate_preview_image(preview=preview, num_of_line=8, hold_ratio=True)

    @classmethod
    async def query_promotes(
            cls,
            type_: int = 27,
            page: Optional[int] = None,
    ) -> list[AlbumsResult]:
        """获取漫画推荐专题

        :param type_: 专题类型, 26連載更新, 27本本推薦, ...
        :param page: 专题页数
        """
        root_url = await cls.get_root_url()
        url = f'{root_url}/promotes/{type_}'
        params = {}
        if page is not None:
            params.update({'page': page})

        content = await cls.request_resource(url=url, params=params)

        return await Comic18Parser(root_url=root_url).parse_query_albums_result_page(content=content)

    @classmethod
    async def query_promotes_with_preview(
            cls,
            type_: int = 27,
            page: Optional[int] = None,
    ) -> TemporaryResource:
        """获取漫画推荐专题并生成预览图"""
        result = await cls.query_promotes(type_=type_, page=page)
        name = f'PromotesList - {type_} - Page {page}'
        preview = await cls._emit_preview_model_from_searching_data(searching_name=name, searching_data=result)
        return await cls._generate_preview_image(preview=preview, num_of_line=8, hold_ratio=True)

    @classmethod
    async def search_photos(
            cls,
            search_query: str,
            *,
            page: Optional[int] = None,
            type_: Optional[Literal['another', 'doujin', 'hanman', 'meiman', 'short', 'single']] = None,
            time: Optional[Literal['a', 't', 'w', 'm']] = None,
            order: Optional[Literal['mr', 'mv', 'mp', 'tf']] = None,
            main_tag: Optional[Literal['0', '1', '2', '3', '4']] = None,
    ) -> list[AlbumsResult]:
        """搜索漫画

        :param search_query: 搜索关键词, 支持[+][-]关键词搜索
        :param page: 搜索结果页数
        :param type_: 搜索类型, another其他, doujin同人本, hanman韩漫, meiman美漫, short短篇, single单行本, None默认全部
        :param time: 时间范围, a全部, t今天, w本周, m本月, 默认全部
        :param order: 结果排序, mr最新(most recent), mv最多点击(most view), mp最多图片(most page), tf最多爱心
        :param main_tag: 搜索类型, 0站内搜索, 1作品, 2作者, 3标签, 4登场人物
        """
        root_url = await cls.get_root_url()
        url = f'{root_url}/search/photos'
        if type_ is not None:
            url = f'{url}/{type_}'

        params = {'search_query': search_query}
        if page is not None:
            params.update({'page': page})
        if main_tag is not None:
            params.update({'main_tag': main_tag})
        if time is not None:
            params.update({'t': time})
        if order is not None:
            params.update({'o': order})

        content = await cls.request_resource(url=url, params=params)

        return await Comic18Parser(root_url=root_url).parse_search_photos_result_page(content=content)

    @classmethod
    async def search_photos_with_preview(
            cls,
            search_query: str,
            *,
            page: Optional[int] = None,
            type_: Optional[Literal['another', 'doujin', 'hanman', 'meiman', 'short', 'single']] = None,
            time: Optional[Literal['a', 't', 'w', 'm']] = None,
            order: Optional[Literal['mr', 'mv', 'mp', 'tf']] = None,
            main_tag: Optional[Literal['0', '1', '2', '3', '4']] = None,
    ) -> TemporaryResource:
        """搜索漫画并生成预览图"""
        result = await cls.search_photos(search_query, page=page, type_=type_, time=time, order=order, main_tag=main_tag)
        name = f'Searching - {search_query} - Page {page}'
        preview = await cls._emit_preview_model_from_searching_data(searching_name=name, searching_data=result)
        return await cls._generate_preview_image(preview=preview, num_of_line=8, hold_ratio=True)

    @classmethod
    async def search_videos(cls):
        """搜索动画"""
        raise NotImplementedError

    @classmethod
    async def search_movies(cls):
        """搜索电影"""
        raise NotImplementedError

    @classmethod
    async def search_blogs(cls):
        """搜索文库"""
        raise NotImplementedError

    async def query_album(self) -> AlbumData:
        """获取漫画信息"""
        if not isinstance(self.album_data, AlbumData):
            root_url = await self.get_root_url()
            url = f'{root_url}/album/{self.aid}'

            content = await self.request_resource(url=url)
            self.album_data = await Comic18Parser(root_url=root_url).parse_album_page(content=content)

        assert isinstance(self.album_data, AlbumData), 'Query album data failed'
        return self.album_data

    async def query_album_with_preview(self) -> TemporaryResource:
        """获取漫画并生成漫画内容预览图"""
        return await self._generate_album_preview_image()

    async def query_pages(self, page: Optional[int] = None) -> AlbumPage:
        """获取漫画图片"""
        root_url = await self.get_root_url()
        url = f'{root_url}/photo/{self.aid}'

        params = None
        if page is not None:
            params = {'page': page}

        content = await self.request_resource(url=url, params=params)

        return await Comic18Parser(root_url=root_url).parse_pages_url(content=content)

    async def query_all_pages(self) -> list[AlbumPageContent]:
        """获取漫画所有的图片"""
        default_page = await self.query_pages()
        if not default_page.pagination:
            return default_page.data

        data = default_page.data
        for p in default_page.pagination:
            extra_page = await self.query_pages(page=p)
            data.extend(extra_page.data)

        return data

    async def _reverse_image(
            self,
            page_id: str,
            file: TemporaryResource,
            save_folder: TemporaryResource
    ) -> TemporaryResource:
        """恢复被分割的图片"""
        image: Comic18ImgOps = await Comic18ImgOps.async_init_from_file(file=file)
        output_image = await image.reverse_segmental_image(album_id=self.aid, page_id=page_id)
        return await output_image.save(save_folder(f'{page_id}.jpg'))

    async def download_album(self, *, ignore_exist_file: bool = True) -> list[TemporaryResource]:
        """下载漫画"""
        album_pages = await self.query_all_pages()

        # 下载目标文件夹
        folder_name = f'album_{self.aid}'
        download_folder = comic18_resource_config.default_download_folder(folder_name)

        # 生成下载任务序列
        download_tasks = []
        for page in album_pages:
            download_tasks.append(
                self.download_resource(url=page.url, folder_name=folder_name, ignore_exist_file=ignore_exist_file)
            )

        # 执行下载任务
        logger.info(f'Comic18 | Start downloading album(id={self.aid})')
        download_result = await semaphore_gather(tasks=download_tasks, semaphore_num=10)
        for result in download_result:
            if isinstance(result, Exception):
                raise Comic18NetworkError(f'Some page(s) download failed, {result}')
        logger.info(f'Comic18 | Downloaded album(id={self.aid}) original image completed, staring reversing')

        # 执行图片恢复
        reverse_tasks = []
        for file in download_result:
            reverse_tasks.append(self._reverse_image(page_id=file.path.name, file=file, save_folder=download_folder))
        reverse_result = await semaphore_gather(tasks=reverse_tasks, semaphore_num=10, return_exceptions=False)
        logger.success(f'Comic18 | Downloaded and reversed album(id={self.aid}) succeed')

        return [x for x in reverse_result if isinstance(x, TemporaryResource)]

    async def download_and_pack_album(self, *, ignore_exist_file: bool = True) -> AlbumPackResult:
        """下载并打包漫画"""
        album_data = await self.query_album()

        # 执行下载任务
        download_folder = comic18_resource_config.default_download_folder(f'album_{self.aid}')
        download_result = await self.download_album(ignore_exist_file=ignore_exist_file)

        # 归档元数据
        metadata_file = download_folder('metadata.json')
        async with metadata_file.async_open('w', encoding='utf8') as af:
            await af.write(album_data.model_dump_json())

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
        logger.info(f'Comic18 | Packing album(id={self.aid}) content, password: {password_str}')
        zip_file = ZipUtils(file_name=f'Comic18_album_{self.aid}.7z', folder=download_folder)
        file_list = [metadata_file, rand_file, password_file, *download_result]
        zip_result = await zip_file.create_7z(files=file_list, password=password_str)
        logger.success(f'Comic18 | Packed album(id={self.aid}) succeed')

        return AlbumPackResult(file=zip_result, password=password_str)

    @classmethod
    async def _request_preview_body(cls, request: Comic18PreviewRequestModel) -> Comic18PreviewBody:
        """获取生成预览图中每个缩略图的数据"""
        request_data = await cls.request_resource(url=request.request_url)
        return Comic18PreviewBody(desc_text=request.desc_text, preview_thumb=request_data)

    @classmethod
    async def _request_preview_model(
            cls,
            preview_name: str,
            requests: list[Comic18PreviewRequestModel]
    ) -> Comic18PreviewModel:
        """获取生成预览图所需要的数据模型"""
        _tasks = [cls._request_preview_body(request) for request in requests]
        _requests_data = await semaphore_gather(tasks=_tasks, semaphore_num=30, filter_exception=True)
        _requests_data = list(_requests_data)
        count = len(_requests_data)
        return Comic18PreviewModel(preview_name=preview_name, count=count, previews=_requests_data)

    @staticmethod
    async def _generate_preview_image(
            preview: Comic18PreviewModel,
            *,
            preview_size: tuple[int, int] = (300, 450),
            hold_ratio: bool = False,
            num_of_line: int = 4,
            limit: int = 1000
    ) -> TemporaryResource:
        """生成多个图片内容的预览图

        :param preview_size: 单个小缩略图的尺寸
        :param hold_ratio: 是否保持缩略图原图比例
        :param num_of_line: 生成预览每一行的预览图数
        :param limit: 限制生成时加载 preview 中图片的最大值
        """
        return await generate_thumbs_preview_image(
            preview=preview,
            preview_size=preview_size,
            font_path=comic18_resource_config.default_font_file,
            header_color=(215, 64, 87),
            hold_ratio=hold_ratio,
            num_of_line=num_of_line,
            limit=limit,
            output_folder=comic18_resource_config.default_preview_folder
        )

    @classmethod
    async def _emit_preview_model_from_searching_data(
            cls,
            searching_name: str,
            searching_data: list[AlbumsResult],
    ) -> Comic18PreviewModel:
        """从搜索结果中获取生成预览图所需要的数据模型"""
        request_list = [
            Comic18PreviewRequestModel(
                desc_text=f'JM{data.aid}\n{data.title[:18]}\n{data.title[18:36]}...'
                if len(data.title) > 36
                else f'JM{data.aid}\n{data.title[:18]}\n{data.title[18:]}',
                request_url=data.cover_image_url
            )
            for data in searching_data
        ]
        preview_model = await cls._request_preview_model(preview_name=searching_name, requests=request_list)
        return preview_model

    async def _emit_preview_model_from_album_data(self) -> Comic18PreviewModel:
        """从作品信息中获取生成预览图所需要的数据模型"""
        album_data = await self.query_album()
        preview_name = f'18Comic - JM{album_data.aid} - {album_data.title}'
        pages = await self.download_album()
        count = len(pages)

        previews = []
        for index, file in enumerate(pages):
            async with file.async_open('rb') as af:
                page_content = await af.read()
            previews.append(Comic18PreviewBody(
                desc_text=f'Page: {index+1} / {count}',
                preview_thumb=page_content
            ))

        return Comic18PreviewModel(preview_name=preview_name, count=count, previews=previews)

    async def _generate_album_preview_image(self) -> TemporaryResource:
        """生成作品预览图"""
        preview_data = await self._emit_preview_model_from_album_data()
        return await self._generate_preview_image(preview=preview_data, hold_ratio=True)


__all__ = [
    'Comic18'
]
