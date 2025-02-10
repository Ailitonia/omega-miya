"""
@Author         : Ailitonia
@Date           : 2025/1/16 14:44:53
@FileName       : excel_tools.py
@Project        : omega-miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Any, Iterable, Self

import pandas as pd
from nonebot.utils import run_sync
from pydantic import BaseModel, ConfigDict, create_model

if TYPE_CHECKING:
    from src.resource import BaseResource


class ExcelTools[DataModel_T: BaseModel]:
    """Excel 导入导出工具"""

    def __init__(self, data_model: type[DataModel_T]):
        self.data_model = data_model

    @classmethod
    def _init_from_fields(cls, fields: Iterable[str]) -> Self:
        return cls(create_model(
            'ExcelDataModel',
            __config__=ConfigDict(extra='ignore', coerce_numbers_to_str=True),
            **{field: (str, ...) for field in fields}  # type: ignore
        ))

    @classmethod
    def _read_excel(
            cls,
            excel_file: 'BaseResource',
            *,
            sheet_name: str | int = 0,
            header: int | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> 'pd.DataFrame':
        """读取 Excel 数据"""
        return pd.read_excel(excel_file.path, sheet_name, header=header, skiprows=skiprows, nrows=nrows)

    @classmethod
    def _write_excel(
            cls,
            data: 'pd.DataFrame',
            excel_file: 'BaseResource',
            *,
            index: bool = False,
            sheet_name: str = 'Default',
    ) -> None:
        """导出 Excel 数据"""
        return data.to_excel(excel_file.path, index=index, sheet_name=sheet_name)

    def _dump_excel_data(self, data: Iterable[DataModel_T | dict[str, Any]]) -> 'pd.DataFrame':
        """将模型数据列表转换为 Excel 数据"""
        parsed_data = map(lambda x: x if isinstance(x, self.data_model) else self.data_model.model_validate(x), data)
        return pd.DataFrame([x.model_dump() for x in parsed_data])

    def _load_excel_data(self, data: 'pd.DataFrame') -> list[DataModel_T]:
        """将 Excel 数据转换为模型数据列表"""
        return [self.data_model(**{str(k): v for k, v in row.items()}) for row in data.to_dict(orient='records')]

    @run_sync
    def _dump_excel(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
            excel_file: 'BaseResource',
            *,
            index: bool = False,
            sheet_name: str = 'Default',
    ) -> None:
        """导出 Excel 数据"""
        return self._write_excel(self._dump_excel_data(data), excel_file, index=index, sheet_name=sheet_name)

    @run_sync
    def _load_excel(
            self,
            excel_file: 'BaseResource',
            *,
            sheet_name: str | int = 0,
            header: int | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> list[DataModel_T]:
        """读取并解析 Excel 数据"""
        return self._load_excel_data(self._read_excel(
            excel_file, sheet_name=sheet_name, header=header, skiprows=skiprows, nrows=nrows
        ))

    @classmethod
    @run_sync
    def _auto_load_excel(
            cls,
            excel_file: 'BaseResource',
            *,
            sheet_name: str | int = 0,
            header: int | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> list[DataModel_T]:
        """读取并解析 Excel 数据, 自动生成数据模型"""
        data = cls._read_excel(excel_file, sheet_name=sheet_name, header=header, skiprows=skiprows, nrows=nrows)
        fields = data.to_dict(orient='list').keys()
        return cls._init_from_fields(str(field) for field in fields)._load_excel_data(data)

    async def dump_excel(
            self,
            data: Iterable[DataModel_T | dict[str, Any]],
            excel_file: 'BaseResource',
            *,
            index: bool = True,
            sheet_name: str | None = None,
    ) -> None:
        """导出 Excel 数据"""
        if sheet_name is None:
            sheet_name = self.data_model.__name__
        return await self._dump_excel(data, excel_file, index=index, sheet_name=sheet_name)

    async def load_excel(
            self,
            excel_file: 'BaseResource',
            *,
            sheet_name: str | int = 0,
            header: int | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> list[DataModel_T]:
        """读取并解析 Excel 数据"""
        return await self._load_excel(
            excel_file, sheet_name=sheet_name, header=header, skiprows=skiprows, nrows=nrows
        )

    @classmethod
    async def auto_load_excel(
            cls,
            excel_file: 'BaseResource',
            *,
            sheet_name: str | int = 0,
            header: int | None = 0,
            skiprows: int | None = None,
            nrows: int | None = None,
    ) -> list[DataModel_T]:
        """读取并解析 Excel 数据, 自动生成数据模型"""
        return await cls._auto_load_excel(
            excel_file, sheet_name=sheet_name, header=header, skiprows=skiprows, nrows=nrows
        )


__all__ = [
    'ExcelTools',
]
