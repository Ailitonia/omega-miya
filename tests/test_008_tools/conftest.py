"""
@Author         : Ailitonia
@Date           : 2026/10/8 20:00
@FileName       : conftest
@Project        : omega-miya
@Description    : test_008_tools pytest 配置及共享 fixture
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import shutil

import pytest


@pytest.fixture
def pixiv_output_downloader():
    """构造已设置唯一输出文件的 PixivArtworkDownloader, 测试结束后自动清理输出文件"""
    from tests.utils import unique_test_id
    from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader

    downloader = PixivArtworkDownloader()
    downloader.set_output_file(category='test', filename=f'{unique_test_id('test_output')}.txt')
    try:
        yield downloader
    finally:
        downloader.output_file.path.unlink(missing_ok=True)


@pytest.fixture
def osu_test_root(monkeypatch: pytest.MonkeyPatch) -> str:
    """隔离的 osu 曲包爬虫测试输出根目录, 测试结束后自动清理"""
    from src.resource import TemporaryResource
    from tests.utils import unique_test_id
    from tools.osu_packs_crawler.config import osu_web_config

    test_root = unique_test_id('osu_packs_crawler_test')
    monkeypatch.setattr(osu_web_config, 'omega_tool_osu_output_root_folder', test_root)
    try:
        yield test_root
    finally:
        shutil.rmtree(TemporaryResource(test_root).path, ignore_errors=True)
