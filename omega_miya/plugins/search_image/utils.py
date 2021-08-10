import re
from typing import Dict, Callable, Awaitable
import nonebot
from bs4 import BeautifulSoup
from nonebot import logger
from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from omega_miya.utils.Omega_Base import Result


global_config = nonebot.get_driver().config
API_KEY = global_config.saucenao_api_key
API_URL_SAUCENAO = 'https://saucenao.com/search.php'
API_URL_ASCII2D = 'https://ascii2d.net/search/url/'
API_URL_IQDB = 'https://iqdb.org/'


HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/89.0.4389.114 Safari/537.36'}

T_SearchEngine = Callable[[str], Awaitable[Result.DictListResult]]


# 获取识别结果 Saucenao模块
async def get_saucenao_identify_result(url: str) -> Result.DictListResult:
    fetcher = HttpFetcher(timeout=10, flag='search_image_saucenao', headers=HEADERS)

    if not API_KEY:
        logger.opt(colors=True).warning(f'<r>Saucenao API KEY未配置</r>, <y>无法使用Saucenao API进行识图!</y>')
        return Result.DictListResult(error=True, info='Saucenao API KEY未配置', result=[])

    __payload = {'output_type': 2,
                 'api_key': API_KEY,
                 'testmode': 1,
                 'numres': 6,
                 'db': 999,
                 'url': url}
    saucenao_result = await fetcher.get_json(url=API_URL_SAUCENAO, params=__payload)
    if saucenao_result.error:
        logger.warning(f'get_saucenao_identify_result failed, Network error: {saucenao_result.info}')
        return Result.DictListResult(error=True, info=f'Network error: {saucenao_result.info}', result=[])

    __result_json = saucenao_result.result

    if __result_json['header']['status'] != 0:
        logger.error(f"get_saucenao_identify_result failed, DataSource error, "
                     f"status code: {__result_json['header']['status']}")
        return Result.DictListResult(
            error=True, info=f"DataSource error, status code: {__result_json['header']['status']}", result=[])

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
            logger.warning(f"get_saucenao_identify_result failed: {repr(res_err)}, can not resolve results")
            continue
    return Result.DictListResult(error=False, info='Success', result=__result)


# 获取识别结果 ascii2d模块
async def get_ascii2d_identify_result(url: str) -> Result.DictListResult:
    fetcher = HttpFetcher(timeout=10, flag='search_image_ascii2d', headers=HEADERS)

    search_url = f'{API_URL_ASCII2D}{url}'
    saucenao_redirects_result = await fetcher.get_text(url=search_url, allow_redirects=False)
    if saucenao_redirects_result.error:
        logger.error(f'get_ascii2d_identify_result failed: 获取识别结果url发生错误, 错误信息详见日志.')
        return Result.DictListResult(error=True, info=f'Get identify result url failed', result=[])

    ascii2d_color_url = saucenao_redirects_result.headers.get('Location')
    if not ascii2d_color_url:
        logger.error(f'get_ascii2d_identify_result failed: 获取识别结果url发生错误, 可能被流量限制, 或图片大小超过5Mb.')
        return Result.DictListResult(error=True, info=f'Get identify result url failed, may be limited', result=[])
    ascii2d_bovw_url = re.sub(
        r'https://ascii2d\.net/search/color/', r'https://ascii2d.net/search/bovw/', ascii2d_color_url)

    color_res = await fetcher.get_text(url=ascii2d_color_url)
    bovw_res = await fetcher.get_text(url=ascii2d_bovw_url)

    pre_bs_list = []
    if color_res.success():
        pre_bs_list.append(color_res.result)
    if bovw_res.success():
        pre_bs_list.append(bovw_res.result)
    if not pre_bs_list:
        logger.error(f'get_ascii2d_identify_result ERROR: 获取识别结果异常, 错误信息详见日志.')
        return Result.DictListResult(error=True, info=f'Get identify result data failed', result=[])

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
    return Result.DictListResult(error=False, info=f'Success', result=__result)


# 获取识别结果 iqdb模块
async def get_iqdb_identify_result(url: str) -> Result.DictListResult:
    headers = HEADERS.copy().update({
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                  'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundarycljlxd876c1ld4Zr',
        'dnt': '1',
        'Host': 'iqdb.org',
        'Origin': 'https://iqdb.org',
        'Referer': 'https://iqdb.org/',
        'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
        'sec-ch-ua-mobile': '?0',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'sec-gpc': '1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36'
    })
    fetcher = HttpFetcher(timeout=30, flag='search_image_iqdb', headers=headers)
    data = fetcher.FormData(boundary='----WebKitFormBoundarycljlxd876c1ld4Zr')
    data.add_field(name='MAX_FILE_SIZE', value='')
    for i in [1, 2, 3, 4, 5, 6, 11, 13]:
        data.add_field(name='service[]', value=str(i))
    data.add_field(name='file', value=b'', content_type='application/octet-stream', filename='')
    data.add_field(name='url', value=url)
    iqdb_result = await fetcher.post_text(url=API_URL_IQDB, data=data)

    if iqdb_result.error or iqdb_result.status != 200:
        logger.warning(f'get_iqdb_identify_result failed, 获取识别结果失败: {iqdb_result.status}, {iqdb_result.info}')
        return Result.DictListResult(error=True, info=f'Get identify result failed: {iqdb_result.info}', result=[])

    try:
        gallery_soup = BeautifulSoup(iqdb_result.result, 'lxml')
        # 搜索结果
        result_div = gallery_soup.find('div', {'id': 'pages', 'class': 'pages'}).children
        # 从搜索结果中解析具体每一个结果
        result_list = [x.find_all('tr') for x in result_div if x.name == 'div']
    except Exception as page_err:
        logger.warning(f'get_iqdb_identify_result failed: {repr(page_err)}, 解析结果页时发生错误.')
        return Result.DictListResult(error=True, info=f'Parse identify result failed: {repr(page_err)}', result=[])

    result = []
    for item in result_list:
        try:
            if item[0].get_text() == 'Best match':
                # 第二行是匹配缩略图及链接
                urls = '\n'.join([str(x.find('a').get('href')).strip('/') for x in item if x.find('a')])
                img = item[1].find('img').get('src')
                # 最后一行是相似度
                similarity = item[-1].get_text()
                result.append({
                    'similarity': similarity,
                    'thumbnail': f'https://iqdb.org{img}',
                    'index_name': f'iqdb - Best match',
                    'ext_urls': urls
                })
            elif item[0].get_text() == 'Additional match':
                # 第二行是匹配缩略图及链接
                urls = '\n'.join([str(x.find('a').get('href')).strip('/') for x in item if x.find('a')])
                img = item[1].find('img').get('src')
                # 最后一行是相似度
                similarity = item[-1].get_text()
                result.append({
                    'similarity': similarity,
                    'thumbnail': f'https://iqdb.org{img}',
                    'index_name': f'iqdb - Additional match',
                    'ext_urls': urls
                })
            elif item[0].get_text() == 'Possible match':
                # # 第二行是匹配缩略图及链接
                # urls = '\n'.join([str(x.find('a').get('href')).strip('/') for x in item if x.find('a')])
                # img = item[1].find('img').get('src')
                # # 最后一行是相似度
                # similarity = item[-1].get_text()
                # result.append({
                #     'similarity': similarity,
                #     'thumbnail': f'https://iqdb.org{img}',
                #     'index_name': f'iqdb - Possible match',
                #     'ext_urls': urls
                # })
                pass
        except Exception as parse_err:
            logger.warning(f'get_iqdb_identify_result parse error: {repr(parse_err)}, 解搜索结果条目时发生错误..')
    return Result.DictListResult(error=False, info='Success', result=result)


# 可用的识图api
SEARCH_ENGINE: Dict[str, T_SearchEngine] = {
    'saucenao': get_saucenao_identify_result,
    'iqdb': get_iqdb_identify_result,
    'ascii2d': get_ascii2d_identify_result
}


__all__ = [
    'HEADERS',
    'SEARCH_ENGINE'
]
