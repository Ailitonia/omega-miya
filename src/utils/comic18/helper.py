"""
@Author         : Ailitonia
@Date           : 2024/6/16 下午7:05
@FileName       : helper
@Project        : nonebot2_miya
@Description    : 18Comic parser
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

图片分割数算法参考:
https://github.com/jiayaoO3O/18-comic-finder/blob/6caed4df25859439ef1ed9f3d9048f359c8e50f2/src/main/java/io/github/jiayaoO3O/finder/service/TaskService.java#L242-L302
https://github.com/tonquer/JMComic-qt/blob/8b59628a0c0357b31911b98176c10c2bf4452b73/src/tools/tool.py#L845-L956
"""

from hashlib import md5
from typing import TYPE_CHECKING

from PIL import Image
from lxml import etree
from nonebot.log import logger
from nonebot.utils import run_sync
from pydantic import ValidationError

from src.utils.image_utils import ImageUtils
from .model import AlbumData, AlbumPage, AlbumsResult

if TYPE_CHECKING:
    from lxml.etree import _Element


class Comic18Parser:
    """Comic18 解析工具"""
    def __init__(self, root_url: str):
        self.root_url = root_url

    @staticmethod
    def parse_root_url(content: str) -> str:
        """解析主站地址"""
        html = etree.HTML(content)
        script_text = html.xpath('/html/body/script').pop(0).text
        return script_text[script_text.index('"')+1:script_text.rindex('"')]

    def _parse_query_albums_container(self, container: '_Element') -> AlbumsResult:
        relative_url = container.xpath('div[contains(@class, "thumb-overlay")]/a').pop(0).attrib.get('href')
        url = f'{self.root_url}{relative_url}'
        aid = relative_url.split('/')[2]
        cover_image = container.xpath('div[contains(@class, "thumb-overlay")]/a/img').pop(0)
        cover_url = cover_image.attrib.get('data-original') or cover_image.attrib.get('src')

        category_containers = container.xpath(
            'div[contains(@class, "thumb-overlay")]/div[@class="category-icon"]/div'
        )
        categories = [x.text.strip() for x in category_containers if x.text is not None]

        title = container.xpath('span').pop(0).text
        artist_containers = container.xpath('div[contains(@class, "title-truncate")]').pop(0).xpath('a')
        artist = ', '.join(x.text for x in artist_containers if x.text is not None)

        tags_containers = container.xpath('div[contains(@class, "title-truncate")]/a[@class="tag"]')
        tags = [x.text.strip() for x in tags_containers if x.text is not None]

        return AlbumsResult.model_validate({
                    'aid': aid,
                    'title': title,
                    'artist': artist,
                    'categories': categories,
                    'tags': tags,
                    'url': url,
                    'cover_image_url': cover_url,
                })

    @run_sync
    def parse_query_albums_result_page(self, content: str) -> list[AlbumsResult]:
        """解析漫画搜分类/排行页面"""
        html = etree.HTML(content)

        containers = html.xpath(
            '/html/body/div[@id="wrapper"]/div[@class="container"]/div[@class="row"]/div/div/div/div'
        )
        filtered_containers = [x for x in containers if x.xpath('div[contains(@class, "thumb-overlay")]')]

        results = []
        for container in filtered_containers:
            try:
                results.append(self._parse_query_albums_container(container=container))
            except (IndexError, AttributeError, ValidationError) as e:
                logger.warning(f'Comic18 | Parse albums result failed in row, {e}')
                continue

        return results

    def _parse_search_photos_container(self, container: '_Element') -> AlbumsResult:
        relative_url = container.xpath('a').pop(0).attrib.get('href')
        url = f'{self.root_url}{relative_url}'
        aid = relative_url.split('/')[2]
        cover_image = container.xpath('a/div[contains(@class, "thumb-overlay")]/img').pop(0)
        cover_url = cover_image.attrib.get('data-original') or cover_image.attrib.get('src')

        category_containers = container.xpath(
            'a/div[contains(@class, "thumb-overlay")]/div[@class="category-icon"]/div'
        )
        categories = [x.text.strip() for x in category_containers if x.text is not None]

        title = container.xpath('a/span').pop(0).text
        artist_containers = container.xpath('div[contains(@class, "title-truncate")]').pop(0)
        artist = ', '.join(x.text for x in artist_containers.xpath('a') if x.text is not None)

        tags_containers = container.xpath('div[contains(@class, "title-truncate")]/a[@class="tag"]')
        tags = [x.text.strip() for x in tags_containers if x.text is not None]

        return AlbumsResult.model_validate({
                    'aid': aid,
                    'title': title,
                    'artist': artist,
                    'categories': categories,
                    'tags': tags,
                    'url': url,
                    'cover_image_url': cover_url,
                })

    @run_sync
    def parse_search_photos_result_page(self, content: str) -> list[AlbumsResult]:
        """解析漫画搜索结果"""
        html = etree.HTML(content)

        containers = html.xpath(
            '/html/body/div[@id="wrapper"]/div[@class="container"]/div[@class="row"]/div/div/div/div'
        )
        filtered_containers = [x for x in containers if x.xpath('a/div[contains(@class, "thumb-overlay")]')]

        results = []
        for container in filtered_containers:
            try:
                results.append(self._parse_search_photos_container(container=container))
            except (IndexError, AttributeError, ValidationError) as e:
                logger.warning(f'Comic18 | Parse searching photo result failed in row, {e}')
                continue

        return results

    @run_sync
    def parse_album_page(self, content: str) -> AlbumData:
        """解析漫画作品页"""
        html = etree.HTML(content)

        container = html.xpath(
            '/html/body/div[@id="wrapper"]/div[@class="container"]/div[@class="row"]/div/'
            'div[contains(@class, "visible-lg") and @itemscope]'
        ).pop(0)

        title = container.xpath('div[@class="panel-heading"]/div[@itemprop="name"]/h1').pop(0).text.strip()
        data_row = container.xpath('div[@class="panel-body"]/div[@class="row"]').pop(0)

        cover_image = data_row.xpath(
            'div[@id="album_photo_cover"]/div[@class="thumb-overlay"]/a/div[@class="thumb-overlay"]/img'
        ).pop(0)
        cover_image_url = cover_image.attrib.get('data-original') or cover_image.attrib.get('src')

        # 作品详情部分的元素没啥 id 和 style 的区分了, 就只能按顺序未知来解析了, 如果出错大概率也是这里的问题
        info_row = data_row.xpath('div[2]/div[1]/div')
        jm_car = info_row[0].text.strip()
        artwork_tag = [x.text for x in info_row[1].xpath('span[@itemprop="author" and @data-type="works"]/a')]
        characters = [x.text for x in info_row[2].xpath('span[@itemprop="author" and @data-type="actor"]/a')]
        tags = [x.text for x in info_row[3].xpath('span[@itemprop="genre" and @data-type="tags"]/a')]
        artist = ', '.join(x.text for x in info_row[4].xpath('span[@itemprop="author" and @data-type="author"]/a'))

        description = info_row[7].text.strip()
        description_extra = ' '.join(x.strip() for x in info_row[9].itertext())

        pages = info_row[8].text.strip()
        aid = jm_car[jm_car.index('JM')+2:]

        # 解析章节(不是所有的作品都有多个章节)
        chapters_row = data_row.xpath('div/div/div[@class="episode"]/ul/a')
        chapters = [
            {
                'chapter_id': a.attrib.get('data-album'),
                'chapter_title': ' | '.join(x.strip().replace('\n', ' ') for x in a.itertext() if x.strip())
            }
            for a in chapters_row
        ]

        return AlbumData.model_validate({
            'aid': aid,
            'title': title,
            'artist': artist,
            'categories': [],
            'tags': tags,
            'url': f'{self.root_url}/album/{aid}',
            'cover_image_url': cover_image_url,
            'jm_car': jm_car,
            'artwork_tag': artwork_tag,
            'characters': characters,
            'description': f'{description}\n\n{description_extra}',
            'pages': pages,
            'chapters': chapters
        })

    @run_sync
    def parse_pages_url(self, content: str) -> AlbumPage:
        """解析阅读页面图片链接"""
        html = etree.HTML(content)

        page_content = [
            {
                'page_id': (page_id := x.attrib.get('id')),
                'page_index': page_id.split('.')[0],
                'page_type': page_id.rsplit('.')[-1],
                'url': [img.attrib.get('data-original') or img.attrib.get('src') for img in x.xpath('img')].pop(0),
                'description': [div.text.replace('\n', ' ').strip() for div in x.xpath('div')].pop(0),
            }
            for x in html.xpath(
                '/html/body/div[@id="wrapper"]/div[@class="container"]/div[@class="row"]/div/div/'
                'div[@class="panel-body"]/div/div[contains(@class, "scramble-page") and @id]'
            )
        ]

        pagination = [
            x.text
            for x in html.xpath(
                '/html/body/div[@id="wrapper"]/div[@class="container"]/div[@class="row"]/div/div/'
                'div[@class="panel-body"]/div/div/ul[@class="pagination"]/li/a'
            )
            if x.text and x.text.isdigit()
        ]

        return AlbumPage.model_validate({
            'count': len(page_content),
            'data': page_content,
            'pagination': pagination
        })


class Comic18ImgOps(ImageUtils):
    """Comic18 图片处理工具"""

    @staticmethod
    def get_split_num(album_id: int, page_id: str) -> int:
        """获取图片分割数"""
        page_index_str = page_id.split('.')[0]

        if album_id < 220971:
            split_num = 0
        elif album_id < 268850:
            split_num = 10
        elif album_id < 421926:
            split_seed = md5(f'{album_id}{page_index_str}'.encode()).hexdigest()
            split_num = (ord(split_seed[-1]) % 10) * 2 + 2
        else:
            split_seed = md5(f'{album_id}{page_index_str}'.encode()).hexdigest()
            split_num = (ord(split_seed[-1]) % 8) * 2 + 2

        return split_num

    @run_sync
    def reverse_segmental_image(self, album_id: int, page_id: str) -> 'Comic18ImgOps':
        """对被分割图片进行重新排序"""
        split_num = self.get_split_num(album_id=album_id, page_id=page_id)
        if split_num <= 1:
            return self

        src_image = self.image
        width, height = src_image.size
        output_image = Image.new(src_image.mode, src_image.size)

        # 图片高度一般不能被分割数整除
        # 分割图片最下面一条(即原图最上面一条)需保留余数高度
        remain_height = height % split_num
        split_height = (height - remain_height) // split_num

        down_pointer = height
        for up_pointer in range(height - remain_height - split_height, - split_height, - split_height):
            # 裁剪分割区块
            segment_block_image = src_image.crop(box=(0, up_pointer, width, down_pointer))
            # 倒序粘贴
            output_image.paste(segment_block_image, box=(0, height - down_pointer, width, height - up_pointer))
            # 移动区块指针
            down_pointer = up_pointer

        self._image = output_image
        return self


__all__ = [
    'Comic18Parser',
    'Comic18ImgOps'
]
