"""
@Author         : Ailitonia
@Date           : 2026/10/4 23:14
@FileName       : pixiv
@Project        : omega-miya
@Description    : pixiv 数据源
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import hashlib
import re
from tkinter import Tk, filedialog, messagebox, simpledialog
from typing import TYPE_CHECKING

from nonebot.log import logger
from pydantic import ValidationError

from src.compat import dump_json_as, parse_json_as
from src.resource import AnyResource
from src.service.artwork_proxy import PixivArtworkProxy
from ..data_source import BaseArtworkSource, SourceOpenFp
from ..model import CurrentArtwork

if TYPE_CHECKING:
    from src.service.artwork_proxy.internal import BaseArtworkProxy

_PIXIV_FILE_NAME_PATTERN: re.Pattern[str] = re.compile(r'^(\d+)(?=[_-])')
"""pixiv 作品文件命名规范(数字 ID 开头)"""


class PixivLocalArtworkFileSource(BaseArtworkSource):
    """Pixiv 已下载本地图片"""

    @property
    def source_type(self) -> str:
        return 'local_pixiv_image'

    @property
    def source_origin(self) -> str:
        return 'pixiv'

    @property
    def title_name(self) -> str:
        return '本地图片'

    @property
    def _current_artwork_proxy(self) -> 'BaseArtworkProxy':
        # 由 _set_current 保证调用时当前作品已加载展示
        assert self._current_source is not None
        return PixivArtworkProxy(artwork_id=self._current_source.aid)

    async def _load_source(self, source: CurrentArtwork) -> 'SourceOpenFp':
        return source.source_path

    async def _select_current_source(self) -> None:
        file_name = filedialog.askopenfilename()
        if not file_name:
            # 用户取消了文件选择
            logger.info('No file selected, cancelled initializing local artwork source')
            self._select_cancelled = True
            return

        current_file = AnyResource(file_name)
        if not re.match(_PIXIV_FILE_NAME_PATTERN, current_file.name):
            # 所选文件不符合 pixiv 作品文件命名规范(数字 ID 开头), 无法解析作品 ID
            logger.error(f'Invalid artwork file name: {current_file.name}')
            messagebox.showerror(
                title='文件选择无效',
                message=f'所选文件 {current_file.name} 不符合 Pixiv 作品文件命名规范(数字 ID 开头), 无法解析作品 ID',
            )
            self._select_cancelled = True
            return

        # 写入初始化锚点而非当前作品, 锚点仅在本次初始化中用于过滤队列起始位置,
        # 与当前已展示作品(_current_source)语义分离, 避免初始化失败时误评级未展示的作品
        self._anchor_source = CurrentArtwork.model_validate({
            'aid': current_file.name.split('_')[0].split('-')[0],
            'source_path': current_file.resolve_path,
        })
        self._working_path = current_file.parent.resolve_path

    async def _init_working_path(self) -> None:
        # 初始化锚点及工作路径由 _select_current_source 写入, 仅在本初始化流程内使用
        assert self._anchor_source is not None
        assert self._working_path is not None
        working_dir = AnyResource(self._working_path)
        working_dir_hash = hashlib.sha256(working_dir.resolve_path.encode('utf-8')).hexdigest()[:16]

        # 文件列表缓存
        working_dir_all_files_cache = self._output_path.cache_dir(
            f'working_files_cache_{working_dir.name}_{working_dir_hash}.json'
        )

        exists_files: list[CurrentArtwork] = []
        if working_dir_all_files_cache.is_file:
            # 若存在文件列表缓存, 则加载文件列表缓存
            try:
                async with working_dir_all_files_cache.async_open('r', encoding='utf-8') as af:
                    exists_files = parse_json_as(list[CurrentArtwork], await af.read())
            except (ValidationError, OSError, UnicodeDecodeError) as e:
                # 缓存损坏(如写入中断残留的截断文件), 移除缓存并回退到重新扫描目录
                logger.warning(f'Load working directory files cache failed, fallback to rescan, {e}')
                working_dir_all_files_cache.remove(missing_ok=True)
            else:
                logger.info(f'发现目录缓存, 已载入, 共计 {len(exists_files)}')

        if not exists_files:
            # 无可用缓存或缓存为空, 扫描工作目录并初始化文件列表
            exists_files = sorted(
                (
                    CurrentArtwork.model_validate({
                        'aid': x.name.split('_')[0].split('-')[0],
                        'source_path': x.resolve_path,
                    })
                    for x in working_dir.iter_current_files()
                    if re.match(_PIXIV_FILE_NAME_PATTERN, x.name)
                ),
                key=lambda x: int(x.aid),
            )
            logger.info(f'已载入目录作品文件, 共计 {len(exists_files)}')

            # 保存目录缓存(缓存全量扫描结果, 载入时再按起始作品过滤, 避免历史作品被排除)
            await working_dir_all_files_cache.safe_write_text(
                dump_json_as(list[CurrentArtwork], exists_files),
                encoding='utf-8',
            )

        current_id = int(self._anchor_source.aid)
        self._remaining_source = sorted(
            (x for x in exists_files if int(x.aid) >= current_id),
            key=lambda x: int(x.aid),
        )
        logger.info(f'剩余待处理 {len(self._remaining_source)}')


class _PixivPoolArtworkSource(BaseArtworkSource, abc.ABC):
    """Pixiv 图集类型图片源"""

    @property
    def source_origin(self) -> str:
        return 'pixiv'

    @property
    def _current_artwork_proxy(self) -> 'BaseArtworkProxy':
        # 由 _set_current 保证调用时当前作品已加载展示
        assert self._current_source is not None
        return PixivArtworkProxy(artwork_id=self._current_source.aid)

    @abc.abstractmethod
    async def query_pool_artworks(self) -> list[str]:
        """获取图集中作品 ID 序列"""
        raise NotImplementedError

    async def _load_source(self, source: CurrentArtwork) -> 'SourceOpenFp':
        logger.info(f'获取作品 {source.aid} 图片中, 请稍候')
        file = await PixivArtworkProxy(artwork_id=source.aid).get_page_file()
        return file.resolve_path

    async def _select_current_source(self) -> None:
        return

    async def _init_working_path(self) -> None:
        aids = await self.query_pool_artworks()
        if self._select_cancelled:
            # 用户在获取来源参数时取消, 不初始化
            return
        if not aids:
            logger.error(f'{self.source_type} 来源为空, 可能是网络异常或无符合条件的作品')
            raise RuntimeError('null of artwork source')

        logger.info(f'已从 {self.source_type} 来源获取作品 {len(aids)} 个, 正在初始化处理队列')

        self._remaining_source = sorted(
            (
                CurrentArtwork.model_validate({
                    'aid': x,
                    'source_path': f'https://www.pixiv.net/artworks/{x}',
                })
                for x in aids
            ),
            key=lambda x: int(x.aid),
            reverse=True,
        )


class PixivTopRecommendArtworkSource(_PixivPoolArtworkSource):
    """Pixiv 首页推荐作品"""

    @property
    def source_type(self) -> str:
        return 'pixiv_top_recommend'

    @property
    def title_name(self) -> str:
        return 'Pixiv 首页推荐作品'

    async def query_pool_artworks(self) -> list[str]:
        from src.utils.pixiv_api.pixiv import PixivCommon

        logger.info('正在从 Pixiv 发现/推荐获取作品来源, 请稍候')
        discovery_result = await PixivCommon.query_discovery_artworks()
        top_result = await PixivCommon.query_top_illust()
        aids = [str(x) for x in (discovery_result.recommend_pids + top_result.recommend_pids)]

        return [
            x.s_aid
            for x in await PixivArtworkProxy.query_db_not_exists_artworks(
                aids,
                exclude_classification=(3, 4),
            )
        ]


class PixivRelatedArtworkSource(_PixivPoolArtworkSource):
    """Pixiv 作品相关推荐作品"""

    @property
    def source_type(self) -> str:
        return 'pixiv_related_artwork'

    @property
    def title_name(self) -> str:
        return 'Pixiv 作品相关推荐作品'

    @staticmethod
    def _ask_pid() -> int | None:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        try:
            pid = simpledialog.askinteger(
                '目标作品',
                '请输入想要获取相关推荐的作品 PID',
                parent=tmp_root,
                minvalue=1,
            )
        finally:
            tmp_root.destroy()

        return pid

    async def query_pool_artworks(self) -> list[str]:
        from src.utils.pixiv_api.pixiv import PixivArtwork

        pid = self._ask_pid()
        if pid is None:
            logger.info('No PID input, cancelled initializing related artwork source')
            self._select_cancelled = True
            return []

        logger.info(f'正在从获取作品 {pid} 相关推荐, 请稍候')
        recommend_result = await PixivArtwork(pid=pid).query_recommend(init_limit=100)

        return [
            x.s_aid
            for x in await PixivArtworkProxy.query_db_not_exists_artworks(
                recommend_result.illust_ids,
                exclude_classification=(3, 4),
            )
        ]


class PixivSearchPopularArtworkSource(_PixivPoolArtworkSource):
    """Pixiv 搜索作品"""

    @property
    def source_type(self) -> str:
        return 'pixiv_search_popular_artwork'

    @property
    def title_name(self) -> str:
        return 'Pixiv 搜索热门作品'

    @staticmethod
    def _ask_keyword() -> str | None:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        try:
            keyword = simpledialog.askstring(
                '搜索关键词',
                '请输入搜索关键词',
                parent=tmp_root,
            )
        finally:
            tmp_root.destroy()

        return keyword

    @staticmethod
    def _ask_page() -> int | None:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        try:
            page = simpledialog.askinteger('页码', '请输入请求的搜索结果页码', parent=tmp_root, minvalue=1)
        finally:
            tmp_root.destroy()

        return page

    async def query_pool_artworks(self) -> list[str]:
        from src.utils.pixiv_api.pixiv import PixivArtwork

        keyword = self._ask_keyword()
        if not keyword:
            # 用户取消或未输入关键词
            logger.info('No keyword input, cancelled initializing search artwork source')
            self._select_cancelled = True
            return []

        page = self._ask_page()
        if page is None:
            # 用户取消了页码输入
            logger.info('No page input, cancelled initializing search artwork source')
            self._select_cancelled = True
            return []

        logger.info(f'正在从 {keyword!r} 搜索结果 Page-{page} 获取作品信息, 请稍候')
        search_result = await PixivArtwork.search_by_default_popular_condition(word=keyword, page=page)
        aids = [str(x.id) for x in search_result.artworks]

        return [
            x.s_aid
            for x in await PixivArtworkProxy.query_db_not_exists_artworks(
                aids,
                exclude_classification=(3, 4),
            )
        ]


__all__ = [
    'PixivLocalArtworkFileSource',
    'PixivRelatedArtworkSource',
    'PixivSearchPopularArtworkSource',
    'PixivTopRecommendArtworkSource',
]
