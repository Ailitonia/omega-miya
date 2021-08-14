import re
import asyncio
import os
import json
import random
import string
import aiofiles
from dataclasses import dataclass
from bs4 import BeautifulSoup
from nonebot import logger, get_driver
from omega_miya.utils.omega_plugin_utils import HttpFetcher, create_7z_file
from omega_miya.database import Result

global_config = get_driver().config
TMP_PATH = global_config.tmp_path_


class NHException(Exception):
    def __init__(self, *args):
        super(NHException, self).__init__(*args)


class Nhentai(object):
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

    # 通过关键词搜索本子id和标题
    @classmethod
    async def search_gallery_by_keyword(cls, keyword: str) -> Result.ListResult:
        # 搜索关键词
        payload_keyword = {'q': keyword}
        search_url = f'https://nhentai.net/search/'
        headers = cls.HEADERS.copy()
        headers.update({'referer': search_url})

        fetcher = HttpFetcher(timeout=10, flag='nhentai_search', headers=headers)
        html_result = await fetcher.get_text(url=search_url, params=payload_keyword)
        if html_result.error:
            return Result.ListResult(error=True, info=f'Search keyword failed, {html_result.info}', result=[])

        search_res = html_result.result
        result = []
        try:
            gallery_soup = BeautifulSoup(search_res, 'lxml').find_all('div', class_='gallery')
            # 只取前10个结果
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


class NhentaiGallery(Nhentai):
    def __init__(self, gallery_id: int):
        self.gallery_id = gallery_id

    @dataclass
    class GalleryPage:
        index: int
        type_: str
        width: int
        height: int

    # 获取gallery信息
    async def get_data(self) -> Result.DictResult:
        url = f'https://nhentai.net/g/{self.gallery_id}/1/'
        fetcher = HttpFetcher(timeout=10, flag='nhentai_get_gallery_data', headers=self.HEADERS)
        html_result = await fetcher.get_text(url=url)
        if html_result.error:
            return Result.DictResult(error=True, info=f'访问本子页面时异常，似乎网络不行. {html_result.info}', result={})
        html_text = html_result.result

        # 从html文本中找到包含本子数据的那一行 即粗定位数据
        try:
            start = html_text.find('window._gallery')
            middle_text = html_text[start:]
            end = middle_text.find('\n')
            js_text = middle_text[:end]
        except Exception as e:
            return Result.DictResult(error=True, info=f'解析本子信息时异常，读取信息行失败. Exception: {repr(e)}', result={})

        # 从单行JS脚本中取出JSON字符串的部分 细定位
        try:
            start_tips = 'JSON.parse'
            start = js_text.find(start_tips)
            stop = js_text.rindex('"')
            start += len(start_tips) + 2
            json_text = js_text[start:stop]
        except Exception as e:
            return Result.DictResult(error=True, info=f'解析本子信息时异常，分割JSON字符串失败. Exception: {repr(e)}', result={})

        # 从JSON字符串解析数据 转为python结构
        try:
            # 把字符串中的\u都反解析掉
            decodeable_json_text = json_text.encode('utf-8').decode('unicode_escape')
            gallery = json.loads(decodeable_json_text)
        except Exception as e:
            return Result.DictResult(error=True, info=f'解析本子信息时异常，解析JSON失败. Exception: {repr(e)}', result={})

        """
        解析json内容:
        {
            "id": int,  # gallery id
            "media_id": str,  # media id
            "title": {
                "english": str,
                "japanese": str,
                "pretty": str
            },
            # 每页图片信息
            "images": {
                "pages": [
                    {
                        "t": str,  # 图片格式, j 为 jpg , p 为 png
                        "w": int,  # 宽
                        "h": int  # 高
                    },
                    ...
                ],
                # 封面
                "cover": {
                    "t": str,  # 图片格式, j 为 jpg , p 为 png
                    "w": int,  # 宽
                    "h": int
                },
                # 缩略图
                "thumbnail": {
                    "t": str,  # 图片格式, j 为 jpg , p 为 png
                    "w": int,  # 宽
                    "h": int
                }
            },
            "scanlator": str,
            "upload_date": int,
            "tags": [
                {
                    "id": int,
                    "type": str,
                    "name": str,
                    "url": str,
                    "count": int
                },
                ...
            ],
            "num_pages": int,
            "num_favorites": int
        }   
        """
        return Result.DictResult(error=False, info='Success', result=gallery)

    # 下载所有图片到指定目录
    async def fetch_gallery(self) -> Result.DictResult:
        # 获取gallery信息
        gallery_result = await self.get_data()
        if gallery_result.error:
            return Result.DictResult(error=True, info=f'获取本子信息失败, {gallery_result.info}', result={})
        gallery = gallery_result.result

        # 获取总页数
        total_page_count = len(gallery['images']['pages'])
        # 处理每一页图片信息
        gallery_pages = []
        for num in range(total_page_count):
            page_index = num + 1
            page_width = gallery['images']['pages'][num]['w']
            page_height = gallery['images']['pages'][num]['h']
            page_type = gallery['images']['pages'][num]['t']
            if page_type == 'j':
                gallery_pages.append(
                    self.GalleryPage(index=page_index, width=page_width, height=page_height, type_='jpg'))
            elif page_type == 'p':
                gallery_pages.append(
                    self.GalleryPage(index=page_index, width=page_width, height=page_height, type_='png'))
            else:
                gallery_pages.append(
                    self.GalleryPage(index=page_index, width=page_width, height=page_height, type_=page_type))

        # 本子图片的media编号
        media_id = gallery['media_id']

        # 下载到公用临时目录
        file_path = os.path.abspath(os.path.join(TMP_PATH, 'nhentai_gallery', str(self.gallery_id)))
        headers = self.HEADERS.copy()
        headers.update({
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site'
        })
        fetcher = HttpFetcher(timeout=30, flag='nhentai_download_image', headers=headers)

        # 每个切片任务数量为10, 每个切片打包一个任务
        pool = 10
        downloaded_list = []
        failed_num = 0
        for i in range(0, total_page_count, pool):
            # 产生请求序列
            tasks = []
            for page in gallery_pages[i:i + pool]:
                logger.debug(f'Nhentai | Downloading: {self.gallery_id}/{page} ...')
                url = f'https://i.nhentai.net/galleries/{media_id}/{page.index}.{page.type_}'
                file_name = os.path.basename(url)
                if not file_name:
                    file_name = f'{page.index}.tmp'

                # 检测文件是否已经存在避免重复下载
                if os.path.exists(os.path.abspath(os.path.join(file_path, file_name))):
                    downloaded_list.append(os.path.abspath(os.path.join(file_path, file_name)))
                    logger.debug(f'Nhentai | File: {self.gallery_id}/{file_name} exists, pass.')
                    continue

                tasks.append(fetcher.download_file(url=url, path=file_path, file_name=file_name))

            # 开始下载
            download_result = await asyncio.gather(*tasks)
            downloaded_list.extend([x.result for x in download_result if x.success()])
            failed_num += len([x for x in download_result if x.error])

        logger.debug(f'Nhentai | Gallery download completed, succeed: {downloaded_list}, failed number: {failed_num}')
        if failed_num > 0:
            return Result.DictResult(error=True, info=f'{failed_num} page(s) download failed', result={})

        # 生成包含本子原始信息的文件
        manifest_path = os.path.abspath(os.path.join(file_path, f'manifest.json'))
        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(json.dumps(gallery))
        downloaded_list.append(manifest_path)

        # 生成一段随机字符串改变打包后压缩文件的hash
        rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=1024))
        rand_file = os.path.abspath(os.path.join(file_path, f'mask'))
        async with aiofiles.open(rand_file, 'w') as f:
            await f.write(rand_str)
        downloaded_list.append(rand_file)

        # 生成压缩包随机密码
        password_str = ''.join(random.sample(string.ascii_letters + string.digits, k=8))
        password_file = os.path.abspath(os.path.join(file_path, f'password'))
        async with aiofiles.open(password_file, 'w') as f:
            await f.write(password_str)

        # 打包
        c7z_result = await create_7z_file(
            files=downloaded_list, file_path=file_path, file_name=str(self.gallery_id), password=password_str)
        if c7z_result.error:
            return Result.DictResult(error=True, info=f'创建压缩文件失败, error: {c7z_result.info}', result={})
        else:
            result = {
                'password': password_str,
                'file_name': c7z_result.info,
                'file_path': c7z_result.result
            }
            return Result.DictResult(error=False, info='Success', result=result)


__all__ = [
    'NhentaiGallery'
]
