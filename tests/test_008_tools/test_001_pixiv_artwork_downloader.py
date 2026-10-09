"""
@Author         : Ailitonia
@Date           : 2026/10/5 23:18
@FileName       : test_001_pixiv_artwork_downloader
@Project        : omega-miya
@Description    : pixiv 作品批量下载工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
from types import SimpleNamespace

import pytest

from tests.test_008_tools.helpers import (
    capture_async_sleep,
    make_bookmark_page_querier,
    patch_fake_pixiv_downloader,
    patch_zero_page_interval,
    write_output_file,
)


class TestLoadOutputFileDownloadUrls:
    """输出文件下载链接加载测试"""

    async def test_strip_and_skip_blank_lines(self, pixiv_output_downloader):
        await write_output_file(
            pixiv_output_downloader,
            'https://example.com/a.png\n'
            '\n'
            '  https://example.com/b.png  \n'
            ' \n'
            'https://example.com/c.png\n',
        )
        urls = await pixiv_output_downloader._load_output_file_download_urls()

        assert urls == [
            'https://example.com/a.png',
            'https://example.com/b.png',
            'https://example.com/c.png',
        ]

    async def test_empty_file(self, pixiv_output_downloader):
        await write_output_file(pixiv_output_downloader, '')
        urls = await pixiv_output_downloader._load_output_file_download_urls()

        assert urls == []


class TestHandleDownloadArtworksFromOutputFile:
    """输出文件批量下载测试"""

    async def test_all_success_passes_clean_urls(self, pixiv_output_downloader):
        from src.resource import TemporaryResource
        from tools.pixiv_artwork_downloader.downloader import CustomUserDownloader

        recorded_urls = []

        async def fake_download_any_url(url, save_folder, **kwargs):
            recorded_urls.append(url)
            return save_folder

        await write_output_file(
            pixiv_output_downloader, 'https://example.com/a.png\n\nhttps://example.com/b.png\n',
        )
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                CustomUserDownloader, 'download_any_url', staticmethod(fake_download_any_url),
            )
            await pixiv_output_downloader._handle_download_artworks_from_output_file(
                save_folder=TemporaryResource('test'),
            )

        assert recorded_urls == ['https://example.com/a.png', 'https://example.com/b.png']

    async def test_partial_failure_raises(self, pixiv_output_downloader):
        from src.exception import WebSourceException
        from src.resource import TemporaryResource
        from tools.pixiv_artwork_downloader.downloader import CustomUserDownloader

        async def fake_download_any_url(url, save_folder, **kwargs):
            if url.endswith('bad.png'):
                raise WebSourceException(403, f'Download {url} forbidden')
            return save_folder

        await write_output_file(
            pixiv_output_downloader,
            'https://example.com/a.png\nhttps://example.com/bad.png\nhttps://example.com/c.png\n',
        )
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                CustomUserDownloader, 'download_any_url', staticmethod(fake_download_any_url),
            )
            with pytest.raises(WebSourceException, match='1 of 3 urls failed'):
                await pixiv_output_downloader._handle_download_artworks_from_output_file(
                    save_folder=TemporaryResource('test'),
                )

    async def test_empty_file_skips_download(self, pixiv_output_downloader):
        from src.resource import TemporaryResource
        from tools.pixiv_artwork_downloader.downloader import CustomUserDownloader

        async def fake_download_any_url(url, save_folder, **kwargs):
            pytest.fail(f'should not download anything, but got {url}')

        await write_output_file(pixiv_output_downloader, '\n \n')
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                CustomUserDownloader, 'download_any_url', staticmethod(fake_download_any_url),
            )
            await pixiv_output_downloader._handle_download_artworks_from_output_file(
                save_folder=TemporaryResource('test'),
            )


class TestDownloadAnyUrlRetry:
    """任意链接下载自动重试测试"""

    @staticmethod
    def _patch_download_resource(monkeypatch: pytest.MonkeyPatch, failures: list[Exception]) -> list[str]:
        """以按顺序抛出注入异常的替身替换 _download_resource, 异常耗尽后返回成功, 返回调用 url 记录列表"""
        import tools.pixiv_artwork_downloader.downloader as downloader_module

        calls: list[str] = []

        async def fake_download_resource(url, save_folder, **kwargs):
            calls.append(url)
            if failures:
                raise failures.pop(0)
            return save_folder

        monkeypatch.setattr(
            downloader_module.CustomUserDownloader, '_download_resource', staticmethod(fake_download_resource),
        )
        return calls

    async def test_success_after_transient_failures(self):
        import tools.pixiv_artwork_downloader.downloader as downloader_module
        from src.exception import WebSourceException
        from src.resource import TemporaryResource
        from tools.pixiv_artwork_downloader.downloader import CustomUserDownloader

        with pytest.MonkeyPatch.context() as monkeypatch:
            calls = self._patch_download_resource(
                monkeypatch, [WebSourceException(500, 'Server error'), ConnectionError('Connection reset')],
            )
            sleep_calls = capture_async_sleep(monkeypatch, downloader_module)
            save_folder = TemporaryResource('test')
            async with asyncio.timeout(5):
                result = await CustomUserDownloader.download_any_url(
                    url='https://example.com/a.png', save_folder=save_folder,
                )

        assert len(calls) == 3
        assert result is save_folder
        assert sleep_calls == [5, 10]

    async def test_retry_exhaustion_raises(self):
        import tools.pixiv_artwork_downloader.downloader as downloader_module
        from src.exception import WebSourceException
        from src.resource import TemporaryResource
        from tools.pixiv_artwork_downloader.downloader import CustomUserDownloader

        with pytest.MonkeyPatch.context() as monkeypatch:
            calls = self._patch_download_resource(
                monkeypatch, [WebSourceException(500, 'Server error') for _ in range(10)],
            )
            sleep_calls = capture_async_sleep(monkeypatch, downloader_module)
            with pytest.raises(WebSourceException, match='Server error'):
                async with asyncio.timeout(5):
                    await CustomUserDownloader.download_any_url(
                        url='https://example.com/a.png', save_folder=TemporaryResource('test'), retry_num=2,
                    )

        assert len(calls) == 3
        assert sleep_calls == [5, 10]

    async def test_client_error_fails_fast_without_retry(self):
        import tools.pixiv_artwork_downloader.downloader as downloader_module
        from src.exception import WebSourceException
        from src.resource import TemporaryResource
        from tools.pixiv_artwork_downloader.downloader import CustomUserDownloader

        with pytest.MonkeyPatch.context() as monkeypatch:
            calls = self._patch_download_resource(
                monkeypatch, [WebSourceException(404, 'Not found') for _ in range(10)],
            )
            sleep_calls = capture_async_sleep(monkeypatch, downloader_module)
            with pytest.raises(WebSourceException, match='Not found'):
                async with asyncio.timeout(5):
                    await CustomUserDownloader.download_any_url(
                        url='https://example.com/a.png', save_folder=TemporaryResource('test'),
                    )

        assert len(calls) == 1
        assert sleep_calls == []

    async def test_rate_limit_429_is_retried(self):
        import tools.pixiv_artwork_downloader.downloader as downloader_module
        from src.exception import WebSourceException
        from src.resource import TemporaryResource
        from tools.pixiv_artwork_downloader.downloader import CustomUserDownloader

        with pytest.MonkeyPatch.context() as monkeypatch:
            calls = self._patch_download_resource(
                monkeypatch, [WebSourceException(429, 'Too many requests')],
            )
            sleep_calls = capture_async_sleep(monkeypatch, downloader_module)
            save_folder = TemporaryResource('test')
            async with asyncio.timeout(5):
                result = await CustomUserDownloader.download_any_url(
                    url='https://example.com/a.png', save_folder=save_folder,
                )

        assert len(calls) == 2
        assert result is save_folder
        assert sleep_calls == [5]


class TestQueryAllBookmarkIllust:
    """收藏分页查询测试"""

    @pytest.mark.parametrize(
        ('total', 'before', 'expected_offsets', 'expected_id_count', 'expected_sleep_calls'),
        [
            pytest.param(200, None, [0, 100], 200, [0], id='exact-multiple'),
            pytest.param(250, None, [0, 100, 200], 250, [0, 0], id='non-multiple'),
            pytest.param(200, 50, [0], 100, [], id='before-cap-first-page-only'),
            pytest.param(0, None, [0], 0, [], id='empty-bookmark'),
        ],
    )
    async def test_pagination_offsets(self, total, before, expected_offsets, expected_id_count, expected_sleep_calls):
        import tools.pixiv_artwork_downloader.downloader as downloader_module
        from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader

        requested_offsets: list[int] = []
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                downloader_module.CustomUserDownloader,
                'query_bookmarks',
                make_bookmark_page_querier(total=total, requested_offsets=requested_offsets),
            )
            sleep_calls = patch_zero_page_interval(monkeypatch)
            ids = await PixivArtworkDownloader._query_all_bookmark_illust(before=before)

        assert requested_offsets == expected_offsets
        assert ids == list(range(expected_id_count))
        assert sleep_calls == expected_sleep_calls


class TestFollowingPageQueryInterval:
    """关注流分页查询限速测试"""

    async def test_following_pagination_sleeps_between_pages(self):
        import tools.pixiv_artwork_downloader.downloader as downloader_module
        from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader

        pages = {1: ['100', '101'], 2: ['98', '99'], 3: []}

        async def fake_query_following(page, **kwargs):
            return SimpleNamespace(illust_ids=pages[page])

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                downloader_module.CustomUserDownloader, 'query_following_user_latest_illust', fake_query_following,
            )
            sleep_calls = patch_zero_page_interval(monkeypatch)
            ids = await PixivArtworkDownloader._query_following_user_latest_illust()

        assert ids == [98, 99, 100, 101]
        assert sleep_calls == [0, 0]


class TestEntryArgParsing:
    """CLI 入口参数解析测试"""

    async def test_download_users_artworks_filters_invalid_args(self):
        import tools.pixiv_artwork_downloader as tool_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            captured = patch_fake_pixiv_downloader(monkeypatch)
            await tool_module.download_users_artworks('123', 'abc', '456')

        assert len(captured) == 1
        assert captured[0].user_ids == [123, 456]
        assert captured[0].init_kwargs == {'fast_mode': False, 'use_cache': False}

    @pytest.mark.parametrize(
        'args',
        [
            pytest.param((), id='no-args'),
            pytest.param(('abc', '-1'), id='all-invalid'),
        ],
    )
    async def test_download_users_artworks_no_valid_args_aborts(self, args):
        import tools.pixiv_artwork_downloader as tool_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            captured = patch_fake_pixiv_downloader(monkeypatch)
            await tool_module.download_users_artworks(*args)

        assert captured == []

    @pytest.mark.parametrize(
        ('args', 'expected_before'),
        [
            pytest.param((), 480, id='default-before'),
            pytest.param(('100',), 100, id='explicit-before'),
            pytest.param(('abc',), 480, id='invalid-before-fallback'),
        ],
    )
    async def test_download_bookmark_artworks_before_parsing(self, args, expected_before):
        import tools.pixiv_artwork_downloader as tool_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            captured = patch_fake_pixiv_downloader(monkeypatch)
            await tool_module.download_bookmark_artworks(*args)

        assert len(captured) == 1
        assert captured[0].before == expected_before
        assert captured[0].init_kwargs == {'fast_mode': True, 'use_cache': True}


class TestResolveOutputAllUrls:
    """作品下载链接筛选真值表测试"""

    @pytest.mark.parametrize(
        ('rating', 'like_count', 'enable_filter', 'expected'),
        [
            pytest.param(0, 0, False, True, id='filter-disabled-all'),
            pytest.param(3, 2000, True, True, id='explicit-high-like-all'),
            pytest.param(3, 1666, True, False, id='explicit-boundary-like-cover'),
            pytest.param(3, None, True, False, id='explicit-none-like-cover'),
            pytest.param(2, 2000, True, True, id='questionable-high-like-all'),
            pytest.param(2, 1666, True, False, id='questionable-boundary-like-cover'),
            pytest.param(1, 666, True, True, id='sensitive-boundary-like-all'),
            pytest.param(1, 665, True, False, id='sensitive-low-like-cover'),
            pytest.param(0, None, True, False, id='general-none-like-cover'),
        ],
    )
    def test_truth_table(self, rating, like_count, enable_filter, expected):
        from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader

        artwork_data = SimpleNamespace(rating=rating, like_count=like_count)
        assert PixivArtworkDownloader._resolve_output_all_urls(artwork_data, enable_filter) is expected


class TestQueryArtworksAndWriteDownloadUrls:
    """批量获取作品信息写入测试"""

    @staticmethod
    def _patch_query_and_write(monkeypatch: pytest.MonkeyPatch, written: list, query_map: dict[int, Exception]):
        """以注入的查询/写入替身替换作品查询与下载链接写入方法"""
        from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader

        async def fake_query_artwork_data(self, pid):
            failure = query_map.get(pid)
            if failure is not None:
                raise failure
            return SimpleNamespace(aid=str(pid), rating=0, like_count=0)

        async def fake_append_write(self, artwork_data, output_all_urls=False):
            written.append((artwork_data.aid, output_all_urls))

        monkeypatch.setattr(PixivArtworkDownloader, '_handle_query_artwork_data', fake_query_artwork_data)
        monkeypatch.setattr(
            PixivArtworkDownloader,
            '_handle_append_write_artworks_download_urls_into_output_file',
            fake_append_write,
        )

    async def test_partial_failure_raises_and_keeps_success_writes(self):
        from src.exception import WebSourceException
        from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader

        written: list[tuple[str, bool]] = []
        query_map = {
            4: WebSourceException(404, 'Artwork not found'),
            5: WebSourceException(500, 'Server error'),
            6: WebSourceException(500, 'Server error'),
        }

        downloader = PixivArtworkDownloader()
        with pytest.MonkeyPatch.context() as monkeypatch:
            self._patch_query_and_write(monkeypatch, written, query_map)
            with pytest.raises(WebSourceException, match='2 of 6 pids failed'):
                await downloader._handle_query_artworks_and_write_download_urls_into_output_file(
                    pids=[1, 2, 3, 4, 5, 6],
                )

        assert sorted(aid for aid, _ in written) == ['1', '2', '3']

    async def test_all_success_writes_without_raise(self):
        from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader

        written: list[tuple[str, bool]] = []

        downloader = PixivArtworkDownloader()
        with pytest.MonkeyPatch.context() as monkeypatch:
            self._patch_query_and_write(monkeypatch, written, query_map={})
            await downloader._handle_query_artworks_and_write_download_urls_into_output_file(pids=[1, 2])

        assert sorted(aid for aid, _ in written) == ['1', '2']


class TestDownloadFollowArtworksEmpty:
    """关注流为空跳过更新测试"""

    async def test_empty_follow_artworks_skips_update(self):
        import tools.pixiv_artwork_downloader.downloader as downloader_module
        from tools.pixiv_artwork_downloader.downloader import PixivArtworkDownloader

        async def fake_query_following(page, **kwargs):
            return SimpleNamespace(illust_ids=[])

        async def fail_get_last_pid():
            pytest.fail('should not read last follow pid when no following artworks')

        async def fail_set_last_pid(pid):
            pytest.fail(f'should not write last follow pid when no following artworks, got {pid}')

        downloader = PixivArtworkDownloader(use_cache=False)
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                downloader_module.CustomUserDownloader, 'query_following_user_latest_illust', fake_query_following,
            )
            monkeypatch.setattr(downloader_module, 'get_last_follow_illust_pid', fail_get_last_pid)
            monkeypatch.setattr(downloader_module, 'set_last_follow_illust_pid', fail_set_last_pid)
            await downloader._download_follow_artworks()

        with pytest.raises(ValueError, match='output_file has not been set'):
            _ = downloader.output_file


class TestGetLastFollowIllustPid:
    """分界 pid 读取容错测试"""

    async def test_invalid_setting_value_returns_none(self):
        import tools.pixiv_artwork_downloader.utils as utils_module
        from tools.pixiv_artwork_downloader.utils import get_last_follow_illust_pid

        class _FakeDal:
            async def query_unique(self, **kwargs):
                return SimpleNamespace(setting_value='not-a-number', info='broken')

        class _FakeDalContext:
            async def __aenter__(self):
                return _FakeDal()

            async def __aexit__(self, *args):
                return False

        class _FakeSystemSettingDAL:
            @classmethod
            def create(cls):
                return _FakeDalContext()

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(utils_module, 'SystemSettingDAL', _FakeSystemSettingDAL)
            assert await get_last_follow_illust_pid() is None


class TestQueryTagUserId:
    """标签用户分页查询测试"""

    @staticmethod
    async def _run_tag_query(
            monkeypatch: pytest.MonkeyPatch,
            fake_query,
    ) -> tuple[list[int], list[float]]:
        """以注入的分页查询替身执行标签用户查询, 返回 (用户 id 列表, sleep 调用记录)"""
        from tools.pixiv_artwork_downloader.downloader import CustomUserDownloader

        downloader = CustomUserDownloader(uid=0)
        monkeypatch.setattr(CustomUserDownloader, 'query_user_following_users', fake_query)
        sleep_calls = patch_zero_page_interval(monkeypatch)
        ids = await downloader._query_tag_user_id(tag='tag_a')
        return ids, sleep_calls

    async def test_persistent_error_stops_querying(self):
        from src.exception import WebSourceException

        query_count = 0

        async def fake_query_user_following_users(self, **kwargs):
            nonlocal query_count
            query_count += 1
            raise WebSourceException(403, 'Forbidden')

        with pytest.MonkeyPatch.context() as monkeypatch:
            async with asyncio.timeout(5):
                ids, sleep_calls = await self._run_tag_query(monkeypatch, fake_query_user_following_users)

        assert ids == []
        assert query_count == 1
        assert sleep_calls == []

    async def test_pagination_sleeps_between_pages(self):
        pages = {0: ['1', '2'], 1: ['3'], 2: []}

        async def fake_query_user_following_users(self, *, tag, offset, limit, **kwargs):
            return SimpleNamespace(
                body=SimpleNamespace(users=[SimpleNamespace(userId=x) for x in pages[offset // limit]]),
            )

        with pytest.MonkeyPatch.context() as monkeypatch:
            ids, sleep_calls = await self._run_tag_query(monkeypatch, fake_query_user_following_users)

        assert ids == [1, 2, 3]
        assert sleep_calls == [0, 0]

    async def test_not_found_stops_querying_and_keeps_results(self):
        from src.exception import WebSourceException

        async def fake_query_user_following_users(self, *, tag, offset, limit, **kwargs):
            if offset == 0:
                return SimpleNamespace(body=SimpleNamespace(users=[SimpleNamespace(userId='7')]))
            raise WebSourceException(404, 'Not found')

        with pytest.MonkeyPatch.context() as monkeypatch:
            ids, sleep_calls = await self._run_tag_query(monkeypatch, fake_query_user_following_users)

        assert ids == [7]
        assert sleep_calls == [0]


class TestDownloadTagUsersArtworks:
    """标签下载入口测试"""

    @staticmethod
    def _make_fake_custom_downloader(tag_users: dict[str, list[int]]):
        """构造按标签返回用户 id 的 CustomUserDownloader 替身"""

        class _FakeCustomUserDownloader:
            @classmethod
            async def query_default_user_tag_user_id(cls, tag: str) -> list[int]:
                return list(tag_users[tag])

        return _FakeCustomUserDownloader

    async def test_deduplicate_user_ids_across_tags(self):
        import tools.pixiv_artwork_downloader as tool_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                tool_module,
                'CustomUserDownloader',
                self._make_fake_custom_downloader({'tag_a': [1, 2, 3], 'tag_b': [3, 4]}),
            )
            captured = patch_fake_pixiv_downloader(monkeypatch)
            await tool_module.download_tag_users_artworks('tag_a', 'tag_b')

        assert len(captured) == 1
        assert captured[0].user_ids == [1, 2, 3, 4]
        assert captured[0].init_kwargs == {'fast_mode': False, 'use_cache': False}

    async def test_no_tag_aborts(self):
        import tools.pixiv_artwork_downloader as tool_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            captured = patch_fake_pixiv_downloader(monkeypatch)
            await tool_module.download_tag_users_artworks()

        assert captured == []

    async def test_no_valid_user_queried_aborts(self):
        import tools.pixiv_artwork_downloader as tool_module

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                tool_module,
                'CustomUserDownloader',
                self._make_fake_custom_downloader({'tag_a': []}),
            )
            captured = patch_fake_pixiv_downloader(monkeypatch)
            await tool_module.download_tag_users_artworks('tag_a')

        assert captured == []
