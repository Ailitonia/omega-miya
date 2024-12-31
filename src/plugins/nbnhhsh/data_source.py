"""
@Author         : Ailitonia
@Date           : 2023/7/16 22:00
@FileName       : data_source.py
@Project        : nonebot2_miya
@Description    : nbnhhsh api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""


from pydantic import BaseModel

from src.compat import parse_obj_as
from src.utils import OmegaRequests


class GuessResult(BaseModel):
    name: str
    trans: list[str] | None = None
    inputting: list[str] | None = None

    @property
    def guess_result(self) -> list[str]:
        result = []
        if self.trans is not None:
            result.extend(self.trans)
        if self.inputting is not None:
            result.extend(self.inputting)
        result = list(set(result))
        result.sort()
        return result


async def _query_guess(guess: str) -> list[GuessResult]:
    """从 magiconch API 处获取缩写查询结果"""
    # 该 api 当前不支持查询的缩写中有空格 这里去除待查询文本中的空格
    guess = guess.replace(' ', '').strip()
    url = 'https://lab.magiconch.com/api/nbnhhsh/guess'
    payload = {'text': guess}
    response = await OmegaRequests().post(url=url, json=payload)
    return parse_obj_as(list[GuessResult], OmegaRequests.parse_content_as_json(response=response))


async def query_guess(guess: str) -> list[str]:
    guess_result = await _query_guess(guess=guess)
    return [trans_word for x in guess_result for trans_word in x.guess_result]


__all__ = [
    'query_guess',
]
