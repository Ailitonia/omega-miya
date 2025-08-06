"""
@Author         : Ailitonia
@Date           : 2024/9/9 23:21
@FileName       : data_source
@Project        : ailitonia-toolkit
@Description    :
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import asyncio
import inspect
import re
import threading
from collections.abc import Callable, Coroutine
from datetime import datetime
from functools import wraps
from tkinter import Tk, filedialog, simpledialog
from typing import IO, TYPE_CHECKING, Any, Self, cast

from PIL import Image, ImageTk
from nonebot.log import logger
from pydantic import BaseModel, ConfigDict

from src.compat import dump_json_as, parse_json_as
from src.resource import AnyResource, TemporaryResource
from src.service.artwork_collection import PixivArtworkCollection
from .model import CustomImportArtwork

if TYPE_CHECKING:
    from os import PathLike
    from tkinter.ttk import Entry, Label

    from src.database.internal.artwork_collection import ArtworkCollection as DBArtworkCollection

type SourceOpenFp = str | bytes | PathLike[str] | IO[bytes]


class OutputPath:
    TMP_DIR = TemporaryResource('manual_rate_pixiv_artwork')

    def __init__(self, working_name: str):
        self._working_timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        self._output_dir = self.TMP_DIR(working_name)

    @property
    def output_dir(self) -> TemporaryResource:
        return self._output_dir(self._working_timestamp)

    @property
    def cache_dir(self) -> TemporaryResource:
        return self._output_dir('working_dir_cache')

    @property
    def import_data_file(self) -> TemporaryResource:
        return self.output_dir('custom_import_collected_artworks.json')


class CurrentArtwork(BaseModel):
    """当前进行分级的作品"""
    pid: int
    source_path: str

    model_config = ConfigDict(extra='ignore', from_attributes=True, frozen=True, coerce_numbers_to_str=True)


class BasePixivArtworkSource(abc.ABC):
    """待分级作品源基类"""

    __slots__ = (
        '_async_loop',
        '_current_source',
        '_current_source_image',
        '_remaining_source',
        '_working_path',
        '_output_path',
    )

    if TYPE_CHECKING:
        _current_source: CurrentArtwork
        _remaining_source: list[CurrentArtwork]
        _working_path: str

    def __init__(self) -> None:
        self._async_loop = asyncio.new_event_loop()
        self._remaining_source = []
        self._output_path = OutputPath(self.source_type)

    @property
    @abc.abstractmethod
    def source_type(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def title_name(self) -> str:
        raise NotImplementedError

    @property
    def current_source_path(self) -> str:
        return self._current_source.source_path

    @property
    def working_path(self) -> str:
        return self._working_path

    @staticmethod
    def _run_in_async_event_loop[** P, T](func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, None]:
        """装饰一个异步方法, 使其在 async event loop 中执行"""
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f'{func.__name__} is not coroutine function')

        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs):
            self: Self = cast(Self, args[0])
            coro = func(*args, **kwargs)

            if self._async_loop.is_running():
                self._async_loop.create_task(coro=coro)
            else:
                threading.Thread(target=self._async_loop.run_until_complete, args=(coro,)).start()

        return _wrapper

    @abc.abstractmethod
    async def _load_current_source(self) -> SourceOpenFp:
        """内部方法, 加载目标作品图片"""
        raise NotImplementedError

    async def _load_current(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
            *,
            rs_width: int = 1024,
            rs_height: int = 768,
    ) -> None:
        """内部方法, 加载的目标作品图片并在控件上显示"""
        image = Image.open(await self._load_current_source()).convert('RGB')

        width, height = image.size
        scale = min(rs_width / width, rs_height / height)
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        box = (int(abs(width * scale - rs_width) / 2), int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode='RGB', size=(rs_width, rs_height), color=(0, 0, 0))
        background.paste(image, box=box)

        self._current_source_image = ImageTk.PhotoImage(background)
        image_label.config(image=self._current_source_image)  # type: ignore

        image.close()
        background.close()

        show_current_entry.delete(0, 'end')
        show_current_entry.insert(0, self._current_source.source_path)
        show_remaining_entry.delete(0, 'end')
        show_remaining_entry.insert(0, str(len(self._remaining_source)))

    @_run_in_async_event_loop
    async def load_current(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
            *,
            rs_width: int = 1024,
            rs_height: int = 768,
    ) -> None:
        """加载的目标作品图片并在控件上显示, 同时可用于立即刷新图片控件"""
        await self._load_current(
            image_label, show_current_entry, show_remaining_entry, rs_width=rs_width, rs_height=rs_height
        )

    @abc.abstractmethod
    async def _select_current_source(self) -> None:
        """内部方法, 选择开始时的目标作品"""
        raise NotImplementedError

    @abc.abstractmethod
    async def _init_working_path(self) -> None:
        """内部方法, 初始化工作路径, 预处理和缓存待处理作品列表"""
        raise NotImplementedError

    @_run_in_async_event_loop
    async def _select_current(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """选择开始时的目标作品, 初始化工作目录"""
        await self._select_current_source()
        await self._init_working_path()
        await self.next_image_async(image_label, show_current_entry, show_remaining_entry)

    def select_current(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """选择开始时的目标作品, 初始化工作目录, 并在输出控件中显示作品位置"""
        self._select_current(image_label, show_current_entry, show_remaining_entry)

    async def next_image_async(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """异步加载待处理作品列表中的下一个作品, 刷新控件显示"""
        if self._remaining_source:
            self._current_source = self._remaining_source.pop(0)
        await self._load_current(image_label, show_current_entry, show_remaining_entry)

    def next_image(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """加载待处理作品列表中的下一个作品, 刷新控件显示"""
        if self._remaining_source:
            self._current_source = self._remaining_source.pop(0)
        self.load_current(image_label, show_current_entry, show_remaining_entry)

    @_run_in_async_event_loop
    async def _merge_all_output(self) -> None:
        import_artworks_data: list[CustomImportArtwork] = []

        for file in self._output_path.output_dir.list_current_files():
            async with file.async_open('r', encoding='utf-8') as af:
                import_artworks_data.append(CustomImportArtwork.model_validate_json(await af.read()))

        async with self._output_path.import_data_file.async_open('w', encoding='utf-8') as af:
            await af.write(dump_json_as(list[CustomImportArtwork], import_artworks_data))

    def merge(self) -> None:
        self._merge_all_output()
        logger.info(f'Merge all rating data into {self._output_path.import_data_file.resolve_path}')

    async def _generate_output(self, rating: int, *, classification: int = 3) -> None:
        aid = str(self._current_source.pid)
        data = CustomImportArtwork(origin='pixiv', classification=classification, aid=aid, rating=rating)
        async with self._output_path.output_dir(f'{aid}.json').async_open('w', encoding='utf-8') as af:
            await af.write(data.model_dump_json())

    @_run_in_async_event_loop
    async def _set_current(
            self,
            rating: int,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
            *,
            classification: int = 3,
    ) -> None:
        aid = str(self._current_source.pid)
        try:
            artwork = PixivArtworkCollection(artwork_id=aid)
            artwork_info = await artwork.artwork_proxy.query()

            rating = 3 if artwork_info.rating == 3 else rating
            classification = 1 if artwork_info.classification == 1 else classification

            await artwork.add_and_upgrade_artwork_into_database(
                classification=classification, rating=rating, force_update_mark=True
            )
            await self._generate_output(rating=rating, classification=classification)

            logger.opt(colors=True).success(
                f'Set classification=<lc>{classification}</lc> rating=<lc>{rating}</lc> succeed, '
                f'artwork(id={aid}, title={artwork_info.title}, username={artwork_info.uname})'
            )
        except Exception as e:
            logger.error(f'Set artwork(id={aid}) rating failed, {repr(e)}')
        finally:
            await self.next_image_async(image_label, show_current_entry, show_remaining_entry)

    def set_current_general(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._set_current(0, image_label, show_current_entry, show_remaining_entry)

    def set_current_sensitive(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._set_current(1, image_label, show_current_entry, show_remaining_entry)

    def set_current_questionable(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._set_current(2, image_label, show_current_entry, show_remaining_entry)

    def set_current_explicit(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._set_current(3, image_label, show_current_entry, show_remaining_entry)

    def set_current_reset(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._set_current(-1, image_label, show_current_entry, show_remaining_entry, classification=0)

    def set_current_ignored(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._set_current(-1, image_label, show_current_entry, show_remaining_entry, classification=-2)


class LocalPixivArtworkSource(BasePixivArtworkSource):
    """本地图片"""

    @property
    def source_type(self) -> str:
        return 'local_pixiv_image'

    @property
    def title_name(self) -> str:
        return '本地图片'

    async def _load_current_source(self) -> SourceOpenFp:
        return self._current_source.source_path

    async def _select_current_source(self) -> None:
        current_file = AnyResource(filedialog.askopenfilename())
        self._current_source = CurrentArtwork.model_validate({
            'pid': current_file.name.split('_')[0],
            'source_path': current_file.resolve_path,
        })
        self._working_path = current_file.parent.resolve_path

    async def _init_working_path(self) -> None:
        working_dir = AnyResource(self._working_path)

        # 文件列表缓存
        working_dir_all_files_cache = self._output_path.cache_dir(
            f'{working_dir.parent.name}-{working_dir.name}.txt'
        )

        # 加载文件列表缓存
        if working_dir_all_files_cache.is_file:
            async with working_dir_all_files_cache.async_open('r', encoding='utf-8') as af:
                cache_files = parse_json_as(list[CurrentArtwork], await af.read())
            working_dir_all_files = sorted(
                (x for x in cache_files if x.pid >= self._current_source.pid),
                key=lambda x: x.pid
            )
            logger.info(f'发现目录缓存, 已载入, 共计 {len(cache_files)}, 剩余待处理 {len(working_dir_all_files)}')
        else:
            exists_files = sorted(
                (
                    CurrentArtwork.model_validate({
                        'pid': x.name.split('_')[0],
                        'source_path': x.resolve_path,
                    })
                    for x in working_dir.list_current_files()
                    if re.match(r'^\d+?_p0\d*?\.(jpg|jpeg|png|JPG|JPEG|PNG)$', x.name)
                ),
                key=lambda x: x.pid
            )
            working_dir_all_files = sorted(
                (x for x in exists_files if x.pid >= self._current_source.pid),
                key=lambda x: x.pid
            )
            logger.info(f'已筛选目录作品文件, 共计 {len(exists_files)}, 剩余待处理 {len(working_dir_all_files)}')

        self._remaining_source = working_dir_all_files

        # 保存文件清单缓存
        async with working_dir_all_files_cache.async_open('w', encoding='utf-8') as af:
            await af.write(dump_json_as(list[CurrentArtwork], self._remaining_source))


class BaseDatabasePixivArtworkSource(BasePixivArtworkSource, abc.ABC):
    """从数据中获取作品方法基类"""

    @property
    def source_type(self) -> str:
        return 'database_pixiv_artwork'

    @abc.abstractmethod
    async def query_some_artworks_from_database(self) -> list['DBArtworkCollection']:
        """从数据库中获取作品的条件方法"""
        raise NotImplementedError

    async def _load_current_source(self) -> SourceOpenFp:
        logger.info(f'获取作品 {self._current_source.pid} 图片中, 请稍候')
        file = await PixivArtworkCollection(artwork_id=self._current_source.pid).artwork_proxy.get_page_file()
        return file.resolve_path

    async def _select_current_source(self) -> None:
        pass

    async def _init_working_path(self) -> None:
        artworks = await self.query_some_artworks_from_database()
        logger.info(f'已从数据中获取作品 {len(artworks)} 个, 正在初始化处理队列')

        self._remaining_source = sorted(
            (
                CurrentArtwork.model_validate({
                    'pid': x.aid,
                    'source_path': x.cover_page,
                })
                for x in artworks
            ),
            key=lambda x: x.pid,
            reverse=True
        )


class NonRatingPixivArtworkSource(BaseDatabasePixivArtworkSource):
    """从数据中获取尚未分级的作品作品"""

    @property
    def title_name(self) -> str:
        return '数据库中未分级作品'

    async def query_some_artworks_from_database(self) -> list['DBArtworkCollection']:
        return await PixivArtworkCollection.query_by_condition(
            keywords=None, num=200,
            allow_classification_range=(-1, 0), allow_rating_range=(-1, 3),
            order_mode='aid_desc',
        )


class BaseCustomPixivArtworkSource(BasePixivArtworkSource, abc.ABC):
    """自定义任意处理作品方法基类"""

    @property
    def source_type(self) -> str:
        return 'custom_pixiv_artwork'

    @abc.abstractmethod
    async def query_some_artworks(self) -> list[int]:
        """自定义获取作品 ID 的条件方法"""
        raise NotImplementedError

    async def _load_current_source(self) -> SourceOpenFp:
        logger.info(f'获取作品 {self._current_source.pid} 图片中, 请稍候')
        file = await PixivArtworkCollection(artwork_id=self._current_source.pid).artwork_proxy.get_page_file()
        return file.resolve_path

    async def _select_current_source(self) -> None:
        pass

    async def _init_working_path(self) -> None:
        artworks = await self.query_some_artworks()
        logger.info(f'已从自定义来源获取作品 {len(artworks)} 个, 正在初始化处理队列')

        self._remaining_source = sorted(
            (
                CurrentArtwork.model_validate({
                    'pid': x,
                    'source_path': f'https://www.pixiv.net/artworks/{x}',
                })
                for x in artworks
            ),
            key=lambda x: x.pid,
            reverse=True
        )


class RecommendPixivArtworkSource(BaseCustomPixivArtworkSource):
    """Pixiv 首页推荐作品"""

    @property
    def title_name(self) -> str:
        return 'Pixiv 首页推荐作品'

    async def query_some_artworks(self) -> list[int]:
        from src.utils.pixiv_api.pixiv import PixivCommon

        logger.info('正在从 Pixiv 发现/推荐获取作品来源, 请稍候')
        discovery_result = await PixivCommon.query_discovery_artworks()
        top_result = await PixivCommon.query_top_illust()
        aids = [str(x) for x in (discovery_result.recommend_pids + top_result.recommend_pids)]

        return [int(x) for x in await PixivArtworkCollection.query_not_exists_aids(aids, exclude_classification=3)]


class ArtworkRecommendPixivArtworkSource(BaseCustomPixivArtworkSource):
    """Pixiv 作品相关推荐作品"""

    @property
    def title_name(self) -> str:
        return 'Pixiv 作品相关推荐作品'

    @staticmethod
    def _ask_pid() -> int:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        pid = simpledialog.askinteger('目标作品', '请输入想要获取相关推荐的作品 PID', parent=tmp_root)
        while pid is None:
            pid = simpledialog.askinteger('目标作品', 'PID 不能为空, 请输入想要获取相关推荐的作品 PID', parent=tmp_root)

        tmp_root.destroy()
        return pid

    async def query_some_artworks(self) -> list[int]:
        from src.utils.pixiv_api.pixiv import PixivArtwork

        pid = self._ask_pid()

        logger.info(f'正在从获取作品 {pid} 相关推荐, 请稍候')
        recommend_result = await PixivArtwork(pid=pid).query_recommend(init_limit=100)
        aids = [str(x.id) for x in recommend_result.illusts]

        return [int(x) for x in await PixivArtworkCollection.query_not_exists_aids(aids, exclude_classification=3)]


class SearchPopularPixivArtworkSource(BaseCustomPixivArtworkSource):
    """Pixiv 搜索作品"""

    @property
    def title_name(self) -> str:
        return 'Pixiv 搜索'

    @staticmethod
    def _ask_keyword() -> str:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        keyword = simpledialog.askstring('搜索关键词', '请输入搜索关键词', parent=tmp_root)
        while keyword is None:
            keyword = simpledialog.askstring('搜索关键词', '关键词不能为空, 请输入搜索关键词', parent=tmp_root)

        tmp_root.destroy()
        return keyword

    @staticmethod
    def _ask_page() -> int:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        page = simpledialog.askinteger('页码', '请输入请求的搜索结果页码', parent=tmp_root)
        page = 1 if page is None else page

        tmp_root.destroy()
        return page

    async def query_some_artworks(self) -> list[int]:
        from src.utils.pixiv_api.pixiv import PixivArtwork

        keyword = self._ask_keyword()
        page = self._ask_page()

        logger.info(f'正在从 {keyword!r} 搜索结果 Page-{page} 获取作品信息, 请稍候')
        search_result = await PixivArtwork.search_by_default_popular_condition(word=keyword, page=page)
        aids = [str(x.id) for x in search_result.searching_result]

        return [int(x) for x in await PixivArtworkCollection.query_not_exists_aids(aids, exclude_classification=3)]


__all__ = [
    'BasePixivArtworkSource',
    'LocalPixivArtworkSource',
    'NonRatingPixivArtworkSource',
    'RecommendPixivArtworkSource',
    'ArtworkRecommendPixivArtworkSource',
    'SearchPopularPixivArtworkSource',
]
