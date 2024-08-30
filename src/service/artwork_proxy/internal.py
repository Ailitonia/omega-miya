"""
@Author         : Ailitonia
@Date           : 2024/8/4 下午7:21
@FileName       : internal
@Project        : nonebot2_miya
@Description    : Artwork Proxy 统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from pathlib import PurePath
from typing import TYPE_CHECKING, Optional, Self
from urllib.parse import urlparse, unquote

from pydantic import ValidationError

from src.utils.process_utils import semaphore_gather
from .config import ArtworkProxyPathConfig
from .models import ArtworkData

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from .typing import ArtworkPageParamType


class BaseArtworkProxy(abc.ABC):
    """Artwork Proxy 基类"""

    def __init__(self, artwork_id: str | int):
        self.__id = artwork_id
        self.__path_config = self._generate_path_config()

        # 实例缓存
        self.artwork_data: Optional[ArtworkData] = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(artwork_id={self.s_aid})'

    @property
    def i_aid(self) -> int:
        if isinstance(self.__id, int):
            return self.__id
        else:
            return int(self.__id)  # 忽略类型检查，任由异常抛出并由后续流程处理

    @property
    def s_aid(self) -> str:
        return str(self.__id)

    @property
    def meta_file_name(self) -> str:
        return f'{self.s_aid}.json'

    @property
    def meta_file(self) -> "TemporaryResource":
        return self._get_path_config().meta_path(self.meta_file_name)

    @property
    def origin_name(self) -> str:
        """对外暴露该作品对应图库的来源名称, 用于数据库收录"""
        return self.get_base_origin_name()

    @property
    def path_config(self) -> ArtworkProxyPathConfig:
        """对外暴露该作品对应存储路径配置, 便于插件调用"""
        return self._get_path_config()

    @staticmethod
    def parse_url_file_suffix(url: str) -> str:
        """尝试解析 url 对应的文件后缀名"""
        return PurePath(unquote(urlparse(url=url, allow_fragments=True).path)).suffix

    @classmethod
    @abc.abstractmethod
    def get_base_origin_name(cls) -> str:
        """内部方法, 返回该图库的来源名称, 作为缓存路径及数据库收录分类字段名"""
        raise NotImplementedError

    @classmethod
    def _generate_path_config(cls) -> ArtworkProxyPathConfig:
        """内部方法, 生成该图库的本地存储路径配置项"""
        return ArtworkProxyPathConfig(base_path_name=cls.get_base_origin_name())

    def _get_path_config(self) -> ArtworkProxyPathConfig:
        """内部方法, 获取该图库的本地存储路径配置项"""
        return self.__path_config

    @classmethod
    @abc.abstractmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        """内部方法, 请求原始资源内容, 并转换为 bytes 类型返回"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _get_resource_as_text(cls, url: str, *, timeout: int = 10) -> str:
        """内部方法, 请求原始资源内容, 并转换为 str 类型返回"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        """内部方法, 随机获取作品 ID 列表"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _search(cls, keyword: str, *, page: Optional[int] = None, **kwargs) -> list[str | int]:
        """内部方法, 根据关键词搜索作品 ID 列表"""
        raise NotImplementedError

    @classmethod
    async def random(cls, *, limit: int = 20) -> list[Self]:
        """随机获取作品列表"""
        return [cls(artwork_id=aid) for aid in await cls._random(limit=limit)]

    @classmethod
    async def search(cls, keyword: str, *, page: Optional[int] = None, **kwargs) -> list[Self]:
        """根据关键词搜索作品列表"""
        return [cls(artwork_id=aid) for aid in await cls._search(keyword=keyword, page=page, **kwargs)]

    @abc.abstractmethod
    async def _query(self) -> ArtworkData:
        """内部方法, 获取作品信息"""
        raise NotImplementedError

    async def _dumps_meta(self, artwork_data: ArtworkData) -> None:
        """内部方法, 缓存元数据"""
        async with self.meta_file.async_open('w', encoding='utf8') as af:
            await af.write(artwork_data.model_dump_json())

    async def _fast_query(self, *, use_cache: bool = True) -> ArtworkData:
        """获取作品信息, 优先从本地缓存加载"""
        if use_cache and self.meta_file.is_file:
            try:
                async with self.meta_file.async_open('r', encoding='utf8') as af:
                    artwork_data = ArtworkData.model_validate_json(await af.read())
            except ValidationError:
                artwork_data = await self._query()
                await self._dumps_meta(artwork_data=artwork_data)
        else:
            artwork_data = await self._query()
            await self._dumps_meta(artwork_data=artwork_data)

        return artwork_data

    async def query(self, *, use_cache: bool = True) -> ArtworkData:
        """获取作品信息"""
        if not isinstance(self.artwork_data, ArtworkData):
            self.artwork_data = await self._fast_query(use_cache=use_cache)

        assert isinstance(self.artwork_data, ArtworkData), 'Query artwork data failed'
        return self.artwork_data

    @abc.abstractmethod
    async def get_std_desc(self, *, desc_len_limit: int = 128) -> str:
        """获取格式化作品描述文本"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_std_preview_desc(self, *, text_len_limit: int = 12) -> str:
        """获取格式化作品在预览图中的描述信息"""
        raise NotImplementedError

    async def _query_page(
            self,
            page_index: int = 0,
            page_type: "ArtworkPageParamType" = 'regular'
    ) -> bytes:
        """内部方法, 加载作品图片资源"""
        artwork_data = await self.query()

        match page_type:
            case 'preview':
                file_url = artwork_data.preview_pages_url[page_index]
            case 'original':
                file_url = artwork_data.original_pages_url[page_index]
            case 'regular' | _:
                file_url = artwork_data.regular_pages_url[page_index]

        return await self._get_resource_as_bytes(url=file_url)  # type: ignore

    async def _save_page(
            self,
            page_index: int = 0,
            page_type: "ArtworkPageParamType" = 'regular'
    ) -> "TemporaryResource":
        """内部方法, 保存作品资源到本地"""
        artwork_data = await self.query()

        match page_type:
            case 'preview':
                page = artwork_data.index_pages[page_index].preview_file
            case 'original':
                page = artwork_data.index_pages[page_index].original_file
            case 'regular' | _:
                page = artwork_data.index_pages[page_index].regular_file

        page_file_name = f'{self.s_aid}_{page_type}_p{page_index}.{page.file_ext.strip(".")}'
        page_file = self._get_path_config().artwork_path(page_file_name)

        # 如果已经存在则直接返回本地资源
        if page_file.is_file:
            return page_file

        # 没有的话再下载并保存文件
        page_content = await self._query_page(page_index=page_index, page_type=page_type)
        async with page_file.async_open('wb') as af:
            await af.write(page_content)
        return page_file

    async def _load_page(
            self,
            page_index: int = 0,
            page_type: "ArtworkPageParamType" = 'regular'
    ) -> bytes:
        """内部方法, 获取作品资源, 优先从本地缓存资源加载"""
        page_file = await self._save_page(page_index=page_index, page_type=page_type)

        async with page_file.async_open('rb') as af:
            page_content = await af.read()
        return page_content

    async def get_page_bytes(
            self,
            page_index: int = 0,
            page_type: "ArtworkPageParamType" = 'regular'
    ) -> bytes:
        """获取作品文件内容, 使用本地缓存"""
        return await self._load_page(page_index=page_index, page_type=page_type)

    async def get_page_file(
            self,
            page_index: int = 0,
            page_type: "ArtworkPageParamType" = 'regular'
    ) -> "TemporaryResource":
        """获取作品文件资源, 使用本地缓存"""
        return await self._save_page(page_index=page_index, page_type=page_type)

    async def get_all_pages_file(
            self,
            page_limit: int = 10,
            page_type: "ArtworkPageParamType" = 'regular'
    ) -> list["TemporaryResource"]:
        """获取作品所有文件资源列表, 使用本地缓存

        :param page_limit: 返回作品图片最大数量限制, 从第一张图开始计算, 避免漫画作品等单作品图片数量过多出现问题, 0 为无限制
        :param page_type: 类型, original: 原始图片, regular: 默认大图, preview: 缩略图
        """
        artwork_data = await self.query()

        # 创建获取作品页资源文件的 Task
        if page_limit <= 0:
            tasks = [
                self.get_page_file(page_index=index, page_type=page_type)
                for index, _ in artwork_data.index_pages.items()
            ]
        else:
            tasks = [
                self.get_page_file(page_index=index, page_type=page_type)
                for index, _ in artwork_data.index_pages.items()
                if index < page_limit
            ]

        all_pages_file = await semaphore_gather(tasks=tasks, semaphore_num=8, return_exceptions=False)

        return list(all_pages_file)

    async def download_page(self, page_index: int = 0) -> "TemporaryResource":
        """下载作品原图到本地"""
        return await self.get_page_file(page_index=page_index, page_type='original')

    async def download_all_pages(self) -> list["TemporaryResource"]:
        """下载作品全部原图到本地"""
        return await self.get_all_pages_file(page_limit=0, page_type='original')


__all__ = [
    'BaseArtworkProxy'
]
