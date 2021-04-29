import re
import os
import json
import asyncio
import aiofiles
from nonebot import logger, get_driver
from omega_miya.utils.Omega_plugin_utils import HttpFetcher, PicEncoder, create_zip_file
from omega_miya.utils.Omega_Base import Result

global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
PIXIV_PHPSESSID = global_config.pixiv_phpsessid

if PIXIV_PHPSESSID:
    COOKIES = {'PHPSESSID': PIXIV_PHPSESSID}
else:
    COOKIES = None


class Pixiv(object):
    ILLUST_DATA_URL = 'https://www.pixiv.net/ajax/illust/'
    ILLUST_ARTWORK_URL = 'https://www.pixiv.net/artworks/'
    RANKING_URL = 'http://www.pixiv.net/ranking.php'

    HEADERS = {'accept': '*/*',
               'accept-encoding': 'gzip, deflate',
               'accept-language': 'zh-CN,zh;q=0.9',
               'dnt': '1',
               'referer': 'https://www.pixiv.net/',
               'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
               'sec-ch-ua-mobile': '?0',
               'sec-fetch-dest': 'empty',
               'sec-fetch-mode': 'cors',
               'sec-fetch-site': 'same-origin',
               'sec-gpc': '1',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/89.0.4389.114 Safari/537.36'}

    @classmethod
    async def daily_ranking(cls) -> Result.DictResult:
        payload_daily = {'format': 'json', 'mode': 'daily',
                         'content': 'illust', 'p': 1}
        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_daily_ranking', headers=cls.HEADERS)
        daily_ranking_result = await fetcher.get_json(url=cls.RANKING_URL, params=payload_daily)
        if daily_ranking_result.error:
            return Result.DictResult(
                error=True, info=f'Fetch daily ranking failed, {daily_ranking_result.info}', result={})

        daily_ranking_data = daily_ranking_result.result.get('contents')
        if type(daily_ranking_data) != list:
            return Result.DictResult(
                error=True, info=f'Daily ranking data error, {daily_ranking_result.result}', result={})

        result = {}
        for num in range(len(daily_ranking_data)):
            try:
                illust_id = daily_ranking_data[num].get('illust_id')
                illust_title = daily_ranking_data[num].get('title')
                illust_uname = daily_ranking_data[num].get('user_name')
                result.update({num: {
                    'illust_id': illust_id,
                    'illust_title': illust_title,
                    'illust_uname': illust_uname
                }})
            except Exception as e:
                logger.debug(f'Pixiv | Daily ranking data error at {num}, ignored. {str(e)},')
                continue
        return Result.DictResult(error=False, info='Success', result=result)

    @classmethod
    async def weekly_ranking(cls) -> Result.DictResult:
        payload_weekly = {'format': 'json', 'mode': 'weekly',
                          'content': 'illust', 'p': 1}
        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_weekly_ranking', headers=cls.HEADERS)
        weekly_ranking_result = await fetcher.get_json(url=cls.RANKING_URL, params=payload_weekly)
        if weekly_ranking_result.error:
            return Result.DictResult(
                error=True, info=f'Fetch weekly ranking failed, {weekly_ranking_result.info}', result={})

        weekly_ranking_data = weekly_ranking_result.result.get('contents')
        if type(weekly_ranking_data) != list:
            return Result.DictResult(
                error=True, info=f'Weekly ranking data error, {weekly_ranking_result.result}', result={})

        result = {}
        for num in range(len(weekly_ranking_data)):
            try:
                illust_id = weekly_ranking_data[num].get('illust_id')
                illust_title = weekly_ranking_data[num].get('title')
                illust_uname = weekly_ranking_data[num].get('user_name')
                result.update({num: {
                    'illust_id': illust_id,
                    'illust_title': illust_title,
                    'illust_uname': illust_uname
                }})
            except Exception as e:
                logger.debug(f'Pixiv | Weekly ranking data error at {num}, ignored. {str(e)},')
                continue
        return Result.DictResult(error=False, info='Success', result=result)

    @classmethod
    async def monthly_ranking(cls) -> Result.DictResult:
        payload_monthly = {'format': 'json', 'mode': 'monthly',
                           'content': 'illust', 'p': 1}
        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_monthly_ranking', headers=cls.HEADERS)
        monthly_ranking_result = await fetcher.get_json(url=cls.RANKING_URL, params=payload_monthly)
        if monthly_ranking_result.error:
            return Result.DictResult(
                error=True, info=f'Fetch monthly ranking failed, {monthly_ranking_result.info}', result={})

        monthly_ranking_data = monthly_ranking_result.result.get('contents')
        if type(monthly_ranking_data) != list:
            return Result.DictResult(
                error=True, info=f'Monthly ranking data error, {monthly_ranking_result.result}', result={})

        result = {}
        for num in range(len(monthly_ranking_data)):
            try:
                illust_id = monthly_ranking_data[num].get('illust_id')
                illust_title = monthly_ranking_data[num].get('title')
                illust_uname = monthly_ranking_data[num].get('user_name')
                result.update({num: {
                    'illust_id': illust_id,
                    'illust_title': illust_title,
                    'illust_uname': illust_uname
                }})
            except Exception as e:
                logger.debug(f'Pixiv | Monthly ranking data error at {num}, ignored. {repr(e)},')
                continue
        return Result.DictResult(error=False, info='Success', result=result)


class PixivIllust(Pixiv):
    def __init__(self, pid: int):
        self.__pid = pid

    # 获取作品完整信息（pixiv api 获取 json）
    # 返回格式化后的作品信息
    async def get_illust_data(self) -> Result.DictResult:
        illust_url = f'{self.ILLUST_DATA_URL}{self.__pid}'
        illust_artworks_url = f'{self.ILLUST_ARTWORK_URL}{self.__pid}'

        headers = self.HEADERS.copy()
        headers.update({'referer': illust_artworks_url})

        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_illust', headers=headers, cookies=COOKIES)

        # 获取作品信息
        illust_data_result = await fetcher.get_json(url=illust_url)
        if illust_data_result.error:
            return Result.DictResult(error=True, info=f'Fetch illust data failed, {illust_data_result.info}', result={})

        # 检查返回状态
        if illust_data_result.result.get('error') or not illust_data_result.result:
            return Result.DictResult(error=True, info=f'PixivApiError: {illust_data_result.result}', result={})

        # 获取多张图作品图片列表
        illust_page_url = illust_url + '/pages'
        illust_pages_result = await fetcher.get_json(url=illust_page_url)
        if illust_pages_result.error:
            return Result.DictResult(
                error=True, info=f'Fetch illust pages failed, {illust_pages_result.info}', result={})

        illust_data = illust_data_result.result
        illust_pages = illust_pages_result.result

        try:
            # 处理作品基本信息
            illust_type = int(illust_data['body']['illustType'])
            illustid = int(illust_data['body']['illustId'])
            illusttitle = str(illust_data['body']['illustTitle'])
            userid = int(illust_data['body']['userId'])
            username = str(illust_data['body']['userName'])
            url = f'{self.ILLUST_ARTWORK_URL}{self.__pid}'
            page_count = int(illust_data['body']['pageCount'])
            illust_orig_url = str(illust_data['body']['urls']['original'])
            illust_regular_url = str(illust_data['body']['urls']['regular'])
            illust_description = str(illust_data['body']['description'])
            re_std_description_s1 = r'(\<br\>|\<br \/\>)'
            re_std_description_s2 = r'<[^>]+>'
            illust_description = re.sub(re_std_description_s1, '\n', illust_description)
            illust_description = re.sub(re_std_description_s2, '', illust_description)

            # 处理作品tag
            illusttag = []
            tag_number = len(illust_data['body']['tags']['tags'])
            for num in range(tag_number):
                tag = str(illust_data['body']['tags']['tags'][num]['tag'])
                illusttag.append(tag)
                try:
                    transl_tag = str(illust_data['body']['tags']['tags'][num]['translation']['en'])
                    illusttag.append(transl_tag)
                except Exception as e:
                    logger.debug(f'PixivIllust | Tag "{tag}" has not translation, ignored. {str(e)},')
                    continue
            if 'R-18' in illusttag:
                is_r18 = True
            else:
                is_r18 = False

            # 处理图片列表
            all_url = {
                'thumb_mini': [],
                'small': [],
                'regular': [],
                'original': [],
            }
            if not illust_pages.get('error') and illust_pages:
                for item in illust_pages.get('body'):
                    all_url.get('thumb_mini').append(item['urls']['thumb_mini'])
                    all_url.get('small').append(item['urls']['small'])
                    all_url.get('regular').append(item['urls']['regular'])
                    all_url.get('original').append(item['urls']['original'])

            ugoira_meta = {
                'frames': None,
                'mime_type': None,
                'originalsrc': None,
                'src': None
            }
            # 如果是动图额外处理动图资源
            if illust_type == 2:
                illust_ugoira_meta_url = illust_url + '/ugoira_meta'
                illust_ugoira_meta_result = await fetcher.get_json(url=illust_ugoira_meta_url)
                if illust_ugoira_meta_result.error:
                    return Result.DictResult(
                        error=True, info=f'Fetch illust pages failed, {illust_ugoira_meta_result.info}', result={})
                illust_ugoira_meta = illust_ugoira_meta_result.result
                if illust_ugoira_meta_result.success() and not illust_ugoira_meta.get('error') and illust_ugoira_meta:
                    ugoira_meta['frames'] = illust_ugoira_meta['body']['frames']
                    ugoira_meta['mime_type'] = illust_ugoira_meta['body']['mime_type']
                    ugoira_meta['originalsrc'] = illust_ugoira_meta['body']['originalSrc']
                    ugoira_meta['src'] = illust_ugoira_meta['body']['src']

            result = {
                'illust_type': illust_type,
                'pid': illustid,
                'title': illusttitle,
                'uid': userid,
                'uname': username,
                'url': url,
                'page_count': page_count,
                'orig_url': illust_orig_url,
                'regular_url': illust_regular_url,
                'all_url': all_url,
                'ugoira_meta': ugoira_meta,
                'description': illust_description,
                'tags': illusttag,
                'is_r18': is_r18
            }
            return Result.DictResult(error=False, info='Success', result=result)
        except Exception as e:
            logger.error(f'PixivIllust | Parse illust data failed, error: {repr(e)}')
            return Result.DictResult(error=True, info=f'Parse illust data failed', result={})

    # 图片转base64
    async def pic_2_base64(self, original: bool = False) -> Result.TextResult:
        illust_data_result = await self.get_illust_data()
        if illust_data_result.error:
            return Result.TextResult(error=True, info='Fetch illust data failed', result='')

        illust_data = dict(illust_data_result.result)
        title = illust_data.get('title')
        author = illust_data.get('uname')
        url = illust_data.get('url')
        description = illust_data.get('description')
        tags = ''
        for tag in illust_data.get('tags'):
            tags += f'#{tag}  '

        if not description:
            info = f'「{title}」/「{author}」\n{tags}\n{url}'
        else:
            info = f'「{title}」/「{author}」\n{tags}\n{url}\n----------------\n{description[:28]}......'

        if original:
            url = illust_data.get('orig_url')
        else:
            url = illust_data.get('regular_url')

        headers = self.HEADERS.copy()
        headers.update({
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site'
        })

        fetcher = HttpFetcher(timeout=30, attempt_limit=2, flag='pixiv_utils_get_image', headers=headers)
        bytes_result = await fetcher.get_bytes(url=url)
        if bytes_result.error:
            return Result.TextResult(error=True, info='Image download failed', result='')

        encode_result = PicEncoder.bytes_to_b64(image=bytes_result.result)

        if encode_result.success():
            return Result.TextResult(error=False, info=info, result=encode_result.result)
        else:
            return Result.TextResult(error=True, info=encode_result.info, result='')

    async def download_illust(self, page: int = None) -> Result.TextResult:
        """
        :param page: 仅下载特定页码
        """
        if page and page < 1:
            page = None

        illust_data_result = await self.get_illust_data()
        if illust_data_result.error:
            return Result.TextResult(error=True, info='Fetch illust data failed', result='')

        download_url_list = []
        page_count = illust_data_result.result.get('page_count')
        illust_type = illust_data_result.result.get('illust_type')
        if illust_type == 2:
            # 作品类型为动图
            download_url_list.append(illust_data_result.result.get('ugoira_meta').get('originalsrc'))
        if page_count == 1:
            download_url_list.append(illust_data_result.result.get('orig_url'))
        else:
            download_url_list.extend(illust_data_result.result.get('all_url').get('original'))

        if page and page <= page_count:
            download_url_list = [download_url_list[page - 1]]
        elif page and page > page_count:
            return Result.TextResult(error=True, info='请求页数大于插画总页数', result='')

        headers = self.HEADERS.copy()
        headers.update({
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site'
        })

        fetcher = HttpFetcher(timeout=45, attempt_limit=2, flag='pixiv_utils_download_illust', headers=headers)
        file_path = os.path.abspath(os.path.join(TMP_PATH, 'pixiv_illust'))

        if len(download_url_list) == 1:
            file_name = os.path.basename(download_url_list[0])
            if not file_name:
                file_name = f'{self.__pid}.tmp'

            download_result = await fetcher.download_file(url=download_url_list[0], path=file_path, file_name=file_name)
            if download_result.success():
                return Result.TextResult(error=False, info=file_name, result=download_result.result)
            else:
                return Result.TextResult(error=True, info=download_result.info, result='')
        elif len(download_url_list) > 1:
            tasks = []
            for url in download_url_list:
                file_name = os.path.basename(url)
                if not file_name:
                    file_name = f'{self.__pid}.tmp'
                tasks.append(fetcher.download_file(url=url, path=file_path, file_name=file_name))
            download_result = await asyncio.gather(*tasks)
            downloaded_list = [x.result for x in download_result if x.success()]
            failed_num = len([x for x in download_result if x.error])
            if len(downloaded_list) != len(download_url_list):
                return Result.TextResult(error=True, info=f'{failed_num} illust download failed', result='')

            # 动图额外保存原始ugoira_meta信息
            if illust_type == 2:
                pid = illust_data_result.result.get('pid')
                ugoira_meta = illust_data_result.result.get('ugoira_meta')
                ugoira_meta_file = os.path.abspath(os.path.join(file_path, f'{pid}_ugoira_meta'))
                async with aiofiles.open(ugoira_meta_file, 'w') as f:
                    await f.write(json.dumps(ugoira_meta))
                downloaded_list.append(ugoira_meta_file)

            # 打包
            zip_result = await create_zip_file(files=downloaded_list, file_path=file_path, file_name=str(self.__pid))
            return zip_result
        else:
            return Result.TextResult(error=True, info='Get illust url failed', result='')


__all__ = [
    'Pixiv',
    'PixivIllust'
]
