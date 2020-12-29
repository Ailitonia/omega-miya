import aiohttp
import base64
import re
from io import BytesIO
from bs4 import BeautifulSoup
from nonebot import logger
from omega_miya.utils.Omega_Base import Result


API_KEY = ''
API_URL = 'https://saucenao.com/search.php'
API_URL_ASCII2D = 'https://ascii2d.net/search/url/'


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


# 获取识别结果 Saucenao模块
async def get_identify_result(url: str) -> list:
    async def get_result(__url: str, paras: dict) -> dict:
        timeout_count = 0
        while timeout_count < 3:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as __session:
                    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
                    async with __session.get(url=__url, params=paras, headers=headers, timeout=timeout) as resp:
                        json = await resp.json()
                return json
            except Exception as e:
                error_info = f'{repr(e)} Occurred in get_result trying {timeout_count + 1} using paras: {paras}'
                logger.info(error_info)
            finally:
                timeout_count += 1
        else:
            error_info = f'Failed too many times in get_result using paras: {paras}'
            logger.warning(error_info)
            return {'header': {'status': 1}, 'results': []}

    __payload = {'output_type': 2,
                 'api_key': API_KEY,
                 'testmode': 1,
                 'numres': 6,
                 'db': 999,
                 'url': url}
    __result_json = await get_result(__url=API_URL, paras=__payload)
    if __result_json['header']['status'] != 0:
        logger.error(f"get_identify_result failed, "
                     f"status code: {__result_json['header']['status']}, Sever or Client error")
        return []
    __result = []
    for __item in __result_json['results']:
        try:
            if int(float(__item['header']['similarity'])) < 75:
                continue
            else:
                __result.append({'similarity': __item['header']['similarity'],
                                 'thumbnail': __item['header']['thumbnail'],
                                 'index_name': __item['header']['index_name'],
                                 'ext_urls': __item['data']['ext_urls']})
        except Exception as res_err:
            logger.error(f"get_identify_result failed: {repr(res_err)}, can not resolve results")
            continue
    return __result


# 获取识别结果 ascii2d模块
async def get_ascii2d_identify_result(url: str) -> list:
    async def get_ascii2d_redirects(_url: str) -> dict:
        timeout_count = 0
        while timeout_count < 3:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as __session:
                    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                               'accept-language': 'zh-CN,zh;q=0.9'}
                    async with __session.get(url=_url, headers=headers, timeout=timeout,
                                             allow_redirects=False) as resp:
                        res_headers = resp.headers
                        res_dict = {'error': False, 'body': dict(res_headers)}
                return res_dict
            except Exception as e:
                error_info = f'{repr(e)} Occurred in get_ascii2d_redirects trying {timeout_count + 1} using url: {_url}'
                logger.info(error_info)
            finally:
                timeout_count += 1
        else:
            error_info = f'Failed too many times in get_result using url: {_url}'
            logger.warning(error_info)
            return {'error': True, 'body': None}

    async def get_ascii2d_result(__url: str) -> str:
        timeout_count = 0
        while timeout_count < 3:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as __session:
                    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                                             'Chrome/83.0.4103.116 Safari/537.36',
                               'accept-language': 'zh-CN,zh;q=0.9'}
                    async with __session.get(url=__url, headers=headers, timeout=timeout) as resp:
                        res_headers = await resp.text()
                return res_headers
            except Exception as e:
                error_info = f'{repr(e)} Occurred in get_ascii2d_result trying {timeout_count + 1} using url: {__url}'
                logger.info(error_info)
            finally:
                timeout_count += 1
        else:
            error_info = f'Failed too many times in get_result using url: {__url}'
            logger.warning(error_info)
            return ''

    search_url = f'{API_URL_ASCII2D}{url}'
    __result_json = await get_ascii2d_redirects(_url=search_url)
    if not __result_json['error']:
        ascii2d_color_url = __result_json['body']['Location']
        ascii2d_bovw_url = re.sub(
            r'https://ascii2d\.net/search/color/', r'https://ascii2d.net/search/bovw/', ascii2d_color_url)
    else:
        logger.error(f'get_ascii2d_identify_result failed: 获取识别结果url发生错误, 错误信息详见日志.')
        return []

    color_res = await get_ascii2d_result(ascii2d_color_url)
    bovw_res = await get_ascii2d_result(ascii2d_bovw_url)

    pre_bs_list = []
    if color_res:
        pre_bs_list.append(color_res)
    if bovw_res:
        pre_bs_list.append(bovw_res)
    if not pre_bs_list:
        logger.error(f'get_ascii2d_identify_result ERROR: 获取识别结果异常, 错误信息详见日志.')
        return []

    __result = []

    for result in pre_bs_list:
        try:
            gallery_soup = BeautifulSoup(result, 'lxml')
            # 模式
            search_mode = gallery_soup.find('h5', {'class': 'p-t-1 text-xs-center'}).get_text(strip=True)
            # 每一个搜索结果
            row = gallery_soup.find_all('div', {'class': 'row item-box'})
        except Exception as page_err:
            logger.warning(f'get_ascii2d_identify_result failed: {repr(page_err)}, 解析结果页时发生错误.')
            continue
        # ascii2d搜索偏差过大,pixiv及twitter结果只取第一个
        pixiv_count = 0
        twitter_count = 0
        for row_item in row:
            # 对每个搜索结果进行解析
            try:
                detail = row_item.find('div', {'class': 'detail-box gray-link'})
                is_null = detail.get_text(strip=True)
                if not is_null:
                    continue
                # 来源部分,ascii2d网页css调整大概率导致此处解析失败,调试重点关注
                source_type = detail.find('h6').find('small').get_text(strip=True)
                if source_type == 'pixiv':
                    if pixiv_count > 0:
                        break
                    else:
                        pixiv_count += 1
                elif source_type == 'twitter':
                    if twitter_count > 0:
                        break
                    else:
                        twitter_count += 1
                else:
                    continue
                source = detail.find('h6').get_text('/', strip=True)
                source_url = detail.find('h6').find('a', {'title': None, 'style': None}).get('href')
                # 预览图部分,ascii2d网页css调整大概率导致此处解析失败,调试重点关注
                preview_img_url = row_item. \
                    find('div', {'class': 'col-xs-12 col-sm-12 col-md-4 col-xl-4 text-xs-center image-box'}). \
                    find('img').get('src')
                __result.append({'similarity': 'null',
                                 'thumbnail': f'https://ascii2d.net{preview_img_url}',
                                 'index_name': f'ascii2d - {search_mode} - {source}',
                                 'ext_urls': source_url})
            except Exception as row_err:
                logger.warning(f'get_ascii2d_identify_result ERROR: {repr(row_err)}, 解搜索结果条目时发生错误.')
                continue
    return __result
