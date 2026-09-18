"""
@Author         : Ailitonia
@Date           : 2026/9/18 14:44
@FileName       : test_002_excel_tools
@Project        : omega-miya
@Description    : Excel 工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import shutil
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from openpyxl import Workbook
from pydantic import BaseModel, ValidationError, create_model

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.resource import TemporaryResource
    from src.utils.excel_tools import ExcelTools


class SampleModel(BaseModel):
    """全字段必填的混合类型样例模型"""

    name: str
    count: int
    score: float
    enabled: bool
    created_at: datetime


class OptionalModel(BaseModel):
    """含可选字段的样例模型"""

    name: str
    remark: str | None = None
    score: float | None = None


class NullableModel(BaseModel):
    """全可选字段的样例模型"""

    a: int | None = None
    b: str | None = None


MultiHeaderModel = create_model(
    'MultiHeaderModel',
    **{"('a', 'x')": (int | None, None), "('a', 'y')": (int | None, None)},
)
"""多级表头(header=[0, 1])读回列名 str 化后的显式样例模型"""

SAMPLE_MODELS = [
    SampleModel(name='alpha', count=1, score=1.5, enabled=True, created_at=datetime(2024, 1, 1, 12, 30, 45)),
    SampleModel(name='beta', count=-20, score=-0.001, enabled=False, created_at=datetime(2025, 6, 15, 8, 0, 0)),
    SampleModel(
        name='中文测试', count=2147483649, score=1e10, enabled=True, created_at=datetime(2026, 12, 31, 23, 59, 59),
    ),
]


def _make_multi_header_workbook() -> Workbook:
    """构造两个 sheet 的多级表头工作簿, 每个 sheet 前两行为表头"""
    workbook = Workbook()
    sheet1 = workbook.active
    sheet1.title = 'M1'
    sheet1.append(['a', 'a', 'b'])
    sheet1.append(['x', 'y', 'x'])
    sheet1.append([1, 2, 3])
    sheet2 = workbook.create_sheet('M2')
    sheet2.append(['a', 'a'])
    sheet2.append(['x', 'y'])
    sheet2.append([4, 5])
    return workbook


# 异常信息片段, 用于 pytest.raises 的 match 校验
_MSG_NOT_FILE = 'is not a file'
_MSG_VALID_STRING = 'valid string'
_MSG_PARSE_FAIL = '解析 Excel 文件失败'
_MSG_WRITE_FAIL = '写入 Excel 文件失败'
_MSG_SHEET_EXISTS = 'already exists'


@pytest.fixture
def sample_tools() -> 'ExcelTools[SampleModel]':
    from src.utils.excel_tools import ExcelTools

    return ExcelTools(SampleModel)


@pytest.fixture
def optional_tools() -> 'ExcelTools[OptionalModel]':
    from src.utils.excel_tools import ExcelTools

    return ExcelTools(OptionalModel)


@pytest.fixture
def nullable_tools() -> 'ExcelTools[NullableModel]':
    from src.utils.excel_tools import ExcelTools

    return ExcelTools(NullableModel)


@pytest.fixture
def excel_file() -> 'Callable[..., TemporaryResource]':
    """工厂 fixture, 在 .tmp 下创建测试用临时文件资源并在用例结束后清理"""
    from src.resource import TemporaryResource

    created: list[TemporaryResource] = []

    def _factory(*names: str) -> 'TemporaryResource':
        resource = TemporaryResource('excel_tools_test', *names)
        created.append(resource)
        return resource

    TemporaryResource('excel_tools_test').path.mkdir(parents=True, exist_ok=True)
    yield _factory

    for resource in created:
        resource.remove(missing_ok=True)
    shutil.rmtree(TemporaryResource('excel_tools_test').path, ignore_errors=True)


class TestModuleContract:
    def test_all_exports(self):
        from src.utils import excel_tools

        assert excel_tools.__all__ == ['ExcelTools', 'ExcelToolsException']
        assert excel_tools.ExcelTools is not None
        assert excel_tools.ExcelToolsException is not None

    def test_init_binds_data_model(self, sample_tools):
        from src.utils.excel_tools import ExcelTools

        assert isinstance(sample_tools, ExcelTools)
        assert sample_tools.data_model is SampleModel


class TestDumpExcel:
    async def test_dump_creates_file(self, sample_tools, excel_file):
        file = excel_file('dump_basic.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        assert file.is_file
        assert file.file_size > 0

    async def test_dump_accepts_dicts(self, sample_tools, excel_file):
        file = excel_file('dump_dicts.xlsx')
        data = [m.model_dump() for m in SAMPLE_MODELS]

        await sample_tools.dump_excel(data, file)
        loaded = await sample_tools.load_excel(file)

        assert loaded == SAMPLE_MODELS

    async def test_dump_default_no_index_column(self, sample_tools, excel_file):
        file = excel_file('dump_default_index.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        columns = pd.read_excel(file.path).columns.tolist()
        assert columns == list(SampleModel.model_fields)
        assert 'Unnamed: 0' not in columns

    async def test_dump_with_index_true_keeps_model_loadable(self, sample_tools, excel_file):
        file = excel_file('dump_index_true.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file, index=True)

        columns = pd.read_excel(file.path).columns.tolist()
        assert 'Unnamed: 0' in columns

        loaded = await sample_tools.load_excel(file)
        assert loaded == SAMPLE_MODELS

    async def test_dump_default_sheet_name_is_model_name(self, sample_tools, excel_file):
        file = excel_file('dump_default_sheet.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        with pd.ExcelFile(file.path) as excel:
            assert excel.sheet_names == [SampleModel.__name__]

    async def test_dump_custom_sheet_name(self, sample_tools, excel_file):
        file = excel_file('dump_custom_sheet.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file, sheet_name='Custom')

        with pd.ExcelFile(file.path) as excel:
            assert excel.sheet_names == ['Custom']
        loaded = await sample_tools.load_excel(file, sheet_name='Custom')
        assert loaded == SAMPLE_MODELS

    async def test_dump_creates_missing_parent_dirs(self, sample_tools, excel_file):
        file = excel_file('deep', 'nested', 'subdir', 'dump.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        assert file.is_file

    async def test_dump_empty_data_writes_header_only(self, sample_tools, excel_file):
        file = excel_file('dump_empty.xlsx')

        await sample_tools.dump_excel([], file)

        assert file.is_file
        assert pd.read_excel(file.path).columns.tolist() == list(SampleModel.model_fields)
        assert await sample_tools.load_excel(file) == []

    async def test_dump_invalid_data_raises_validation_error(self, sample_tools, excel_file):
        file = excel_file('dump_invalid.xlsx')

        with pytest.raises(ValidationError):
            await sample_tools.dump_excel([{'name': 'alpha'}], file)

    async def test_dump_overwrites_existing_file(self, sample_tools, excel_file):
        file = excel_file('dump_overwrite.xlsx')
        replacement = [SampleModel(
            name='replacement', count=99, score=9.9, enabled=True, created_at=datetime(2024, 2, 2),
        )]

        await sample_tools.dump_excel(SAMPLE_MODELS, file)
        await sample_tools.dump_excel(replacement, file)

        assert await sample_tools.load_excel(file) == replacement

    @pytest.mark.parametrize(
        ('name', 'remark', 'score'),
        [
            ('中文测试', '含"引号"和,逗号', -1.5),
            ('🔐🔑', 'line1\nline2\ttab', 1e10),
            ('a' * 500, None, None),
            ('neg', '-', -0.001),
        ],
        ids=['chinese', 'emoji', 'long-string', 'negative'],
    )
    async def test_dump_special_values_round_trip(self, optional_tools, excel_file, name, remark, score):
        file = excel_file('dump_special.xlsx')
        data = [OptionalModel(name=name, remark=remark, score=score)]

        await optional_tools.dump_excel(data, file)

        assert await optional_tools.load_excel(file) == data


class TestLoadExcel:
    async def test_round_trip(self, sample_tools, excel_file):
        file = excel_file('load_round_trip.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        assert await sample_tools.load_excel(file) == SAMPLE_MODELS

    async def test_empty_cells_become_none_for_optional_fields(self, optional_tools, excel_file):
        file = excel_file('load_empty_cells.xlsx')
        data = [
            OptionalModel(name='a', remark='r', score=1.5),
            OptionalModel(name='b', remark=None, score=None),
        ]

        await optional_tools.dump_excel(data, file)

        assert await optional_tools.load_excel(file) == data

    async def test_empty_cell_on_required_field_raises(self, sample_tools, excel_file):
        file = excel_file('load_required_missing.xlsx')
        pd.DataFrame({
            'name': [None],
            'count': [1],
            'score': [1.5],
            'enabled': [True],
            'created_at': [datetime(2024, 1, 1)],
        }).to_excel(file.path, index=False)

        with pytest.raises(ValidationError, match=_MSG_VALID_STRING):
            await sample_tools.load_excel(file)

    async def test_load_sheet_by_name_and_index(self, sample_tools, excel_file):
        file = excel_file('load_sheets.xlsx')
        second = SampleModel(name='second', count=2, score=2.5, enabled=False, created_at=datetime(2024, 2, 2))
        with pd.ExcelWriter(file.path) as writer:
            pd.DataFrame([SAMPLE_MODELS[0].model_dump()]).to_excel(writer, sheet_name='S1', index=False)
            pd.DataFrame([second.model_dump()]).to_excel(writer, sheet_name='S2', index=False)

        assert await sample_tools.load_excel(file) == [SAMPLE_MODELS[0]]
        assert await sample_tools.load_excel(file, sheet_name='S2') == [second]
        assert await sample_tools.load_excel(file, sheet_name=1) == [second]

    async def test_load_all_sheets_returns_dict(self, sample_tools, excel_file):
        file = excel_file('load_all_sheets.xlsx')
        second = SampleModel(name='second', count=2, score=2.5, enabled=False, created_at=datetime(2024, 2, 2))
        with pd.ExcelWriter(file.path) as writer:
            pd.DataFrame([m.model_dump() for m in SAMPLE_MODELS]).to_excel(writer, sheet_name='S1', index=False)
            pd.DataFrame([second.model_dump()]).to_excel(writer, sheet_name='S2', index=False)

        loaded = await sample_tools.load_excel(file, sheet_name=None)

        assert loaded == {'S1': SAMPLE_MODELS, 'S2': [second]}

    async def test_load_all_sheets_with_multi_header(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('load_all_multi_header.xlsx')
        _make_multi_header_workbook().save(file.path)

        tools = ExcelTools(MultiHeaderModel)
        loaded = await tools.load_excel(file, sheet_name=None, header=[0, 1])

        assert loaded == {
            'M1': [MultiHeaderModel.model_validate({"('a', 'x')": 1, "('a', 'y')": 2})],
            'M2': [MultiHeaderModel.model_validate({"('a', 'x')": 4, "('a', 'y')": 5})],
        }

    async def test_load_with_skiprows(self, sample_tools, excel_file):
        file = excel_file('load_skiprows.xlsx')
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['junk title row'])
        sheet.append(list(SampleModel.model_fields))
        for m in SAMPLE_MODELS:
            sheet.append([m.name, m.count, m.score, m.enabled, m.created_at])
        workbook.save(file.path)

        loaded = await sample_tools.load_excel(file, skiprows=1)

        assert loaded == SAMPLE_MODELS

    async def test_load_with_nrows(self, sample_tools, excel_file):
        file = excel_file('load_nrows.xlsx')
        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        assert await sample_tools.load_excel(file, nrows=2) == SAMPLE_MODELS[:2]

    async def test_load_nonexistent_file_raises(self, sample_tools, excel_file):
        from src.resource import ResourceNotFileError

        file = excel_file('not_exists.xlsx')

        with pytest.raises(ResourceNotFileError, match=_MSG_NOT_FILE):
            await sample_tools.load_excel(file)

    async def test_load_directory_raises(self, sample_tools):
        from src.resource import ResourceNotFileError, TemporaryResource

        with pytest.raises(ResourceNotFileError, match=_MSG_NOT_FILE):
            await sample_tools.load_excel(TemporaryResource('excel_tools_test'))

    async def test_load_header_only_file_returns_empty(self, sample_tools, excel_file):
        file = excel_file('load_header_only.xlsx')
        await sample_tools.dump_excel([], file)

        assert await sample_tools.load_excel(file) == []

    async def test_fully_empty_rows_become_none_models(self, nullable_tools, excel_file):
        file = excel_file('load_empty_rows.xlsx')
        pd.DataFrame({'a': [1, None, 3], 'b': ['x', None, 'z']}).to_excel(file.path, index=False)

        loaded = await nullable_tools.load_excel(file)

        assert loaded == [
            NullableModel(a=1, b='x'),
            NullableModel(a=None, b=None),
            NullableModel(a=3, b='z'),
        ]


class TestAutoLoadExcel:
    async def test_generates_fields_from_header(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_basic.xlsx')
        pd.DataFrame({'a': [1, 2], 'b': [1.5, 2.5], 'c': ['x', 'y']}).to_excel(file.path, index=False)

        loaded = await ExcelTools.auto_load_excel(file)

        assert list(type(loaded[0]).model_fields) == ['a', 'b', 'c']
        assert [m.model_dump() for m in loaded] == [
            {'a': '1', 'b': '1.5', 'c': 'x'},
            {'a': '2', 'b': '2.5', 'c': 'y'},
        ]

    async def test_empty_cells_become_none(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_empty_cells.xlsx')
        pd.DataFrame({'a': [1, None], 'b': ['x', 'y']}).to_excel(file.path, index=False)

        loaded = await ExcelTools.auto_load_excel(file)

        assert [m.model_dump() for m in loaded] == [
            {'a': '1.0', 'b': 'x'},
            {'a': None, 'b': 'y'},
        ]

    async def test_empty_cells_never_become_nan_string(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_nan_string.xlsx')
        pd.DataFrame({'a': [None, None], 'b': [None, 2]}).to_excel(file.path, index=False)

        loaded = await ExcelTools.auto_load_excel(file)

        for m in loaded:
            assert 'nan' not in m.model_dump().values()
        assert loaded[1].model_dump() == {'a': None, 'b': '2.0'}

    async def test_date_column_stringified(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_date.xlsx')
        pd.DataFrame({'d': [datetime(2024, 1, 1, 12, 30)]}).to_excel(file.path, index=False)

        loaded = await ExcelTools.auto_load_excel(file)

        assert [m.model_dump() for m in loaded] == [{'d': '2024-01-01 12:30:00'}]

    async def test_bool_column_stringified(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_bool.xlsx')
        pd.DataFrame({'flag': [True, False]}).to_excel(file.path, index=False)

        loaded = await ExcelTools.auto_load_excel(file)

        assert [m.model_dump() for m in loaded] == [{'flag': 'True'}, {'flag': 'False'}]

    async def test_duplicate_and_blank_headers(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_dup_headers.xlsx')
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['a', 'a', ''])
        sheet.append([1, 2, 3])
        workbook.save(file.path)

        loaded = await ExcelTools.auto_load_excel(file)

        assert list(type(loaded[0]).model_fields) == ['a', 'a.1', 'Unnamed: 2']
        assert loaded[0].model_dump() == {'a': '1', 'a.1': '2', 'Unnamed: 2': '3'}

    async def test_round_trip_from_dump(self, sample_tools, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_from_dump.xlsx')
        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        loaded = await ExcelTools.auto_load_excel(file)

        assert [m.model_dump() for m in loaded] == [
            {
                'name': 'alpha',
                'count': '1',
                'score': '1.5',
                'enabled': 'True',
                'created_at': '2024-01-01 12:30:45',
            },
            {
                'name': 'beta',
                'count': '-20',
                'score': '-0.001',
                'enabled': 'False',
                'created_at': '2025-06-15 08:00:00',
            },
            {
                'name': '中文测试',
                'count': '2147483649',
                'score': '10000000000.0',
                'enabled': 'True',
                'created_at': '2026-12-31 23:59:59',
            },
        ]

    async def test_nonexistent_file_raises(self, excel_file):
        from src.resource import ResourceNotFileError
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_not_exists.xlsx')

        with pytest.raises(ResourceNotFileError, match=_MSG_NOT_FILE):
            await ExcelTools.auto_load_excel(file)

    async def test_header_none_generates_integer_fields(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_header_none.xlsx')
        pd.DataFrame({'x': [1, 2], 'y': [3, 4]}).to_excel(file.path, index=False, header=False)

        loaded = await ExcelTools.auto_load_excel(file, header=None)

        assert list(type(loaded[0]).model_fields) == ['0', '1']
        assert [m.model_dump() for m in loaded] == [{'0': '1', '1': '3'}, {'0': '2', '1': '4'}]

    async def test_generated_model_fields_are_optional(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_optional_fields.xlsx')
        pd.DataFrame({'a': [1], 'b': ['x']}).to_excel(file.path, index=False)

        loaded = await ExcelTools.auto_load_excel(file)

        dynamic_model = type(loaded[0])
        assert all(not field.is_required() for field in dynamic_model.model_fields.values())
        assert dynamic_model(a=None, b=None).model_dump() == {'a': None, 'b': None}

    async def test_auto_load_all_sheets_returns_dict_with_independent_models(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_all_sheets.xlsx')
        with pd.ExcelWriter(file.path) as writer:
            pd.DataFrame({'x': [1, 2]}).to_excel(writer, sheet_name='A', index=False)
            pd.DataFrame({'y': [3]}).to_excel(writer, sheet_name='B', index=False)

        loaded = await ExcelTools.auto_load_excel(file, sheet_name=None)

        assert set(loaded) == {'A', 'B'}
        assert list(type(loaded['A'][0]).model_fields) == ['x']
        assert list(type(loaded['B'][0]).model_fields) == ['y']
        assert [m.model_dump() for m in loaded['A']] == [{'x': '1'}, {'x': '2'}]
        assert [m.model_dump() for m in loaded['B']] == [{'y': '3'}]

    async def test_auto_load_multi_header_stringified_tuple_fields(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_multi_header.xlsx')
        _make_multi_header_workbook().save(file.path)

        loaded = await ExcelTools.auto_load_excel(file, header=[0, 1])

        assert list(type(loaded[0]).model_fields) == ["('a', 'x')", "('a', 'y')", "('b', 'x')"]
        assert [m.model_dump() for m in loaded] == [
            {"('a', 'x')": '1', "('a', 'y')": '2', "('b', 'x')": '3'},
        ]

    async def test_fully_empty_rows_become_all_none_models(self, excel_file):
        from src.utils.excel_tools import ExcelTools

        file = excel_file('auto_empty_rows.xlsx')
        pd.DataFrame({'a': [1, None, 3], 'b': ['x', None, 'z']}).to_excel(file.path, index=False)

        loaded = await ExcelTools.auto_load_excel(file)

        assert [m.model_dump() for m in loaded] == [
            {'a': '1.0', 'b': 'x'},
            {'a': None, 'b': None},
            {'a': '3.0', 'b': 'z'},
        ]


class TestRoundTrip:
    async def test_multiple_round_trips_preserve_data(self, sample_tools, excel_file):
        file = excel_file('roundtrip_multi.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file)
        first = await sample_tools.load_excel(file)
        await sample_tools.dump_excel(first, file)
        second = await sample_tools.load_excel(file)

        assert first == SAMPLE_MODELS
        assert second == SAMPLE_MODELS

    async def test_round_trip_with_none_optionals(self, optional_tools, excel_file):
        file = excel_file('roundtrip_none.xlsx')
        data = [OptionalModel(name='a', remark='r', score=None), OptionalModel(name='b', remark=None, score=2.5)]

        await optional_tools.dump_excel(data, file)

        assert await optional_tools.load_excel(file) == data


class TestAppendExcel:
    async def test_append_new_sheet_preserves_existing(self, sample_tools, excel_file):
        file = excel_file('append_new.xlsx')
        extra = [SampleModel(name='extra', count=9, score=9.5, enabled=True, created_at=datetime(2024, 9, 9))]

        await sample_tools.dump_excel(SAMPLE_MODELS, file)
        await sample_tools.append_excel(extra, file, sheet_name='Extra')

        with pd.ExcelFile(file.path) as excel:
            assert excel.sheet_names == [SampleModel.__name__, 'Extra']
        assert await sample_tools.load_excel(file) == SAMPLE_MODELS
        assert await sample_tools.load_excel(file, sheet_name='Extra') == extra

    async def test_append_default_sheet_name_is_model_name(self, sample_tools, excel_file):
        file = excel_file('append_default_name.xlsx')
        pd.DataFrame({'old': [1]}).to_excel(file.path, sheet_name='Old', index=False)

        await sample_tools.append_excel(SAMPLE_MODELS, file)

        with pd.ExcelFile(file.path) as excel:
            assert excel.sheet_names == ['Old', SampleModel.__name__]

    async def test_append_nonexistent_file_raises(self, sample_tools, excel_file):
        from src.resource import ResourceNotFileError

        file = excel_file('append_not_exists.xlsx')

        with pytest.raises(ResourceNotFileError, match=_MSG_NOT_FILE):
            await sample_tools.append_excel(SAMPLE_MODELS, file)

    async def test_append_duplicate_sheet_raises_by_default(self, sample_tools, excel_file):
        from src.utils.excel_tools import ExcelToolsException

        file = excel_file('append_dup_error.xlsx')
        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        with pytest.raises(ExcelToolsException, match=_MSG_SHEET_EXISTS):
            await sample_tools.append_excel(SAMPLE_MODELS, file)

    async def test_append_replace_existing_sheet(self, sample_tools, excel_file):
        file = excel_file('append_replace.xlsx')
        replacement = [SampleModel(
            name='replacement', count=99, score=9.9, enabled=True, created_at=datetime(2024, 2, 2),
        )]

        await sample_tools.dump_excel(SAMPLE_MODELS, file)
        await sample_tools.append_excel(replacement, file, if_sheet_exists='replace')

        with pd.ExcelFile(file.path) as excel:
            assert excel.sheet_names == [SampleModel.__name__]
        assert await sample_tools.load_excel(file) == replacement

    async def test_append_replace_creates_sheet_when_missing(self, sample_tools, excel_file):
        file = excel_file('append_replace_missing.xlsx')
        pd.DataFrame({'old': [1]}).to_excel(file.path, sheet_name='Old', index=False)

        await sample_tools.append_excel(SAMPLE_MODELS, file, sheet_name='New', if_sheet_exists='replace')

        with pd.ExcelFile(file.path) as excel:
            assert excel.sheet_names == ['Old', 'New']
        assert await sample_tools.load_excel(file, sheet_name='New') == SAMPLE_MODELS

    async def test_append_empty_data_writes_header_only_sheet(self, sample_tools, excel_file):
        file = excel_file('append_empty.xlsx')
        pd.DataFrame({'old': [1]}).to_excel(file.path, sheet_name='Old', index=False)

        await sample_tools.append_excel([], file, sheet_name='Extra')

        assert await sample_tools.load_excel(file, sheet_name='Extra') == []
        assert pd.read_excel(file.path, sheet_name='Extra').columns.tolist() == list(SampleModel.model_fields)


class TestDumpExcelInChunks:
    async def test_in_chunks_equals_full_dump(self, sample_tools, excel_file):
        """逐行分块写出与非分块写出的数据内容等值"""
        chunked = excel_file('dump_in_chunks.xlsx')
        full = excel_file('dump_full_for_compare.xlsx')

        await sample_tools.dump_excel((m for m in SAMPLE_MODELS), chunked, in_chunks=True)
        await sample_tools.dump_excel(SAMPLE_MODELS, full)

        assert await sample_tools.load_excel(chunked) == SAMPLE_MODELS
        assert await sample_tools.load_excel(chunked) == await sample_tools.load_excel(full)

    async def test_in_chunks_default_off(self, sample_tools, excel_file):
        file = excel_file('dump_default_not_chunked.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        assert await sample_tools.load_excel(file) == SAMPLE_MODELS

    async def test_in_chunks_empty_data_writes_header_only(self, sample_tools, excel_file):
        file = excel_file('dump_in_chunks_empty.xlsx')

        await sample_tools.dump_excel([], file, in_chunks=True)

        assert file.is_file
        assert pd.read_excel(file.path).columns.tolist() == list(SampleModel.model_fields)
        assert await sample_tools.load_excel(file) == []

    async def test_in_chunks_custom_sheet_name_single_sheet(self, sample_tools, excel_file):
        file = excel_file('dump_in_chunks_custom.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file, sheet_name='Chunked', in_chunks=True)

        with pd.ExcelFile(file.path) as excel:
            assert excel.sheet_names == ['Chunked']
        assert await sample_tools.load_excel(file, sheet_name='Chunked') == SAMPLE_MODELS

    async def test_in_chunks_accepts_generator_input(self, sample_tools, excel_file):
        file = excel_file('dump_in_chunks_generator.xlsx')

        def _gen():
            yield from SAMPLE_MODELS

        await sample_tools.dump_excel(_gen(), file, in_chunks=True)

        assert await sample_tools.load_excel(file) == SAMPLE_MODELS

    async def test_in_chunks_with_index_writes_zero_index_column(self, sample_tools, excel_file):
        """index=True 时逐行写出的索引列值均为 0, 数据列不受影响(固有行为快照)"""
        file = excel_file('dump_in_chunks_index.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file, index=True, in_chunks=True)

        df = pd.read_excel(file.path)
        assert 'Unnamed: 0' in df.columns
        assert df['Unnamed: 0'].tolist() == [0] * len(SAMPLE_MODELS)
        loaded = await sample_tools.load_excel(file)
        assert loaded == SAMPLE_MODELS

    async def test_in_chunks_first_item_invalid_raises_validation_error(self, sample_tools, excel_file):
        """首条数据校验失败时裸抛 ValidationError, 不被包装成 ExcelToolsException"""
        from src.utils.excel_tools import ExcelToolsException

        file = excel_file('dump_in_chunks_bad_first.xlsx')

        with pytest.raises(ValidationError) as exc_info:
            await sample_tools.dump_excel([{'name': 'alpha'}], file, in_chunks=True)

        assert not isinstance(exc_info.value, ExcelToolsException)

    async def test_in_chunks_later_item_invalid_raises_validation_error(self, sample_tools, excel_file):
        """后续条目校验失败时同样裸抛 ValidationError, 与非分块路径语义一致"""
        from src.utils.excel_tools import ExcelToolsException

        file = excel_file('dump_in_chunks_bad_later.xlsx')

        with pytest.raises(ValidationError) as exc_info:
            await sample_tools.dump_excel(
                [SAMPLE_MODELS[0], {'name': 'bad'}], file, in_chunks=True
            )

        assert not isinstance(exc_info.value, ExcelToolsException)

    async def test_in_chunks_creates_missing_parent_dirs(self, sample_tools, excel_file):
        file = excel_file('deep', 'nested', 'dump_in_chunks.xlsx')

        await sample_tools.dump_excel(SAMPLE_MODELS, file, in_chunks=True)

        assert file.is_file
        assert await sample_tools.load_excel(file) == SAMPLE_MODELS


class TestExceptionWrapping:
    async def test_read_corrupt_file_wrapped(self, sample_tools, excel_file):
        from src.utils.excel_tools import ExcelToolsException

        file = excel_file('corrupt.xlsx')
        file.path.write_text('this is not an excel file', encoding='utf-8')

        with pytest.raises(ExcelToolsException, match=_MSG_PARSE_FAIL) as exc_info:
            await sample_tools.load_excel(file)

        assert exc_info.value.__cause__ is not None
        assert not isinstance(exc_info.value.__cause__, ExcelToolsException)

    async def test_read_missing_sheet_wrapped_with_sheet_name(self, sample_tools, excel_file):
        from src.utils.excel_tools import ExcelToolsException

        file = excel_file('missing_sheet.xlsx')
        await sample_tools.dump_excel(SAMPLE_MODELS, file)

        with pytest.raises(ExcelToolsException, match='NOPE'):
            await sample_tools.load_excel(file, sheet_name='NOPE')

    async def test_write_to_directory_wrapped(self, sample_tools):
        from src.resource import TemporaryResource
        from src.utils.excel_tools import ExcelToolsException

        target = TemporaryResource('excel_tools_test', 'as_dir.xlsx')
        target.path.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ExcelToolsException, match=_MSG_WRITE_FAIL):
            await sample_tools.dump_excel(SAMPLE_MODELS, target)

    async def test_exception_contract(self):
        from src.exception import OmegaException
        from src.utils.excel_tools import ExcelToolsException

        assert issubclass(ExcelToolsException, OmegaException)

        exc = ExcelToolsException('some message')
        assert exc.message == 'some message'
        assert 'some message' in str(exc)
        assert repr(exc) == "ExcelToolsException(message='some message')"

    async def test_validation_error_not_wrapped(self, sample_tools, excel_file):
        from src.utils.excel_tools import ExcelToolsException

        file = excel_file('invalid_data.xlsx')

        with pytest.raises(ValidationError) as exc_info:
            await sample_tools.dump_excel([{'name': 'alpha'}], file)

        assert not isinstance(exc_info.value, ExcelToolsException)
        assert not file.is_file
