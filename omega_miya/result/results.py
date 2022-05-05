from pydantic import Json
from pydantic.generics import GenericModel
from typing import Dict, List, Set, Tuple, Any, Optional, TypeVar, Generic
from datetime import date


T = TypeVar('T')


class BaseResult(GenericModel, Generic[T]):
    error: bool
    info: str
    result: Optional[T] = None

    @property
    def success(self) -> bool:
        return not self.error


class DictResult(BaseResult):
    result: dict


class IntDictResult(BaseResult):
    result: Dict[int, int]


class TextDictResult(BaseResult):
    result: Dict[str, str]


class JsonDictResult(BaseResult):
    result: Json


class ListResult(BaseResult):
    result: list


class IntListResult(BaseResult):
    result: List[int]


class TextListResult(BaseResult):
    result: List[str]


class TupleListResult(BaseResult):
    result: List[tuple]


class DictListResult(BaseResult):
    result: List[dict]


class DateListResult(BaseResult):
    result: List[date]


class SetResult(BaseResult):
    result: set


class IntSetResult(BaseResult):
    result: Set[int]


class TextSetResult(BaseResult):
    result: Set[str]


class TupleResult(BaseResult):
    result: tuple


class IntTupleResult(BaseResult):
    result: Tuple[int, ...]


class TextTupleResult(BaseResult):
    result: Tuple[str, ...]


class IntResult(BaseResult):
    result: int


class TextResult(BaseResult):
    result: str


class BoolResult(BaseResult):
    result: bool


class BytesResult(BaseResult):
    result: bytes


class AnyResult(BaseResult):
    result: Any


__all__ = [
    'BaseResult',
    'DictResult',
    'IntDictResult',
    'TextDictResult',
    'JsonDictResult',
    'ListResult',
    'IntListResult',
    'TextListResult',
    'TupleListResult',
    'DictListResult',
    'DateListResult',
    'SetResult',
    'IntSetResult',
    'TextSetResult',
    'TupleResult',
    'IntTupleResult',
    'TextTupleResult',
    'IntResult',
    'TextResult',
    'BoolResult',
    'BytesResult',
    'AnyResult'
]
