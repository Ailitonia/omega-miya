"""
@Author         : Ailitonia
@Date           : 2026/10/5 20:00
@FileName       : test_002_manual_rate_artwork_gui
@Project        : omega-miya
@Description    : 作品人工评级工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
import hashlib
import io
import json
from collections.abc import Callable

import pytest

_PNG_1X1_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)
"""1x1 PNG 图片字节, 供预览图加载成功路径使用"""


class _FakeLabel:
    """模拟图片显示控件"""

    def __init__(self) -> None:
        self.image = None

    def config(self, **kwargs) -> None:
        self.image = kwargs.get('image')


class _FakeEntry:
    """模拟文本显示控件"""

    def __init__(self) -> None:
        self.content = ''
        self.state: str | None = None

    def config(self, **kwargs) -> None:
        self.state = kwargs.get('state')

    def delete(self, *_args) -> None:
        self.content = ''

    def insert(self, _index, s: str) -> None:
        self.content = s


class _FakeMessagebox:
    """模拟弹窗, 记录调用避免真实弹出对话框"""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []
        self.infos: list[tuple[str, str]] = []

    def showerror(self, title=None, message=None, **_kwargs) -> None:
        self.errors.append((title, message))

    def showwarning(self, title=None, message=None, **_kwargs) -> None:
        self.warnings.append((title, message))

    def showinfo(self, title=None, message=None, **_kwargs) -> None:
        self.infos.append((title, message))


def _patch_messagebox(monkeypatch: pytest.MonkeyPatch) -> _FakeMessagebox:
    """向 data_source 模块注入假弹窗, 返回调用记录"""
    from tools.manual_rate_artwork_gui import data_source as ds_module

    fake_box = _FakeMessagebox()
    monkeypatch.setattr(ds_module, 'messagebox', fake_box)
    return fake_box


def _make_source(
        load_map: dict[str, bytes | Exception],
        *,
        select_hook: 'Callable | None' = None,
        init_hook: 'Callable | None' = None,
):
    """构造 BaseArtworkSource 最小实现, 按 aid 注入加载结果(成功字节或待抛异常)"""
    from tools.manual_rate_artwork_gui.data_source import BaseArtworkSource

    class _FakeSource(BaseArtworkSource):
        @property
        def source_type(self) -> str:
            return 'fake_test_source'

        @property
        def source_origin(self) -> str:
            return 'fake'

        @property
        def title_name(self) -> str:
            return 'fake'

        @property
        def _current_artwork_proxy(self):
            pytest.fail('不应访问 _current_artwork_proxy')

        async def _load_source(self, source):
            result = load_map[source.aid]
            if isinstance(result, Exception):
                raise result
            return io.BytesIO(result)

        async def _select_current_source(self) -> None:
            if select_hook is not None:
                select_hook(self)

        async def _init_working_path(self) -> None:
            if init_hook is not None:
                init_hook(self)

    return _FakeSource()


def _make_artwork(aid: str):
    from tools.manual_rate_artwork_gui.model import CurrentArtwork

    return CurrentArtwork.model_validate({'aid': aid, 'source_path': f'fake/path/{aid}'})


def _require_tk_root():
    """尝试创建 Tk 根窗口, 无显示环境时跳过测试"""
    tkinter = pytest.importorskip('tkinter')
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        pytest.skip('no display available for Tk')
    root.withdraw()
    return root


class TestLoadNextAsync:
    """异步加载下一作品测试"""

    async def test_load_failure_keeps_current_source(self):
        source = _make_source({'2': RuntimeError('network down')})
        source._current_source = _make_artwork('1')
        source._remaining_source = [_make_artwork('2'), _make_artwork('3')]

        label, current_entry, remaining_entry = _FakeLabel(), _FakeEntry(), _FakeEntry()
        with pytest.MonkeyPatch.context() as monkeypatch:
            fake_box = _patch_messagebox(monkeypatch)
            await source._load_next_async(label, current_entry, remaining_entry)

        assert source._current_source.aid == '1'
        assert source._queue_finished is False
        assert len(fake_box.errors) == 1
        assert remaining_entry.content == '1'
        assert current_entry.content == ''

    async def test_empty_queue_marks_finished(self):
        source = _make_source({})
        source._current_source = _make_artwork('1')
        source._remaining_source = []

        label, current_entry, remaining_entry = _FakeLabel(), _FakeEntry(), _FakeEntry()
        await source._load_next_async(label, current_entry, remaining_entry)

        assert source._queue_finished is True
        assert current_entry.content == '队列已处理完毕'
        assert remaining_entry.content == '0'

    async def test_load_success_commits_current_source(self):
        root = _require_tk_root()
        try:
            from tkinter import ttk

            label = ttk.Label(root)
            current_entry, remaining_entry = ttk.Entry(root), ttk.Entry(root)

            source = _make_source({'2': _PNG_1X1_BYTES})
            source._current_source = _make_artwork('1')
            source._remaining_source = [_make_artwork('2'), _make_artwork('3')]

            with pytest.MonkeyPatch.context() as monkeypatch:
                fake_box = _patch_messagebox(monkeypatch)
                await source._load_next_async(label, current_entry, remaining_entry)

            assert not fake_box.errors
            assert source._current_source.aid == '2'
            assert source._current_source_image is not None
            assert current_entry.get() == 'fake/path/2'
            assert remaining_entry.get() == '1'
        finally:
            root.destroy()


class TestSelectCurrent:
    """选择当前作品初始化测试"""

    async def test_reinit_resets_state_flags(self):
        source = _make_source(
            {'5': RuntimeError('network down')},
            init_hook=lambda s: setattr(s, '_remaining_source', [_make_artwork('5')]),
        )
        source._queue_finished = True
        source._select_cancelled = True
        source._current_source = _make_artwork('1')

        label, current_entry, remaining_entry = _FakeLabel(), _FakeEntry(), _FakeEntry()
        with pytest.MonkeyPatch.context() as monkeypatch:
            fake_box = _patch_messagebox(monkeypatch)
            await source._select_current(label, current_entry, remaining_entry)

        assert source._select_cancelled is False
        assert source._queue_finished is False
        assert source._current_source is None
        assert len(fake_box.errors) == 1

    async def test_select_cancelled_skips_init(self):
        init_called = False

        def _select_hook(s) -> None:
            s._select_cancelled = True

        def _init_hook(_s) -> None:
            nonlocal init_called
            init_called = True

        source = _make_source({}, select_hook=_select_hook, init_hook=_init_hook)
        await source._select_current(_FakeLabel(), _FakeEntry(), _FakeEntry())

        assert init_called is False
        assert source._select_cancelled is True

    async def test_init_failure_shows_error(self):
        def _init_hook(_s) -> None:
            raise RuntimeError('null of artwork source')

        source = _make_source({}, init_hook=_init_hook)
        source._current_source = _make_artwork('1')

        with pytest.MonkeyPatch.context() as monkeypatch:
            fake_box = _patch_messagebox(monkeypatch)
            await source._select_current(_FakeLabel(), _FakeEntry(), _FakeEntry())

        assert len(fake_box.errors) == 1
        assert '初始化作品源失败' in fake_box.errors[0][1]
        assert source._current_source.aid == '1'


class TestSetCurrent:
    """评级守卫分支测试"""

    @pytest.mark.parametrize(
        'preset',
        [
            pytest.param('queue_finished', id='queue-finished-blocks-rating'),
            pytest.param('no_current_source', id='no-current-source-blocks-rating'),
        ],
    )
    async def test_guard_blocks_rating(self, preset):
        source = _make_source({})
        if preset == 'queue_finished':
            source._queue_finished = True
            source._current_source = _make_artwork('1')

        with pytest.MonkeyPatch.context() as monkeypatch:
            fake_box = _patch_messagebox(monkeypatch)
            await source._set_current(0, _FakeLabel(), _FakeEntry(), _FakeEntry())

        assert len(fake_box.warnings) == 1


class TestPixivLocalArtworkFileSource:
    """本地文件源工作目录缓存测试"""

    async def test_cache_stores_full_scan(self, tmp_path):
        from src.resource import AnyResource
        from tools.manual_rate_artwork_gui.sources.pixiv import PixivLocalArtworkFileSource

        for name in ['100_p0.jpg', '200_p0.jpg', '300_p0.jpg', 'not_artwork.jpg']:
            (tmp_path / name).write_bytes(b'x')

        source = PixivLocalArtworkFileSource()
        source._anchor_source = _make_artwork('200')
        source._working_path = str(tmp_path)

        working_dir = AnyResource(str(tmp_path))
        working_dir_hash = hashlib.sha256(working_dir.resolve_path.encode('utf-8')).hexdigest()[:16]
        cache_file = source._output_path.cache_dir(
            f'working_files_cache_{working_dir.name}_{working_dir_hash}.json'
        )

        try:
            await source._init_working_path()

            assert [x.aid for x in source._remaining_source] == ['200', '300']

            async with cache_file.async_open('r', encoding='utf-8') as af:
                cache_data = json.loads(await af.read())
            assert sorted(int(x['aid']) for x in cache_data) == [100, 200, 300]
        finally:
            cache_file.remove()
