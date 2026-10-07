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
import asyncio
import glob
import hashlib
import re
import time
import unicodedata
import weakref
from collections.abc import Sequence
from datetime import datetime
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self
from urllib.parse import unquote, urlparse

from pydantic import ValidationError

from src.database.internal.artwork_collection import (
    Artwork,
    ArtworkClassificationStatistic,
    ArtworkCollectionDAL,
    ArtworkRatingStatistic,
    ArtworkReviewRecord,
)
from src.utils import semaphore_gather
from .config import ArtworkProxyPathConfig
from .models import (
    ArtistUserData,
    ArtworkPoolData,
    ArtworkProxyData,
    ArtworkRating,
    PreviewImageThumbsItem,
    PreviewImagesData,
)
from .preview_image_utils import ArtworkImageOps

if TYPE_CHECKING:
    from src.resource import TemporaryResource

type ArtworkPageParamType = Literal['preview', 'regular', 'original']
"""作品页面可选类型参数"""
type ArtworkProcessParamType = Literal['mark', 'blur', 'noise']
"""作品图片处理方法可选参数类型"""
type ArtworkRankParamType = Literal['daily', 'weekly', 'monthly']
"""作品榜单页面可选类型参数"""

_INT_AID_SLICED_SIZE: int = 1_000_000
"""数字型 artwork_id 切分目录分片大小(按分段)"""
_STR_AID_SLICED_LEN: int = 3
"""字符型 artwork_id 切分目录分片长度(按哈希)"""

_FILE_NAME_INVALID_CHARS = re.compile(r'[/\\<>:"|?*\x00-\x1f]')
"""缓存文件名中不允许出现的字符(Windows/POSIX 文件名保留字符与控制字符/路径分隔符/NUL)"""
_FILE_NAME_MAX_LENGTH: int = 128
"""清洗后文件名长度上限(超出时截断基名并追加确定性短哈希后缀)"""
_WINDOWS_RESERVED_FILE_NAMES = frozenset(
    {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}
)
"""Windows 保留设备文件名(不区分大小写, 含扩展名形式, 不可用作文件名)"""
_PAGE_FILE_LOCKS: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
"""作品页面文件写入的进程内锁注册表(按目标文件解析路径, 弱引用自动清理)"""
_DATABASE_WRITE_LOCK: asyncio.Lock = asyncio.Lock()
"""数据库写入锁, 避免数据库并发写入时的冲突"""
_META_SNAPSHOT_KEPT_NUM: int = 8
"""每个作品保留的元数据快照数量上限"""


class BaseArtworkProxy(abc.ABC):
    """Artwork Proxy 基类"""

    _path_config: ClassVar[ArtworkProxyPathConfig | None] = None
    """作品相关缓存及数据存储路径配置"""

    def __init__(self, artwork_id: str | int):
        self.__id: str = self._clean_file_name(artwork_id)

        # 实例缓存
        self.artwork_data: ArtworkProxyData | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(origin={self._get_base_origin_name()}, artwork_id={self.__id})'

    @property
    def i_aid(self) -> int:
        if self.__id.isdecimal():
            return int(self.__id)
        raise ValueError(f'aid {self.__id} is not a number')

    @property
    def s_aid(self) -> str:
        return self.__id

    @staticmethod
    def _clean_file_name(value: str | int) -> str:
        """规范化文件名, 拦截路径分隔符/特殊目录名/NUL/Windows 保留字符及保留设备名, 为空时回退为哈希文件名

        清洗结果与原始值不一致或超出长度上限时, 截断基名并追加确定性短哈希后缀,
        保证最终文件名长度不超过 _FILE_NAME_MAX_LENGTH 且不同原始值不碰撞到同一文件名;
        底层路径越界最终由 TemporaryResource confinement 兜底
        """
        cleaned = _FILE_NAME_INVALID_CHARS.sub('_', str(value).strip().rstrip('. '))
        value_hash = hashlib.sha256(str(value).encode('utf-8')).hexdigest()

        if cleaned and cleaned.upper().split('.')[0] in _WINDOWS_RESERVED_FILE_NAMES:
            # Windows 保留设备名(含扩展名形式)不可用作文件名, 按无效输入回退为哈希文件名
            cleaned = ''

        if not cleaned:
            # 原始值全部无效或为 Windows 保留设备名时, 回退为确定性哈希文件名
            return value_hash[:16]

        if cleaned != str(value) or len(cleaned) > _FILE_NAME_MAX_LENGTH:
            # 清洗改变了原始值或超出长度上限时, 截断基名并追加确定性短哈希后缀,
            # 避免 'a/b' 与 'a\\b' 等不同原始值碰撞到同一文件名, 且总长度不超过上限
            cleaned = f'{cleaned[:_FILE_NAME_MAX_LENGTH - 5]}.{value_hash[:4]}'
        return cleaned

    @classmethod
    @abc.abstractmethod
    def _get_base_origin_name(cls) -> str:
        """内部方法, 获取该图库的来源名称, 作为缓存路径及数据库收录分类字段名"""
        raise NotImplementedError

    @classmethod
    def get_origin_name(cls) -> str:
        """对外暴露该图库的来源名称, 作为缓存路径及数据库收录分类字段名"""
        return cls._get_base_origin_name()

    @classmethod
    def _get_path_config(cls) -> ArtworkProxyPathConfig:
        """内部方法, 初始化该图库的本地存储路径配置项(仅使用本类自身的缓存, 避免继承自父类的配置串 origin 目录)"""
        config = cls.__dict__.get('_path_config')
        if not isinstance(config, ArtworkProxyPathConfig):
            config = ArtworkProxyPathConfig(base_path_name=cls._get_base_origin_name())
            cls._path_config = config
        return config

    @property
    def origin_name(self) -> str:
        """对外暴露该作品对应图库的来源名称, 作为缓存路径及数据库收录分类字段名"""
        return self._get_base_origin_name()

    @property
    def path_config(self) -> ArtworkProxyPathConfig:
        """对外暴露该作品对应存储路径配置, 便于插件调用"""
        return self._get_path_config()

    @property
    def sliced_aid_subdir_name(self) -> str:
        """根据 artwork_id 切分缓存及数据文件子目录, 避免单一目录文件过多"""
        if self.s_aid.isdecimal() and (i_aid := int(self.s_aid)) <= _INT_AID_SLICED_SIZE ** 2:
            start, _ = divmod(i_aid, _INT_AID_SLICED_SIZE)
            subdir_name = f'artwork_id_{start * _INT_AID_SLICED_SIZE}-{(start + 1) * _INT_AID_SLICED_SIZE - 1}'
        else:
            id_hash = hashlib.sha256(unicodedata.normalize('NFC', self.s_aid).encode('utf-8')).hexdigest()
            subdir_name = f'artwork_id_H{id_hash[:_STR_AID_SLICED_LEN]}'
        return subdir_name

    @property
    def meta_path(self) -> 'TemporaryResource':
        """本类型作品元数据文件目录"""
        return self._get_path_config().meta_path(self.sliced_aid_subdir_name)

    @property
    def artwork_path(self) -> 'TemporaryResource':
        """本类型作品图片缓存文件目录"""
        return self._get_path_config().artwork_path(self.sliced_aid_subdir_name)

    @property
    def meta_file(self) -> 'TemporaryResource':
        """作品元数据文件路径"""
        return self.meta_path(f'{self.s_aid}.json')

    @property
    def meta_file_date_snapshot(self) -> 'TemporaryResource':
        """作品元数据文件(获取时快照副本)路径"""
        return self.meta_path(f'{self.s_aid}.{datetime.now().strftime("%Y%m%d%H%M%S%f")}.json.snapshot')

    @staticmethod
    def parse_url_file_suffix(url: str) -> str:
        """尝试解析 url 对应的文件后缀名"""
        return PurePath(unquote(urlparse(url=url, allow_fragments=True).path)).suffix

    # ------------------------------------------------------------------ #
    # 源站或 API 请求相关方法
    # ------------------------------------------------------------------ #

    @classmethod
    @abc.abstractmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        """内部方法, 请求原始资源内容, 并转换为 bytes 类型返回"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        """内部方法, 从源站或 API 随机获取作品 ID 列表"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        """内部方法, 从源站或 API 根据关键词搜索作品 ID 列表"""
        raise NotImplementedError

    @classmethod
    async def random(cls, *, limit: int = 20) -> list[Self]:
        """从源站或 API 随机获取作品列表"""
        return [cls(artwork_id=aid) for aid in await cls._random(limit=limit)]

    @classmethod
    async def search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[Self]:
        """从源站或 API 根据关键词搜索作品列表"""
        return [cls(artwork_id=aid) for aid in await cls._search(keyword=keyword, page=page, **kwargs)]

    @abc.abstractmethod
    async def _query(self) -> ArtworkProxyData:
        """内部方法, 从源站或 API 获取作品信息"""
        raise NotImplementedError

    async def _dumps_meta(self, artwork_data: ArtworkProxyData) -> None:
        """内部方法, 缓存元数据, 默认额外保存当前快照副本(仅保留最新若干份)"""
        async with self.meta_file.async_open('w', encoding='utf-8') as af:
            await af.write(artwork_data.model_dump_json())
        async with self.meta_file_date_snapshot.async_open('w', encoding='utf-8') as asf:
            await asf.write(artwork_data.model_dump_json())

        # 清理超出保留上限的历史快照(文件名时间戳定宽, 按名称排序即按时间排序), 避免快照只增不减
        snapshots = sorted(self.meta_path.path.glob(f'{glob.escape(self.s_aid)}.*.json.snapshot'))
        for stale_snapshot in snapshots[:-_META_SNAPSHOT_KEPT_NUM]:
            stale_snapshot.unlink(missing_ok=True)

    async def _fast_query(self, *, use_cache: bool = True) -> ArtworkProxyData:
        """获取作品信息, 优先从本地缓存加载(缓存损坏或读取失败时回源重建)"""
        if use_cache and self.meta_file.is_file:
            try:
                async with self.meta_file.async_open('r', encoding='utf-8') as af:
                    artwork_data = ArtworkProxyData.model_validate_json(await af.read())
            except (ValidationError, OSError, UnicodeDecodeError):
                artwork_data = await self._query()
                await self._dumps_meta(artwork_data=artwork_data)
        else:
            artwork_data = await self._query()
            await self._dumps_meta(artwork_data=artwork_data)

        return artwork_data

    async def query(self, *, use_cache: bool = True) -> ArtworkProxyData:
        """获取作品信息"""
        if not isinstance(self.artwork_data, ArtworkProxyData):
            self.artwork_data = await self._fast_query(use_cache=use_cache)
        return self.artwork_data

    @abc.abstractmethod
    async def get_std_desc(self, *, split_len: int = 128) -> str:
        """获取格式化作品描述文本"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
        """获取格式化作品预览图描述信息"""
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # 图集相关方法
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_pool_meta_file(cls, pool_id: str | int) -> 'TemporaryResource':
        pool_id = cls._clean_file_name(pool_id)
        return cls._get_path_config().meta_path('pool', f'pool_{pool_id}.json')

    @classmethod
    @abc.abstractmethod
    async def _query_pool(cls, pool_id: str | int) -> ArtworkPoolData:
        """获取图集信息"""
        raise NotImplementedError

    @classmethod
    async def _dumps_pool_meta(cls, pool_data: ArtworkPoolData) -> None:
        """内部方法, 缓存图集元数据"""
        pid = pool_data.pool_id
        async with cls._get_pool_meta_file(pool_id=pid).async_open('w', encoding='utf8') as af:
            await af.write(pool_data.model_dump_json())

    @classmethod
    async def _fast_query_pool(cls, pool_id: str | int, *, use_cache: bool = True) -> ArtworkPoolData:
        """获取图集信息, 优先从本地缓存加载(缓存损坏或读取失败时回源重建)"""
        if use_cache and cls._get_pool_meta_file(pool_id=pool_id).is_file:
            try:
                async with cls._get_pool_meta_file(pool_id).async_open('r', encoding='utf8') as af:
                    pool_data = ArtworkPoolData.model_validate_json(await af.read())
            except (ValidationError, OSError, UnicodeDecodeError):
                pool_data = await cls._query_pool(pool_id=pool_id)
                await cls._dumps_pool_meta(pool_data=pool_data)
        else:
            pool_data = await cls._query_pool(pool_id=pool_id)
            await cls._dumps_pool_meta(pool_data=pool_data)

        return pool_data

    @classmethod
    async def query_pool(cls, pool_id: str | int, *, use_cache: bool = True) -> ArtworkPoolData:
        """获取图集信息"""
        return await cls._fast_query_pool(pool_id=pool_id, use_cache=use_cache)

    @classmethod
    async def query_pool_all_artworks(cls, pool_id: str | int) -> list['ArtworkProxyData']:
        """获取图集中所有作品信息"""
        pool_data = await cls.query_pool(pool_id=pool_id)
        tasks = [cls(aid).query() for aid in pool_data.artwork_ids]
        return list(await semaphore_gather(tasks=tasks, semaphore_num=6, return_exceptions=False))

    @classmethod
    async def query_pool_all_artwork_pages(cls, pool_id: str | int) -> list['TemporaryResource']:
        """获取图集中所有作品封面图片"""
        pool_data = await cls.query_pool(pool_id=pool_id)
        tasks = [cls(aid).get_page_file() for aid in pool_data.artwork_ids]
        return list(await semaphore_gather(tasks=tasks, semaphore_num=6, return_exceptions=False))

    @classmethod
    async def generate_pool_preview(cls, pool_id: str | int) -> 'TemporaryResource':
        """生成图集的预览图"""
        pool_data = await cls.query_pool(pool_id=pool_id)
        return await cls.generate_artworks_preview(
            preview_name=f'{cls._get_base_origin_name().title()} Pool #{pool_id}: {pool_data.name}',
            artworks=[cls(aid) for aid in pool_data.artwork_ids],
        )

    # ------------------------------------------------------------------ #
    # 用户空间相关方法
    # ------------------------------------------------------------------ #

    @classmethod
    @abc.abstractmethod
    async def _discovery(cls, *, limit: int = 20) -> list[str | int]:
        """内部方法, 获取首页/发现页/瀑布流作品"""
        raise NotImplementedError

    @classmethod
    async def discovery(cls, *, limit: int = 20) -> list[Self]:
        """获取首页/发现页/瀑布流作品"""
        return [cls(artwork_id=aid) for aid in await cls._discovery(limit=limit)]

    @classmethod
    @abc.abstractmethod
    async def _recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[str | int]:
        """内部方法, 获取推荐作品, 如未提供基准 Artwork ID, 则使用类似首页推荐机制进行获取"""
        raise NotImplementedError

    @classmethod
    async def recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[Self]:
        """获取推荐作品, 如未提供基准 Artwork ID, 则使用类似首页推荐机制进行获取"""
        return [cls(artwork_id=aid) for aid in await cls._recommend(base_aid=base_aid, limit=limit)]

    @classmethod
    @abc.abstractmethod
    async def _daily_ranking(cls, page: int) -> list[str | int]:
        """内部方法, 获取每日榜单作品"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _weekly_ranking(cls, page: int) -> list[str | int]:
        """内部方法, 获取每周榜单作品"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _monthly_ranking(cls, page: int) -> list[str | int]:
        """内部方法, 获取每月榜单作品"""
        raise NotImplementedError

    @classmethod
    async def ranking(cls, mode: ArtworkRankParamType, page: int) -> list[Self]:
        """获取榜单作品(未知 mode 回退为 monthly)"""
        page = 1 if page < 1 else page
        match mode:
            case 'daily':
                artwork_ids = await cls._daily_ranking(page=page)
            case 'weekly':
                artwork_ids = await cls._weekly_ranking(page=page)
            case 'monthly' | _:
                artwork_ids = await cls._monthly_ranking(page=page)
        return [cls(artwork_id=aid) for aid in artwork_ids]

    @classmethod
    def _get_user_meta_file(cls, uid: str | int) -> 'TemporaryResource':
        uid = cls._clean_file_name(uid)
        return cls._get_path_config().meta_path('user', f'user_{uid}.json')

    @classmethod
    @abc.abstractmethod
    async def _query_user(cls, uid: str | int) -> ArtistUserData:
        """内部方法, 获取用户信息"""
        raise NotImplementedError

    @classmethod
    async def _dumps_user_meta(cls, user_data: ArtistUserData) -> None:
        """内部方法, 缓存用户元数据"""
        uid = user_data.uid
        async with cls._get_user_meta_file(uid=uid).async_open('w', encoding='utf8') as af:
            await af.write(user_data.model_dump_json())

    @classmethod
    async def _fast_query_user(cls, uid: str | int, *, use_cache: bool = True) -> ArtistUserData:
        """内部方法, 获取用户信息, 优先从本地缓存加载(缓存损坏或读取失败时回源重建)"""
        if use_cache and cls._get_user_meta_file(uid=uid).is_file:
            try:
                async with cls._get_user_meta_file(uid=uid).async_open('r', encoding='utf8') as af:
                    user_data = ArtistUserData.model_validate_json(await af.read())
            except (ValidationError, OSError, UnicodeDecodeError):
                user_data = await cls._query_user(uid=uid)
                await cls._dumps_user_meta(user_data=user_data)
        else:
            user_data = await cls._query_user(uid=uid)
            await cls._dumps_user_meta(user_data=user_data)

        return user_data

    @classmethod
    async def query_user(cls, uid: str | int, *, use_cache: bool = True) -> ArtistUserData:
        """获取用户信息"""
        return await cls._fast_query_user(uid=uid, use_cache=use_cache)

    @classmethod
    async def _query_user_artworks(cls, uid: str | int) -> list[str | int]:
        """内部方法, 获取用户作品列表"""
        return list((await cls.query_user(uid=uid, use_cache=False)).artwork_ids)

    @classmethod
    async def query_user_artworks(cls, uid: str | int) -> list[Self]:
        """获取用户作品列表"""
        return [cls(artwork_id=aid) for aid in await cls._query_user_artworks(uid=uid)]

    @classmethod
    @abc.abstractmethod
    async def _query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[str | int]:
        """内部方法, 获取用户收藏作品"""
        raise NotImplementedError

    @classmethod
    async def query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[Self]:
        """获取用户收藏作品"""
        page = 1 if page < 1 else page
        return [cls(artwork_id=aid) for aid in await cls._query_user_bookmark_artworks(uid=uid, page=page)]

    @classmethod
    @abc.abstractmethod
    async def _query_follow_latest(cls, page: int, *, filter_tag: str | None = None) -> list[str | int]:
        """内部方法, 获取已关注的最新作品"""
        raise NotImplementedError

    @classmethod
    async def query_follow_latest(cls, page: int, *, filter_tag: str | None = None) -> list[Self]:
        """获取已关注的最新作品"""
        return [cls(artwork_id=aid) for aid in await cls._query_follow_latest(page=page, filter_tag=filter_tag)]

    # ------------------------------------------------------------------ #
    # 作品获取及本地缓存相关方法
    # ------------------------------------------------------------------ #

    async def _save_page(
            self,
            page_index: int = 0,
            page_type: 'ArtworkPageParamType' = 'regular',
    ) -> 'TemporaryResource':
        """内部方法, 保存作品资源到本地(未知 page_type 回退为 regular 文件, 但文件名沿用传入类型串)"""
        artwork_data = await self.query()
        index_pages = artwork_data.index_pages
        if page_index not in index_pages:
            raise ValueError(f'{self.origin_name} {self.s_aid} has no page with page_index {page_index}')

        match page_type:
            case 'preview':
                page = index_pages[page_index].preview_file
            case 'original':
                page = index_pages[page_index].original_file
            case 'regular' | _:
                page = index_pages[page_index].regular_file

        file_ext = self._clean_file_name(page.file_ext.strip('.'))
        page_file_name = f'{self.s_aid}_{page_type}_p{page_index}.{file_ext}'
        page_file = self.artwork_path(page_file_name)

        # 如果已经存在则直接返回本地资源
        if page_file.is_file:
            return page_file

        # 按目标文件路径加进程内锁(事件循环单线程, setdefault 与加锁之间无 await, 无竞态), 避免同一页并发重复下载
        lock = _PAGE_FILE_LOCKS.setdefault(page_file.resolve_path, asyncio.Lock())
        async with lock:
            # 获取锁后二次检查, 前序任务可能已完成下载
            if page_file.is_file:
                return page_file

            page_content = await self._get_resource_as_bytes(url=page.url)
            await page_file.safe_write_bytes(content=page_content)
            return page_file

    async def _load_page(
            self,
            page_index: int = 0,
            page_type: 'ArtworkPageParamType' = 'regular',
    ) -> bytes:
        """内部方法, 获取作品资源, 优先从本地缓存资源加载"""
        page_file = await self._save_page(page_index=page_index, page_type=page_type)

        async with page_file.async_open('rb') as af:
            page_content = await af.read()
        return page_content

    async def get_page_bytes(
            self,
            page_index: int = 0,
            page_type: 'ArtworkPageParamType' = 'regular',
    ) -> bytes:
        """获取作品文件内容, 使用本地缓存"""
        return await self._load_page(page_index=page_index, page_type=page_type)

    async def get_page_file(
            self,
            page_index: int = 0,
            page_type: 'ArtworkPageParamType' = 'regular',
    ) -> 'TemporaryResource':
        """获取作品文件资源, 使用本地缓存"""
        return await self._save_page(page_index=page_index, page_type=page_type)

    async def get_all_pages_file(
            self,
            page_limit: int = 10,
            page_type: 'ArtworkPageParamType' = 'regular',
    ) -> list['TemporaryResource']:
        """获取作品所有文件资源列表, 使用本地缓存

        :param page_limit: 返回作品图片最大数量限制, 从第一张图开始计算,
            避免漫画作品等单作品图片数量过多出现问题, 0 为无限制
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

    async def download_page(self, page_index: int = 0) -> 'TemporaryResource':
        """下载作品原图到本地"""
        return await self.get_page_file(page_index=page_index, page_type='original')

    async def download_all_pages(self) -> list['TemporaryResource']:
        """下载作品全部原图到本地"""
        return await self.get_all_pages_file(page_limit=0, page_type='original')

    # ------------------------------------------------------------------ #
    # 作品图片处理和生成相关方法
    # ------------------------------------------------------------------ #

    async def _process_artwork_page(
            self,
            page_index: int = 0,
            *,
            page_type: 'ArtworkPageParamType' = 'regular',
            process_mode: 'ArtworkProcessParamType' = 'mark',
    ) -> 'TemporaryResource':
        """处理作品图片(未知 process_mode 回退为 mark)"""
        artwork_data = await self.query()
        origin_mark = f'{artwork_data.origin.title()} | {artwork_data.aid}'

        page_file = await self.get_page_file(page_index=page_index, page_type=page_type)
        match process_mode:
            case 'noise':
                image = await ArtworkImageOps.handle_noise(image=page_file, origin_mark=origin_mark)
                output_file_name = f'{page_file.stem}_noise_sigma16_marked.jpg'
            case 'blur':
                image = await ArtworkImageOps.handle_blur(image=page_file, origin_mark=origin_mark)
                output_file_name = f'{page_file.stem}_blur_marked.jpg'
            case 'mark' | _:
                image = await ArtworkImageOps.handle_mark(image=page_file, origin_mark=origin_mark)
                output_file_name = f'{page_file.stem}_marked.jpg'

        output_file = self._get_path_config().processed_path(output_file_name)
        return await image.save(file=output_file)

    async def get_custom_proceed_page_file(
            self,
            page_index: int = 0,
            *,
            page_type: 'ArtworkPageParamType' = 'regular',
            process_mode: 'ArtworkProcessParamType' = 'mark',
    ) -> 'TemporaryResource':
        """使用相关方法处理作品图片"""
        return await self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode=process_mode)

    async def get_auto_proceed_page_file(
            self,
            page_index: int = 0,
            *,
            page_type: 'ArtworkPageParamType' = 'regular',
            need_blur_rating: int = 2,
    ) -> 'TemporaryResource':
        """根据作品分级处理作品图片

        :param page_index: 作品图片页码
        :param page_type: 作品图片类型
        :param need_blur_rating: 需要模糊处理的最小分级等级, 默认为 2: QUESTIONABLE
        :return: 处理后的图片文件

        注意: UNKNOWN(-1) 可能为任意分级, 按最严格的模糊(blur)处理, 不得直接视为 G-rated 作品
        """
        need_blur_rating = max(0, need_blur_rating)
        artwork_data = await self.query()

        if artwork_data.rating == ArtworkRating.UNKNOWN:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='blur')
        elif artwork_data.rating == 0:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='mark')
        elif artwork_data.rating < need_blur_rating:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='noise')
        else:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='blur')

        return await process

    async def _get_preview_thumb_data(
            self,
            *,
            page_type: 'ArtworkPageParamType' = 'preview',
            need_blur_rating: int = 2,
    ) -> 'PreviewImageThumbsItem':
        """内部方法, 获取生成预览图所需要的每个小缩略图的数据

        缩略图处理策略类似 get_auto_proceed_page_file 方法,
        为保证显示效果 0 < rating <= need_blur_rating 的图片不再 noise 处理;
        UNKNOWN(-1) 可能为任意分级, 按最严格的模糊(blur)处理, 不得直接视为 G-rated 作品
        """
        need_blur_rating = max(0, need_blur_rating)
        artwork_data = await self.query()

        page_file = await self.get_page_file(page_type=page_type)
        origin_mark = f'{artwork_data.origin.title()} | {artwork_data.aid}'
        if artwork_data.rating == ArtworkRating.UNKNOWN:
            proceed_image = await ArtworkImageOps.handle_blur(image=page_file, origin_mark=origin_mark)
        elif 0 <= artwork_data.rating < need_blur_rating:
            proceed_image = await ArtworkImageOps.handle_mark(image=page_file, origin_mark=origin_mark)
        else:
            proceed_image = await ArtworkImageOps.handle_blur(image=page_file, origin_mark=origin_mark)

        desc_text = await self.get_std_preview_desc()
        thumb_data = await proceed_image.async_get_bytes()

        return PreviewImageThumbsItem(desc_text=desc_text, thumb_data=thumb_data)

    @classmethod
    async def _get_artworks_preview_data(
            cls,
            preview_name: str,
            artworks: Sequence[Self],
            *,
            page_type: 'ArtworkPageParamType' = 'preview',
            need_blur_rating: int = 2,
            limit: int = 100,
    ) -> 'PreviewImagesData':
        """内部方法, 获取生成预览图所需要的所有作品的数据"""
        tasks = [
            artwork._get_preview_thumb_data(page_type=page_type, need_blur_rating=need_blur_rating)
            for artwork in artworks[:limit]
        ]
        thumb_items = list(await semaphore_gather(tasks=tasks, semaphore_num=6, filter_exception=True))
        return PreviewImagesData(preview_name=preview_name, thumb_items=thumb_items)

    @classmethod
    async def generate_artworks_preview(
            cls,
            preview_name: str,
            artworks: Sequence[Self],
            *,
            page_type: 'ArtworkPageParamType' = 'preview',
            need_blur_rating: int = 2,
            preview_size: tuple[int, int] = (256, 256),
            header_color: tuple[int, int, int] = (0, 150, 250),
            edge_scale: float = 1 / 32,
            num_of_line: int = 6,
            limit: int = 100,
    ) -> 'TemporaryResource':
        """生成多个作品的预览图

        :param preview_name: 预览图标题
        :param artworks: 作品列表
        :param page_type: 作品图片类型
        :param need_blur_rating: 需要模糊处理的最小分级等级
        :param preview_size: 单个小缩略图的尺寸, 默认为 256x256
        :param header_color: 页眉装饰色, 默认为 (0, 150, 250)
        :param edge_scale: 缩略图添加白边的比例, 范围 0~1
        :param num_of_line: 生成预览每一行的预览图数
        :param limit: 限制生成时缩略图数量的最大值
        :return: 生成的预览图文件
        """
        preview = await cls._get_artworks_preview_data(
            preview_name=preview_name,
            artworks=artworks,
            page_type=page_type,
            need_blur_rating=need_blur_rating,
            limit=limit,
        )
        path_config = cls._get_path_config()

        return await ArtworkImageOps.generate_preview_image(
            preview=preview,
            preview_size=preview_size,
            font_path=path_config.theme_font,
            output_folder=path_config.preview_path,
            header_color=header_color,
            edge_scale=edge_scale,
            num_of_line=num_of_line,
            limit=limit,
        )

    # ------------------------------------------------------------------ #
    # 内部数据库 (artwork_collection) 查询相关方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _convert_proxy_data_to_add_artwork_params(data: ArtworkProxyData) -> dict[str, Any]:
        return {
            'origin': data.origin,
            'aid': data.aid,
            'uid': data.uid,
            'title': data.title,
            'uname': data.uname,
            'classification': data.classification,
            'rating': data.rating,
            'width': data.width,
            'height': data.height,
            'url': data.source,
            'source': data.source,
            'cover_page': data.cover_page_url,
            'raw_tags': ','.join(data.tags),
            'tag_handler': None,
            'description': data.description,
            'published_at': data.published_at,
        }

    @staticmethod
    async def query_db_any_origin_by_condition(
            keywords: str | Sequence[str] | None,
            origin: str | Sequence[str] | None = None,
            page: int = 1,
            size: int = 3,
            *,
            allow_classification_range: tuple[int, int] | None = None,
            allow_rating_range: tuple[int, int] | None = None,
            acc_mode: bool = False,
            ratio: int | None = None,
            has_review_record: bool | None = None,
            order_mode: Literal['random', 'latest', 'aid', 'aid_desc'] = 'random',
    ) -> list[tuple[str, str]]:
        """从数据库所有或任意指定来源根据要求查询作品

        default classification range: 3~4, default rating range: 0~0
        :return: (origin, artwork_id)
        """
        if isinstance(keywords, str):
            keywords = [keywords]

        if allow_classification_range is None:
            allow_classification_range = (3, 4)

        if allow_rating_range is None:
            allow_rating_range = (0, 0)

        async with ArtworkCollectionDAL.create() as dal:
            result = await dal.query_by_condition(
                origin=origin,
                keywords=keywords,
                page=page,
                size=size,
                classification_min=min(allow_classification_range),
                classification_max=max(allow_classification_range),
                rating_min=min(allow_rating_range),
                rating_max=max(allow_rating_range),
                acc_mode=acc_mode,
                ratio=ratio,
                has_review_record=has_review_record,
                order_mode=order_mode,
            )
        return [(x.origin, x.aid) for x in result]

    @classmethod
    async def query_db_by_condition(
            cls,
            keywords: str | Sequence[str] | None,
            page: int = 1,
            size: int = 3,
            *,
            allow_classification_range: tuple[int, int] | None = None,
            allow_rating_range: tuple[int, int] | None = None,
            acc_mode: bool = False,
            ratio: int | None = None,
            has_review_record: bool | None = None,
            order_mode: Literal['random', 'latest', 'aid', 'aid_desc'] = 'random',
    ) -> list[Self]:
        """从数据库根据要求查询作品

        default classification range: 3~4, default rating range: 0~0
        """
        origin_name = cls._get_base_origin_name()
        result = await cls.query_db_any_origin_by_condition(
            origin=origin_name,
            keywords=keywords,
            page=page,
            size=size,
            allow_classification_range=allow_classification_range,
            allow_rating_range=allow_rating_range,
            acc_mode=acc_mode,
            ratio=ratio,
            has_review_record=has_review_record,
            order_mode=order_mode,
        )
        return [cls(artwork_id=aid) for origin, aid in result if origin == origin_name]

    @classmethod
    async def query_db_random(
            cls,
            num: int = 3,
            *,
            allow_classification_range: tuple[int, int] | None = None,
            allow_rating_range: tuple[int, int] | None = None,
            ratio: int | None = None,
    ) -> list[Self]:
        """从数据库获取随机作品

        default classification range: 3~4, default rating range: 0~0
        """
        return await cls.query_db_by_condition(
            keywords=None,
            page=1,
            size=num,
            ratio=ratio,
            allow_classification_range=allow_classification_range,
            allow_rating_range=allow_rating_range,
        )

    @classmethod
    async def query_db_classification_statistic(
            cls,
            *,
            keywords: str | Sequence[str] | None = None,
    ) -> 'ArtworkClassificationStatistic':
        """查询数据库按分类统计收录作品数"""
        if isinstance(keywords, str):
            keywords = [keywords]

        async with ArtworkCollectionDAL.create() as dal:
            result = await dal.query_classification_statistic(
                origin=cls._get_base_origin_name(),
                keywords=keywords,
            )
        return result

    @classmethod
    async def query_db_rating_statistic(
            cls,
            *,
            keywords: str | Sequence[str] | None = None,
    ) -> 'ArtworkRatingStatistic':
        """查询数据库按分级统计收录作品数"""
        if isinstance(keywords, str):
            keywords = [keywords]

        async with ArtworkCollectionDAL.create() as dal:
            result = await dal.query_rating_statistic(
                origin=cls._get_base_origin_name(),
                keywords=keywords,
            )
        return result

    @classmethod
    async def query_db_user_all_artworks(
            cls,
            uid: str | None = None,
            uname: str | None = None,
    ) -> list[Self]:
        """从数据库通过 uid 或用户名精准查找用户所有作品"""
        async with ArtworkCollectionDAL.create() as dal:
            result = await dal.query_user_all_aids(
                origin=cls._get_base_origin_name(),
                uid=uid,
                uname=uname,
            )
        return [cls(artwork_id=aid) for aid in result]

    @classmethod
    async def query_db_exists_artworks(
            cls,
            aids: Sequence[str],
            *,
            filter_classification: int | Sequence[int] | None = None,
            filter_rating: int | Sequence[int] | None = None,
    ) -> list[Self]:
        """从数据库根据提供的 aids 列表查询数据库中已存在的列表中的作品

        :param aids: 待匹配的作品 artwork_id 清单
        :param filter_classification: 筛选指定的作品分类, 只有该分类的作品都会被视为存在
        :param filter_rating: 筛选指定的作品分级, 只有该分级的作品都会被视为存在
        """
        async with ArtworkCollectionDAL.create() as dal:
            result = await dal.query_exists_aids(
                origin=cls._get_base_origin_name(),
                aids=aids,
                filter_classification=filter_classification,
                filter_rating=filter_rating,
            )
        return [cls(artwork_id=aid) for aid in result]

    @classmethod
    async def query_db_not_exists_artworks(
            cls,
            aids: Sequence[str],
            *,
            exclude_classification: int | Sequence[int] | None = None,
            exclude_rating: int | Sequence[int] | None = None,
    ) -> list[Self]:
        """从数据库根据提供的 aids 列表查询数据库中不存在的列表中的作品

        :param aids: 待匹配的作品 artwork_id 清单
        :param exclude_classification: 排除指定的作品分类, 所有非该分类的作品都会被视为不存在
        :param exclude_rating: 排除指定的作品分级, 所有非该分级的作品都会被视为不存在
        """
        async with ArtworkCollectionDAL.create() as dal:
            result = await dal.query_not_exists_aids(
                origin=cls._get_base_origin_name(),
                aids=aids,
                exclude_classification=exclude_classification,
                exclude_rating=exclude_rating,
            )
        return [cls(artwork_id=aid) for aid in result]

    async def add_and_upgrade_artwork_into_database(
            self,
            *,
            use_cache: bool = True,
            classification: int | None = None,
            rating: int | None = None,
            force_update_cr: bool = False,
    ) -> None:
        """查询图站获取作品元数据, 向数据库新增该作品信息, 若已存在则更新

        :param use_cache: 使用缓存的作品信息
        :param classification: 指定写入的 classification
        :param rating: 指定写入的 rating
        :param force_update_cr: 是否强制更新数据库中存在的 classification 及 rating 标签, 若否则仅大于已有值时更新
        """
        artwork_data = await self.query(use_cache=use_cache)
        classification = classification if (classification is not None) else artwork_data.classification
        rating = rating if (rating is not None) else artwork_data.rating

        add_artwork_params = self._convert_proxy_data_to_add_artwork_params(data=artwork_data)
        add_artwork_params.update({
            'classification': classification,
            'rating': rating,
            'force_update_cr': force_update_cr,
        })

        async with _DATABASE_WRITE_LOCK:
            async with ArtworkCollectionDAL.create() as dal:
                await dal.add_artwork_update_exist(**add_artwork_params)

    async def add_artwork_into_database_ignore_exists(
            self,
            *,
            use_cache: bool = True,
            classification: int | None = None,
            rating: int | None = None,
    ) -> None:
        """查询图站获取作品元数据, 向数据库新增该作品信息, 若已存在忽略

        :param use_cache: 使用缓存的作品信息
        :param classification: 指定写入的 classification
        :param rating: 指定写入的 rating
        """
        artwork_data = await self.query(use_cache=use_cache)
        classification = classification if (classification is not None) else artwork_data.classification
        rating = rating if (rating is not None) else artwork_data.rating

        add_artwork_params = self._convert_proxy_data_to_add_artwork_params(data=artwork_data)
        add_artwork_params.update({
            'classification': classification,
            'rating': rating,
        })

        async with _DATABASE_WRITE_LOCK:
            async with ArtworkCollectionDAL.create() as dal:
                await dal.add_artwork_ignore_exist(**add_artwork_params)

    async def delete_artwork_from_database(self) -> None:
        """从数据库删除该作品信息"""
        async with _DATABASE_WRITE_LOCK:
            async with ArtworkCollectionDAL.create() as dal:
                await dal.delete(origin=self._get_base_origin_name(), aid=self.s_aid)

    async def query_artwork_from_database(self) -> 'Artwork':
        """从数据库查询作品信息

        :raises sqlalchemy.exc.NoResultFound: 数据库中不存在该作品时抛出
        """
        async with ArtworkCollectionDAL.create() as dal:
            artwork = await dal.query_unique(origin=self._get_base_origin_name(), aid=self.s_aid)
        return artwork

    async def add_artwork_review_record_into_database(
            self,
            review_classification: int,
            review_rating: int,
            review_from: str,
            review_info: str,
            record_tag: str | None = None,
    ) -> 'ArtworkReviewRecord':
        """向数据库插入作品评审记录"""
        async with _DATABASE_WRITE_LOCK:
            async with ArtworkCollectionDAL.create() as dal:
                record = await dal.add_artwork_review_record(
                    origin=self._get_base_origin_name(),
                    aid=self.s_aid,
                    review_timestamp=int(time.time()),
                    review_classification=review_classification,
                    review_rating=review_rating,
                    review_from=review_from,
                    review_info=review_info,
                    record_tag=record_tag,
                )
        return record


__all__ = [
    'ArtworkPageParamType',
    'ArtworkProcessParamType',
    'ArtworkRankParamType',
    'BaseArtworkProxy',
]
