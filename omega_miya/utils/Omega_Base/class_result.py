from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Union, Any


@dataclass
class BaseResult:
    error: bool
    info: str

    def success(self) -> bool:
        if not self.error:
            return True
        else:
            return False


class Result(object):
    @dataclass
    class DictResult(BaseResult):
        result: dict

        def __repr__(self):
            return f'<DictResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class IntDictResult(BaseResult):
        result: Dict[int, int]

        def __repr__(self):
            return f'<IntDictResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class TextDictResult(BaseResult):
        result: Dict[str, str]

        def __repr__(self):
            return f'<TextDictResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class JsonDictResult(BaseResult):
        result: Dict[str, Union[str, int, bool, list, dict]]

        def __repr__(self):
            return f'<JsonDictResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class ListResult(BaseResult):
        result: list

        def __repr__(self):
            return f'<ListResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class IntListResult(BaseResult):
        result: List[int]

        def __repr__(self):
            return f'<IntListResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class TextListResult(BaseResult):
        result: List[str]

        def __repr__(self):
            return f'<TextListResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class TupleListResult(BaseResult):
        result: List[tuple]

        def __repr__(self):
            return f'<TupleListResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class DictListResult(BaseResult):
        result: List[dict]

        def __repr__(self):
            return f'<DictListResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class SetResult(BaseResult):
        result: set

        def __repr__(self):
            return f'<SetResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class IntSetResult(BaseResult):
        result: Set[int]

        def __repr__(self):
            return f'<IntSetResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class TextSetResult(BaseResult):
        result: Set[str]

        def __repr__(self):
            return f'<TextSetResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class TupleResult(BaseResult):
        result: tuple

        def __repr__(self):
            return f'<TupleResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class IntTupleResult(BaseResult):
        result: Tuple[int, ...]

        def __repr__(self):
            return f'<IntTupleResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class TextTupleResult(BaseResult):
        result: Tuple[str, ...]

        def __repr__(self):
            return f'<TextTupleResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class IntResult(BaseResult):
        result: int

        def __repr__(self):
            return f'<IntResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class TextResult(BaseResult):
        result: str

        def __repr__(self):
            return f'<TextResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class BoolResult(BaseResult):
        result: bool

        def __repr__(self):
            return f'<BoolResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class BytesResult(BaseResult):
        result: bytes

        def __repr__(self):
            return f'<BytesResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class AnyResult(BaseResult):
        result: Any

        def __repr__(self):
            return f'<AnyResult(error={self.error}, info={self.info}, result={self.result})>'


__all__ = [
    'Result'
]
