import aiohttp
import nonebot
from omega_miya.utils.Omega_Base import DBPixivision, Result


global_config = nonebot.get_driver().config
API_KEY = global_config.api_key
API_URL = global_config.pixivision_api_url
DOWNLOAD_API_URL = global_config.pixiv_download_api_url


async def fetch_json(url: str, paras: dict) -> Result:
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=60)
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
async def fetch_image_b64(pid: [int, str]) -> Result:
    # 获取illust
    payload = {'key': API_KEY, 'pid': pid, 'mode': 'regular'}
    _res = await fetch_json(url=DOWNLOAD_API_URL, paras=payload)
    if _res.success() and not _res.result.get('error'):
        illust_data = _res.result.get('body')
        pic_b64 = illust_data.get('pic_b64')
        result = Result(error=False, info='Success', result=pic_b64)
    else:
        result = Result(error=True, info=f'网络超时或 {pid} 不存在', result='')
    return result


async def get_pixivsion_article() -> Result:
    result = await fetch_json(url=API_URL, paras={'key': API_KEY, 'mode': 'illustration'})
    return result


async def get_pixivsion_article_info(aid: int) -> Result:
    result = await fetch_json(url=API_URL, paras={'key': API_KEY, 'mode': 'article', 'aid': aid})
    return result


async def pixivsion_article_parse(aid: int, tags: list) -> Result:
    _res = await get_pixivsion_article_info(aid=aid)
    if _res.success() and not _res.result.get('error'):
        try:
            article_info = dict(_res.result)

            title = str(article_info['body']['article']['article_title'])
            description = str(article_info['body']['article']['article_description'])
            url = f'https://www.pixivision.net/zh/a/{aid}'
            illusts_list = []

            for illust in article_info['body']['article']['illusts_list']:
                illusts_list.append(int(illust['illusts_id']))

            pixivision = DBPixivision(aid=aid)
            db_res = pixivision.add(title=title, description=description,
                                    tags=repr(tags), illust_id=repr(illusts_list), url=url)
            if db_res.success():
                __res = {
                    'title': title,
                    'description': description,
                    'url': url,
                    'image:': article_info['body']['article']['article_eyecatch_image'],
                    'illusts_list': illusts_list
                }
                result = Result(error=False, info='Success', result=__res)
            else:
                result = Result(error=True, info=db_res.info, result={})
        except Exception as e:
            result = Result(error=True, info=repr(e), result={})
        return result
    else:
        _res.info += f" // error data: {repr(_res.result)}"
        _res.error = True
        return _res

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(get_pixivsion_article_info(6083))
    print(res.result)
