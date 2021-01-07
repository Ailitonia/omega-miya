import aiohttp
import json
from omega_miya.utils.Omega_Base import Result

API_URL = 'https://lab.magiconch.com/api/nbnhhsh/guess/'


async def get_guess(guess: str) -> Result:
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                data = {'text': guess}
                async with session.post(url=API_URL, data=data, timeout=timeout) as resp:
                    _json = await resp.json()
                result = Result(error=False, info='Success', result=_json)
            return result
        except Exception as e:
            error_info += f'{repr(e)} Occurred in get_guess trying {timeout_count + 1} using paras: {data}\n'
        finally:
            timeout_count += 1
    else:
        error_info += f'Failed too many times in get_guess using paras: {data}'
        result = Result(error=True, info=error_info, result=[])
        return result
