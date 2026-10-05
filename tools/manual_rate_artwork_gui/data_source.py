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
from uuid import uuid4

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
        """内部方法, 获取需要导入图库的作品分级元数据, 同一作品以最新一次会话的评级数据为准"""
        # 遍历工作目录获取所有的导入文件, 按路径排序保证从旧到新读取
        import_files = sorted(
            (
                file
                for file in self._output_path.output_dir.iter_all_files()
                if file.name == _IMPORT_META_DATA_FILE_NAME
            ),
            key=lambda x: x.resolve_path,
        )

        import_data: dict[tuple[str, str], CustomImportArtwork] = {}
        for file in import_files:
            async with file.async_open('r', encoding='utf-8') as af:
                for data in parse_json_as(list[CustomImportArtwork], await af.read()):
                    import_data[(data.origin, data.aid)] = data
        return list(import_data.values())

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
            return

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
            self._import_artwork_rating_into_database(import_data=data, need_retry=True, log_index=index)
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
        '_processing',
        '_queue_finished',
        '_select_cancelled',
        '_background_tasks',
    )

    def __init__(self) -> None:
        self._current_source: CurrentArtwork | None = None
        self._current_source_image: ImageTk.PhotoImage | None = None
        self._remaining_source: list[CurrentArtwork] = []
        self._working_path: str | None = None
        self._output_path = OutputPath(self.source_type)
        self._processing: bool = False
        self._queue_finished: bool = False
        self._select_cancelled: bool = False
        self._background_tasks: set[asyncio.Task[None]] = set()

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

    def _spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        """在主线程事件循环中调度异步任务, 供按钮回调等同步入口使用"""

        def _log_task_exception(future: asyncio.Task[None]) -> None:
            self._background_tasks.discard(future)
            if future.cancelled():
                return
            if (exception := future.exception()) is not None:
                logger.error(f'Manual rating task failed, {exception}')

        # 持有任务强引用, 避免事件循环仅存的弱引用导致任务被垃圾回收
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(_log_task_exception)

    def _spawn_exclusive(self, coro: Coroutine[Any, Any, None]) -> None:
        """带互斥保护的异步任务调度, 上一操作未完成时忽略新操作, 防止并发任务竞争队列状态"""
        if self._processing:
            logger.warning('Previous operation is still in progress, ignoring this action')
            return
        self._processing = True

        async def _runner() -> None:
            try:
                await coro
            finally:
                self._processing = False

        self._spawn(_runner())

    @property
    def processing(self) -> bool:
        """是否有互斥操作正在进行"""
        return self._processing

    @property
    def has_pending_tasks(self) -> bool:
        """是否有在途后台任务"""
        return bool(self._background_tasks)

    def cancel_pending_tasks(self) -> None:
        """取消所有在途后台任务"""
        for task in self._background_tasks:
            task.cancel()

    @property
    @abc.abstractmethod
    def _current_artwork_proxy(self) -> 'BaseArtworkProxy':
        """内部属性, 目标作品的 ArtworkProxy 实例"""
        raise NotImplementedError

    @abc.abstractmethod
    async def _load_source(self, source: CurrentArtwork) -> 'SourceOpenFp':
        """内部方法, 异步加载指定作品及其预览图"""
        raise NotImplementedError

    async def _load_source_async(
            self,
            source: CurrentArtwork,
            image_label: 'Label',
            *,
            rs_width: int = 1024,
            rs_height: int = 1024,
    ) -> None:
        """内部方法, 异步加载指定作品及其预览图, 刷新图片控件显示预览图

        以参数传入目标作品而, 由调用方在加载成功后再提交状态, 避免加载失败时界面显示与内部状态错位
        """
        image = Image.open(await self._load_source(source)).convert('RGB')

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

    async def _load_next_async(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """内部方法, 异步加载待处理作品列表中的下一个作品及其预览图, 刷新控件显示预览图"""
        if not self._remaining_source:
            # 队列已空, 当前作品已被处理过, 标记后禁止重复评级
            self._queue_finished = True
            show_current_entry.delete(0, 'end')
            show_current_entry.insert(0, '队列已处理完毕')
            show_remaining_entry.delete(0, 'end')
            show_remaining_entry.insert(0, '0')
            return

        next_source = self._remaining_source.pop(0)
        show_remaining_entry.delete(0, 'end')
        show_remaining_entry.insert(0, str(len(self._remaining_source)))

        try:
            await self._load_source_async(next_source, image_label)
        except Exception as e:
            # 加载失败时跳过该作品并保持当前作品及界面显示不变, 避免对未展示的作品误评级
            logger.error(f'Load artwork(origin={self.source_origin}, aid={next_source.aid}) failed, {e}')
            messagebox.showerror(
                title='作品加载失败',
                message=f'作品 {next_source.aid} 加载失败\n该作品已跳过, 当前作品已保留, 可重新评级或手动跳过',
            )
            return

        # 加载成功后再提交当前作品状态, 保证界面显示与内部状态一致
        self._current_source = next_source
        show_current_entry.delete(0, 'end')
        show_current_entry.insert(0, next_source.source_path)

    def load_next(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """加载待处理作品列表中的下一个作品及其预览图, 刷新控件显示预览图"""
        self._spawn_exclusive(self._load_next_async(image_label, show_current_entry, show_remaining_entry))

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
        # 复位状态标志位, 允许重新初始化新的评级队列
        self._select_cancelled = False
        self._queue_finished = False

        try:
            await self._select_current_source()
            if self._select_cancelled:
                # 用户取消了文件/参数选择, 未初始化
                return
            await self._init_working_path()
            if self._select_cancelled:
                # 用户在初始化过程中(参数输入)取消, 未初始化
                return
        except Exception as e:
            logger.error(f'Initialize artwork source failed, {e}')
            messagebox.showerror(title='初始化失败', message='初始化作品源失败')
            return

        # 清空当前作品, 由 _load_next_async 在加载成功后再提交, 避免未经加载展示的作品被评级
        self._current_source = None
        await self._load_next_async(image_label, show_current_entry, show_remaining_entry)

    def select_current(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        """选择开始时的目标作品, 初始化工作目录, 刷新控件显示预览图"""
        self._spawn_exclusive(self._select_current(image_label, show_current_entry, show_remaining_entry))

    async def _merge_all_output(self) -> None:
        """内部方法, 合并所有人工评级的元数据文件, 生成一个汇总的导入文件"""
        if not self._output_path.import_data_dir.is_dir:
            raise RuntimeError('no rating data to merge')

        import_artworks_data: list[CustomImportArtwork] = []

        # 跳过本会话已生成的汇总文件, 避免重复合并历史汇总数据
        for file in self._output_path.import_data_dir.iter_current_files():
            if file.name == _IMPORT_META_DATA_FILE_NAME:
                continue
            async with file.async_open('r', encoding='utf-8') as af:
                import_artworks_data.append(CustomImportArtwork.model_validate_json(await af.read()))

        # 先写临时文件再原子替换, 避免写入中断残留截断文件
        tmp_file = self._output_path.import_data_file.with_name(
            f'{self._output_path.import_data_file.name}.{uuid4().hex}.tmp'
        )
        async with tmp_file.async_open('w', encoding='utf-8') as af:
            await af.write(dump_json_as(list[CustomImportArtwork], import_artworks_data))
        tmp_file.replace(self._output_path.import_data_file.path)

        logger.info(f'Merge all rating data into {self._output_path.import_data_file.resolve_path}')

    async def _merge_all_output_and_notify(self) -> None:
        """内部方法, 执行合并并根据实际执行结果提示用户"""
        try:
            await self._merge_all_output()
        except Exception as e:
            logger.error(f'Merge rating data failed, {e}')
            messagebox.showerror(
                title='合并生成导入文件失败',
                message='合并生成评级导入文件失败',
            )
        else:
            messagebox.showinfo(
                title='合并生成导入文件完成',
                message=f'已合并生成评级导入文件: {self._output_path.import_data_file.resolve_path}',
            )

    def merge(self) -> None:
        """合并所有人工评级的元数据文件, 生成一个汇总的导入文件"""
        self._spawn(self._merge_all_output_and_notify())

    async def _generate_output(self, rating: int, *, classification: int = 3) -> None:
        """内部方法, 生成人工评级的元数据文件"""
        data = CustomImportArtwork.model_validate({
            'origin': (origin := self.source_origin),
            'aid': (aid := self._current_source.aid),
            'classification': classification,
            'rating': rating,
        })
        import_data_file = self._output_path.import_data_dir(f'{origin}_{aid}.json')

        # 先写临时文件再原子替换, 避免写入中断残留截断文件
        tmp_file = import_data_file.with_name(f'{import_data_file.name}.{uuid4().hex}.tmp')
        async with tmp_file.async_open('w', encoding='utf-8') as af:
            await af.write(data.model_dump_json())
        tmp_file.replace(import_data_file.path)

    async def _set_current(
            self,
            rating: int,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
            *,
            classification: int = 3,
            review_info: str = '人工审核',
            record_tag: str = 'approved',
    ) -> None:
        """内部方法, 设置人工评级, 写入数据库并生成元数据文件"""
        if self._current_source is None:
            logger.warning('No artwork selected, skip setting rating')
            messagebox.showwarning(
                title='无法评级',
                message='尚未选择并加载作品, 请先初始化数据源',
            )
            return
        if self._queue_finished:
            logger.warning('Rating queue is empty, current artwork has already been processed')
            messagebox.showwarning(
                title='无法评级',
                message='评级队列已处理完毕, 请重新初始化数据源',
            )
            return

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
                review_info=review_info,
                record_tag=record_tag,
            )
            # 生成导入元数据
            await self._generate_output(rating=rating, classification=classification)

            logger.opt(colors=True).success(
                f'Set classification=<lc>{classification}</lc> rating=<lc>{rating}</lc> succeed, '
                f'artwork(id={artwork_info.aid}, title={artwork_info.title}, username={artwork_info.uname})'
            )
        except Exception as e:
            # 评级失败时保留当前作品, 不自动前进, 供用户重试或手动跳过
            logger.error(f'Set artwork(id={self._current_source.aid}) rating failed, {e}')
            messagebox.showerror(
                title='评级失败',
                message=f'作品 {self._current_source.aid} 评级失败\n当前作品已保留, 可重试评级或手动跳过',
            )
        else:
            await self._load_next_async(image_label, show_current_entry, show_remaining_entry)

    def set_current_general_c3(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            0, image_label, show_current_entry, show_remaining_entry, classification=3,
        ))

    def set_current_sensitive_c3(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            1, image_label, show_current_entry, show_remaining_entry, classification=3,
        ))

    def set_current_questionable_c3(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            2, image_label, show_current_entry, show_remaining_entry, classification=3,
        ))

    def set_current_explicit_c3(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            3, image_label, show_current_entry, show_remaining_entry, classification=3,
        ))

    def set_current_general_c4(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            0, image_label, show_current_entry, show_remaining_entry, classification=4,
        ))

    def set_current_sensitive_c4(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            1, image_label, show_current_entry, show_remaining_entry, classification=4,
        ))

    def set_current_questionable_c4(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            2, image_label, show_current_entry, show_remaining_entry, classification=4,
        ))

    def set_current_explicit_c4(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            3, image_label, show_current_entry, show_remaining_entry, classification=4,
        ))

    def set_current_reset(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            -1, image_label, show_current_entry, show_remaining_entry,
            classification=0, review_info='人工重置', record_tag='pending',
        ))

    def set_current_ignored(
            self,
            image_label: 'Label',
            show_current_entry: 'Entry',
            show_remaining_entry: 'Entry',
    ) -> None:
        self._spawn_exclusive(self._set_current(
            -1, image_label, show_current_entry, show_remaining_entry,
            classification=-2, review_info='人工忽略', record_tag='rejected',
        ))


__all__ = [
    'ArtworkRatingImportTool',
    'BaseArtworkSource',
]
