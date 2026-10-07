"""
@Author         : Ailitonia
@Date           : 2026/10/7 14:04
@FileName       : test_003_osu_packs_crawler
@Project        : omega-miya
@Description    : osu! 曲包下载链接批量获取工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pytest

from tests.test_008_tools.helpers import capture_async_sleep, make_fake_query_packs_recorder

_PACKS_LIST_HTML = """
<html>
  <body>
    <div>
      <div class="osu-page">
        <div class="beatmap-packs js-accordion">
          <div class="beatmap-pack js-beatmap-pack js-accordion__item" data-pack-tag="S1000"></div>
          <div class="beatmap-pack js-beatmap-pack js-accordion__item" data-pack-tag="S1001"></div>
          <div class="beatmap-pack js-beatmap-pack js-accordion__item"></div>
        </div>
      </div>
    </div>
  </body>
</html>
"""

_PACKS_LIST_EMPTY_HTML = """
<html>
  <body>
    <div>
      <div class="osu-page">
        <div class="beatmap-packs js-accordion"></div>
      </div>
    </div>
  </body>
</html>
"""

_PACK_DETAIL_HTML = """
<html>
  <body>
    <div class="beatmap-pack-description">
      <a class="beatmap-pack-download__link" href="https://osu.ppy.sh/beatmaps/packs/S1000/download">Download</a>
    </div>
    <ul class="beatmap-pack-items">
      <li class="beatmap-pack-items__set">
        <a class="beatmap-pack-items__link" href="https://osu.ppy.sh/beatmapsets/123456">
          <span>Artist</span><span> - </span><span>Title</span><span></span>
        </a>
      </li>
      <li class="beatmap-pack-items__set">
        <a class="beatmap-pack-items__link" href="https://osu.ppy.sh/beatmapsets/234567">
          <span>Foo</span>
        </a>
      </li>
    </ul>
  </body>
</html>
"""

_PACK_DETAIL_NO_LINK_HTML = """
<html>
  <body>
    <ul class="beatmap-pack-items"></ul>
  </body>
</html>
"""

_ALL_PACK_TYPES = ['standard', 'featured', 'tournament', 'loved', 'chart', 'theme', 'artist']


async def _run_info_crawl(
        monkeypatch: pytest.MonkeyPatch,
        fake_query_list,
        fake_query_pack=None,
        **config_overrides,
) -> list[float]:
    """以注入的列表/详情查询替身执行曲包信息抓取, 返回 sleep 调用记录"""
    import tools.osu_packs_crawler as tool_module
    from tools.osu_packs_crawler.api import OsuWeb
    from tools.osu_packs_crawler.config import osu_web_config

    for name, value in config_overrides.items():
        monkeypatch.setattr(osu_web_config, name, value)
    monkeypatch.setattr(OsuWeb, 'query_beatmaps_packs_list', fake_query_list)
    if fake_query_pack is not None:
        monkeypatch.setattr(OsuWeb, 'query_beatmap_pack', fake_query_pack)
    sleep_calls = capture_async_sleep(monkeypatch, tool_module)
    await tool_module._query_beatmaps_packs_info_output_to_meta_file('standard')
    return sleep_calls


class TestMainEntry:
    """CLI 默认入口分发测试"""

    @pytest.mark.parametrize(
        ('args', 'expected_types'),
        [
            pytest.param((), _ALL_PACK_TYPES, id='no-args-runs-all-types'),
            pytest.param(('standard', 'loved'), ['standard', 'loved'], id='with-args-runs-specified-types'),
        ],
    )
    async def test_main_dispatches_pack_types(self, args, expected_types):
        import tools.osu_packs_crawler as tool_module

        called: list[str] = []
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                tool_module, '_query_packs_download_urls', make_fake_query_packs_recorder(called),
            )
            await tool_module.main(*args)

        assert called == expected_types


class TestQueryPacksDownloadUrlsArgValidation:
    """类型参数校验测试"""

    async def test_invalid_type_raises(self):
        import tools.osu_packs_crawler as tool_module

        with pytest.raises(ValueError, match='invalid beatmaps packs type'):
            await tool_module.query_packs_download_urls('std')

    @pytest.mark.parametrize(
        ('args', 'expected_types'),
        [
            pytest.param(('featured', 'standard'), ['featured', 'standard'], id='explicit-types-dispatch-in-order'),
            pytest.param((), ['standard'], id='no-args-defaults-to-standard'),
        ],
    )
    async def test_dispatch(self, args, expected_types):
        import tools.osu_packs_crawler as tool_module

        called: list[str] = []
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                tool_module, '_query_packs_download_urls', make_fake_query_packs_recorder(called),
            )
            await tool_module.query_packs_download_urls(*args)

        assert called == expected_types


class TestParseBeatmapsPacks:
    """曲包列表页解析测试"""

    @pytest.mark.parametrize(
        ('html', 'expected'),
        [
            pytest.param(_PACKS_LIST_HTML, ['S1000', 'S1001'], id='extract-pack-tags'),
            pytest.param(_PACKS_LIST_EMPTY_HTML, [], id='empty-page'),
        ],
    )
    async def test_parse(self, html, expected):
        from tools.osu_packs_crawler.api import OsuWeb

        assert await OsuWeb._parse_beatmaps_packs(html) == expected


class TestParseBeatmapPack:
    """曲包详情页解析测试"""

    async def test_extract_pack_detail(self):
        from tools.osu_packs_crawler.api import OsuWeb

        pack = await OsuWeb._parse_beatmap_pack('S1000', _PACK_DETAIL_HTML)

        assert pack.id == 'S1000'
        assert pack.download_url == 'https://osu.ppy.sh/beatmaps/packs/S1000/download'
        assert len(pack.beatmaps) == 2
        assert pack.beatmaps[0].id == '123456'
        assert pack.beatmaps[0].url == 'https://osu.ppy.sh/beatmapsets/123456'
        assert pack.beatmaps[0].name == 'Artist - Title'
        assert pack.beatmaps[1].id == '234567'
        assert pack.beatmaps[1].name == 'Foo'

    async def test_missing_download_link_raises(self):
        from tools.osu_packs_crawler.api import OsuWeb

        with pytest.raises(IndexError):
            await OsuWeb._parse_beatmap_pack('S1000', _PACK_DETAIL_NO_LINK_HTML)


class TestQueryBeatmapsPacksInfoCircuitBreaker:
    """曲包分页抓取熔断测试"""

    async def test_persistent_error_aborts_after_threshold(self, osu_test_root):
        from src.exception import WebSourceException

        query_pages: list[int] = []

        async def fake_query_list(type_='standard', page=1):
            query_pages.append(page)
            raise WebSourceException(500, 'Server error')

        with pytest.MonkeyPatch.context() as monkeypatch:
            await _run_info_crawl(monkeypatch, fake_query_list, omega_tool_osu_max_consecutive_failures=3)

        assert query_pages == [1, 2, 3]

    async def test_not_found_stops_immediately(self, osu_test_root):
        from src.exception import WebSourceException

        query_pages: list[int] = []

        async def fake_query_list(type_='standard', page=1):
            query_pages.append(page)
            raise WebSourceException(404, 'Not found')

        with pytest.MonkeyPatch.context() as monkeypatch:
            await _run_info_crawl(monkeypatch, fake_query_list)

        assert query_pages == [1]

    async def test_empty_page_stops_immediately(self, osu_test_root):
        query_pages: list[int] = []

        async def fake_query_list(type_='standard', page=1):
            query_pages.append(page)
            return []

        with pytest.MonkeyPatch.context() as monkeypatch:
            await _run_info_crawl(monkeypatch, fake_query_list)

        assert query_pages == [1]

    async def test_transient_error_resets_consecutive_counter(self, osu_test_root):
        from src.exception import WebSourceException
        from tools.osu_packs_crawler.config import osu_web_config
        from tools.osu_packs_crawler.model import BeatmapsPack

        query_pages: list[int] = []
        queried_packs: list[str] = []

        async def fake_query_list(type_='standard', page=1):
            query_pages.append(page)
            if page == 1:
                raise WebSourceException(500, 'Server error')
            if page == 2:
                return ['S1000']
            raise WebSourceException(404, 'Not found')

        async def fake_query_pack(beatmap_pack_id):
            queried_packs.append(beatmap_pack_id)
            return BeatmapsPack(
                id=beatmap_pack_id,
                download_url=f'https://osu.ppy.sh/beatmaps/packs/{beatmap_pack_id}/download',
            )

        with pytest.MonkeyPatch.context() as monkeypatch:
            sleep_calls = await _run_info_crawl(
                monkeypatch,
                fake_query_list,
                fake_query_pack,
                omega_tool_osu_request_interval=3.0,
                omega_tool_osu_max_consecutive_failures=3,
            )

        assert query_pages == [1, 2, 3]
        assert queried_packs == ['S1000']
        assert sleep_calls == [3.0, 3.0, 3.0]
        assert osu_web_config.meta_dir('standard', 'S1000.json').is_file

    async def test_existing_meta_file_skips_pack_query(self, osu_test_root):
        from tools.osu_packs_crawler.config import osu_web_config
        from tools.osu_packs_crawler.model import BeatmapsPack

        pages = {1: ['S1000'], 2: []}

        async def fake_query_list(type_='standard', page=1):
            return pages[page]

        async def fail_query_pack(beatmap_pack_id):
            pytest.fail(f'should not query pack with existing meta file, got {beatmap_pack_id}')

        pack = BeatmapsPack(
            id='S1000',
            download_url='https://osu.ppy.sh/beatmaps/packs/S1000/download',
        )
        meta_file = osu_web_config.meta_dir('standard', 'S1000.json')
        await meta_file.safe_write_text(pack.model_dump_json(), encoding='utf-8')

        with pytest.MonkeyPatch.context() as monkeypatch:
            await _run_info_crawl(monkeypatch, fake_query_list, fail_query_pack)


class TestGenDownloadUrlFromMetaFile:
    """下载链接生成测试"""

    async def test_skips_invalid_meta_file(self, osu_test_root):
        import tools.osu_packs_crawler as tool_module
        from tools.osu_packs_crawler.config import osu_web_config
        from tools.osu_packs_crawler.model import BeatmapsPack

        valid_pack = BeatmapsPack(
            id='S1000',
            download_url='https://osu.ppy.sh/beatmaps/packs/S1000/download',
        )
        meta_dir = osu_web_config.meta_dir('standard')
        await meta_dir('S1000.json').safe_write_text(valid_pack.model_dump_json(), encoding='utf-8')
        await meta_dir('broken.json').safe_write_text('{"id": ', encoding='utf-8')

        await tool_module._gen_download_url_from_meta_file('standard')

        output_file = osu_web_config.urls_dir('standard_beatmaps_packs_download_urls.txt')
        assert output_file.is_file
        async with output_file.async_open('r', encoding='utf-8') as af:
            content = await af.read()
        assert content == 'https://osu.ppy.sh/beatmaps/packs/S1000/download\n'
