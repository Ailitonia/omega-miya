"""
@Author         : Ailitonia
@Date           : 2022/04/08 2:15
@FileName       : helper.py
@Project        : nonebot2_miya
@Description    : 常用的一些工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re

from lxml import etree
from nonebot.utils import run_sync

from .model.pixivision import PixivisionArticle, PixivisionIllustrations
from .model.user import PixivUserSearchingResult

_LOCALE_ARTICLE_PATH_PREFIX = re.compile(r'^/[a-z]{2}/a/(?=\d+)')
"""pixivision 文章链接地域前缀(形如 /zh/a/12345)"""
_LOCALE_TAG_PATH_PREFIX = re.compile(r'^/[a-z]{2}/t/(?=\d+)')
"""pixivision 标签链接地域前缀(形如 /zh/t/6789)"""
_BACKGROUND_IMAGE_URL = re.compile(r'background-image:\s*url\((.+?)\)')
"""内联样式 background-image 中的图片链接"""


class PixivParser:
    """Pixiv 页面解析工具集"""

    @staticmethod
    def parse_pid_from_url(text: str, *, url_mode: bool = True) -> int | None:
        """从字符串解析 pid"""
        if url_mode:
            # 分别匹配不同格式 pixiv 链接格式, 仅能匹配特定 url 格式的字符串
            if url_new := re.search(
                    r'^https?://(?:[a-zA-Z0-9-]+\.)*pixiv\.net/(?:artworks|i)/(\d+)(?:[/?#].*)?$', text
            ):
                return int(url_new.group(1))
            elif url_old := re.search(
                    r'^https?://(?:[a-zA-Z0-9-]+\.)*pixiv\.net(?:[/?#]\S*)?illust_id=(\d+)(?:[&#].*)?$', text
            ):
                return int(url_old.group(1))
        else:
            # 分别匹配不同格式 pixiv 链接格式, 可匹配任何字符串中的 url
            if url_new := re.search(
                    r'https?://(?:[a-zA-Z0-9-]+\.)*pixiv\.net/(?:artworks|i)/(\d+)', text
            ):
                return int(url_new.group(1))
            elif url_old := re.search(
                    r'https?://(?:[a-zA-Z0-9-]+\.)*pixiv\.net(?:[/?#].*)?illust_id=(\d+)', text
            ):
                return int(url_old.group(1))
        return None

    @staticmethod
    @run_sync
    def parse_user_searching_result_page(content: str) -> PixivUserSearchingResult:
        """解析 pixiv 用户搜索结果页内容, 任意一条解析失败均直接抛出异常

        :param content: 网页 html
        """
        html = etree.HTML(content)

        title_h1 = html.xpath('/html/body/div/div/div/div/div/div/div/h1').pop(0)
        title = title_h1.text
        count = title_h1.xpath('following-sibling::div/span[1]').pop(0).text

        # 直接定位到用户头像部分
        user_icon_list = html.xpath(
            '/html/body/div[@id="__next"]/div/div/div/div/div/div/'
            'li[contains(@class, "list-none")]/div/div/div/a[@data-ga4-label="user_icon_link"]'
        )

        # 解析搜索结果中用户内容的部分
        user_list = []
        for user_icon in user_icon_list:
            # 解析头像
            # user_icon_img = user_icon.xpath('div/img').pop(0)  # 头像是动态加载的, 忽略
            # user_head_url = user_icon_img.attrib.get('src')

            # 解析用户名和uid, 用户名在其相邻节点
            user_name_a = user_icon.xpath('following-sibling::div/div[1]/a[@data-ga4-label="user_name_link"]')
            if not user_name_a:
                raise ValueError('Parse user searching result failed, user name link not found')
            user_name_a_item = user_name_a.pop(0)
            user_name = user_name_a_item.text
            if not user_name:
                raise ValueError('Parse user searching result failed, user name not found')

            # 用户 id 位于用户名链接的 href 中
            user_href = user_name_a_item.attrib.get('href') or ''
            user_id_matched = re.search(r'/users/(\d+)', user_href)
            if user_id_matched is None:
                raise ValueError(
                    f'Parse user searching result failed, cannot parse user id from herf {user_href!r}'
                )
            user_id = user_id_matched.group(1)

            # 解析用户简介
            user_desc_divs = user_icon.xpath('following-sibling::div/div[2]')
            if user_desc_divs:
                user_desc = user_desc_divs.pop(0).text
                user_desc = '' if not user_desc else user_desc.replace('\r\n', ' ')
            else:
                user_desc = None

            # 解析用户作品预览图
            illust_thumbs = user_icon.xpath(
                f'parent::div/parent::div/parent::div//div[@type="illust"]/'
                f'div/a[@data-gtm-user-id="{user_id}"]/div/img'
            )
            illusts_thumb_urls = [
                x.attrib.get('src')
                for x in illust_thumbs
                if x.attrib.get('src') is not None
            ]

            user_list.append({
                'user_id': user_id,
                'user_name': user_name,
                'user_desc': user_desc,
                'illusts_thumb_urls': illusts_thumb_urls,
            })

        result = {
            'search_name': title,
            'count': count,
            'users': user_list,
        }
        return PixivUserSearchingResult.model_validate(result)

    @staticmethod
    @run_sync
    def parse_pixivision_show_page(content: str, root_url: str) -> PixivisionIllustrations:
        """解析 pixivision 导览页面内容, 任意一条解析失败均直接抛出异常

        :param content: 网页 html
        :param root_url: pixivision 主域名
        """
        html = etree.HTML(content)
        illustration_cards = html.xpath('/html/body//li[@class="article-card-container"]')

        result_list = []
        for card in illustration_cards:
            # 解析每篇文章对应 card 的内容
            title_href = card.xpath('article//h2[@class="arc__title"]/a[1]')
            if not title_href:
                raise ValueError('Parse pixivision show page failed, article title link not found')
            title_href_item = title_href.pop(0)
            title = (title_href_item.text or '').strip()
            title_rela_url = title_href_item.attrib.get('href') or ''

            aid = _LOCALE_ARTICLE_PATH_PREFIX.sub('', title_rela_url)
            if not aid.isdigit():
                raise ValueError(
                    f'Parse pixivision show page failed, cannot parse article id from href {title_rela_url!r}'
                )

            thumbnail = card.xpath('article//div[@class="_thumbnail"]').pop(0).attrib.get('style')
            matched_thumbnail = _BACKGROUND_IMAGE_URL.search(thumbnail or '')
            if matched_thumbnail is None:
                continue
            thumbnail_url = matched_thumbnail.group(1).strip('\'" ')

            tag_container = card.xpath('article//ul[@class="_tag-list"]/li[@class="tls__list-item-container"]')
            tag_list = []
            for tag in tag_container:
                tag_href = tag.xpath('a[1]')
                if not tag_href:
                    continue

                tag_href_item = tag_href.pop(0)
                tag_name = tag_href_item.attrib.get('data-gtm-label')
                tag_rela_url = tag_href_item.attrib.get('href')
                if not tag_name or not tag_rela_url:
                    raise ValueError('Parse pixivision tag failed, tag name or href not found')

                tag_id = _LOCALE_TAG_PATH_PREFIX.sub('', tag_rela_url)
                if not tag_id.isdigit():
                    raise ValueError(f'Parse pixivision tag id from href {tag_rela_url!r} failed')
                tag_list.append({'tag_id': tag_id, 'tag_name': tag_name, 'tag_url': root_url + tag_rela_url})

            result_list.append({
                'aid': aid,
                'title': title,
                'thumbnail': thumbnail_url,
                'url': root_url + title_rela_url,
                'tags': tag_list,
            })
        return PixivisionIllustrations.model_validate({'illustrations': result_list})

    @classmethod
    @run_sync
    def parse_pixivision_article_page(cls, content: str, root_url: str) -> PixivisionArticle:
        """解析 pixivision 文章页面内容, 任意一条解析失败均直接抛出异常

        :param content: 网页 html
        :param root_url: pixivision 主域名
        """
        html = etree.HTML(content)
        article_main = html.xpath('/html/body//div[@class="_article-main"]').pop(0)

        # 解析 article 描述部分
        article = article_main.xpath('article[@class="am__article-body-container"]').pop(0)
        article_title = article.xpath('header[1]//h1[@class="am__title"]').pop(0).text.strip()
        eyecatch = article.xpath('div//div[@class="_article-illust-eyecatch"]')
        eyecatch_image = eyecatch.pop(0).xpath('img[1]').pop(0).attrib.get('src') if eyecatch else None

        # 解析 article 主体部分
        article_body = article_main.xpath('article//div[@class="am__body"]').pop(0)

        # 获取文章描述
        # 注意 pixivision illustration 的文章有两种页面样式
        article_description = article_body.xpath(
            'div//div[@class="fab__paragraph _medium-editor-text" or @class="am__description _medium-editor-text"]'
        ).pop(0)
        description = '\n'.join(text.strip() for text in article_description.itertext())

        # 特辑内容是作品的, 获取所有作品内容
        artwork_list = []
        artworks = article_body.xpath('div//div[@class="am__work"]')
        for artwork in artworks:
            # 解析作品信息
            artwork_info = artwork.xpath('div[@class="am__work__info"]').pop(0)
            artwork_title = artwork_info.xpath('div//h3[@class="am__work__title"]/a[1]').pop(0).text.strip()
            artwork_user_name = artwork_info.xpath(
                'div//p[@class="am__work__user-name"]/a[@class="author-img-container inner-link"]'
            ).pop(0).text.strip()

            artwork_main = artwork.xpath('div[@class="am__work__main"]').pop(0)
            artwork_url = artwork_main.xpath('a[@class="inner-link"]').pop(0).attrib.get('href')
            if not artwork_url:
                raise ValueError('Parse pixivision article page artwork failed, artwork url not found')

            artwork_id = cls.parse_pid_from_url(text=artwork_url, url_mode=False)
            if artwork_id is None:
                raise ValueError(
                    f'Parse pixivision article page artwork failed, cannot parse artwork id from url {artwork_url!r}'
                )
            image_url = artwork_main.xpath(
                'a//img[contains(@class, "am__work__illust")]'
            ).pop(0).attrib.get('src')

            artwork_list.append({
                'artwork_id': artwork_id,
                'artwork_user': artwork_user_name,
                'artwork_title': artwork_title,
                'artwork_url': artwork_url,
                'image_url': image_url,
            })

        # 特辑内容是其他特辑合集的, 获取所有特辑内容
        illustration_list = []
        illustrations = article_body.xpath('div//article[@class="_article-card spotlight"]')
        for illustration in illustrations:
            # 解析特辑信息
            illustration_thumbnail = illustration.xpath(
                'div/a/div[@class="_thumbnail"]'
            ).pop(0).attrib.get('style')
            matched_thumbnail = _BACKGROUND_IMAGE_URL.search(illustration_thumbnail or '')
            if matched_thumbnail is None:
                continue
            illustration_thumbnail_url = matched_thumbnail.group(1).strip('\'" ')

            illustration_info = illustration.xpath('div/h2[@class="arc__title"]/a').pop(0)
            illustration_title = (illustration_info.text or '').strip()
            illustration_href = illustration_info.attrib.get('href') or ''

            illustration_aid = _LOCALE_ARTICLE_PATH_PREFIX.sub('', illustration_href)
            if not illustration_aid.isdigit():
                raise ValueError(
                    f'Parse pixivision article page illustration failed, '
                    f'cannot parse illustration id from href {illustration_href!r}'
                )
            illustration_tags = [
                {
                    'tag_id': tag_id,
                    'tag_name': tag_name.strip(),
                    'tag_url': root_url + tag_href,
                }
                for x in illustration.xpath('div/ul[@class="_tag-list"]/li[@class="tls__list-item-container"]/a')
                if (
                        (tag_href := x.attrib.get('href')) is not None
                        and (tag_id := _LOCALE_TAG_PATH_PREFIX.sub('', tag_href))
                        and (tag_name := x.attrib.get('data-gtm-label')) is not None
                )
            ]
            illustration_list.append({
                'aid': illustration_aid,
                'title': illustration_title,
                'thumbnail': illustration_thumbnail_url,
                'url': root_url + illustration_href,
                'tags': illustration_tags,
            })

        # 解析 tag
        tag_list = []
        tag_hrefs = article_main.xpath('div//ul[@class="_tag-list"]/a')
        for tag in tag_hrefs:
            tag_name = tag.attrib.get('data-gtm-label')
            tag_rela_url = tag.attrib.get('href')
            if not tag_rela_url:
                continue
            tag_id = _LOCALE_TAG_PATH_PREFIX.sub('', tag_rela_url)
            tag_url = root_url + tag_rela_url
            tag_list.append({'tag_id': tag_id, 'tag_name': tag_name, 'tag_url': tag_url})

        result = {
            'title': article_title,
            'description': description,
            'eyecatch_image': eyecatch_image,
            'artwork_list': artwork_list,
            'illustration_list': illustration_list,
            'tags_list': tag_list,
        }
        return PixivisionArticle.model_validate(result)


__all__ = [
    'PixivParser',
]
