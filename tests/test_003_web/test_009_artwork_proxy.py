"""
@Author         : Ailitonia
@Date           : 2026/10/1 18:37
@FileName       : test_009_artwork_proxy
@Project        : omega-miya
@Description    : artwork_proxy 单元测试(BaseArtworkProxy 基类行为, 全部经由 mock/隔离文件系统, 不发起真实请求)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import hashlib
import re
import unicodedata
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def isolated_temporary_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """将 TemporaryResource 根目录隔离到 tmp_path, 避免污染项目 .tmp 缓存目录"""
    import src.resource

    monkeypatch.setattr(src.resource, '_TEMPORARY_RESOURCE_FOLDER', tmp_path)
    monkeypatch.setattr(src.resource.TemporaryResource, '_CONFINEMENT_ROOT', tmp_path.resolve())
    return tmp_path


def make_page(page_index: int, *, base_url: str = 'https://unit.test', ext: str = '.jpg') -> dict[str, Any]:
    """构造单页作品页面数据"""
    return {
        'page_index': page_index,
        'preview_file': {'url': f'{base_url}/{page_index}_preview{ext}', 'file_ext': ext},
        'regular_file': {'url': f'{base_url}/{page_index}_regular{ext}', 'file_ext': ext},
        'original_file': {'url': f'{base_url}/{page_index}_original{ext}', 'file_ext': ext},
    }


def make_artwork_data(
        aid: str = '123',
        *,
        rating: int = 0,
        classification: int = 3,
        title: str = 'title',
        num_pages: int = 2,
        ext: str = '.jpg',
        pages: list[dict[str, Any]] | None = None,
):
    from src.service.artwork_proxy.models import ArtworkProxyData

    return ArtworkProxyData.model_validate({
        'origin': 'unit_test_proxy', 'aid': aid, 'uid': '456', 'title': title, 'uname': 'uname',
        'classification': classification, 'rating': rating, 'width': 100, 'height': 200,
        'tags': ['tag1', 'tag2'], 'description': 'desc',
        'source': f'https://unit.test/artwork/{aid}',
        'pages': [make_page(i, ext=ext) for i in range(num_pages)] if pages is None else pages,
        'published_at': '2024-01-01T00:00:00',
    })


def make_pool_data(pool_id: str = 'p1', *, name: str = 'pool name', artwork_ids: list[str] | None = None):
    from src.service.artwork_proxy.models import ArtworkPoolData

    return ArtworkPoolData.model_validate({
        'origin': 'unit_test_proxy', 'pool_id': pool_id, 'name': name,
        'artwork_ids': ['1', '2'] if artwork_ids is None else artwork_ids,
    })


def make_user_data(uid: str = '456', artwork_ids: list[str] | None = None):
    from src.service.artwork_proxy.models import ArtistUserData

    return ArtistUserData.model_validate({
        'origin': 'unit_test_proxy', 'uid': uid, 'name': 'uname',
        'artwork_ids': ['1'] if artwork_ids is None else artwork_ids,
    })


@pytest.fixture
def proxy_factory() -> SimpleNamespace:
    """构造受控的 BaseArtworkProxy 测试子类及钩子 mocks(每个测试独立子类, 避免 _path_config 类级缓存串扰)"""
    from src.service.artwork_proxy.internal import BaseArtworkProxy

    hooks = SimpleNamespace(
        get_resource_as_bytes=AsyncMock(return_value=b'page-bytes'),
        random=AsyncMock(return_value=[]),
        search=AsyncMock(return_value=[]),
        query=AsyncMock(),
        std_desc=AsyncMock(return_value='std desc'),
        std_preview_desc=AsyncMock(return_value='preview desc'),
        query_pool=AsyncMock(),
        discovery=AsyncMock(return_value=[]),
        recommend=AsyncMock(return_value=[]),
        daily_ranking=AsyncMock(return_value=[]),
        weekly_ranking=AsyncMock(return_value=[]),
        monthly_ranking=AsyncMock(return_value=[]),
        query_user=AsyncMock(),
        query_user_bookmark_artworks=AsyncMock(return_value=[]),
        query_follow_latest=AsyncMock(return_value=[]),
    )

    class _TestArtworkProxy(BaseArtworkProxy):
        @classmethod
        def _get_base_origin_name(cls) -> str:
            return 'unit_test_proxy'

        @classmethod
        async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
            return await hooks.get_resource_as_bytes(url, timeout=timeout)

        @classmethod
        async def _random(cls, *, limit: int = 20) -> list[str | int]:
            return await hooks.random(limit=limit)

        @classmethod
        async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
            return await hooks.search(keyword, page=page, **kwargs)

        async def _query(self):
            return await hooks.query(self)

        async def get_std_desc(self, *, split_len: int = 128) -> str:
            return await hooks.std_desc(self, split_len=split_len)

        async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
            return await hooks.std_preview_desc(self, split_len=split_len)

        @classmethod
        async def _query_pool(cls, pool_id: str | int):
            return await hooks.query_pool(pool_id)

        @classmethod
        async def _discovery(cls, *, limit: int = 20) -> list[str | int]:
            return await hooks.discovery(limit=limit)

        @classmethod
        async def _recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[str | int]:
            return await hooks.recommend(base_aid=base_aid, limit=limit)

        @classmethod
        async def _daily_ranking(cls, page: int) -> list[str | int]:
            return await hooks.daily_ranking(page)

        @classmethod
        async def _weekly_ranking(cls, page: int) -> list[str | int]:
            return await hooks.weekly_ranking(page)

        @classmethod
        async def _monthly_ranking(cls, page: int) -> list[str | int]:
            return await hooks.monthly_ranking(page)

        @classmethod
        async def _query_user(cls, uid: str | int):
            return await hooks.query_user(uid)

        @classmethod
        async def _query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[str | int]:
            return await hooks.query_user_bookmark_artworks(uid, page)

        @classmethod
        async def _query_follow_latest(cls, page: int, *, filter_tag: str | None = None) -> list[str | int]:
            return await hooks.query_follow_latest(page, filter_tag=filter_tag)

    return SimpleNamespace(cls=_TestArtworkProxy, hooks=hooks)


@pytest.fixture
def fake_artwork_dal(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """以记录调用的伪 DAL 替换 ArtworkCollectionDAL.create, 不触真实数据库"""
    from src.database.internal.artwork_collection import ArtworkCollectionDAL

    dal = SimpleNamespace(
        query_by_condition=AsyncMock(return_value=[]),
        query_classification_statistic=AsyncMock(return_value='classification_stat'),
        query_rating_statistic=AsyncMock(return_value='rating_stat'),
        query_user_all_aids=AsyncMock(return_value=[]),
        query_exists_aids=AsyncMock(return_value=[]),
        query_not_exists_aids=AsyncMock(return_value=[]),
        query_unique=AsyncMock(return_value='artwork_from_db'),
        add_artwork_update_exist=AsyncMock(),
        add_artwork_ignore_exist=AsyncMock(),
        delete=AsyncMock(),
    )

    @asynccontextmanager
    async def _create(_cls):
        yield dal

    monkeypatch.setattr(ArtworkCollectionDAL, 'create', classmethod(_create))
    return dal


@pytest.fixture
def fake_image_ops(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """替换 internal 模块内的 ArtworkImageOps, 记录 mark/noise/blur 调用并返回伪图片对象"""
    import src.service.artwork_proxy.internal as internal

    class _FakeImage:
        def __init__(self, tag: str):
            self.tag = tag
            self.saved_files: list = []

        async def save(self, file):
            self.saved_files.append(file)
            return file

        async def async_get_bytes(self, *, format_: str = 'JPEG') -> bytes:
            return self.tag.encode()

    calls: list[tuple[str, Any, str]] = []

    async def _handle_mark(image, origin_mark):
        calls.append(('mark', image, origin_mark))
        return _FakeImage('mark')

    async def _handle_blur(image, origin_mark):
        calls.append(('blur', image, origin_mark))
        return _FakeImage('blur')

    async def _handle_noise(image, origin_mark):
        calls.append(('noise', image, origin_mark))
        return _FakeImage('noise')

    ops = SimpleNamespace(
        handle_mark=_handle_mark,
        handle_blur=_handle_blur,
        handle_noise=_handle_noise,
        generate_preview_image=AsyncMock(),
    )
    monkeypatch.setattr(internal, 'ArtworkImageOps', ops)
    return SimpleNamespace(ops=ops, calls=calls)


class TestBasicInterface:
    """基类标识、id 与路径属性测试"""

    def test_base_class_cannot_instantiate(self):
        from src.service.artwork_proxy.internal import BaseArtworkProxy

        with pytest.raises(TypeError):
            BaseArtworkProxy('1')

    def test_init_coerces_id_to_str(self, proxy_factory: SimpleNamespace):
        assert proxy_factory.cls(123).s_aid == '123'
        assert proxy_factory.cls('007').s_aid == '007'

    @pytest.mark.parametrize(
        ('aid', 'expected'),
        [
            ('a/b', f'a_b.{hashlib.sha256(b'a/b').hexdigest()[:4]}'),
            ('a\\b', f'a_b.{hashlib.sha256(b'a\\b').hexdigest()[:4]}'),
            ('a//b', f'a__b.{hashlib.sha256(b'a//b').hexdigest()[:4]}'),
            ('a:b', f'a_b.{hashlib.sha256(b'a:b').hexdigest()[:4]}'),
            ('a*b', f'a_b.{hashlib.sha256(b'a*b').hexdigest()[:4]}'),
            ('a\x00b', f'a_b.{hashlib.sha256(b'a\x00b').hexdigest()[:4]}'),
            ('', hashlib.sha256(b'').hexdigest()[:16]),
            ('.', hashlib.sha256(b'.').hexdigest()[:16]),
            ('..', hashlib.sha256(b'..').hexdigest()[:16]),
            ('CON', hashlib.sha256(b'CON').hexdigest()[:16]),
            ('com1', hashlib.sha256(b'com1').hexdigest()[:16]),
        ],
    )
    def test_init_cleans_invalid_aid(self, proxy_factory: SimpleNamespace, aid: str, expected: str):
        """非法文件名字符清洗为下划线并追加短哈希后缀防碰撞, 保留设备名与全空输入回退 sha256 哈希"""
        assert proxy_factory.cls(aid).s_aid == expected

    @pytest.mark.parametrize(
        ('raw', 'expected'),
        [
            ('  padded  ', f'padded.{hashlib.sha256(b'  padded  ').hexdigest()[:4]}'),
            ('name.', f'name.{hashlib.sha256(b'name.').hexdigest()[:4]}'),
            ('name. ', f'name.{hashlib.sha256(b'name. ').hexdigest()[:4]}'),
            ('a\x01b', f'a_b.{hashlib.sha256(b'a\x01b').hexdigest()[:4]}'),
            ('a\tb', f'a_b.{hashlib.sha256(b'a\tb').hexdigest()[:4]}'),
            ('a<b>c', f'a_b_c.{hashlib.sha256(b'a<b>c').hexdigest()[:4]}'),
            ('nul.txt', hashlib.sha256(b'nul.txt').hexdigest()[:16]),
            ('dot..inside', 'dot..inside'),
            ('.hidden', '.hidden'),
        ],
    )
    def test_clean_file_name_edge_semantics(self, proxy_factory: SimpleNamespace, raw: str, expected: str):
        """清洗边界语义: 首尾空白/尾点剥离, 控制字符替换, 保留设备名(含扩展名形式)回退, 合法点号保留"""
        assert proxy_factory.cls._clean_file_name(raw) == expected

    def test_clean_file_name_default_max_length(self):
        import src.service.artwork_proxy.internal as internal

        assert internal._FILE_NAME_MAX_LENGTH == 128

    @pytest.mark.parametrize(('raw', 'expect_unchanged'), [('a' * 128, True), ('a' * 129, False), ('a' * 200, False)])
    def test_clean_file_name_length_limit(self, proxy_factory: SimpleNamespace, raw: str, expect_unchanged: bool):
        """超长文件名截断至上限并追加短哈希后缀(恰为上限时原样保留)"""
        result = proxy_factory.cls._clean_file_name(raw)
        if expect_unchanged:
            assert result == raw
        else:
            assert len(result) == 128
            assert result == f'{'a' * 123}.{hashlib.sha256(raw.encode()).hexdigest()[:4]}'

    def test_clean_file_name_truncates_after_cleaning(self, proxy_factory: SimpleNamespace):
        """清洗改变原始值且基名超出 123 时, 基名截断至 123 并追加短哈希后缀(总长不超上限)"""
        raw = 'a/' + 'b' * 124  # 清洗后为 'a_b' + 'b'*124, 共 127 字符
        result = proxy_factory.cls._clean_file_name(raw)
        assert len(result) == 128
        assert result == f'{'a_b' + 'b' * 120}.{hashlib.sha256(raw.encode()).hexdigest()[:4]}'

    def test_clean_file_name_max_length_is_dynamic(
            self, proxy_factory: SimpleNamespace, monkeypatch: pytest.MonkeyPatch,
    ):
        """长度上限为模块级变量, 运行时读取(可配置)"""
        import src.service.artwork_proxy.internal as internal

        monkeypatch.setattr(internal, '_FILE_NAME_MAX_LENGTH', 16)
        raw = 'a/very/long/path'
        result = proxy_factory.cls._clean_file_name(raw)
        assert len(result) == 16
        assert result == f'a_very_long.{hashlib.sha256(raw.encode()).hexdigest()[:4]}'

    def test_i_aid_decimal(self, proxy_factory: SimpleNamespace):
        assert proxy_factory.cls('123').i_aid == 123

    @pytest.mark.parametrize('aid', ['abc', '-1', '1.5'])
    def test_i_aid_non_decimal_raises(self, proxy_factory: SimpleNamespace, aid: str):
        proxy = proxy_factory.cls(aid)
        with pytest.raises(ValueError, match='is not a number'):
            proxy.i_aid  # noqa: B018

    def test_repr(self, proxy_factory: SimpleNamespace):
        assert repr(proxy_factory.cls('123')) == '_TestArtworkProxy(origin=unit_test_proxy, artwork_id=123)'

    def test_origin_name_and_get_origin_name(self, proxy_factory: SimpleNamespace):
        assert proxy_factory.cls.get_origin_name() == 'unit_test_proxy'
        assert proxy_factory.cls('1').origin_name == 'unit_test_proxy'

    def test_path_config_cached_per_class(self, proxy_factory: SimpleNamespace):
        proxy = proxy_factory.cls('1')
        assert proxy.path_config is proxy.path_config

        class _OtherProxy(proxy_factory.cls):
            @classmethod
            def _get_base_origin_name(cls) -> str:
                return 'other_unit_test_proxy'

        other = _OtherProxy('1')
        assert other.path_config is not proxy.path_config
        assert other.path_config.base_path.name == 'other_unit_test_proxy'

    @pytest.mark.parametrize(
        ('aid', 'expected'),
        [
            ('0', 'artwork_id_0-999999'),
            ('999999', 'artwork_id_0-999999'),
            ('1000000', 'artwork_id_1000000-1999999'),
        ],
    )
    def test_sliced_aid_subdir_numeric(self, proxy_factory: SimpleNamespace, aid: str, expected: str):
        assert proxy_factory.cls(aid).sliced_aid_subdir_name == expected

    def test_sliced_aid_subdir_numeric_upper_boundary(self, proxy_factory: SimpleNamespace):
        assert proxy_factory.cls(str(10 ** 12)).sliced_aid_subdir_name == 'artwork_id_1000000000000-1000000999999'

        hashed = proxy_factory.cls(str(10 ** 12 + 1)).sliced_aid_subdir_name
        assert re.fullmatch(r'artwork_id_H[0-9a-f]{3}', hashed) is not None

    @pytest.mark.parametrize('aid', ['abc', '-1'])
    def test_sliced_aid_subdir_non_decimal_hashed(self, proxy_factory: SimpleNamespace, aid: str):
        expected_hash = hashlib.sha256(unicodedata.normalize('NFC', aid).encode('utf-8')).hexdigest()[:3]
        assert proxy_factory.cls(aid).sliced_aid_subdir_name == f'artwork_id_H{expected_hash}'

    def test_sliced_aid_subdir_nfc_normalization(self, proxy_factory: SimpleNamespace):
        composed = proxy_factory.cls('é').sliced_aid_subdir_name
        decomposed = proxy_factory.cls('é').sliced_aid_subdir_name
        assert composed == decomposed

    @pytest.mark.parametrize(
        ('url', 'expected'),
        [
            ('https://example.com/path/image.jpg', '.jpg'),
            ('https://example.com/path/image.JPG', '.JPG'),
            ('https://example.com/image.jpg?query=.png', '.jpg'),
            ('https://example.com/image.jpg#frag', '.jpg'),
            ('https://example.com/path/', ''),
            ('https://example.com/file', ''),
            ('https://example.com/%E5%9B%BE.jpg', '.jpg'),
            ('https://example.com/archive.tar.gz', '.gz'),
            ('https://example.com/.hidden', ''),
        ],
    )
    def test_parse_url_file_suffix(self, proxy_factory: SimpleNamespace, url: str, expected: str):
        assert proxy_factory.cls.parse_url_file_suffix(url) == expected

    def test_meta_file_and_paths(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        proxy = proxy_factory.cls('123')
        base = isolated_temporary_root / 'unit_test_proxy'
        assert proxy.meta_path.path == base / 'metadata' / 'artwork_id_0-999999'
        assert proxy.artwork_path.path == base / 'artwork' / 'artwork_id_0-999999'
        assert proxy.meta_file.name == '123.json'
        assert re.fullmatch(r'123\.\d{20}\.json\.snapshot', proxy.meta_file_date_snapshot.name) is not None

    def test_pool_meta_file_cleans_pool_id(self, proxy_factory: SimpleNamespace):
        """pool_id 非法文件名字符被清洗(sanitize 实现)"""
        file = proxy_factory.cls._get_pool_meta_file(pool_id='a/b')
        assert file.name == f'pool_a_b.{hashlib.sha256(b'a/b').hexdigest()[:4]}.json'

    def test_user_meta_file_cleans_uid(self, proxy_factory: SimpleNamespace):
        """uid 非法文件名字符被清洗(sanitize 实现), 清洗后不产生路径嵌套"""
        file = proxy_factory.cls._get_user_meta_file(uid='../x')
        assert file.name == f'user_.._x.{hashlib.sha256(b'../x').hexdigest()[:4]}.json'

    def test_all_exports_complete(self):
        """__all__ 须导出全部已注册 proxy 类(含 BilibiliDynamic/TweetPic)"""
        import src.service.artwork_proxy as artwork_proxy

        for name in ('BilibiliDynamicPicArtworkProxy', 'TweetPicArtworkProxy'):
            assert name in artwork_proxy.__all__
            assert hasattr(artwork_proxy, name)

    def test_artwork_proxy_registry(self):
        from src.service.artwork_proxy import get_artwork_proxy, get_available_artwork_proxy_origin_name
        from src.service.artwork_proxy.sites.pixiv import PixivArtworkProxy

        assert get_artwork_proxy('pixiv') is PixivArtworkProxy
        origins = get_available_artwork_proxy_origin_name()
        assert 'pixiv' in origins
        assert 'local_collected_artwork' in origins
        with pytest.raises(KeyError):
            get_artwork_proxy('not_exist_origin')

    def test_path_config_fonts(self, proxy_factory: SimpleNamespace):
        path_config = proxy_factory.cls._get_path_config()
        assert path_config.text_font.name == 'SourceHanSansSC-Regular.otf'
        assert path_config.theme_font.name == 'fzzxhk.ttf'


class TestArtworkMetaCache:
    """作品元数据缓存(_fast_query/query/_dumps_meta)测试"""

    async def test_fast_query_cold_writes_meta_and_snapshot(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        from src.service.artwork_proxy.models import ArtworkProxyData

        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        result = await proxy.query()

        proxy_factory.hooks.query.assert_awaited_once()
        assert result == proxy_factory.hooks.query.return_value
        assert proxy.meta_file.is_file
        async with proxy.meta_file.async_open('r', encoding='utf-8') as af:
            cached = ArtworkProxyData.model_validate_json(await af.read())
        assert cached == result

        snapshots = [f for f in proxy.meta_path.list_all_files() if f.name.endswith('.json.snapshot')]
        assert len(snapshots) == 1
        assert re.fullmatch(r'123\.\d{20}\.json\.snapshot', snapshots[0].name) is not None

    async def test_dumps_meta_prunes_snapshots(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        """快照按保留上限裁剪, 仅保留最新 8 份(时间戳定宽, 名称序即时间序)"""
        import src.service.artwork_proxy.internal as internal

        class _FakeDatetime(datetime):
            _counter = 0

            @classmethod
            def now(cls, tz=None) -> datetime:
                cls._counter += 1
                return datetime(2026, 1, 1) + timedelta(microseconds=cls._counter)

        monkeypatch.setattr(internal, 'datetime', _FakeDatetime)
        proxy = proxy_factory.cls('123')
        data = make_artwork_data()

        for _ in range(10):
            await proxy._dumps_meta(artwork_data=data)

        snapshots = sorted(f.name for f in proxy.meta_path.list_all_files() if f.name.endswith('.json.snapshot'))
        expected = [
            f'123.{(datetime(2026, 1, 1) + timedelta(microseconds=i)).strftime('%Y%m%d%H%M%S%f')}.json.snapshot'
            for i in range(3, 11)
        ]
        assert len(snapshots) == 8
        assert snapshots == expected

    async def test_fast_query_warm_uses_cache(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        data = make_artwork_data()
        proxy = proxy_factory.cls('123')
        async with proxy.meta_file.async_open('w', encoding='utf-8') as af:
            await af.write(data.model_dump_json())

        result = await proxy.query()

        proxy_factory.hooks.query.assert_not_awaited()
        assert result == data

    async def test_fast_query_use_cache_false_rewrites(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        from src.service.artwork_proxy.models import ArtworkProxyData

        proxy = proxy_factory.cls('123')
        async with proxy.meta_file.async_open('w', encoding='utf-8') as af:
            await af.write(make_artwork_data(title='old title').model_dump_json())
        proxy_factory.hooks.query.return_value = make_artwork_data(title='new title')

        result = await proxy.query(use_cache=False)

        proxy_factory.hooks.query.assert_awaited_once()
        assert result.title == 'new title'
        async with proxy.meta_file.async_open('r', encoding='utf-8') as af:
            assert ArtworkProxyData.model_validate_json(await af.read()).title == 'new title'

    @pytest.mark.parametrize(
        ('content', 'open_mode'),
        [
            pytest.param(b'not json', 'wb', id='corrupt_json'),
            pytest.param('{"foo": 1}', 'w', id='schema_mismatch'),
            pytest.param('', 'w', id='empty_file'),
            pytest.param(b'\xff\xfe\xff', 'wb', id='corrupt_encoding'),
        ],
    )
    async def test_fast_query_invalid_cache_requery(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
            content: str | bytes, open_mode: str,
    ):
        """缓存文件损坏(非法 JSON / schema 不符 / 空文件 / 非 UTF-8 编码)时应回源重建, 而非外抛解析异常"""
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')
        open_kwargs = {} if 'b' in open_mode else {'encoding': 'utf-8'}
        async with proxy.meta_file.async_open(open_mode, **open_kwargs) as af:
            await af.write(content)

        result = await proxy.query()

        proxy_factory.hooks.query.assert_awaited_once()
        assert result == proxy_factory.hooks.query.return_value

    async def test_query_memoizes_on_instance(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        first = await proxy.query()
        second = await proxy.query()

        assert first is second
        proxy_factory.hooks.query.assert_awaited_once()

    async def test_query_new_instance_reads_cache(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        data = make_artwork_data()
        proxy = proxy_factory.cls('123')
        async with proxy.meta_file.async_open('w', encoding='utf-8') as af:
            await af.write(data.model_dump_json())

        other = proxy_factory.cls('123')
        result = await other.query()

        proxy_factory.hooks.query.assert_not_awaited()
        assert result == data


class TestPageFiles:
    """作品页面文件获取/缓存(_save_page/_load_page 等)测试"""

    @pytest.mark.parametrize(
        ('page_type', 'url_part'),
        [
            ('preview', '0_preview.jpg'),
            ('regular', '0_regular.jpg'),
            ('original', '0_original.jpg'),
        ],
    )
    async def test_save_page_type_dispatch(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path, page_type: str, url_part: str,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        result = await proxy.get_page_file(page_type=page_type)

        proxy_factory.hooks.get_resource_as_bytes.assert_awaited_once_with(
            f'https://unit.test/{url_part}', timeout=30,
        )
        assert result.name == f'123_{page_type}_p0.jpg'

    async def test_save_page_unknown_type_falls_back_to_regular(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        """未知 page_type 静默回退到 regular 文件, 但文件名沿用传入类型串(文档化现状)"""
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        result = await proxy.get_page_file(page_type='other')

        proxy_factory.hooks.get_resource_as_bytes.assert_awaited_once_with(
            'https://unit.test/0_regular.jpg', timeout=30,
        )
        assert result.name == '123_other_p0.jpg'

    @pytest.mark.parametrize(
        ('ext', 'expected_name'),
        [
            ('.jpg', '123_regular_p0.jpg'),
            ('jpg', '123_regular_p0.jpg'),
            ('', f'123_regular_p0.{hashlib.sha256(b'').hexdigest()[:16]}'),
        ],
    )
    async def test_save_page_file_ext_stripped(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path, ext: str, expected_name: str,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data(ext=ext)
        proxy = proxy_factory.cls('123')

        result = await proxy.get_page_file()

        assert result.name == expected_name

    async def test_save_page_existing_file_skips_download(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')
        target = proxy.artwork_path('123_regular_p0.jpg')
        async with target.async_open('wb') as af:
            await af.write(b'cached-content')

        result = await proxy.get_page_file()

        proxy_factory.hooks.get_resource_as_bytes.assert_not_awaited()
        assert result.path == target.path

    async def test_save_page_downloads_and_persists(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        result = await proxy.get_page_file()

        assert result.is_file
        async with result.async_open('rb') as af:
            assert await af.read() == b'page-bytes'

    async def test_save_page_cleans_file_ext(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        """file_ext 非法文件名字符被清洗(sanitize 实现)"""
        proxy_factory.hooks.query.return_value = make_artwork_data(ext='a/b')
        proxy = proxy_factory.cls('123')

        result = await proxy.get_page_file()

        assert result.name == f'123_regular_p0.a_b.{hashlib.sha256(b'a/b').hexdigest()[:4]}'
        assert result.is_file

    async def test_save_page_atomic_write_no_temp_left(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        await proxy.get_page_file()

        names = [f.name for f in proxy.artwork_path.list_all_files()]
        assert names == ['123_regular_p0.jpg']

    async def test_save_page_concurrent_same_page_single_download(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        cls = proxy_factory.cls

        results = await asyncio.gather(*(cls('123').get_page_file() for _ in range(5)))

        # 进程内锁 + 二次检查, 同一页并发获取仅下载一次
        proxy_factory.hooks.get_resource_as_bytes.assert_awaited_once()
        assert {r.name for r in results} == {'123_regular_p0.jpg'}
        for r in results:
            assert r.is_file

    async def test_save_page_missing_page_index_raises(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        with pytest.raises(ValueError, match='has no page'):
            await proxy.get_page_file(page_index=9)

    async def test_get_page_bytes_roundtrip(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        content = await proxy.get_page_bytes()

        assert content == b'page-bytes'

    async def test_download_page_uses_original(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        result = await proxy.download_page()

        proxy_factory.hooks.get_resource_as_bytes.assert_awaited_once_with(
            'https://unit.test/0_original.jpg', timeout=30,
        )
        assert result.name == '123_original_p0.jpg'

    async def test_download_all_pages_uses_original_for_all(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data(num_pages=2)
        proxy = proxy_factory.cls('123')

        result = await proxy.download_all_pages()

        assert {f.name for f in result} == {'123_original_p0.jpg', '123_original_p1.jpg'}
        for call in proxy_factory.hooks.get_resource_as_bytes.await_args_list:
            assert '_original.jpg' in call.args[0]

    @pytest.mark.parametrize(
        ('page_limit', 'expected_names'),
        [
            (2, {'123_regular_p0.jpg', '123_regular_p1.jpg'}),
            (0, {'123_regular_p0.jpg', '123_regular_p1.jpg', '123_regular_p2.jpg'}),
            (99, {'123_regular_p0.jpg', '123_regular_p1.jpg', '123_regular_p2.jpg'}),
        ],
    )
    async def test_get_all_pages_file_limit(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
            page_limit: int, expected_names: set[str],
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data(num_pages=3)
        proxy = proxy_factory.cls('123')

        result = await proxy.get_all_pages_file(page_limit=page_limit)

        assert {f.name for f in result} == expected_names

    async def test_duplicate_page_index_raises_value_error(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data(pages=[make_page(0), make_page(0)])
        proxy = proxy_factory.cls('123')

        with pytest.raises(ValueError, match='erroneous or duplicate'):
            await proxy.get_page_file()


class TestPool:
    """图集元数据缓存与图集查询测试"""

    def test_pool_meta_file_naming(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        file = proxy_factory.cls._get_pool_meta_file(pool_id='p1')
        assert file.path == isolated_temporary_root / 'unit_test_proxy' / 'metadata' / 'pool' / 'pool_p1.json'

    async def test_fast_query_pool_cold_and_warm(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        proxy_factory.hooks.query_pool.return_value = make_pool_data()
        cls = proxy_factory.cls

        first = await cls.query_pool('p1')
        second = await cls.query_pool('p1')

        proxy_factory.hooks.query_pool.assert_awaited_once()
        assert first == second

    async def test_fast_query_pool_use_cache_false(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        cls = proxy_factory.cls
        async with cls._get_pool_meta_file(pool_id='p1').async_open('w', encoding='utf-8') as af:
            await af.write(make_pool_data(name='stale name').model_dump_json())
        proxy_factory.hooks.query_pool.return_value = make_pool_data(name='fresh name')

        result = await cls.query_pool('p1', use_cache=False)

        proxy_factory.hooks.query_pool.assert_awaited_once()
        assert result.name == 'fresh name'

    async def test_fast_query_pool_corrupt_requery(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        cls = proxy_factory.cls
        async with cls._get_pool_meta_file(pool_id='p1').async_open('wb') as af:
            await af.write(b'not json')
        proxy_factory.hooks.query_pool.return_value = make_pool_data()

        result = await cls.query_pool('p1')

        proxy_factory.hooks.query_pool.assert_awaited_once()
        assert result == make_pool_data()

    async def test_query_pool_all_artworks(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        async def _query_side_effect(proxy_self):
            return make_artwork_data(aid=proxy_self.s_aid)

        proxy_factory.hooks.query_pool.return_value = make_pool_data(artwork_ids=['1', '2'])
        proxy_factory.hooks.query.side_effect = _query_side_effect

        result = await proxy_factory.cls.query_pool_all_artworks('p1')

        assert [d.aid for d in result] == ['1', '2']

    async def test_query_pool_all_artworks_empty_pool(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query_pool.return_value = make_pool_data(artwork_ids=[])

        result = await proxy_factory.cls.query_pool_all_artworks('p1')

        assert result == []
        proxy_factory.hooks.query.assert_not_awaited()

    async def test_query_pool_all_artwork_pages(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        async def _query_side_effect(proxy_self):
            return make_artwork_data(aid=proxy_self.s_aid)

        proxy_factory.hooks.query_pool.return_value = make_pool_data(artwork_ids=['1', '2'])
        proxy_factory.hooks.query.side_effect = _query_side_effect

        result = await proxy_factory.cls.query_pool_all_artwork_pages('p1')

        assert {f.name for f in result} == {'1_regular_p0.jpg', '2_regular_p0.jpg'}

    async def test_generate_pool_preview_delegates(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        proxy_factory.hooks.query_pool.return_value = make_pool_data(pool_id='p1', artwork_ids=['1', '2'])
        captured = {}

        @classmethod
        async def _fake_generate(cls, preview_name, artworks, **kwargs):
            captured['preview_name'] = preview_name
            captured['artworks'] = list(artworks)
            captured['kwargs'] = kwargs
            return 'sentinel-file'

        monkeypatch.setattr(proxy_factory.cls, 'generate_artworks_preview', _fake_generate)

        result = await proxy_factory.cls.generate_pool_preview('p1')

        assert result == 'sentinel-file'
        assert captured['preview_name'] == 'Unit_Test_Proxy Pool #p1: pool name'
        assert [a.s_aid for a in captured['artworks']] == ['1', '2']


class TestUserSpace:
    """用户空间(用户元数据缓存/作品列表/收藏/关注)测试"""

    def test_user_meta_file_naming(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        file = proxy_factory.cls._get_user_meta_file(uid='456')
        assert file.path == isolated_temporary_root / 'unit_test_proxy' / 'metadata' / 'user' / 'user_456.json'

    async def test_fast_query_user_cold_and_warm(self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path):
        proxy_factory.hooks.query_user.return_value = make_user_data()
        cls = proxy_factory.cls

        first = await cls.query_user('456')
        second = await cls.query_user('456')

        proxy_factory.hooks.query_user.assert_awaited_once()
        assert first == second

    async def test_fast_query_user_corrupt_requery(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        cls = proxy_factory.cls
        async with cls._get_user_meta_file(uid='456').async_open('wb') as af:
            await af.write(b'not json')
        proxy_factory.hooks.query_user.return_value = make_user_data()

        result = await cls.query_user('456')

        proxy_factory.hooks.query_user.assert_awaited_once()
        assert result == make_user_data()

    async def test_query_user_artworks_bypasses_cache(
            self, proxy_factory: SimpleNamespace, isolated_temporary_root: Path,
    ):
        """query_user_artworks 内部固定 use_cache=False, 即使存在陈旧缓存也必须回源"""
        cls = proxy_factory.cls
        async with cls._get_user_meta_file(uid='456').async_open('w', encoding='utf-8') as af:
            await af.write(make_user_data(artwork_ids=['stale']).model_dump_json())
        proxy_factory.hooks.query_user.return_value = make_user_data(artwork_ids=['7', '8'])

        result = await cls.query_user_artworks('456')

        proxy_factory.hooks.query_user.assert_awaited_once()
        assert [x.s_aid for x in result] == ['7', '8']

    @pytest.mark.parametrize(('page', 'expected_page'), [(0, 1), (-5, 1), (3, 3)])
    async def test_query_user_bookmark_artworks_clamps_page(
            self, proxy_factory: SimpleNamespace, page: int, expected_page: int,
    ):
        proxy_factory.hooks.query_user_bookmark_artworks.return_value = ['1']

        result = await proxy_factory.cls.query_user_bookmark_artworks('456', page)

        proxy_factory.hooks.query_user_bookmark_artworks.assert_awaited_once_with('456', expected_page)
        assert [x.s_aid for x in result] == ['1']

    async def test_query_follow_latest_passthrough(self, proxy_factory: SimpleNamespace):
        proxy_factory.hooks.query_follow_latest.return_value = ['9']

        result = await proxy_factory.cls.query_follow_latest(2, filter_tag='tag')

        proxy_factory.hooks.query_follow_latest.assert_awaited_once_with(2, filter_tag='tag')
        assert [x.s_aid for x in result] == ['9']


class TestSiteListing:
    """列表类接口(random/search/discovery/recommend/ranking)测试"""

    @pytest.mark.parametrize(
        ('method', 'hook_name', 'call_args', 'call_kwargs', 'expected_hook_call'),
        [
            pytest.param('random', 'random', (), {'limit': 5}, ((), {'limit': 5}), id='random'),
            pytest.param(
                'search', 'search', ('kw',), {'page': 2, 'extra': 'x'}, (('kw',), {'page': 2, 'extra': 'x'}),
                id='search',
            ),
            pytest.param('discovery', 'discovery', (), {'limit': 7}, ((), {'limit': 7}), id='discovery'),
            pytest.param(
                'recommend', 'recommend', (), {'base_aid': 100, 'limit': 2}, ((), {'base_aid': 100, 'limit': 2}),
                id='recommend',
            ),
        ],
    )
    async def test_listing_wraps_ids(
            self, proxy_factory: SimpleNamespace,
            method: str, hook_name: str,
            call_args: tuple, call_kwargs: dict[str, Any],
            expected_hook_call: tuple[tuple, dict[str, Any]],
    ):
        """列表接口将 id 列表包装为实例并原样透传参数"""
        hook = getattr(proxy_factory.hooks, hook_name)
        hook.return_value = [1, 'a']

        result = await getattr(proxy_factory.cls, method)(*call_args, **call_kwargs)

        hook.assert_awaited_once_with(*expected_hook_call[0], **expected_hook_call[1])
        assert [x.s_aid for x in result] == ['1', 'a']
        assert all(isinstance(x, proxy_factory.cls) for x in result)

    @pytest.mark.parametrize(
        ('mode', 'hook_name'),
        [
            ('daily', 'daily_ranking'),
            ('weekly', 'weekly_ranking'),
            ('monthly', 'monthly_ranking'),
        ],
    )
    async def test_ranking_dispatch(self, proxy_factory: SimpleNamespace, mode: str, hook_name: str):
        hook = getattr(proxy_factory.hooks, hook_name)
        hook.return_value = ['1']

        result = await proxy_factory.cls.ranking(mode, 2)

        hook.assert_awaited_once_with(2)
        assert [x.s_aid for x in result] == ['1']

    async def test_ranking_unknown_mode_falls_back_to_monthly(self, proxy_factory: SimpleNamespace):
        """未知 mode 静默回退到 monthly(文档化现状)"""
        proxy_factory.hooks.monthly_ranking.return_value = []

        await proxy_factory.cls.ranking('other', 1)

        proxy_factory.hooks.monthly_ranking.assert_awaited_once_with(1)
        proxy_factory.hooks.daily_ranking.assert_not_awaited()
        proxy_factory.hooks.weekly_ranking.assert_not_awaited()

    @pytest.mark.parametrize(('page', 'expected_page'), [(0, 1), (-1, 1), (3, 3)])
    async def test_ranking_clamps_page(self, proxy_factory: SimpleNamespace, page: int, expected_page: int):
        proxy_factory.hooks.daily_ranking.return_value = []

        await proxy_factory.cls.ranking('daily', page)

        proxy_factory.hooks.daily_ranking.assert_awaited_once_with(expected_page)


class TestImageProcessing:
    """作品图片处理(_process_artwork_page/get_auto_proceed_page_file/_get_preview_thumb_data)测试"""

    @pytest.mark.parametrize(
        ('process_mode', 'expected_tag', 'expected_suffix'),
        [
            ('mark', 'mark', '_marked.jpg'),
            ('noise', 'noise', '_noise_sigma16_marked.jpg'),
            ('blur', 'blur', '_blur_marked.jpg'),
        ],
    )
    async def test_process_artwork_page_mode_dispatch(
            self, proxy_factory: SimpleNamespace, fake_image_ops: SimpleNamespace, isolated_temporary_root: Path,
            process_mode: str, expected_tag: str, expected_suffix: str,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        result = await proxy.get_custom_proceed_page_file(process_mode=process_mode)

        assert len(fake_image_ops.calls) == 1
        tag, _image, origin_mark = fake_image_ops.calls[0]
        assert tag == expected_tag
        assert origin_mark == 'Unit_Test_Proxy | 123'
        assert result.name == f'123_regular_p0{expected_suffix}'

    async def test_process_artwork_page_unknown_mode_falls_back_to_mark(
            self, proxy_factory: SimpleNamespace, fake_image_ops: SimpleNamespace, isolated_temporary_root: Path,
    ):
        """未知 process_mode 静默回退到 mark(文档化现状)"""
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        result = await proxy.get_custom_proceed_page_file(process_mode='other')

        assert [call[0] for call in fake_image_ops.calls] == ['mark']
        assert result.name == '123_regular_p0_marked.jpg'

    @pytest.mark.parametrize(
        ('rating', 'need_blur_rating', 'expected_tag'),
        [
            (0, 2, 'mark'),
            (1, 2, 'noise'),
            (2, 2, 'blur'),
            (3, 2, 'blur'),
            (-1, 2, 'blur'),
            (1, 1, 'blur'),
            (0, 0, 'mark'),
            (1, 0, 'blur'),
            (-1, 0, 'blur'),
            (1, -3, 'blur'),
        ],
    )
    async def test_auto_proceed_rating_matrix(
            self, proxy_factory: SimpleNamespace, fake_image_ops: SimpleNamespace, isolated_temporary_root: Path,
            rating: int, need_blur_rating: int, expected_tag: str,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data(rating=rating)
        proxy = proxy_factory.cls('123')

        await proxy.get_auto_proceed_page_file(need_blur_rating=need_blur_rating)

        assert [call[0] for call in fake_image_ops.calls] == [expected_tag]

    @pytest.mark.parametrize(
        ('rating', 'need_blur_rating', 'expected_tag'),
        [
            (0, 2, 'mark'),
            (1, 2, 'mark'),
            (-1, 2, 'blur'),
            (2, 2, 'blur'),
            (3, 2, 'blur'),
            (0, 0, 'blur'),
        ],
    )
    async def test_preview_thumb_rating_matrix(
            self, proxy_factory: SimpleNamespace, fake_image_ops: SimpleNamespace, isolated_temporary_root: Path,
            rating: int, need_blur_rating: int, expected_tag: str,
    ):
        """预览缩略图 0 <= rating < need_blur_rating 时打水印(mark), UNKNOWN 及其余一律模糊(blur)"""
        proxy_factory.hooks.query.return_value = make_artwork_data(rating=rating)
        proxy = proxy_factory.cls('123')

        item = await proxy._get_preview_thumb_data(need_blur_rating=need_blur_rating)

        assert [call[0] for call in fake_image_ops.calls] == [expected_tag]
        assert fake_image_ops.calls[0][2] == 'Unit_Test_Proxy | 123'
        assert item.desc_text == 'preview desc'
        assert item.thumb_data == expected_tag.encode()


class TestPreviewGeneration:
    """预览拼图数据收集与生成委托测试"""

    async def test_get_artworks_preview_data_applies_limit(
            self, proxy_factory: SimpleNamespace, fake_image_ops: SimpleNamespace, isolated_temporary_root: Path,
    ):
        async def _query_side_effect(proxy_self):
            return make_artwork_data(aid=proxy_self.s_aid)

        proxy_factory.hooks.query.side_effect = _query_side_effect
        artworks = [proxy_factory.cls(aid) for aid in ('1', '2', '3')]

        data = await proxy_factory.cls._get_artworks_preview_data('preview', artworks, limit=2)

        assert data.preview_name == 'preview'
        assert data.count == 2
        assert len(fake_image_ops.calls) == 2

    async def test_get_artworks_preview_data_filters_exceptions(
            self, proxy_factory: SimpleNamespace, fake_image_ops: SimpleNamespace, isolated_temporary_root: Path,
    ):
        async def _query_side_effect(proxy_self):
            if proxy_self.s_aid == 'bad':
                raise RuntimeError('boom')
            return make_artwork_data(aid=proxy_self.s_aid)

        proxy_factory.hooks.query.side_effect = _query_side_effect
        artworks = [proxy_factory.cls(aid) for aid in ('1', 'bad', '2')]

        data = await proxy_factory.cls._get_artworks_preview_data('preview', artworks)

        assert data.count == 2

    async def test_generate_artworks_preview_delegates(
            self, proxy_factory: SimpleNamespace, fake_image_ops: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        sentinel = object()
        fake_image_ops.ops.generate_preview_image.return_value = sentinel

        result = await proxy_factory.cls.generate_artworks_preview(
            preview_name='test preview',
            artworks=[proxy_factory.cls('123')],
            preview_size=(128, 128),
            limit=10,
        )

        assert result is sentinel
        fake_image_ops.ops.generate_preview_image.assert_awaited_once()
        call_kwargs = fake_image_ops.ops.generate_preview_image.await_args.kwargs
        assert call_kwargs['preview'].preview_name == 'test preview'
        assert call_kwargs['preview'].count == 1
        assert call_kwargs['preview_size'] == (128, 128)
        assert call_kwargs['font_path'].name == 'fzzxhk.ttf'
        assert call_kwargs['output_folder'].path == isolated_temporary_root / 'unit_test_proxy' / 'preview'
        assert call_kwargs['limit'] == 10

    async def test_generate_preview_image_stable_name(
            self, isolated_temporary_root: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        """预览图文件名使用稳定哈希前缀(跨进程一致), 不再使用内置 hash()"""
        from src.resource import StaticResource, TemporaryResource
        from src.service.artwork_proxy.models import PreviewImagesData
        from src.service.artwork_proxy.preview_image_utils import ArtworkImageOps

        monkeypatch.setattr(ArtworkImageOps, '_handle_preview_image', AsyncMock(return_value=b'jpeg-bytes'))
        preview = PreviewImagesData.model_validate({'preview_name': 'test', 'thumb_items': []})

        first = await ArtworkImageOps.generate_preview_image(
            preview=preview, preview_size=(256, 256),
            font_path=StaticResource('fonts', 'fzzxhk.ttf'),
            output_folder=TemporaryResource('preview_test'),
        )
        second = await ArtworkImageOps.generate_preview_image(
            preview=preview, preview_size=(256, 256),
            font_path=StaticResource('fonts', 'fzzxhk.ttf'),
            output_folder=TemporaryResource('preview_test'),
        )

        expected_prefix = f'preview_{hashlib.sha256(b'test').hexdigest()[:16]}_'
        assert first.name.startswith(expected_prefix)
        assert second.name.startswith(expected_prefix)
        assert first.is_file

    @pytest.mark.parametrize(
        'kwargs',
        [
            {'num_of_line': 0},
            {'preview_size': (10, 256)},
            {'edge_scale': 1.5},
            {'limit': 0},
        ],
    )
    async def test_generate_preview_image_invalid_params(self, isolated_temporary_root: Path, kwargs: dict):
        from src.resource import StaticResource, TemporaryResource
        from src.service.artwork_proxy.models import PreviewImagesData
        from src.service.artwork_proxy.preview_image_utils import ArtworkImageOps

        preview = PreviewImagesData.model_validate({'preview_name': 'test', 'thumb_items': []})
        base_kwargs = {
            'preview': preview, 'preview_size': (256, 256),
            'font_path': StaticResource('fonts', 'fzzxhk.ttf'), 'output_folder': TemporaryResource('preview_test'),
        }
        with pytest.raises(ValueError, match='must be'):
            await ArtworkImageOps.generate_preview_image(**(base_kwargs | kwargs))


class TestDatabaseOps:
    """数据库收录/查询(ArtworkCollectionDAL 交互)测试"""

    async def test_query_db_any_origin_by_condition_defaults(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        fake_artwork_dal.query_by_condition.return_value = [SimpleNamespace(origin='unit_test_proxy', aid='1')]

        result = await proxy_factory.cls.query_db_any_origin_by_condition(keywords='a')

        assert result == [('unit_test_proxy', '1')]
        fake_artwork_dal.query_by_condition.assert_awaited_once_with(
            origin=None, keywords=['a'], page=1, size=3,
            classification_min=3, classification_max=4,
            rating_min=0, rating_max=0,
            acc_mode=False, ratio=None, order_mode='random',
        )

    async def test_query_db_any_origin_by_condition_custom_ranges(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        await proxy_factory.cls.query_db_any_origin_by_condition(
            keywords=['a', 'b'], origin='x', page=2, size=5,
            allow_classification_range=(4, 1), allow_rating_range=(3, 0),
            acc_mode=True, ratio=2, order_mode='latest',
        )

        fake_artwork_dal.query_by_condition.assert_awaited_once_with(
            origin='x', keywords=['a', 'b'], page=2, size=5,
            classification_min=1, classification_max=4,
            rating_min=0, rating_max=3,
            acc_mode=True, ratio=2, order_mode='latest',
        )

    async def test_query_db_by_condition_filters_origin(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        fake_artwork_dal.query_by_condition.return_value = [
            SimpleNamespace(origin='unit_test_proxy', aid='1'),
            SimpleNamespace(origin='other_origin', aid='2'),
        ]

        result = await proxy_factory.cls.query_db_by_condition(keywords=None)

        assert [x.s_aid for x in result] == ['1']
        assert isinstance(result[0], proxy_factory.cls)
        assert fake_artwork_dal.query_by_condition.await_args.kwargs['origin'] == 'unit_test_proxy'

    async def test_query_db_random(self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace):
        await proxy_factory.cls.query_db_random(num=5)

        fake_artwork_dal.query_by_condition.assert_awaited_once_with(
            origin='unit_test_proxy', keywords=None, page=1, size=5,
            classification_min=3, classification_max=4,
            rating_min=0, rating_max=0,
            acc_mode=False, ratio=None, order_mode='random',
        )

    async def test_query_db_classification_statistic(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        result = await proxy_factory.cls.query_db_classification_statistic(keywords='kw')

        assert result == 'classification_stat'
        fake_artwork_dal.query_classification_statistic.assert_awaited_once_with(
            origin='unit_test_proxy', keywords=['kw'],
        )

    async def test_query_db_rating_statistic(self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace):
        result = await proxy_factory.cls.query_db_rating_statistic(keywords='kw')

        assert result == 'rating_stat'
        fake_artwork_dal.query_rating_statistic.assert_awaited_once_with(
            origin='unit_test_proxy', keywords=['kw'],
        )

    async def test_query_db_user_all_artworks(self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace):
        fake_artwork_dal.query_user_all_aids.return_value = ['1', '2']

        result = await proxy_factory.cls.query_db_user_all_artworks(uid='9', uname='x')

        fake_artwork_dal.query_user_all_aids.assert_awaited_once_with(
            origin='unit_test_proxy', uid='9', uname='x',
        )
        assert [x.s_aid for x in result] == ['1', '2']

    async def test_query_db_exists_artworks(self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace):
        fake_artwork_dal.query_exists_aids.return_value = ['1']

        result = await proxy_factory.cls.query_db_exists_artworks(['1', '2'], filter_classification=3, filter_rating=0)

        fake_artwork_dal.query_exists_aids.assert_awaited_once_with(
            origin='unit_test_proxy', aids=['1', '2'], filter_classification=3, filter_rating=0,
        )
        assert [x.s_aid for x in result] == ['1']

    async def test_query_db_not_exists_artworks(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        fake_artwork_dal.query_not_exists_aids.return_value = ['2']

        result = await proxy_factory.cls.query_db_not_exists_artworks(
            ['1', '2'], exclude_classification=3, exclude_rating=0,
        )

        fake_artwork_dal.query_not_exists_aids.assert_awaited_once_with(
            origin='unit_test_proxy', aids=['1', '2'], exclude_classification=3, exclude_rating=0,
        )
        assert [x.s_aid for x in result] == ['2']

    def test_convert_proxy_data_to_add_artwork_params(self, proxy_factory: SimpleNamespace):
        data = make_artwork_data()

        params = proxy_factory.cls._convert_proxy_data_to_add_artwork_params(data=data)

        assert params['origin'] == 'unit_test_proxy'
        assert params['aid'] == '123'
        assert params['url'] == data.source
        assert params['source'] == data.source
        assert params['cover_page'] == data.cover_page_url
        assert params['raw_tags'] == 'tag1,tag2'
        assert params['tag_handler'] is None
        assert params['published_at'] == data.published_at

    async def test_add_and_upgrade_artwork_into_database(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        await proxy.add_and_upgrade_artwork_into_database()

        proxy_factory.hooks.query.assert_awaited_once()
        fake_artwork_dal.add_artwork_update_exist.assert_awaited_once()
        kwargs = fake_artwork_dal.add_artwork_update_exist.await_args.kwargs
        assert kwargs['classification'] == 3
        assert kwargs['rating'] == 0
        assert kwargs['force_update_cr'] is False
        assert kwargs['aid'] == '123'

    async def test_add_and_upgrade_artwork_into_database_with_overrides(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        await proxy.add_and_upgrade_artwork_into_database(classification=4, rating=3, force_update_cr=True)

        kwargs = fake_artwork_dal.add_artwork_update_exist.await_args.kwargs
        assert kwargs['classification'] == 4
        assert kwargs['rating'] == 3
        assert kwargs['force_update_cr'] is True

    async def test_add_artwork_into_database_ignore_exists(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace, isolated_temporary_root: Path,
    ):
        proxy_factory.hooks.query.return_value = make_artwork_data()
        proxy = proxy_factory.cls('123')

        await proxy.add_artwork_into_database_ignore_exists()

        fake_artwork_dal.add_artwork_ignore_exist.assert_awaited_once()
        kwargs = fake_artwork_dal.add_artwork_ignore_exist.await_args.kwargs
        assert kwargs['classification'] == 3
        assert kwargs['rating'] == 0
        assert 'force_update_cr' not in kwargs

    async def test_delete_artwork_from_database(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        proxy = proxy_factory.cls('123')

        await proxy.delete_artwork_from_database()

        fake_artwork_dal.delete.assert_awaited_once_with(origin='unit_test_proxy', aid='123')

    async def test_query_artwork_from_database(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        proxy = proxy_factory.cls('123')

        result = await proxy.query_artwork_from_database()

        assert result == 'artwork_from_db'
        fake_artwork_dal.query_unique.assert_awaited_once_with(origin='unit_test_proxy', aid='123')

    async def test_query_artwork_from_database_not_found(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        """作品不存在时原样传播 NoResultFound"""
        from sqlalchemy.exc import NoResultFound

        fake_artwork_dal.query_unique.side_effect = NoResultFound
        proxy = proxy_factory.cls('123')

        with pytest.raises(NoResultFound):
            await proxy.query_artwork_from_database()

    async def test_query_artwork_from_database_uses_cleaned_aid(
            self, proxy_factory: SimpleNamespace, fake_artwork_dal: SimpleNamespace,
    ):
        """含路径分隔符的 aid 按清洗后的 s_aid 查询数据库, 与 delete/add 同口径"""
        proxy = proxy_factory.cls('a/b')

        await proxy.query_artwork_from_database()

        kwargs = fake_artwork_dal.query_unique.await_args.kwargs
        assert kwargs['origin'] == 'unit_test_proxy'
        assert kwargs['aid'] == proxy.s_aid


class TestModels:
    """ArtworkProxyData 模型边界(支撑基类行为)测试"""

    def test_index_pages_valid(self):
        data = make_artwork_data(num_pages=3)
        assert sorted(data.index_pages.keys()) == [0, 1, 2]

    def test_pool_data_count_num(self):
        assert make_pool_data(artwork_ids=['1', '2', '3']).count_num == 3

    @pytest.mark.parametrize('page_indexes', [[0, 0], [0, 2], [1, 0]])
    def test_index_pages_invalid_raises(self, page_indexes: list[int]):
        data = make_artwork_data(pages=[make_page(i) for i in page_indexes])
        with pytest.raises(ValueError, match='erroneous or duplicate'):
            data.index_pages  # noqa: B018

    def test_cover_page_url_empty_pages_raises(self):
        data = make_artwork_data(num_pages=0)
        with pytest.raises(ValueError, match='has no pages'):
            data.cover_page_url  # noqa: B018

    def test_cover_page_url_returns_first_page_original(self):
        data = make_artwork_data()
        assert data.cover_page_url == 'https://unit.test/0_original.jpg'

    def test_model_frozen(self):
        from pydantic import ValidationError

        data = make_artwork_data()
        with pytest.raises(ValidationError):
            data.title = 'x'

    def test_model_coerce_numbers_to_str(self):
        from src.service.artwork_proxy.models import ArtworkProxyData

        data = ArtworkProxyData.model_validate({
            'origin': 'unit_test_proxy', 'aid': 123, 'uid': 456, 'title': 't', 'uname': 'u',
            'classification': 3, 'rating': 0, 'width': 100, 'height': 200,
            'source': 'https://unit.test/artwork/123', 'pages': [make_page(0)],
        })
        assert data.aid == '123'
        assert data.uid == '456'


class TestSitesFixes:
    """站点适配层行为测试"""

    async def test_local_random_sample_clamped_by_available(self, isolated_temporary_root: Path):
        """候选文件数少于 limit 时返回全部而非抛 ValueError"""
        from src.service.artwork_proxy.sites.local import LocalCollectedArtworkProxy

        artwork_path = LocalCollectedArtworkProxy._get_path_config().artwork_path
        artwork_path.path.mkdir(parents=True)
        for name in ('a.jpg', 'b.jpg'):
            artwork_path.path.joinpath(name).write_bytes(b'x')

        result = await LocalCollectedArtworkProxy._random(limit=5)

        assert sorted(result) == ['a.jpg', 'b.jpg']


class TestArtworkImageOpsReal:
    """ArtworkImageOps 真实图片处理测试(真实 PIL + 本地字体, 不经网络)"""

    @staticmethod
    def _make_image_file(tmp_path: Path, name: str = 'sample.png'):
        from PIL import Image

        from src.resource import AnyResource

        file = AnyResource(tmp_path, name)
        Image.new('RGB', (64, 64), (128, 64, 200)).save(file.path)
        return file

    @pytest.mark.parametrize('handler_name', ['handle_mark', 'handle_blur', 'handle_noise'])
    async def test_handle_modes_produce_rgb_image(self, tmp_path: Path, handler_name: str):
        from src.service.artwork_proxy.preview_image_utils import ArtworkImageOps

        image_file = self._make_image_file(tmp_path)
        handler = getattr(ArtworkImageOps, handler_name)

        processor = await handler(image=image_file, origin_mark='mark')

        assert processor.image.mode == 'RGB'
        assert processor.image.size == (64, 64)

    async def test_handle_preview_image_empty_previews(self):
        """空缩略图列表: 输出仅含标题的合法 JPEG(布局边界)"""
        from src.resource import StaticResource
        from src.service.artwork_proxy.preview_image_utils import ArtworkImageOps

        content = await ArtworkImageOps._handle_preview_image(
            preview_name='empty', previews=[], preview_size=(64, 64),
            font_path=StaticResource('fonts', 'fzzxhk.ttf'),
        )

        assert content[:2] == b'\xff\xd8'  # JPEG SOI

    async def test_generate_preview_image_real_roundtrip(
            self, tmp_path: Path, isolated_temporary_root: Path,
    ):
        """真实端到端: 含一张损坏缩略图(走灰色占位分支), 输出合法 JPEG"""
        import src.resource
        from src.resource import StaticResource
        from src.service.artwork_proxy.models import PreviewImagesData
        from src.service.artwork_proxy.preview_image_utils import ArtworkImageOps

        preview = PreviewImagesData.model_validate({
            'preview_name': 'roundtrip',
            'thumb_items': [
                {'desc_text': 'one', 'thumb_data': self._make_image_file(tmp_path, 'a.jpg').path.read_bytes()},
                {'desc_text': 'bad', 'thumb_data': b'not an image'},
                {'desc_text': 'two', 'thumb_data': self._make_image_file(tmp_path, 'b.jpg').path.read_bytes()},
            ],
        })

        result = await ArtworkImageOps.generate_preview_image(
            preview=preview, preview_size=(64, 64),
            font_path=StaticResource('fonts', 'fzzxhk.ttf'),
            output_folder=src.resource.TemporaryResource('preview_real'),
        )

        assert result.is_file
        with result.open('rb') as f:
            assert f.read(2) == b'\xff\xd8'
