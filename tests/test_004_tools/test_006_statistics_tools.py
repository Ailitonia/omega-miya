"""
@Author         : Ailitonia
@Date           : 2026/9/20 18:21
@FileName       : test_006_statistics_tools
@Project        : omega-miya
@Description    : 统计图表生成工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import io
from contextlib import contextmanager
from typing import TYPE_CHECKING

import pytest
from PIL import Image as PILImage

if TYPE_CHECKING:
    from collections.abc import Iterator


class _StubOutputResource:
    """导出资源桩, open 返回 BytesIO, 不落盘"""

    last_saved: 'bytes | None' = None

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def resolve_path(self) -> str:
        return f'/stub-output/{self.name}'

    def open(self, mode: str = 'r', encoding: str | None = None, **kwargs) -> 'Iterator[io.BytesIO]':
        @contextmanager
        def _ctx() -> 'Iterator[io.BytesIO]':
            buf = io.BytesIO()
            yield buf
            _StubOutputResource.last_saved = buf.getvalue()

        return _ctx()


class _StubStatisticsToolsConfig:
    """statistics_tools_config 桩, default_output_folder 返回导出资源桩"""

    def __init__(self) -> None:
        self.last_resource: _StubOutputResource | None = None

    def default_output_folder(self, name: str) -> '_StubOutputResource':
        resource = _StubOutputResource(name)
        self.last_resource = resource
        return resource


def _install_output_stub(monkeypatch: pytest.MonkeyPatch) -> '_StubStatisticsToolsConfig':
    """将 plots 模块内的 statistics_tools_config 替换为导出桩, 确保测试不落盘"""
    from src.utils.statistics_tools import plots

    stub = _StubStatisticsToolsConfig()
    monkeypatch.setattr(plots, 'statistics_tools_config', stub)
    return stub


def _create_test_figure():
    from src.utils.statistics_tools import create_simple_subplots_figure

    fig, ax = create_simple_subplots_figure(figsize=(4, 3))
    ax.plot([1, 2, 3], [1, 4, 9])
    return fig, ax


def _close_test_figure(fig) -> None:
    from matplotlib import pyplot as plt

    plt.close(fig)


def _assert_valid_jpeg() -> None:
    """断言桩最近一次导出内容为有效 JPEG"""
    saved = _StubOutputResource.last_saved
    assert saved is not None, 'nothing saved to stub output'
    assert saved.startswith(b'\xff\xd8'), 'JPEG magic bytes missing'
    image = PILImage.open(io.BytesIO(saved))
    assert image.format == 'JPEG', image.format


@pytest.fixture(autouse=True)
def assert_no_disk_write():
    """保障测试不产生落盘文件: 对比用例前后真实输出目录内的文件集合"""
    from src.resource import TemporaryResource

    output_folder = TemporaryResource('statistics_tools', 'output')

    def _snapshot() -> 'set[str]':
        if not output_folder.path.exists():
            return set()
        return {f.name for f in output_folder.path.iterdir()}

    before = _snapshot()
    yield
    after = _snapshot()
    assert after <= before, f'测试产生了落盘文件: {after - before}'


class TestConfig:

    def test_font_resources_exist(self):
        from src.utils.statistics_tools.config import statistics_tools_config

        assert statistics_tools_config.default_font.is_file
        assert statistics_tools_config.alternative_font.is_file

    def test_default_output_folder_path(self):
        from src.utils.statistics_tools.config import statistics_tools_config

        folder = statistics_tools_config.default_output_folder
        assert folder.path.as_posix().endswith('.tmp/statistics_tools/output')


class TestFontNames:

    def test_registered_font_names(self):
        from src.utils.statistics_tools.plots import get_font_names

        names = get_font_names()
        assert 'Microsoft YaHei' in names
        assert 'FZZhengHei-EL-GBK' in names


class TestCreateFigure:

    def test_create_simple_figure(self):
        from matplotlib.figure import Figure

        from src.utils.statistics_tools import create_simple_figure

        fig = create_simple_figure(figsize=(6, 4), dpi=50)
        try:
            assert isinstance(fig, Figure)
            assert fig.get_size_inches().tolist() == [6.0, 4.0]
            assert fig.dpi == 50
            assert not fig.axes
        finally:
            _close_test_figure(fig)

    def test_create_simple_subplots_figure(self):
        from src.utils.statistics_tools import create_simple_subplots_figure

        fig, ax = create_simple_subplots_figure(figsize=(5, 3))
        try:
            assert ax in fig.axes
        finally:
            _close_test_figure(fig)


class TestOutputFigure:

    def test_export_jpeg_and_close_figure(self, monkeypatch: pytest.MonkeyPatch):
        from matplotlib import pyplot as plt

        from src.utils.statistics_tools import output_figure

        stub = _install_output_stub(monkeypatch)
        fig, _ = _create_test_figure()
        figure_number = fig.number

        resource = output_figure(fig, 'test_output.jpg')

        assert resource is stub.last_resource
        _assert_valid_jpeg()
        assert not plt.fignum_exists(figure_number), 'figure not closed after output_figure'

    def test_savefig_failure_closes_figure(self, monkeypatch: pytest.MonkeyPatch):
        from matplotlib import pyplot as plt

        from src.utils.statistics_tools import output_figure

        _install_output_stub(monkeypatch)
        fig, _ = _create_test_figure()

        def _boom(*args, **kwargs):
            raise RuntimeError('savefig boom')

        fig.savefig = _boom
        with pytest.raises(RuntimeError, match='savefig boom'):
            output_figure(fig, 'test_fail.jpg')
        assert not plt.fignum_exists(fig.number), 'figure leaked on save failure'

    def test_invalid_filename_rejected(self, monkeypatch: pytest.MonkeyPatch):
        from matplotlib import pyplot as plt

        from src.utils.statistics_tools import output_figure

        stub = _install_output_stub(monkeypatch)
        fig, _ = _create_test_figure()
        try:
            for bad_name in ('../evil.jpg', 'C:/evil.jpg', 'sub/evil.jpg', ''):
                with pytest.raises(ValueError, match='invalid output filename'):
                    output_figure(fig, bad_name)
            # 校验失败时不接管 Figure 实例
            assert plt.fignum_exists(fig.number)
            assert stub.last_resource is None
        finally:
            _close_test_figure(fig)

    def test_unsupported_format_rejected(self, monkeypatch: pytest.MonkeyPatch):
        from matplotlib import pyplot as plt

        from src.utils.statistics_tools import output_figure

        stub = _install_output_stub(monkeypatch)
        fig, _ = _create_test_figure()
        try:
            with pytest.raises(ValueError, match='unsupported output format'):
                output_figure(fig, 'test.xyz', format_='XYZ')
            # 参数校验失败时不接管 Figure 实例
            assert plt.fignum_exists(fig.number)
            assert stub.last_resource is None
        finally:
            _close_test_figure(fig)

    def test_lowercase_format_accepted(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.statistics_tools import output_figure

        _install_output_stub(monkeypatch)
        fig, _ = _create_test_figure()

        output_figure(fig, 'test_lowercase.jpg', format_='jpg')
        _assert_valid_jpeg()


class TestCreateDictDataFigure:

    def test_basic_figure_and_labels(self):
        from src.utils.statistics_tools import create_dict_data_figure

        data = {'插件A': 30, '插件B': 120.5, '插件C': 7}
        fig, ax = create_dict_data_figure(data, title='测试')
        try:
            assert len(ax.patches) == len(data)

            fig.canvas.draw()
            # barh 自下而上绘制, 'desc' 排序时最大值在顶部
            y_labels = [t.get_text() for t in ax.get_yticklabels()]
            assert y_labels == ['插件C', '插件A', '插件B']

            label_texts = [t.get_text() for t in ax.texts]
            assert '120.5' in label_texts
            assert '30' in label_texts
            assert '7' in label_texts
            assert ax.get_title() == '测试'
            # 默认添加颜色条
            assert len(fig.axes) == 2
        finally:
            _close_test_figure(fig)

    def test_sort_asc_and_keep(self):
        from src.utils.statistics_tools import create_dict_data_figure

        data = {'a': 3, 'b': 1, 'c': 2}
        fig_asc, ax_asc = create_dict_data_figure(data, sort='asc')
        try:
            fig_asc.canvas.draw()
            assert [t.get_text() for t in ax_asc.get_yticklabels()] == ['a', 'c', 'b']
        finally:
            _close_test_figure(fig_asc)

        fig_keep, ax_keep = create_dict_data_figure(data, sort='keep')
        try:
            fig_keep.canvas.draw()
            assert [t.get_text() for t in ax_keep.get_yticklabels()] == ['a', 'b', 'c']
        finally:
            _close_test_figure(fig_keep)

    def test_no_colorbar(self):
        from src.utils.statistics_tools import create_dict_data_figure

        fig, ax = create_dict_data_figure({'a': 1, 'b': 2}, colorbar=False)
        try:
            assert len(fig.axes) == 1
        finally:
            _close_test_figure(fig)

    def test_invalid_data_rejected(self):
        from src.utils.statistics_tools import create_dict_data_figure

        for bad_data in ({}, {'a': float('nan')}, {'a': float('inf')}, {'a': 'x'}):
            with pytest.raises(ValueError, match='data '):
                create_dict_data_figure(bad_data)

    def test_equal_and_negative_values_render(self):
        from src.utils.statistics_tools import create_dict_data_figure

        for data in ({'a': 5, 'b': 5}, {'a': -5, 'b': 10, 'c': 0}):
            fig, ax = create_dict_data_figure(data)
            try:
                fig.canvas.draw()
                assert len(ax.patches) == len(data)
            finally:
                _close_test_figure(fig)


class TestDrawDictData:

    def test_draw_and_export(self, monkeypatch: pytest.MonkeyPatch):
        from matplotlib import pyplot as plt

        from src.utils.statistics_tools import draw_dict_data

        stub = _install_output_stub(monkeypatch)
        figures_before = set(plt.get_fignums())

        resource = draw_dict_data({'插件A': 30, '插件B': 120.5, '插件C': 7}, 'test_dict.jpg', title='统计')

        assert resource is stub.last_resource
        _assert_valid_jpeg()
        assert set(plt.get_fignums()) == figures_before, 'figure leaked in draw_dict_data'


class TestSample:

    def test_invest_test_deterministic(self):
        import numpy as np

        from src.utils.statistics_tools.sample import invest_test

        result_1 = invest_test(step=50, seed=42)
        result_2 = invest_test(step=50, seed=42)
        assert np.array_equal(result_1, result_2)
        assert result_1.shape == (51,)
        assert result_1[0] == 1000000.0
        assert (result_1 > 0).all()

    def test_coin_test_deterministic(self):
        import numpy as np

        from src.utils.statistics_tools.sample import coin_test

        result_1, step_1 = coin_test(seed=42)
        result_2, step_2 = coin_test(seed=42)
        assert step_1 == step_2 >= 1
        assert np.array_equal(result_1, result_2)
        assert result_1.shape == (step_1 + 1,)

    def test_run_figure_example(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.statistics_tools.sample import run_figure_example

        _install_output_stub(monkeypatch)
        resource = run_figure_example()
        assert resource.name == 'sample.jpg'
        _assert_valid_jpeg()

    def test_run_invest_test(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.statistics_tools.sample import run_invest_test

        stub = _install_output_stub(monkeypatch)
        resource = run_invest_test(step=20, times=3, seed=1)
        assert resource is stub.last_resource
        _assert_valid_jpeg()

    def test_run_coin_test(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.statistics_tools.sample import run_coin_test

        stub = _install_output_stub(monkeypatch)
        resource = run_coin_test(times=5, seed=1)
        assert resource is stub.last_resource
        _assert_valid_jpeg()
