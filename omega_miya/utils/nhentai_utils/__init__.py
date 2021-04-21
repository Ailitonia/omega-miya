import re
import asyncio
import os
import json
import hashlib
import py7zr
from typing import Tuple
from bs4 import BeautifulSoup
from nonebot import logger
from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from omega_miya.utils.Omega_Base import Result

HEADERS = {'accept': '*/*',
           'accept-encoding': 'gzip, deflate',
           'accept-language': 'zh-CN,zh;q=0.9',
           'dnt': '1',
           'referer': 'https://nhentai.net/',
           'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
           'sec-ch-ua-mobile': '?0',
           'sec-fetch-dest': 'document',
           'sec-fetch-mode': 'navigate',
           'sec-fetch-site': 'same-origin',
           'sec-fetch-user': '?1',
           'sec-gpc': '1',
           'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/89.0.4389.114 Safari/537.36'}


class NHException(Exception):
    def __init__(self, *args):
        super(NHException, self).__init__(*args)


# 通过关键词搜索本子id和标题
async def search_gallery_by_tag(keyword: str) -> Result.ListResult:
    # 搜索关键词
    payload_keyword = {'q': keyword}
    search_url = f'https://nhentai.net/search/'
    headers = HEADERS.copy()
    headers.update({'referer': search_url})

    fetcher = HttpFetcher(timeout=10, flag='nhentai_search', headers=headers)
    html_result = await fetcher.get_text(url=search_url, params=payload_keyword)
    if html_result.error:
        return Result.ListResult(error=True, info=f'Search keyword failed, {html_result.info}', result=[])

    search_res = html_result.result
    result = []
    try:
        gallery_soup = BeautifulSoup(search_res, 'lxml').find_all('div', class_='gallery')
        if len(gallery_soup) >= 10:
            for item in gallery_soup[0:10]:
                gallery_title = item.find('div', class_='caption').get_text(strip=True)
                gallery_id = re.sub(r'\D', '', item.find('a', class_='cover').get('href'))
                result.append({'id': gallery_id, 'title': gallery_title})
        else:
            for item in gallery_soup:
                gallery_title = item.find('div', class_='caption').get_text(strip=True)
                gallery_id = re.sub(r'\D', '', item.find('a', class_='cover').get('href'))
                result.append({'id': gallery_id, 'title': gallery_title})
        return Result.ListResult(error=False, info='Success', result=result)
    except Exception as e:
        logger.error(f'Nhentai | Parse search result failed, error: {repr(e)}')
        return Result.ListResult(error=True, info=f'Parse search result failed', result=[])


# 下载一张图片
async def download_image(index: int, url: str, local: str) -> Tuple[int, bool]:
    # 已经下载过了就不再下载
    if os.path.exists(local):
        return index, True

    headers = HEADERS.copy()
    headers.update({
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'cross-site'
    })

    fetcher = HttpFetcher(timeout=30, flag='nhentai_download_image', headers=headers)
    bytes_result = await fetcher.get_bytes(url=url)
    if bytes_result.error:
        return index, False

    try:
        with open(f'{local}', 'wb+') as f:
            f.write(bytes_result.result)
        return index, True
    except Exception as e:
        logger.error(f'Nhentai | Image downloaded failed, error: {repr(e)}')
        return index, False


# 并发执行所有下载请求
async def concurrently_fetch(request_list, pool=10) -> Tuple[bool, list]:
    failed_list = []
    all_count = len(request_list)
    success_count = 0

    # 每个切片任务数量为10, 每个切片打包一个任务
    poll_tasks = []
    for i in range(0, all_count, pool):
        poll_tasks.append(request_list[i:i + pool])

    # 提交任务
    # 每个切片打包一个任务
    for poll_task in poll_tasks:
        tasks = []
        for req in poll_task:
            i, url, local, file_type = req
            tasks.append(download_image(index=i, url=url, local=local))
        # 进行异步处理
        _res = await asyncio.gather(*tasks)
        # 对结果进行计数
        for index, success in _res:
            if success:
                success_count += 1
            else:
                failed_list.append(index)

    if success_count == all_count:
        all_success = True
    else:
        all_success = False

    # 返回下载结果
    return all_success, failed_list


# 从html文本中找到包含本子数据的那一行 即粗定位数据
def get_gallery_line_from_html(html_text: str) -> str:
    start = html_text.find('window._gallery')
    middle_text = html_text[start:]
    end = middle_text.find('\n')
    return middle_text[:end]


# 从单行JS脚本中取出JSON字符串的部分 细定位
def get_json_text_from_js_text(js_text: str) -> str:
    start_tips = 'JSON.parse'
    start = js_text.find(start_tips)
    stop = js_text.rindex('"')
    start += len(start_tips) + 2
    return js_text[start:stop]


# 从JSON字符串解析数据 转为python结构
def get_dict_from_json_text(json_text: str) -> dict:
    # 把字符串中的\u都反解析掉
    decodeable_json_text = json_text.encode('utf-8').decode('unicode_escape')
    return json.loads(decodeable_json_text)


# 获取gallery信息
async def get_gallery_data_by_id(gallery_id: int) -> dict:
    try:
        url = f'https://nhentai.net/g/{gallery_id}/1/'
        fetcher = HttpFetcher(timeout=10, flag='nhentai_get_gallery_data', headers=HEADERS)
        html_result = await fetcher.get_text(url=url)
        if html_result.error:
            raise Exception(html_result.info)
        html_text = html_result.result
    except Exception as e:
        raise NHException(f'访问本子页面时异常，似乎网络不行. Exception: {repr(e)}')
    try:
        js_text = get_gallery_line_from_html(html_text)
    except Exception as e:
        raise NHException(f'解析本子信息时异常，读取信息行失败. Exception: {repr(e)}')
    try:
        json_text = get_json_text_from_js_text(js_text)
    except Exception as e:
        raise NHException(f'解析本子信息时异常，分割JSON字符串失败. Exception: {repr(e)}')
    try:
        gallery = get_dict_from_json_text(json_text)
    except Exception as e:
        raise NHException(f'解析本子信息时异常，解析JSON失败. Exception: {repr(e)}')
    return gallery


# 给定本子ID 下载所有图片到指定目录
async def fetch_gallery(gallery_id: int) -> str:
    # 获取gallery信息
    gallery = await get_gallery_data_by_id(gallery_id)
    # 获取总页数
    total_page_count = len(gallery['images']['pages'])
    # 生成每一页对应的图片格式
    every_page_image_type = []
    for num in range(total_page_count):
        every_page_image_type.append(gallery['images']['pages'][num]['t'])
    # 本子图片的media编号
    media_id = gallery['media_id']
    # 子目录
    nhentai_plugin_path = os.path.dirname(__file__)
    sub_dir = os.path.join(nhentai_plugin_path, 'nhentai_gallery', str(gallery_id))
    # 创建子目录
    if not os.path.exists(sub_dir):
        os.makedirs(sub_dir)

    # 产生请求序列
    request_list = []
    for i in range(total_page_count):
        type_index = i
        index = i + 1
        if every_page_image_type[type_index] == 'j':
            file_type = 'jpg'
        elif every_page_image_type[type_index] == 'p':
            file_type = 'png'
        else:
            file_type = 'undefined'
        url = f'https://i.nhentai.net/galleries/{media_id}/{index}.{file_type}'
        local = os.path.join(sub_dir, f'{index}.{file_type}')
        req = index, url, local, file_type
        request_list.append(req)

    # 下载所有图片
    success, failed_list = await concurrently_fetch(request_list)
    if not success:
        failed_list_str = ','.join([str(x) for x in failed_list])
        raise NHException(f'图片{failed_list_str}下载失败')

    # 打包成7z
    file = os.path.join(sub_dir, f'{gallery_id}.7z')
    password_file = os.path.join(sub_dir, 'password')

    # 密码
    password_hash_str = repr(gallery)
    md5 = hashlib.md5()
    md5.update(password_hash_str.encode('utf-8'))
    password = md5.hexdigest()

    # 异步压缩文件
    async def compress7z(file_: str, password_: str) -> bool:
        def __compress7z() -> bool:
            try:
                # 执行压缩
                with py7zr.SevenZipFile(file_, mode='w', password=password_) as z:
                    z.set_encrypted_header(True)
                    manifest_path = os.path.join(sub_dir, 'manifest.json')
                    with open(manifest_path, 'w') as f:
                        f.write(json.dumps(gallery))
                    z.write(manifest_path, 'manifest.json')
                    for index_, url_, local_, file_type_ in request_list:
                        z.write(local_, f'{index_}.{file_type_}')
                # 保存密码
                with open(password_file, 'w+', encoding='utf-8') as f:
                    f.write(password)
                return True
            except Exception as e:
                logger.error(f'Nhentai | Compress file failed, error: {repr(e)}')
                return False

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, __compress7z)
        return res

    result = await compress7z(file_=file, password_=password)
    if not result:
        raise NHException(f'创建压缩文件失败')

    return password


async def download_gallery(gallery_id: int) -> Tuple[bool, str, str]:
    """
    :param gallery_id: ID
    :return: Tuple[bool, str, str]: Success status, File Password, File Path
    """
    # 子目录
    nhentai_plugin_path = os.path.dirname(__file__)
    sub_dir = os.path.join(nhentai_plugin_path, 'nhentai_gallery', str(gallery_id))
    file = os.path.join(sub_dir, f'{gallery_id}.7z')
    password_file = os.path.join(sub_dir, 'password')
    if os.path.exists(file) and os.path.exists(password_file):
        with open(password_file, 'r', encoding='utf-8') as f:
            password = f.read()
        return True, password, os.path.abspath(file)

    try:
        password = await fetch_gallery(gallery_id)
        return True, password, os.path.abspath(file)
    except Exception as e:
        logger.error(f'Nhentai | Gallery downloaded failed, error: {repr(e)}')
        return False, '', ''


__all__ = [
    'search_gallery_by_tag',
    'download_gallery'
]
