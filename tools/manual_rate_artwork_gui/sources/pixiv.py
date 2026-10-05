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
from tkinter import Tk, filedialog, simpledialog
from typing import IO, TYPE_CHECKING

from nonebot.log import logger

from src.compat import dump_json_as, parse_json_as
from src.resource import AnyResource
from src.service.artwork_proxy import PixivArtworkProxy
from ..data_source import BaseArtworkSource
from ..model import CurrentArtwork

if TYPE_CHECKING:
    from os import PathLike
    from src.service.artwork_proxy.internal import BaseArtworkProxy

    type SourceOpenFp = str | bytes | PathLike[str] | IO[bytes]


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
        return PixivArtworkProxy(artwork_id=self._current_source.aid)

    async def _load_current_source(self) -> 'SourceOpenFp':
        return self._current_source.source_path

    async def _select_current_source(self) -> None:
        current_file = AnyResource(filedialog.askopenfilename())
        self._current_source = CurrentArtwork.model_validate({
            'aid': current_file.name.split('_')[0].split('-')[0],
            'source_path': current_file.resolve_path,
        })
        self._working_path = current_file.parent.resolve_path

    async def _init_working_path(self) -> None:
        working_dir = AnyResource(self._working_path)
        working_dir_hash = hashlib.sha256(working_dir.resolve_path.encode('utf-8')).hexdigest()[:16]

        # 文件列表缓存
        working_dir_all_files_cache = self._output_path.cache_dir(
            f'working_files_cache_{working_dir.name}_{working_dir_hash}.json'
        )

        if working_dir_all_files_cache.is_file:
            # 若存在文件列表缓存, 则加载文件列表缓存
            async with working_dir_all_files_cache.async_open('r', encoding='utf-8') as af:
                cache_files = parse_json_as(list[CurrentArtwork], await af.read())

            current_id = int(self._current_source.aid)
            working_dir_all_files = sorted(
                (x for x in cache_files if int(x.aid) >= current_id),
                key=lambda x: int(x.aid)
            )
            logger.info(f'发现目录缓存, 已载入, 共计 {len(cache_files)}, 剩余待处理 {len(working_dir_all_files)}')
        else:
            # 若不存在文件列表缓存, 则扫描工作目录并初始化文件列表
            pattern = re.compile(r'^(\d+)(?=[_-])')
            exists_files = sorted(
                (
                    CurrentArtwork.model_validate({
                        'aid': x.name.split('_')[0].split('-')[0],
                        'source_path': x.resolve_path,
                    })
                    for x in working_dir.iter_current_files()
                    if re.match(pattern, x.name)
                ),
                key=lambda x: x.aid
            )

            current_id = int(self._current_source.aid)
            working_dir_all_files = sorted(
                (x for x in exists_files if int(x.aid) >= current_id),
                key=lambda x: int(x.aid)
            )
            logger.info(f'已载入目录作品文件, 共计 {len(exists_files)}, 剩余待处理 {len(working_dir_all_files)}')

        self._remaining_source = working_dir_all_files

        # 保存目录缓存
        async with working_dir_all_files_cache.async_open('w', encoding='utf-8') as af:
            await af.write(dump_json_as(list[CurrentArtwork], self._remaining_source))


class _PixivPoolArtworkSource(BaseArtworkSource, abc.ABC):
    """Pixiv 图集类型图片源"""

    @property
    def source_origin(self) -> str:
        return 'pixiv'

    @property
    def _current_artwork_proxy(self) -> 'BaseArtworkProxy':
        return PixivArtworkProxy(artwork_id=self._current_source.aid)

    @abc.abstractmethod
    async def query_pool_artworks(self) -> list[str]:
        """获取图集中作品 ID 序列"""
        raise NotImplementedError

    async def _load_current_source(self) -> 'SourceOpenFp':
        logger.info(f'获取作品 {self._current_source.aid} 图片中, 请稍候')
        file = await self._current_artwork_proxy.get_page_file()
        return file.resolve_path

    async def _select_current_source(self) -> None:
        return

    async def _init_working_path(self) -> None:
        aids = await self.query_pool_artworks()
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
            reverse=True
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
    def _ask_pid() -> int:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        pid = simpledialog.askinteger(
            '目标作品',
            '请输入想要获取相关推荐的作品 PID',
            parent=tmp_root,
        )
        while pid is None:
            pid = simpledialog.askinteger(
                '目标作品',
                'PID 不能为空, 请输入想要获取相关推荐的作品 PID',
                parent=tmp_root,
            )

        tmp_root.destroy()
        del tmp_root
        return pid

    async def query_pool_artworks(self) -> list[str]:
        from src.utils.pixiv_api.pixiv import PixivArtwork

        pid = self._ask_pid()

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
    def _ask_keyword() -> str:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        keyword = simpledialog.askstring(
            '搜索关键词',
            '请输入搜索关键词',
            parent=tmp_root,
        )
        while keyword is None:
            keyword = simpledialog.askstring(
                '搜索关键词',
                '关键词不能为空, 请输入搜索关键词',
                parent=tmp_root,
            )

        tmp_root.destroy()
        del tmp_root
        return keyword

    @staticmethod
    def _ask_page() -> int:
        tmp_root = Tk()  # Create a new temporary "parent", but make it invisible
        tmp_root.withdraw()

        page = simpledialog.askinteger('页码', '请输入请求的搜索结果页码', parent=tmp_root)
        page = 1 if page is None else page

        tmp_root.destroy()
        del tmp_root
        return page

    async def query_pool_artworks(self) -> list[str]:
        from src.utils.pixiv_api.pixiv import PixivArtwork

        keyword = self._ask_keyword()
        page = self._ask_page()

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
