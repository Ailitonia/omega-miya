"""
@Author         : Ailitonia
@Date           : 2025/1/16 14:44:53
@FileName       : excel_tools.py
@Project        : omega-miya
@Description    :
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Generator, Iterable, Sequence
from io import SEEK_END
from pathlib import Path
from typing import Any, BinaryIO, Literal, Self, final, overload

import pandas as pd
from nonebot.utils import run_sync
from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from src.exception import OmegaException
from src.resource import BaseResource

type ExcelFileTarget = BaseResource | BinaryIO
"""Excel 读写目标, 本地资源文件或二进制内存缓冲区"""


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
    excel_file.seek(0)
    return excel_file


def _prepare_overwrite_target(excel_file: ExcelFileTarget) -> Path | BinaryIO:
    """资源文件确保父目录存在后返回路径, 内存缓冲区清空重置后原样返回(等价 'wb' 覆写语义)"""
    if isinstance(excel_file, BaseResource):
        excel_file.ensure_parent_path()
        return excel_file.path
    excel_file.seek(0)
    excel_file.truncate()
    return excel_file


def _prepare_append_target(excel_file: ExcelFileTarget) -> Path | BinaryIO:
    """资源文件确保父目录存在后返回路径, 非空内存缓冲区重置读指针后原样返回, 空缓冲区视为不存在的文件"""
    if isinstance(excel_file, BaseResource):
        excel_file.ensure_parent_path()
        return excel_file.path
    if excel_file.seek(0, SEEK_END) == 0:
        raise ExcelToolsException('无法向空缓冲区追加数据, 目标缓冲区未包含有效的 Excel 内容')
    excel_file.seek(0)
    return excel_file


class ExcelTools[DataModel_T: BaseModel]:
    """Excel 导入导出工具

    读取时空单元格(NaN/NA/NaT)统一解析为 None, 可选字段接收 None, 必填字段抛出 ValidationError;
    auto_load_excel 自动生成的动态模型所有字段均为可选的 str 类型, 数值/日期/布尔单元格一律转为字符串.

    使用约束:
    - 显式模型的 str 字段遇数值单元格会因 pydantic 严格语义抛出 ValidationError,
      建议字段使用对应的数值类型或改用 auto_load_excel;
    - 多级表头(header=[0, 1] 等)读回的列名为 tuple, str 化后形如 "('a', 'x')",
      显式模型字段一般无法匹配, 多级表头建议配合 auto 模式使用;
    - sheet_name=None 时读取全部 sheet, 返回以 sheet 名为键的结果字典, 各 sheet 独立建模;
    - append_excel 向已存在的文件追加/替换 sheet, 不提供分块(同一写入会话内同名 sheet 只能写一次);
    - dump_excel 的 in_chunks 用于逐行惰性写出大数据量, 输入迭代器惰性消费, 避免一次性物化全部数据,
      注意 in_chunks 配合 index=True 时写出的索引列值均为 0(单行 DataFrame 固有行为);
    - 读写目标支持 BinaryIO 内存缓冲区: 读取前重置读指针, 覆写前清空缓冲区(等价 'wb' 语义),
      向空缓冲区追加等同向不存在的文件追加, 抛出 ExcelToolsException, 缓冲区目标跳过路径存在性检查与父目录创建.
    """

    def __init__(self, data_model: type[DataModel_T]):
        self.data_model = data_model

    @classmethod
    def _init_from_fields(cls, fields: Iterable[str]) -> Self:
        return cls(create_model(
            'ExcelDataModel',
            __config__=ConfigDict(extra='ignore', coerce_numbers_to_str=True),
            **dict.fromkeys(fields, (str | None, None))  # type: ignore
        ))

    @staticmethod
    def _clean_dataframe(data: 'pd.DataFrame') -> 'pd.DataFrame':
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
    ) -> 'pd.DataFrame | dict[str, pd.DataFrame]':
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
    def _write_excel(
            data: 'pd.DataFrame',
            excel_file: ExcelFileTarget,
            *,
            index: bool = False,
            sheet_name: str = 'Default',
    ) -> None:
        """导出 Excel 数据"""
        write_target = _prepare_overwrite_target(excel_file)
        try:
            data.to_excel(write_target, index=index, sheet_name=sheet_name)
        except Exception as e:
            raise ExcelToolsException(f'写入 Excel 文件失败: {e}') from e

    @staticmethod
    def _write_excel_in_chunks(
            data_iter: Iterable['pd.DataFrame'],
            excel_file: ExcelFileTarget,
            *,
            index: bool,
            sheet_name: str,
    ) -> None:
        """分块导出 Excel 数据, 首块在写入会话外预取, 数据校验错误在写入会话外抛出"""
        iterator = iter(data_iter)
        first_chunk = next(iterator, None)

        write_target = _prepare_overwrite_target(excel_file)
        try:
            with pd.ExcelWriter(write_target) as writer:
                if first_chunk is not None:
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
            data: 'pd.DataFrame',
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
        """将输入数据校验为模型实例的惰性迭代器"""
        return (x if isinstance(x, self.data_model) else self.data_model.model_validate(x) for x in data)

    def _dump_excel_data(self, data: Iterable[DataModel_T | dict[str, Any]]) -> 'pd.DataFrame':
        """将模型数据列表转换为 Excel 数据, 空数据仅保留表头"""
        parsed_data = list(self._parse_data(data))
        if not parsed_data:
            return pd.DataFrame(columns=list(self.data_model.model_fields))
        return pd.DataFrame([x.model_dump() for x in parsed_data])

    def _dump_excel_data_iter(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
    ) -> Generator['pd.DataFrame', None, None]:
        """将模型数据逐条转换为单行 Excel 数据的惰性迭代器, 空数据仅保留表头"""
        iter_is_null = True
        for parsed_data in self._parse_data(data):
            if iter_is_null:
                iter_is_null = False
            yield pd.DataFrame([parsed_data.model_dump()])
        if iter_is_null:
            yield pd.DataFrame(columns=list(self.data_model.model_fields))

    def _load_excel_data(self, data: 'pd.DataFrame') -> list[DataModel_T]:
        """将 Excel 数据转换为模型数据列表, 空单元格解析为 None"""
        cleaned_data = self._clean_dataframe(data)
        return [
            self.data_model(**{str(k): v for k, v in row.items()})
            for row in cleaned_data.to_dict(orient='records')
        ]

    @classmethod
    def _auto_load_sheet(cls, data: 'pd.DataFrame') -> list[DataModel_T]:
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
        """导出 Excel 数据"""
        self._write_excel(self._dump_excel_data(data), excel_file, index=index, sheet_name=sheet_name)

    @run_sync
    def _dump_excel_in_chunks(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
            excel_file: ExcelFileTarget,
            *,
            index: bool,
            sheet_name: str,
    ) -> None:
        """分块导出 Excel 数据, 输入为原始数据迭代器, 惰性消费, 空数据仅保留表头"""
        self._write_excel_in_chunks(self._dump_excel_data_iter(data), excel_file, index=index, sheet_name=sheet_name)

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

    @classmethod
    @run_sync
    def _load_excel(
            cls,  # noqa: ARG003
            excel_file: ExcelFileTarget,
            data_model: 'type[DataModel_T]',
            *,
            sheet_name: str | int | None = 0,
            header: int | Sequence[int] | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> 'list[DataModel_T] | dict[str, list[DataModel_T]]':
        """读取并解析 Excel 数据"""
        tools = cls(data_model)
        data = cls._read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=header,
            skiprows=skiprows,
            nrows=nrows
        )
        if isinstance(data, dict):
            return {sheet: tools._load_excel_data(sheet_data) for sheet, sheet_data in data.items()}
        return tools._load_excel_data(data)

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
    ) -> 'list[DataModel_T] | dict[str, list[DataModel_T]]':
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

        in_chunks=True 时分块写出, 输入迭代器惰性消费, 适合大数据量场景
        """
        if sheet_name is None:
            sheet_name = self.data_model.__name__
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
        """向已存在的 Excel 文件追加 sheet, 同名 sheet 默认报错, 可选替换"""
        if sheet_name is None:
            sheet_name = self.data_model.__name__
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
    ) -> 'list[DataModel_T]':
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
    ) -> 'dict[str, list[DataModel_T]]':
        ...

    async def load_excel(
            self,
            excel_file: ExcelFileTarget,
            *,
            sheet_name: str | int | None = 0,
            header: int | Sequence[int] | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> 'list[DataModel_T] | dict[str, list[DataModel_T]]':
        """读取并解析 Excel 数据, sheet_name 为 None 时读取全部 sheet 并返回字典"""
        return await self._load_excel(
            excel_file,
            self.data_model,
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
    ) -> 'list[DataModel_T]':
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
    ) -> 'dict[str, list[DataModel_T]]':
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
    ) -> 'list[DataModel_T] | dict[str, list[DataModel_T]]':
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
