import aiohttp
import base64
import datetime
from io import BytesIO
from nonebot import logger
from omega_miya.utils.Omega_Base import Result


API_URL = 'https://trace.moe/api/search'


async def fetch_json(url: str, paras: dict) -> Result:
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
                async with session.get(url=url, params=paras, headers=headers, timeout=timeout) as resp:
                    _json = await resp.json()
                result = Result(error=False, info='Success', result=_json)
            return result
        except Exception as e:
            error_info += f'{repr(e)} Occurred in fetch_json trying {timeout_count + 1} using paras: {paras}\n'
        finally:
            timeout_count += 1
    else:
        error_info += f'Failed too many times in fetch_json using paras: {paras}'
        result = Result(error=True, info=error_info, result={})
        return result


# 图片转base64
async def pic_2_base64(url: str) -> Result:
    async def get_image(pic_url: str):
        timeout_count = 0
        while timeout_count < 3:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
                    async with session.get(url=pic_url, headers=headers, timeout=timeout) as resp:
                        _res = await resp.read()
                return _res
            except Exception as _e:
                error_info = f'{repr(_e)} Occurred in get_image trying {timeout_count + 1} using paras: {pic_url}'
                logger.info(error_info)
            finally:
                timeout_count += 1
        else:
            error_info = f'Failed too many times in get_image using paras: {pic_url}'
            logger.warning(error_info)
            return None

    origin_image_f = BytesIO()
    try:
        origin_image_f.write(await get_image(pic_url=url))
    except Exception as e:
        result = Result(error=True, info=f'pic_2_base64 error: {repr(e)}', result='')
        return result
    b64 = base64.b64encode(origin_image_f.getvalue())
    b64 = str(b64, encoding='utf-8')
    b64 = 'base64://' + b64
    origin_image_f.close()
    result = Result(error=False, info='Success', result=b64)
    return result


# 获取识别结果
async def get_identify_result(img_url: str) -> Result:
    payload = {'url': img_url}
    result_json = await fetch_json(url=API_URL, paras=payload)
    if not result_json.success():
        return result_json

    _res = result_json.result
    if not _res.get('docs'):
        return Result(error=True, info='no result found', result=[])

    _result = []
    for item in _res.get('docs'):
        try:
            if item.get('similarity') < 0.80:
                continue
            _result.append({
                'raw_at': item.get('at'),
                'at': str(datetime.timedelta(seconds=item.get('at'))),
                'anilist_id': item.get('anilist_id'),
                'anime': item.get('anime'),
                'episode': item.get('episode'),
                'tokenthumb': item.get('tokenthumb'),
                'filename': item.get('filename'),
                'similarity': item.get('similarity'),
                'title_native': item.get('title_native'),
                'title_chinese': item.get('title_chinese'),
                'is_adult': item.get('is_adult'),
            })
        except Exception as e:
            logger.warning(f'result parse failed: {repr(e)}, raw_json: {item}')
            continue

    return Result(error=False, info='Success', result=_result)
