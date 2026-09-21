"""
@Author         : Ailitonia
@Date           : 2025/1/16 14:44:53
@FileName       : excel_tools.py
@Project        : omega-miya
@Description    :
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import os
from collections.abc import Callable, Generator, Iterable, Sequence
from io import SEEK_END, BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Literal, Self, final, overload
from uuid import uuid4

import pandas as pd
from nonebot.utils import run_sync
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from src.exception import OmegaException
from src.resource import BaseResource

type ExcelFileTarget = BaseResource | BinaryIO
"""Excel 读写目标, 本地资源文件或二进制内存缓冲区"""

_INVALID_SHEET_NAME_CHARS = frozenset('[]:*?/\\')
"""Excel sheet 名非法字符"""


@final
class ExcelToolsException(OmegaException):
    """Excel 工具读写异常"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(message={self.message!r})'


def _prepare_read_target(excel_file: ExcelFileTarget) -> Path | BinaryIO:
    """资源文件校验存在性后返回路径, 内存缓冲区重置读指针后原样返回"""
    if isinstance(excel_file, BaseResource):
        excel_file.raise_not_file()
        return excel_file.path
    try:
        excel_file.seek(0)
    except (OSError, ValueError) as e:
        raise ExcelToolsException(f'读取目标缓冲区不可用: {e}') from e
    return excel_file


def _prepare_overwrite_target(excel_file: ExcelFileTarget) -> Path | BinaryIO:
    """资源文件确保父目录存在后返回路径, 内存缓冲区清空重置后原样返回(等价 'wb' 覆写语义)"""
    if isinstance(excel_file, BaseResource):
        excel_file.ensure_parent_path()
        return excel_file.path
    try:
        excel_file.seek(0)
        excel_file.truncate()
    except (OSError, ValueError) as e:
        raise ExcelToolsException(f'写入目标缓冲区不可用: {e}') from e
    return excel_file


def _prepare_append_target(excel_file: ExcelFileTarget) -> Path | BinaryIO:
    """资源文件原样返回路径(追加目标存在性由调用方校验), 非空内存缓冲区重置读指针后原样返回, 空缓冲区视为不存在的文件"""
    if isinstance(excel_file, BaseResource):
        return excel_file.path
    try:
        is_empty = excel_file.seek(0, SEEK_END) == 0
    except (OSError, ValueError) as e:
        raise ExcelToolsException(f'追加目标缓冲区不可用: {e}') from e
    if is_empty:
        raise ExcelToolsException('无法向空缓冲区追加数据, 目标缓冲区未包含有效的 Excel 内容')
    excel_file.seek(0)
    return excel_file


def _validate_sheet_name(sheet_name: str) -> None:
    """校验 sheet 名合法性, 空名/超过 31 字符/含非法字符 [ ] : * ? / \\ 时抛出 ExcelToolsException"""
    if not sheet_name:
        raise ExcelToolsException('sheet 名不能为空')
    if len(sheet_name) > 31:
        raise ExcelToolsException(f'sheet 名超过 31 字符限制: {sheet_name!r}')
    if any(char in _INVALID_SHEET_NAME_CHARS for char in sheet_name):
        raise ExcelToolsException(f'sheet 名包含非法字符 [ ] : * ? / \\: {sheet_name!r}')


class ExcelTools[DataModel_T: BaseModel]:
    """Excel 导入导出工具

    读取时空单元格(NaN/NA/NaT)统一解析为 None, 可选字段接收 None, 必填字段抛出 ValidationError;
    auto_load_excel 自动生成的动态模型所有字段均为可选的 str 类型, 数值/日期/布尔单元格一律转为字符串.

    使用约束:
    - 显式模型的 str 字段遇数值单元格会因 pydantic 严格语义抛出 ValidationError,
      建议字段使用对应的数值类型或改用 auto_load_excel;
    - 显式模型建议使用普通字段名: alias/validation_alias 字段无法保证写读往返匹配,
      extra='forbid' 的模型与 index=True 写出的文件(含 Unnamed: 0 索引列)不兼容;
    - 传入 data_model 子类实例时按 data_model 归一化, 子类额外字段不写出;
    - 多级表头(header=[0, 1] 等)读回的列名为 tuple, str 化后形如 "('a', 'x')",
      显式模型字段一般无法匹配, 多级表头建议配合 auto 模式使用;
    - sheet_name=None 时读取全部 sheet, 返回以 sheet 名为键的结果字典, 各 sheet 独立建模;
    - auto 模式自动建模时, 以 model_ 开头/与 BaseModel 成员同名/以下划线开头的列名会被重命名
      (加 col_ 前缀, 与既有字段名冲突时追加序号), 原始列名仍作为数据校验键, 数据不丢失,
      仅 model_dump() 中对应键为重命名后的字段名;
    - datetime 单元格精度为毫秒(Excel 序列日期固有限制), 微秒部分静默截断,
      含微秒的 datetime 无法精确往返; 时区感知 datetime 无法写出(openpyxl 限制), 抛出 ExcelToolsException;
    - sheet 名不能为空且不得超过 31 字符, 不得包含 [ ] : * ? / \\ 字符,
      dump/append 写入前校验, 非法 sheet 名抛出 ExcelToolsException;
    - append_excel 向已存在的文件追加/替换 sheet, 不提供分块(同一写入会话内同名 sheet 只能写一次),
      追加为原地操作, 非原子写入;
    - dump_excel 的 in_chunks 用于逐行惰性写出大数据量, 输入迭代器惰性消费, 避免一次性物化全部数据,
      注意 in_chunks 配合 index=True 时写出的索引列值均为 0(单行 DataFrame 固有行为);
    - dump_excel(整量与分块)采用临时目标原子写入: 全部数据成功写出后才一次性替换目标,
      中途数据校验或写入失败时目标保持写入前内容;
    - 读写目标支持 BinaryIO 内存缓冲区: 读取前重置读指针, 覆写前清空缓冲区(等价 'wb' 语义),
      向空缓冲区追加等同向不存在的文件追加, 抛出 ExcelToolsException, 缓冲区目标跳过路径存在性检查与父目录创建,
      不可 seek 或已关闭的缓冲区在目标检查阶段抛出 ExcelToolsException.
    """

    def __init__(self, data_model: type[DataModel_T]):
        if not (isinstance(data_model, type) and issubclass(data_model, BaseModel)):
            raise TypeError(f'data_model 必须是 pydantic BaseModel 子类: {data_model!r}')
        self.data_model = data_model

    @staticmethod
    def _is_conflicting_field_name(name: str) -> bool:
        """判断字段名是否会与 pydantic 模型机制冲突(model_ 前缀/BaseModel 成员/下划线私有属性)"""
        return name.startswith('model_') or name.startswith('_') or hasattr(BaseModel, name)

    @staticmethod
    def _dedupe_name(candidate: str, used_names: set[str]) -> str:
        """为重命名字段生成不与既有字段名冲突的唯一名称, 必要时追加递增序号"""
        index = 1
        deduped = candidate
        while deduped in used_names:
            index += 1
            deduped = f'{candidate}_{index}'
        return deduped

    @classmethod
    def _init_from_fields(cls, fields: Iterable[str]) -> Self:
        """根据表头字段名自动创建数据模型

        以 model_ 开头/与 BaseModel 成员同名/以下划线开头的字段名会被重命名(加 col_ 前缀),
        原始列名通过 validation_alias 保留为数据校验键
        """
        raw_names = list(dict.fromkeys(fields))
        used_names = set(raw_names)
        field_definitions: dict[str, Any] = {}
        for name in raw_names:
            safe_name = name if not cls._is_conflicting_field_name(name) else cls._dedupe_name(
                f'col_{name}', used_names
            )
            used_names.add(safe_name)
            field_definitions[safe_name] = (str | None, Field(default=None, validation_alias=name))

        try:
            model = create_model(
                'ExcelDataModel',
                __config__=ConfigDict(extra='ignore', coerce_numbers_to_str=True),
                **field_definitions,
            )
        except Exception as e:
            raise ExcelToolsException(f'自动建模失败: {e}') from e
        return cls(model)  # type: ignore

    @staticmethod
    def _clean_dataframe(data: pd.DataFrame) -> pd.DataFrame:
        """将 DataFrame 中的缺失值(NaN/NA/NaT)统一转换为 None"""
        return data.astype(object).where(data.notna(), None)

    @staticmethod
    def _stringify_value(value: Any) -> Any:
        """保留 None 与 str, 将其余值(数值/日期/布尔等)转换为字符串"""
        if value is None or isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _read_excel(
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int | None = 0,
            header: int | Sequence[int] | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> pd.DataFrame | dict[str, pd.DataFrame]:
        """读取 Excel 数据, sheet_name 为 None 时返回全部 sheet 组成的字典"""
        read_target = _prepare_read_target(excel_file)
        try:
            return pd.read_excel(
                read_target,
                sheet_name=sheet_name,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
            )
        except Exception as e:
            raise ExcelToolsException(f'解析 Excel 文件失败: {e}') from e

    @staticmethod
    def _atomic_write(excel_file: ExcelFileTarget, write: Callable[[Path | BinaryIO], None]) -> None:
        """在临时目标上执行写入, 全部成功后原子替换目标, 失败时目标保持写入前内容且不残留临时文件"""
        if isinstance(excel_file, BaseResource):
            excel_file.ensure_parent_path()
            temp_path = excel_file.path.with_name(f'.{excel_file.path.name}.{uuid4().hex}.tmp')
            try:
                write(temp_path)
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
            try:
                os.replace(temp_path, excel_file.path)
            except OSError as e:
                temp_path.unlink(missing_ok=True)
                raise ExcelToolsException(f'写入 Excel 文件失败: {e}') from e
        else:
            temp_buffer = BytesIO()
            write(temp_buffer)
            try:
                excel_file.seek(0)
                excel_file.truncate()
                excel_file.write(temp_buffer.getvalue())
            except (OSError, ValueError) as e:
                raise ExcelToolsException(f'写入 Excel 文件失败: 写入目标缓冲区不可用: {e}') from e

    @staticmethod
    def _write_excel(
            data: pd.DataFrame,
            write_target: Path | BinaryIO,
            *,
            index: bool = False,
            sheet_name: str = 'Default',
    ) -> None:
        """导出 Excel 数据到已就绪的写入目标"""
        try:
            data.to_excel(write_target, index=index, sheet_name=sheet_name, engine='openpyxl')
        except Exception as e:
            raise ExcelToolsException(f'写入 Excel 文件失败: {e}') from e

    @staticmethod
    def _write_excel_in_chunks(
            data_iter: Iterable[pd.DataFrame],
            write_target: Path | BinaryIO,
            *,
            index: bool,
            sheet_name: str,
    ) -> None:
        """分块导出 Excel 数据到已就绪的写入目标

        首块在写入会话外预取, 数据校验错误在写入会话外抛出, 空迭代器写出仅含空 sheet 的文件
        """
        iterator = iter(data_iter)
        first_chunk = next(iterator, None)
        if first_chunk is None:
            first_chunk = pd.DataFrame()
        try:
            with pd.ExcelWriter(write_target, engine='openpyxl') as writer:
                first_chunk.to_excel(writer, index=index, header=True, sheet_name=sheet_name)
                for chunk in iterator:
                    chunk.to_excel(
                        writer,
                        index=index,
                        sheet_name=sheet_name,
                        header=False,
                        startrow=writer.sheets[sheet_name].max_row,
                    )
        except ValidationError:
            raise
        except Exception as e:
            raise ExcelToolsException(f'写入 Excel 文件失败: {e}') from e

    @staticmethod
    def _append_write_excel(
            data: pd.DataFrame,
            excel_file: ExcelFileTarget,
            *,
            index: bool = False,
            sheet_name: str = 'Default',
            if_sheet_exists: Literal['error', 'replace'] = 'error',
    ) -> None:
        """向已存在的 Excel 文件追加或替换 sheet"""
        append_target = _prepare_append_target(excel_file)
        try:
            with pd.ExcelWriter(append_target, mode='a', if_sheet_exists=if_sheet_exists) as writer:
                data.to_excel(writer, index=index, sheet_name=sheet_name)
        except Exception as e:
            raise ExcelToolsException(f'写入 Excel 文件失败: {e}') from e

    def _parse_data(self, data: Iterable[DataModel_T | dict[str, Any]]) -> Generator[DataModel_T, None, None]:
        """将输入数据校验为模型实例的惰性迭代器, data_model 子类实例按 data_model 归一化(子类额外字段丢弃)"""
        return (
            x if type(x) is self.data_model
            else self.data_model.model_validate(x.model_dump() if isinstance(x, BaseModel) else x)
            for x in data
        )

    def _dump_excel_data(self, data: Iterable[DataModel_T | dict[str, Any]]) -> pd.DataFrame:
        """将模型数据列表转换为 Excel 数据, 空数据仅保留表头"""
        parsed_data = list(self._parse_data(data))
        if not parsed_data:
            return pd.DataFrame(columns=list(self.data_model.model_fields))
        return pd.DataFrame([x.model_dump() for x in parsed_data])

    def _dump_excel_data_iter(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
    ) -> Generator[pd.DataFrame, None, None]:
        """将模型数据逐条转换为单行 Excel 数据的惰性迭代器, 空数据仅保留表头"""
        iter_is_null = True
        for parsed_data in self._parse_data(data):
            if iter_is_null:
                iter_is_null = False
            yield pd.DataFrame([parsed_data.model_dump()])
        if iter_is_null:
            yield pd.DataFrame(columns=list(self.data_model.model_fields))

    def _load_excel_data(self, data: pd.DataFrame) -> list[DataModel_T]:
        """将 Excel 数据转换为模型数据列表, 空单元格解析为 None"""
        cleaned_data = self._clean_dataframe(data)
        return [
            self.data_model(**{str(k): v for k, v in row.items()})
            for row in cleaned_data.to_dict(orient='records')
        ]

    @classmethod
    def _auto_load_sheet(cls, data: pd.DataFrame) -> list[DataModel_T]:
        """将单个 sheet 的 Excel 数据按表头自动建模并解析"""
        stringified_data = cls._clean_dataframe(data).map(cls._stringify_value)
        fields = stringified_data.to_dict(orient='list').keys()
        return cls._init_from_fields(str(field) for field in fields)._load_excel_data(stringified_data)

    @run_sync
    def _dump_excel(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
            excel_file: ExcelFileTarget,
            *,
            index: bool = False,
            sheet_name: str = 'Default',
    ) -> None:
        """导出 Excel 数据, 采用临时目标原子写入"""
        data_frame = self._dump_excel_data(data)
        self._atomic_write(
            excel_file,
            lambda target: self._write_excel(data_frame, target, index=index, sheet_name=sheet_name),
        )

    @run_sync
    def _dump_excel_in_chunks(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
            excel_file: ExcelFileTarget,
            *,
            index: bool,
            sheet_name: str,
    ) -> None:
        """分块导出 Excel 数据, 输入为原始数据迭代器, 惰性消费, 空数据仅保留表头

        采用临时目标原子写入: 全部数据成功写出后才一次性替换目标, 中途失败时目标保持写入前内容
        """
        data_iter = self._dump_excel_data_iter(data)
        self._atomic_write(
            excel_file,
            lambda target: self._write_excel_in_chunks(data_iter, target, index=index, sheet_name=sheet_name),
        )

    @run_sync
    def _append_excel(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
            excel_file: ExcelFileTarget,
            *,
            index: bool = False,
            sheet_name: str = 'Default',
            if_sheet_exists: Literal['error', 'replace'] = 'error',
    ) -> None:
        """向已存在的 Excel 文件追加或替换 sheet"""
        if isinstance(excel_file, BaseResource):
            excel_file.raise_not_file()
        self._append_write_excel(
            self._dump_excel_data(data),
            excel_file,
            index=index,
            sheet_name=sheet_name,
            if_sheet_exists=if_sheet_exists,
        )

    @run_sync
    def _load_excel(
            self,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int | None = 0,
            header: int | Sequence[int] | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> list[DataModel_T] | dict[str, list[DataModel_T]]:
        """读取并解析 Excel 数据"""
        data = self._read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
        )
        if isinstance(data, dict):
            return {sheet: self._load_excel_data(sheet_data) for sheet, sheet_data in data.items()}
        return self._load_excel_data(data)

    @classmethod
    @run_sync
    def _auto_load_excel(
            cls,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int | None = 0,
            header: int | Sequence[int] | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> list[DataModel_T] | dict[str, list[DataModel_T]]:
        """读取并解析 Excel 数据, 自动生成数据模型"""
        data = cls._read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
        )
        if isinstance(data, dict):
            return {sheet: cls._auto_load_sheet(sheet_data) for sheet, sheet_data in data.items()}
        return cls._auto_load_sheet(data)

    async def dump_excel(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
            excel_file: ExcelFileTarget,
            *,
            index: bool = False,
            sheet_name: str | None = None,
            in_chunks: bool = False,
    ) -> None:
        """导出 Excel 数据

        in_chunks=True 时分块写出, 输入迭代器惰性消费, 适合大数据量场景;
        整量与分块写出均采用临时目标原子写入, 数据校验或写入失败时目标保持写入前内容
        """
        if sheet_name is None:
            sheet_name = self.data_model.__name__
        _validate_sheet_name(sheet_name)
        if in_chunks:
            return await self._dump_excel_in_chunks(data, excel_file, index=index, sheet_name=sheet_name)
        return await self._dump_excel(data, excel_file, index=index, sheet_name=sheet_name)

    async def append_excel(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
            excel_file: ExcelFileTarget,
            *,
            index: bool = False,
            sheet_name: str | None = None,
            if_sheet_exists: Literal['error', 'replace'] = 'error',
    ) -> None:
        """向已存在的 Excel 文件追加 sheet, 同名 sheet 默认报错, 可选替换, 追加为原地操作, 非原子写入"""
        if sheet_name is None:
            sheet_name = self.data_model.__name__
        _validate_sheet_name(sheet_name)
        return await self._append_excel(
            data,
            excel_file,
            index=index,
            sheet_name=sheet_name,
            if_sheet_exists=if_sheet_exists,
        )

    @overload
    async def load_excel(
            self,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int = ...,
            header: int | Sequence[int] | None = ...,
            skiprows: int | None = ...,
            nrows: int | None = ...,
    ) -> list[DataModel_T]:
        ...

    @overload
    async def load_excel(
            self,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: None = ...,
            header: int | Sequence[int] | None = ...,
            skiprows: int | None = ...,
            nrows: int | None = ...,
    ) -> dict[str, list[DataModel_T]]:
        ...

    @overload
    async def load_excel(
            self,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int | None = ...,
            header: int | Sequence[int] | None = ...,
            skiprows: int | None = ...,
            nrows: int | None = ...,
    ) -> list[DataModel_T] | dict[str, list[DataModel_T]]:
        ...

    async def load_excel(
            self,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int | None = 0,
            header: int | Sequence[int] | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> list[DataModel_T] | dict[str, list[DataModel_T]]:
        """读取并解析 Excel 数据, sheet_name 为 None 时读取全部 sheet 并返回字典"""
        return await self._load_excel(
            excel_file,
            sheet_name=sheet_name,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
        )

    @overload
    @classmethod
    async def auto_load_excel(
            cls,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int = ...,
            header: int | Sequence[int] | None = ...,
            skiprows: int | None = ...,
            nrows: int | None = ...,
    ) -> list[DataModel_T]:
        ...

    @overload
    @classmethod
    async def auto_load_excel(
            cls,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: None = ...,
            header: int | Sequence[int] | None = ...,
            skiprows: int | None = ...,
            nrows: int | None = ...,
    ) -> dict[str, list[DataModel_T]]:
        ...

    @overload
    @classmethod
    async def auto_load_excel(
            cls,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int | None = ...,
            header: int | Sequence[int] | None = ...,
            skiprows: int | None = ...,
            nrows: int | None = ...,
    ) -> list[DataModel_T] | dict[str, list[DataModel_T]]:
        ...

    @classmethod
    async def auto_load_excel(
            cls,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int | None = 0,
            header: int | Sequence[int] | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> list[DataModel_T] | dict[str, list[DataModel_T]]:
        """读取并解析 Excel 数据, 自动生成数据模型, sheet_name 为 None 时读取全部 sheet 并返回字典"""
        return await cls._auto_load_excel(
            excel_file,
            sheet_name=sheet_name,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
        )


__all__ = [
    'ExcelFileTarget',
    'ExcelTools',
    'ExcelToolsException',
]
