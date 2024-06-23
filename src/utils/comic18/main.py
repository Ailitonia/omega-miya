"""
@Author         : Ailitonia
@Date           : 2024/5/26 下午7:49
@FileName       : main
@Project        : nonebot2_miya
@Description    : 18Comic
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Literal, Optional

from src.resource import TemporaryResource
from src.service import OmegaRequests

from .config import comic18_config, comic18_resource_config
from .exception import Comic18NetworkError
from .model import AlbumData, AlbumPage, AlbumPageContent, AlbumsResult
from .helper import Comic19Parser


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
            cls.__root_url = Comic19Parser.parse_root_url(content=go_response.content)

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
            timeout: int = 60
    ) -> TemporaryResource:
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        if headers is None:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
            headers.update({'referer': url})

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        file = comic18_resource_config.default_download_folder(original_file_name)
        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=comic18_config.cookies)

        return await requests.download(url=url, file=file, params=params)


class Comic18(_BaseComic18):
    """18Comic 主站功能"""

    def __init__(self, album_id: int):
        self.aid = album_id

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

        return await Comic19Parser(root_url=root_url).parse_query_albums_result_page(content=content)

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

        return await Comic19Parser(root_url=root_url).parse_query_albums_result_page(content=content)

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

        return await Comic19Parser(root_url=root_url).parse_search_photos_result_page(content=content)

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
        root_url = await self.get_root_url()
        url = f'{root_url}/album/{self.aid}'

        content = await self.request_resource(url=url)

        return await Comic19Parser(root_url=root_url).parse_album_page(content=content)

    async def query_pages(self, page: Optional[int] = None) -> AlbumPage:
        """获取漫画图片"""
        root_url = await self.get_root_url()
        url = f'{root_url}/photo/{self.aid}'

        params = None
        if page is not None:
            params = {'page': page}

        content = await self.request_resource(url=url, params=params)

        return await Comic19Parser(root_url=root_url).parse_pages_url(content=content)

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


__all__ = [
    'Comic18'
]
