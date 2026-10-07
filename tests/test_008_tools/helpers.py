"""
@Author         : Ailitonia
@Date           : 2026/10/8 20:00
@FileName       : helpers
@Project        : omega-miya
@Description    : test_008_tools 共享测试工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Callable
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader


async def write_output_file(downloader: 'PixivArtworkDownloader', content: str) -> None:
    """向下载器的输出文件写入原始内容"""
    async with downloader.output_file.async_open('w', encoding='utf-8') as af:
        await af.write(content)


def capture_async_sleep(monkeypatch: pytest.MonkeyPatch, module: ModuleType) -> list[float]:
    """向目标模块注入记录调用参数的假 async_sleep, 返回调用记录列表

    替换的是目标模块命名空间内的 async_sleep 名字, 不触碰进程共享的 asyncio.sleep
    """
    sleep_calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(module, 'async_sleep', _fake_sleep)
    return sleep_calls


def patch_fake_pixiv_downloader(monkeypatch: pytest.MonkeyPatch) -> list:
    """以记录调用参数的替身工厂替换 PixivArtworkDownloader, 返回捕获实例的列表"""
    import tools.pixiv_artwork_downloader as tool_module

    captured: list = []
    monkeypatch.setattr(tool_module, 'PixivArtworkDownloader', make_fake_pixiv_downloader_factory(captured))
    return captured


def patch_zero_page_interval(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """将 pixiv 下载器翻页查询间隔置零并注入假 async_sleep, 返回 sleep 调用记录列表"""
    import tools.pixiv_artwork_downloader.downloader as downloader_module

    monkeypatch.setattr(downloader_module, 'LIST_PAGE_QUERY_INTERVAL', 0)
    return capture_async_sleep(monkeypatch, downloader_module)


def make_fake_pixiv_downloader_factory(captured: list) -> Callable[..., Any]:
    """构造记录调用参数的 PixivArtworkDownloader 替身工厂"""

    class _FakeArtworkDownloader:
        def __init__(self, fast_mode: bool = False, use_cache: bool = True):
            self.init_kwargs = {'fast_mode': fast_mode, 'use_cache': use_cache}
            self.user_ids = None
            self.before = None

        async def download_users_artworks_main(self, user_ids):
            self.user_ids = list(user_ids)

        async def download_bookmark_artworks_main(self, uid=None, *, before=None):
            self.before = before

    def _factory(*args, **kwargs):
        instance = _FakeArtworkDownloader(*args, **kwargs)
        captured.append(instance)
        return instance

    return _factory


def make_bookmark_page_querier(total: int, requested_offsets: list[int] | None = None) -> Callable[..., Any]:
    """构造按 offset 分页返回收藏结果的假 query_bookmarks, 可记录请求过的 offset"""

    def _make_page(offset: int, limit: int) -> SimpleNamespace:
        count = max(0, min(limit, total - offset))
        return SimpleNamespace(total=total, illust_ids=[str(offset + i) for i in range(count)])

    async def _fake_query_bookmarks(uid=None, offset=0, limit=100, rest='show', **kwargs):
        if requested_offsets is not None:
            requested_offsets.append(offset)
        return _make_page(offset=offset, limit=limit)

    return _fake_query_bookmarks


def make_fake_query_packs_recorder(captured: list[str]) -> Callable[..., Any]:
    """构造记录分发类型的假 _query_packs_download_urls"""

    async def _fake_query_packs(type_='standard'):
        captured.append(type_)

    return _fake_query_packs


__all__ = [
    'capture_async_sleep',
    'make_bookmark_page_querier',
    'make_fake_pixiv_downloader_factory',
    'make_fake_query_packs_recorder',
    'patch_fake_pixiv_downloader',
    'patch_zero_page_interval',
    'write_output_file',
]
