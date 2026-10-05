"""
@Author         : Ailitonia
@Date           : 2024/9/9 23:21
@FileName       : data_source
@Project        : omega-miya
@Description    : 作品数据源基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import asyncio
from collections.abc import Coroutine
from datetime import datetime
from tkinter import messagebox
from typing import IO, TYPE_CHECKING, Any

from PIL import Image, ImageTk
from nonebot.log import logger

from src.compat import dump_json_as, parse_json_as
from src.resource import TemporaryResource
from .model import CurrentArtwork, CustomImportArtwork

if TYPE_CHECKING:
    from os import PathLike
    from tkinter.ttk import Entry, Label
    from src.service.artwork_proxy.internal import BaseArtworkProxy

    type SourceOpenFp = str | bytes | PathLike[str] | IO[bytes]

_TOOL_TMP_DIR: TemporaryResource = TemporaryResource('omega_tools_manual_rate_artwork')
"""工具缓存文件夹路径"""
_IMPORT_META_DATA_FILE_NAME: str = 'artwork_collection_manual_rating_meta_for_import.json'
"""人工评级元数据导入文件名"""


class OutputPath:
    """缓存文件路径"""

    def __init__(self, working_name: str):
        self._working_timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        self._working_root_dir = _TOOL_TMP_DIR(working_name)

    @property
    def output_dir(self) -> TemporaryResource:
        return self._working_root_dir('output')

    @property
    def cache_dir(self) -> TemporaryResource:
        return self._working_root_dir('working_dir_cache')

    @property
    def import_data_dir(self) -> TemporaryResource:
        return self.output_dir(self._working_timestamp)

    @property
    def import_data_file(self) -> TemporaryResource:
        return self.import_data_dir(_IMPORT_META_DATA_FILE_NAME)


class ArtworkRatingImportTool:
    """作品分级元数据导入工具"""
    __slots__ = (
        '_output_path',
    )

    if TYPE_CHECKING:
        _output_path: OutputPath

    def __init__(self, source_type: str) -> None:
        self._output_path = OutputPath(source_type)

    async def _get_import_artworks_rating_meta_from_file(self) -> list[CustomImportArtwork]:
        """获取需要导入图库的作品分级元数据"""
        import_data: list[CustomImportArtwork] = []
        # 遍历工作目录获取所有的导入文件
        for file in self._output_path.output_dir.iter_all_files():
            if file.name == _IMPORT_META_DATA_FILE_NAME:
                async with file.async_open('r', encoding='utf-8') as af:
                    import_data.extend(parse_json_as(list[CustomImportArtwork], await af.read()))
        return import_data

    async def _import_artwork_rating_into_database(
            self,
            import_data: CustomImportArtwork,
            *,
            need_retry: bool = False,
            log_index: int = -1,
    ) -> None:
        """内部方法, 导入图库的作品分级元数据, 自动重试"""
        from src.exception import WebSourceException
        from src.service.artwork_proxy import get_artwork_proxy

        try:
            artwork = get_artwork_proxy(import_data.origin)(artwork_id=import_data.aid)
            artwork_info = await artwork.query()

            rating = max(import_data.rating, artwork_info.rating)
            classification = 1 if artwork_info.classification == 1 else import_data.classification

            # 更新数据库作品条目信息
            await artwork.add_and_upgrade_artwork_into_database(
                classification=classification,
                rating=rating,
                force_update_cr=True,
            )
        except WebSourceException as e:
            # 网络问题有可能是风控/限流, 小概率是作品已经被删除
            if e.status_code == 404 or not need_retry:
                raise e

            logger.warning(
                f'Query {import_data.origin}-{import_data.aid} data failed and will retry after 60s, {e}'
            )
            await asyncio.sleep(60)
            await self._import_artwork_rating_into_database(import_data, need_retry=False, log_index=log_index)

        logger.debug(f'Import artworks {import_data} rating succeed, index: {log_index}')

    async def import_artwork_rating_into_database(self) -> None:
        """导入图库的作品分级元数据"""
        from src.utils import semaphore_gather

        try:
            import_data = await self._get_import_artworks_rating_meta_from_file()
            total = len(import_data)
            logger.info(f'Parsing artworks import rating data completed, total: {total}')
        except Exception as e:
            logger.error(f'Parsing artworks import rating data failed, {e}')
            raise e

        import_tasks = [
            self._import_artwork_rating_into_database(import_data=data, log_index=index)
            for index, data in enumerate(import_data)
        ]
        result = await semaphore_gather(
            tasks=import_tasks, semaphore_num=8, return_exceptions=True, filter_exception=True
        )

        logger.success(f'Import artworks rating data completed, total: {total}, succeed: {len(result)}')


class BaseArtworkSource(abc.ABC):
    """待分级作品源基类"""

    __slots__ = (
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
        self._remaining_source: list[CurrentArtwork] = []
        self._output_path = OutputPath(self.source_type)

    @property
    @abc.abstractmethod
    def source_type(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def source_origin(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def title_name(self) -> str:
        raise NotImplementedError

    @staticmethod
    def _spawn(coro: Coroutine[Any, Any, None]) -> None:
        """在主线程事件循环中调度异步任务, 供按钮回调等同步入口使用"""

        def _log_task_exception(future: asyncio.Task[None]) -> None:
            if future.cancelled():
                return
            if (exception := future.exception()) is not None:
                logger.error(f'Manual rating task failed, {exception!r}')

        asyncio.create_task(coro).add_done_callback(_log_task_exception)

    @property
    @abc.abstractmethod
    def _current_artwork_proxy(self) -> 'BaseArtworkProxy':
        """内部属性, 目标作品的 ArtworkProxy 实例"""
        raise NotImplementedError

    @abc.abstractmethod
    async def _load_current_source(self) -> 'SourceOpenFp':
        """内部方法, 异步加载目标作品及其预览图"""
        # load from `self._current_source`
        raise NotImplementedError

    async def _load_current_async(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
            *,
            rs_width: int = 1024,
            rs_height: int = 1024,
    ) -> None:
        """内部方法, 异步加载目标作品及其预览图, 刷新控件显示预览图"""
        image = Image.open(await self._load_current_source()).convert('RGB')

        # 缩放图片到固定尺寸
        width, height = image.size
        scale = min(rs_width / width, rs_height / height)
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        box = (int(abs(width * scale - rs_width) / 2), int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode='RGB', size=(rs_width, rs_height), color=(0, 0, 0))
        background.paste(image, box=box)

        # 更新控件显示作品预览图
        self._current_source_image = ImageTk.PhotoImage(background)
        image_label.config(image=self._current_source_image)

        # 清理 Image 对象
        image.close()
        background.close()
        del image
        del background

        # 更新顶部控件状态显示
        show_current_entry.delete(0, 'end')
        show_current_entry.insert(0, self._current_source.source_path)
        show_remaining_entry.delete(0, 'end')
        show_remaining_entry.insert(0, str(len(self._remaining_source)))

    async def _load_next_async(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """内部方法, 异步加载待处理作品列表中的下一个作品及其预览图, 刷新控件显示预览图"""
        if self._remaining_source:
            self._current_source = self._remaining_source.pop(0)
        await self._load_current_async(image_label, show_current_entry, show_remaining_entry)

    def load_next(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """加载待处理作品列表中的下一个作品及其预览图, 刷新控件显示预览图"""
        self._spawn(self._load_next_async(image_label, show_current_entry, show_remaining_entry))

    @abc.abstractmethod
    async def _select_current_source(self) -> None:
        """内部方法, 选择开始时的目标作品"""
        # self._current_source = ...
        # self._working_path = ...
        raise NotImplementedError

    @abc.abstractmethod
    async def _init_working_path(self) -> None:
        """内部方法, 初始化工作路径, 预处理和缓存待处理作品列表"""
        # self._remaining_source = ...
        raise NotImplementedError

    async def _select_current(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """内部方法, 选择开始时的目标作品, 初始化工作目录, 刷新控件显示预览图"""
        await self._select_current_source()
        await self._init_working_path()
        await self._load_next_async(image_label, show_current_entry, show_remaining_entry)

    def select_current(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """选择开始时的目标作品, 初始化工作目录, 刷新控件显示预览图"""
        self._spawn(self._select_current(image_label, show_current_entry, show_remaining_entry))

    async def _merge_all_output(self) -> None:
        """内部方法, 合并所有人工评级的元数据文件, 生成一个汇总的导入文件"""
        import_artworks_data: list[CustomImportArtwork] = []

        for file in self._output_path.import_data_dir.iter_current_files():
            async with file.async_open('r', encoding='utf-8') as af:
                import_artworks_data.append(CustomImportArtwork.model_validate_json(await af.read()))

        async with self._output_path.import_data_file.async_open('w', encoding='utf-8') as af:
            await af.write(dump_json_as(list[CustomImportArtwork], import_artworks_data))

        logger.info(f'Merge all rating data into {self._output_path.import_data_file.resolve_path}')

    def merge(self) -> None:
        """合并所有人工评级的元数据文件, 生成一个汇总的导入文件"""
        self._spawn(self._merge_all_output())
        messagebox.showinfo(
            title='合并生成导入文件完成',
            message='已合并生成评级导入文件, 文件路径详见日志',
        )

    async def _generate_output(self, rating: int, *, classification: int = 3) -> None:
        """内部方法, 生成人工评级的元数据文件"""
        data = CustomImportArtwork.model_validate({
            'origin': (origin := self.source_origin),
            'aid': (aid := self._current_source.aid),
            'classification': classification,
            'rating': rating,
        })
        import_data_file = self._output_path.import_data_dir(f'{origin}_{aid}.json')
        async with import_data_file.async_open('w', encoding='utf-8') as af:
            await af.write(data.model_dump_json())

    async def _set_current(
            self,
            rating: int,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
            *,
            classification: int = 3,
    ) -> None:
        """内部方法, 设置人工评级, 写入数据库并生成元数据文件"""
        try:
            artwork = self._current_artwork_proxy
            artwork_info = await artwork.query()

            rating = max(rating, artwork_info.rating)
            classification = 1 if artwork_info.classification == 1 else classification

            # 更新数据库作品条目信息
            await artwork.add_and_upgrade_artwork_into_database(
                classification=classification,
                rating=rating,
                force_update_cr=True,
            )
            # 添加评审记录
            await artwork.add_artwork_review_record_into_database(
                review_classification=classification,
                review_rating=rating,
                review_from=f'GUI-{self.source_type}',
                review_info='人工审核',
                record_tag='approved',
            )
            # 生成导入元数据
            await self._generate_output(rating=rating, classification=classification)

            logger.opt(colors=True).success(
                f'Set classification=<lc>{classification}</lc> rating=<lc>{rating}</lc> succeed, '
                f'artwork(id={artwork_info.aid}, title={artwork_info.title}, username={artwork_info.uname})'
            )
        except Exception as e:
            logger.error(f'Set artwork(id={self._current_source.aid}) rating failed, {e}')
        finally:
            await self._load_next_async(image_label, show_current_entry, show_remaining_entry)

    def set_current_general_c3(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            0, image_label, show_current_entry, show_remaining_entry, classification=3,
        ))

    def set_current_sensitive_c3(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            1, image_label, show_current_entry, show_remaining_entry, classification=3,
        ))

    def set_current_questionable_c3(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            2, image_label, show_current_entry, show_remaining_entry, classification=3,
        ))

    def set_current_explicit_c3(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            3, image_label, show_current_entry, show_remaining_entry, classification=3,
        ))

    def set_current_general_c4(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            0, image_label, show_current_entry, show_remaining_entry, classification=4,
        ))

    def set_current_sensitive_c4(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            1, image_label, show_current_entry, show_remaining_entry, classification=4,
        ))

    def set_current_questionable_c4(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            2, image_label, show_current_entry, show_remaining_entry, classification=4,
        ))

    def set_current_explicit_c4(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            3, image_label, show_current_entry, show_remaining_entry, classification=4,
        ))

    def set_current_reset(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            -1, image_label, show_current_entry, show_remaining_entry, classification=0
        ))

    def set_current_ignored(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn(self._set_current(
            -1, image_label, show_current_entry, show_remaining_entry, classification=-2
        ))


__all__ = [
    'ArtworkRatingImportTool',
    'BaseArtworkSource',
]
