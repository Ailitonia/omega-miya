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

from src.compat import parse_json_as
from .model.pixivision import PixivisionArticle, PixivisionIllustrationList
from .model.user import PixivGlobalData, PixivUserSearchingModel


class PixivParser(object):
    """Pixiv 页面解析工具集"""

    @staticmethod
    def parse_pid_from_url(text: str, *, url_mode: bool = True) -> int | None:
        """从字符串解析 pid"""
        if url_mode:
            # 分别匹配不同格式 pixiv 链接格式, 仅能匹配特定 url 格式的字符串
            if url_new := re.search(r'^https?://.*?pixiv\.net/(artworks|i)/(\d+?)$', text):
                return int(url_new.group(2))
            elif url_old := re.search(r'^https?://.*?pixiv\.net.*?illust_id=(\d+?)(&mode=\w+?)?$', text):
                return int(url_old.group(1))
        else:
            # 分别匹配不同格式 pixiv 链接格式, 可匹配任何字符串中的 url
            if url_new := re.search(r'https?://.*?pixiv\.net/(artworks|i)/(\d+)\??', text):
                return int(url_new.group(2))
            elif url_old := re.search(r'https?://.*?pixiv\.net.*?illust_id=(\d+)\??', text):
                return int(url_old.group(1))
        return None

    @staticmethod
    @run_sync
    def parse_user_searching_result_page(content: str) -> PixivUserSearchingModel:
        """解析 pixiv 用户搜索结果页内容

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
            user_name_a = user_icon.xpath('following-sibling::div/div[1]/a[@data-ga4-label="user_name_link"]').pop(0)
            user_name = user_name_a.text
            user_id = user_name_a.attrib.get('id')

            # 解析用户简介
            user_desc_divs = user_icon.xpath('following-sibling::div/div[2]')
            if user_desc_divs:
                user_desc = user_desc_divs.pop(0).text
                user_desc = '' if not user_desc else user_desc.replace('\r\n', ' ')
            else:
                user_desc = None

            # 解析用户作品预览图
            illust_thumbs = user_icon.xpath(
                f'parent::div/parent::div/parent::div//div[@type="illust"]/div/a[@data-gtm-user-id="{user_id}"]/div/img'
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
                'illusts_thumb_urls': illusts_thumb_urls
            })

        result = {
            'search_name': title,
            'count': count,
            'users': user_list
        }
        return PixivUserSearchingModel.model_validate(result)

    @staticmethod
    @run_sync
    def _parse_user_searching_result_page(content: str) -> PixivUserSearchingModel:
        """[Deactivated]解析 pixiv 用户搜索结果页内容 (旧版页面)

        :param content: 网页 html
        """
        html = etree.HTML(content)

        # 获取搜索结果总览的部分
        column_header = html.xpath('/html/body//div[@class="column-header"]').pop(0)
        title = column_header.xpath('h1[@class="column-title"]/a[@class="self"]').pop(0).text
        count = column_header.xpath('span[@class="count-badge"]').pop(0).text

        # 获取搜索结果中用户内容的部分
        user_list = []
        users = html.xpath(
            '/html/body//div[@class="user-search-result-container"]//li[@class="user-recommendation-item"]'
        )
        for user in users:
            # 解析头像
            user_head_a = user.xpath('a[contains(@class, "_user-icon") and @target="_blank" and @title]').pop(0)
            user_head_url = user_head_a.attrib.get('data-src')
            # 解析用户名和uid
            user_href = user.xpath('h1/a[@class="title" and @target="_blank"]').pop(0)
            user_name = user_href.text
            user_id = user_href.attrib.get('href').replace('/users/', '')
            # 解析投稿作品数
            user_illust_count = user.xpath('dl[@class="meta inline-list"]/dd[1]/a').pop(0).text
            # 解析用户简介
            user_desc = user.xpath('p[@class="caption"]').pop(0).text
            user_desc = '' if not user_desc else user_desc.replace('\r\n', ' ')
            # 解析用户作品预览图
            illust_thumb_urls = [
                thumb.attrib.get('data-src')
                for thumb in user.xpath('ul[@class="images"]/li[@class="action-open-thumbnail"]/a')
                if thumb.attrib.get('data-src') is not None
            ]

            user_list.append({
                'user_id': user_id,
                'user_name': user_name,
                'user_head_url': user_head_url,
                'user_illust_count': user_illust_count,
                'user_desc': user_desc,
                'illusts_thumb_urls': illust_thumb_urls
            })
        result = {
            'search_name': title,
            'count': count,
            'users': user_list
        }
        return PixivUserSearchingModel.model_validate(result)

    @staticmethod
    @run_sync
    def parse_global_data(content: str) -> PixivGlobalData:
        """解析 pixiv 主页全局信息

        :param content: 网页 html
        """
        html = etree.HTML(content)

        global_data = html.xpath(
            '/html/head/meta[@name="global-data" and @id="meta-global-data"]'
        ).pop(0).attrib.get('content')
        return parse_json_as(PixivGlobalData, global_data)

    @staticmethod
    @run_sync
    def parse_pixivision_show_page(content: str, root_url: str) -> PixivisionIllustrationList:
        """解析 pixivision 导览页面内容

        :param content: 网页 html
        :param root_url: pixivision 主域名
        """
        html = etree.HTML(content)
        illustration_cards = html.xpath('/html/body//li[@class="article-card-container"]')

        result_list = []
        for card in illustration_cards:
            # 解析每篇文章对应 card 的内容
            title_href = card.xpath('article//h2[@class="arc__title"]/a[1]').pop(0)
            title = title_href.text.strip()
            aid = title_href.attrib.get('data-gtm-label')
            url = root_url + title_href.attrib.get('href')

            thumbnail = card.xpath('article//div[@class="_thumbnail"]').pop(0).attrib.get('style')
            matched_thumbnail = re.search(r'^background-image:\s\surl\((.+)\)$', thumbnail)
            if matched_thumbnail is None:
                continue
            thumbnail_url = matched_thumbnail.group(1)

            tag_container = card.xpath('article//ul[@class="_tag-list"]/li[@class="tls__list-item-container"]')
            tag_list = []
            for tag in tag_container:
                tag_href = tag.xpath('a[1]').pop(0)
                tag_name = tag_href.attrib.get('data-gtm-label').strip()
                tag_rela_url = tag_href.attrib.get('href')
                tag_id = re.sub(r'^/zh/t/(?=\d+)', '', tag_rela_url)
                tag_url = root_url + tag_rela_url
                tag_list.append({'tag_id': tag_id, 'tag_name': tag_name, 'tag_url': tag_url})
            result_list.append({'aid': aid, 'title': title, 'thumbnail': thumbnail_url, 'url': url, 'tags': tag_list})
        return PixivisionIllustrationList.model_validate({'illustrations': result_list})

    @classmethod
    @run_sync
    def parse_pixivision_article_page(cls, content: str, root_url: str) -> PixivisionArticle:
        """解析 pixivision 文章页面内容

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

        # 获取所有作品内容
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
            artwork_id = cls.parse_pid_from_url(text=artwork_url, url_mode=False)
            image_url = artwork_main.xpath('a//img[contains(@class, "am__work__illust")]').pop(0).attrib.get('src')

            artwork_list.append({'artwork_id': artwork_id, 'artwork_user': artwork_user_name,
                                 'artwork_title': artwork_title, 'artwork_url': artwork_url, 'image_url': image_url})

        # 解析 tag
        tag_list = []
        tag_hrefs = article_main.xpath('div//ul[@class="_tag-list"]/a')
        for tag in tag_hrefs:
            tag_name = tag.attrib.get('data-gtm-label')
            tag_rela_url = tag.attrib.get('href')
            tag_id = re.sub(r'^/zh/t/(?=\d+)', '', tag_rela_url)
            tag_url = root_url + tag_rela_url
            tag_list.append({'tag_id': tag_id, 'tag_name': tag_name, 'tag_url': tag_url})

        result = {
            'title': article_title,
            'description': description,
            'eyecatch_image': eyecatch_image,
            'artwork_list': artwork_list,
            'tags_list': tag_list
        }
        return PixivisionArticle.model_validate(result)


__all__ = [
    'PixivParser',
]
