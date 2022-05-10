from typing import Optional
from pydantic import BaseModel, parse_obj_as

from omega_miya.web_resource import HttpFetcher
from omega_miya.utils.process_utils import run_async_catching_exception


_API_URL = 'https://lab.magiconch.com/api/nbnhhsh/guess'


class GuessResult(BaseModel):
    name: str
    trans: Optional[list[str]]
    inputting: Optional[list[str]]

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


async def _get_guess(guess: str) -> list[GuessResult]:
    payload = {'text': guess}
    result = await HttpFetcher().post_json(url=_API_URL, json=payload)
    return parse_obj_as(list[GuessResult], result.result)


@run_async_catching_exception
async def get_guess(guess: str) -> list[str]:
    guess_result = await _get_guess(guess=guess)
    return [trans_word for x in guess_result for trans_word in x.guess_result]


__all__ = [
    'get_guess'
]
