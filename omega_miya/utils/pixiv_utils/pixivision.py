import re
from bs4 import BeautifulSoup
from nonebot import logger
from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from omega_miya.utils.Omega_Base import Result


class Pixivision(object):
    ROOT_URL = 'https://www.pixivision.net'
    ILLUSTRATION_URL = 'https://www.pixivision.net/zh/c/illustration'
    ARTICLES_URL = 'https://www.pixivision.net/zh/a'
    TAG_URL = 'https://www.pixivision.net/zh/t'

    HEADERS = {'accept': '*/*',
               'accept-encoding': 'gzip, deflate',
               'accept-language': 'zh-CN,zh;q=0.9',
               'dnt': '1',
               'referer': 'https://www.pixivision.net/zh/',
               'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
               'sec-ch-ua-mobile': '?0',
               'sec-fetch-dest': 'document',
               'sec-fetch-mode': 'navigate',
               'sec-fetch-site': 'same-origin',
               'sec-fetch-user': '?1',
               'sec-gpc': '1',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/89.0.4389.114 Safari/537.36'}

    @classmethod
    async def get_illustration_list(cls) -> Result:
        fetcher = HttpFetcher(timeout=10, flag='pixivision_utils_illustration_list', headers=cls.HEADERS)
        html_result = await fetcher.get_text(url=cls.ILLUSTRATION_URL, params={'lang': 'zh'})
        if html_result.error:
            return Result(error=True, info=f'Fetch illustration list failed, {html_result.info}', result=[])

        result = []
        try:
            __bs = BeautifulSoup(html_result.result, 'lxml')
            __all_illustration_card = __bs.find_all(name='li', attrs={'class': 'article-card-container'})
            for item in __all_illustration_card:
                aid = item.find(name='h2', attrs={'class': 'arc__title'}).find(name='a').attrs['data-gtm-label']
                url = cls.ROOT_URL + item.find(name='h2', attrs={'class': 'arc__title'}).find(name='a').attrs['href']
                title = item.find(name='h2', attrs={'class': 'arc__title'}).get_text(strip=True)
                tag_tag = item.find(name='ul', attrs={'class': '_tag-list'}).find_all(name='li')
                tag_list = []
                for tag in tag_tag:
                    tag_name = tag.get_text(strip=True)
                    tag_r_url = tag.find(name='a').attrs['href']
                    tag_id = re.sub(r'^/zh/t/(?=\d+)', '', tag_r_url)
                    tag_url = cls.ROOT_URL + tag_r_url
                    tag_list.append({'tag_id': tag_id, 'tag_name': tag_name, 'tag_url': tag_url})
                result.append({'id': aid, 'title': title, 'url': url, 'tags': tag_list})
            return Result(error=False, info='Success', result=result)
        except Exception as e:
            logger.error(f'Pixivision | Parse illustration list failed, error: {repr(e)}')
            return Result(error=True, info=f'Parse illustration list failed', result=[])


class PixivisionArticle(Pixivision):
    def __init__(self, aid: int):
        self.__aid = aid

    async def get_article_info(self) -> Result:
        url = f'{self.ARTICLES_URL}/{self.__aid}'
        fetcher = HttpFetcher(timeout=10, flag='pixivision_utils_article_info', headers=self.HEADERS)
        html_result = await fetcher.get_text(url=url, params={'lang': 'zh'})
        if html_result.error:
            return Result(error=True, info=f'Fetch article info failed, {html_result.info}', result={})

        try:
            __bs = BeautifulSoup(html_result.result, 'lxml')
            article_main = __bs.find(name='div', attrs={'class': '_article-main'})
            article_title = article_main.find(name='h1', attrs={'class': 'am__title'}).get_text(strip=True)
            article_description = article_main.find(
                name='div', attrs={'class': 'am__description _medium-editor-text'}).get_text(strip=True)
            article_eyecatch_image = article_main.find(name='img', attrs={'class': 'aie__image'}).attrs['src']
            article_body = article_main.find(name='div', attrs={'class': 'am__body'})
            # article_illusts = article_body.find_all(name='div', recursive=False)
            article_illusts = article_body.find_all(name='div', attrs={'class': 'am__work__main'})
            illusts_list = []
            for item in article_illusts:
                try:
                    url = item.find(name='a', attrs={'class': 'inner-link'}).attrs['href']
                    pid = int(re.sub(r'^https://www\.pixiv\.net/artworks/(?=\d+)', '', url))
                    image_url = item.find(name='img', attrs={'class': 'am__work__illust'}).attrs['src']
                    illusts_list.append({'illusts_id': pid, 'illusts_url': url, 'illusts_image': image_url})
                except Exception as e:
                    logger.debug(f'PixivisionArticle | Illust in article parse failed, ignored. {str(e)},')
                    continue
            result = {
                'article_title': article_title,
                'article_description': article_description,
                'article_eyecatch_image': article_eyecatch_image,
                'illusts_list': illusts_list
            }
            return Result(error=False, info='Success', result=result)
        except Exception as e:
            logger.error(f'PixivisionArticle | Parse article failed, error: {repr(e)}')
            return Result(error=True, info=f'Parse article failed', result={})


__all__ = [
    'Pixivision',
    'PixivisionArticle'
]
