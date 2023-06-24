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
from io import BytesIO
from datetime import datetime
from lxml import etree
from typing import Optional, Any
from PIL import Image, ImageDraw, ImageFont

from nonebot.utils import run_sync

from src.resource import TemporaryResource
from src.service.omega_requests import OmegaRequests
from src.utils.process_utils import semaphore_gather
from src.utils.image_utils import ImageUtils
from src.utils.image_utils.template import generate_thumbs_preview_image, PreviewImageThumbs, PreviewImageModel

from .config import pixiv_config, pixiv_resource_config
from .exception import PixivNetworkError
from .model.searching import PixivSearchingResultModel
from .model.ranking import PixivRankingModel
from .model.user import PixivUserSearchingBody, PixivUserSearchingModel
from .model.artwork import PixivArtworkPreviewRequestModel
from .model.pixivision import PixivisionArticle, PixivisionIllustrationList


async def _request_resource(
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        timeout: int = 45
) -> bytes:
    """获取任意 pixiv 资源内容"""
    if headers is None:
        headers = OmegaRequests.get_default_headers()
        headers.update({'referer': 'https://www.pixiv.net/'})

    requests = OmegaRequests(timeout=timeout, headers=headers, cookies=pixiv_config.cookie_phpssid)
    response = await requests.get(url=url, params=params)
    if response.status_code != 200:
        raise PixivNetworkError(f'{response.request}, status code {response.status_code}')

    return response.content


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


def parse_user_searching_result_page(content: str) -> PixivUserSearchingModel:
    """解析 pixiv 用户搜索结果页内容

    :param content: 网页 html
    """
    html = etree.HTML(content)

    # 获取搜索结果总览的部分
    column_header = html.xpath('/html/body//div[@class="column-header"]').pop(0)
    title = column_header.xpath('h1[@class="column-title"]/a[@class="self"]').pop(0).text
    count = column_header.xpath('span[@class="count-badge"]').pop(0).text

    # 获取搜索结果中用户内容的部分
    user_list = []
    users = html.xpath('/html/body//div[@class="user-search-result-container"]//li[@class="user-recommendation-item"]')
    for user in users:
        # 解析头像
        user_head_url = user.xpath('a[@class="_user-icon size-128 cover-texture ui-scroll-view" '
                                   'and @target="_blank" and @title]').pop(0).attrib.get('data-src')
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
            for thumb in user.xpath('ul[@class="images"]/li[@class="action-open-thumbnail"]')
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
    return PixivUserSearchingModel.parse_obj(result)


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
        thumbnail = re.search(r'^background-image:\s\surl\((.+)\)$', thumbnail).group(1)

        tag_container = card.xpath('article//ul[@class="_tag-list"]/li[@class="tls__list-item-container"]')
        tag_list = []
        for tag in tag_container:
            tag_href = tag.xpath('a[1]').pop(0)
            tag_name = tag_href.attrib.get('data-gtm-label').strip()
            tag_rela_url = tag_href.attrib.get('href')
            tag_id = re.sub(r'^/zh/t/(?=\d+)', '', tag_rela_url)
            tag_url = root_url + tag_rela_url
            tag_list.append({'tag_id': tag_id, 'tag_name': tag_name, 'tag_url': tag_url})
        result_list.append({'aid': aid, 'title': title, 'thumbnail': thumbnail, 'url': url, 'tags': tag_list})
    return PixivisionIllustrationList.parse_obj({'illustrations': result_list})


def parse_pixivision_article_page(content: str, root_url: str) -> PixivisionArticle:
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
    ).pop(0).xpath('p')
    description = '\n'.join(x.text.strip() for x in article_description if x.text)

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
        artwork_id = parse_pid_from_url(text=artwork_url, url_mode=False)
        image_url = artwork_main.xpath('a//img[@class="am__work__illust "]').pop(0).attrib.get('src')

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
    return PixivisionArticle.parse_obj(result)


async def _generate_user_searching_result_card(user: PixivUserSearchingBody, *, width: int = 1600) -> Image.Image:
    """根据用户搜索结果页面解析内容, 生成单独一个用户的结果 card 图片"""
    # 首先获取用户相关图片资源
    user_head = await _request_resource(url=user.user_head_url)
    user_illusts_thumb = await semaphore_gather(
        tasks=[_request_resource(url=url) for url in user.illusts_thumb_urls],
        semaphore_num=4
    )

    def _handle_generate_card() -> Image.Image:
        """用于图像生成处理的内部函数"""
        # 整体图片大小
        _height = int(width / pixiv_resource_config.user_searching_card_ratio)
        # 字体
        _font_main_size = int(_height / 8)
        _font_desc_size = int(_height / 12)
        _font_main = ImageFont.truetype(pixiv_resource_config.default_font_file.resolve_path, _font_main_size)
        _font_desc = ImageFont.truetype(pixiv_resource_config.default_font_file.resolve_path, _font_desc_size)
        # 创建背景图层
        _background = Image.new(mode="RGB", size=(width, _height), color=(255, 255, 255))
        # 头像及预览图大小
        _user_head_width = int(_height * 5 / 6)
        _thumb_img_width = _user_head_width
        # 根据头像计算标准间距
        _spacing_width = int((_height - _user_head_width) / 2)
        # 绘制背景框
        ImageDraw.Draw(_background).rounded_rectangle(
            xy=(
                int(_spacing_width / 4), int(_spacing_width / 4),
                int(width - _spacing_width / 4), int(_height - _spacing_width / 4)
            ),
            radius=int(_height / 12),
            fill=(228, 250, 255)
        )
        # 读取头像
        with BytesIO(user_head) as bf:
            _user_head_img: Image.Image = Image.open(bf)
            _user_head_img.load()
        _user_head_img = _user_head_img.resize((_user_head_width, _user_head_width))
        _user_head_img = _user_head_img.convert(mode="RGBA")
        # 新建头像蒙版
        _user_head_mask = Image.new(mode="RGBA", size=(_user_head_width, _user_head_width), color=(255, 255, 255, 0))
        _user_head_mask_draw = ImageDraw.Draw(_user_head_mask)
        _user_head_mask_draw.ellipse((0, 0, _user_head_width, _user_head_width), fill=(0, 0, 0, 255))
        # 处理头像蒙版并粘贴
        _background.paste(im=_user_head_img, box=(_spacing_width * 2, _spacing_width), mask=_user_head_mask)
        # 绘制用户名称
        ImageDraw.Draw(_background).text(
            xy=(_spacing_width * 4 + _user_head_width, int(_spacing_width * 1.5)),
            font=_font_main,
            text=user.user_name,
            fill=(0, 0, 0))
        # 绘制用户 uid
        _name_text_w, _name_text_h = _font_main.getsize(user.user_name)
        _uid_text = f'UID：{user.user_id}'
        _uid_text_w, _uid_text_h = _font_desc.getsize(_uid_text)
        ImageDraw.Draw(_background).text(
            xy=(_spacing_width * 4 + _user_head_width, _name_text_h + int(_spacing_width * 1.75)),
            font=_font_desc,
            text=_uid_text,
            fill=(37, 143, 184))
        # 投稿作品数
        _count_text = f'插画投稿数：{user.user_illust_count}'
        _count_text_w, _count_text_h = _font_desc.getsize(_count_text)
        ImageDraw.Draw(_background).text(
            xy=(_spacing_width * 4 + _user_head_width, _name_text_h + _uid_text_h + int(_spacing_width * 2.25)),
            font=_font_desc,
            text=_count_text,
            fill=(37, 143, 184))
        # 绘制用户简介
        # 按长度切分文本
        _desc_text = ImageUtils.split_multiline_text(text=user.user_desc, width=int(_height * 1.5), font=_font_desc)
        ImageDraw.Draw(_background).multiline_text(
            xy=(_spacing_width * 4 + _user_head_width,
                _name_text_h + _uid_text_h + _count_text_h + int(_spacing_width * 2.75)),
            font=_font_desc,
            text=_desc_text,
            fill=(0, 0, 0))

        # 一般页面只有四张预览图 这里也只贴四张
        for _index, _illusts_thumb in enumerate(user_illusts_thumb[:4]):
            # 检查缩略图加载情况
            if isinstance(_illusts_thumb, BaseException):
                # 获取失败或小说等作品没有预览图
                _thumb_img = Image.new(mode="RGB", size=(_thumb_img_width, _thumb_img_width), color=(127, 127, 127))
            else:
                # 正常获取的预览图
                with BytesIO(_illusts_thumb) as bf:
                    _thumb_img: Image.Image = Image.open(bf)
                    _thumb_img.load()
                _thumb_img = _thumb_img.resize((_thumb_img_width, _thumb_img_width))
                _thumb_img = _thumb_img.convert(mode="RGB")
            # 预览图外边框
            ImageDraw.Draw(_background).rectangle(
                xy=((_spacing_width * 6 + _user_head_width + int(_height * 1.5)  # 前面文字的宽度
                     + _index * (_thumb_img_width + _spacing_width)  # 根据缩略图序列增加的位置宽度
                     - int(_thumb_img_width / 80),  # 边框预留的宽度
                     _spacing_width - int(_thumb_img_width / 80)),  # 高度及边框预留宽度
                    (_spacing_width * 6 + _user_head_width + int(_height * 1.5)
                     + _index * (_thumb_img_width + _spacing_width) + _thumb_img_width
                     + int(_thumb_img_width / 96),
                     _spacing_width + _thumb_img_width + int(_thumb_img_width / 96))),
                fill=(224, 224, 224),
                width=0
            )
            # 依次粘贴预览图
            _background.paste(
                im=_thumb_img,
                box=(_spacing_width * 6 + _user_head_width + int(_height * 1.5) +  # 前面头像及介绍文本的宽度
                     _index * (_thumb_img_width + _spacing_width),  # 预览图加间隔的宽度
                     _spacing_width)  # 预览图高度
            )
        return _background

    user_illusts_thumb_image = await run_sync(_handle_generate_card)()
    return user_illusts_thumb_image


async def generate_user_searching_result_image(
        searching: PixivUserSearchingModel,
        *,
        width: int = 1600
) -> TemporaryResource:
    """根据用户搜索结果页面解析内容, 生成结果预览图片"""
    users = searching.users[:pixiv_resource_config.user_searching_card_num]
    tasks = [_generate_user_searching_result_card(user=user, width=width) for user in users]
    cards = await semaphore_gather(tasks=tasks, semaphore_num=8, filter_exception=True)

    def _handle_generate_image() -> bytes:
        """用于图像生成处理的内部函数"""
        _card_height = int(width / pixiv_resource_config.user_searching_card_ratio)
        # 根据卡片计算标准间距
        _spacing_width = int(_card_height / 12)
        # 字体
        _font_title_size = int(_card_height / 6)
        _font_title = ImageFont.truetype(pixiv_resource_config.default_font_file.resolve_path, _font_title_size)
        # 标题
        _title_text = f'Pixiv 用户搜索：{searching.search_name} - 共{searching.count}'
        _title_text_w, _title_text_h = _font_title.getsize_multiline(_title_text)
        # 整体图片高度
        _height = (_card_height + _spacing_width) * len(cards) + _title_text_h + 3 * _spacing_width
        # 创建背景图层
        _background = Image.new(mode="RGB", size=(width + _spacing_width * 2, _height), color=(255, 255, 255))
        # 绘制标题
        ImageDraw.Draw(_background).text(
            xy=(_spacing_width * 2, _spacing_width),
            font=_font_title,
            text=_title_text,
            fill=(37, 143, 184)
        )
        # 依次粘贴各结果卡片
        for _index, _card in enumerate(cards):
            _background.paste(
                im=_card,
                box=(_spacing_width, _spacing_width * 2 + _title_text_h + (_card_height + _spacing_width) * _index)
            )
        # 生成结果图片
        with BytesIO() as _bf:
            _background.save(_bf, 'JPEG')
            _content = _bf.getvalue()
        return _content

    image_content = await run_sync(_handle_generate_image)()
    image_file_name = f"preview_search_user_{searching.search_name}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"
    save_file = pixiv_resource_config.default_preview_img_folder(image_file_name)
    async with save_file.async_open('wb') as af:
        await af.write(image_content)
    return save_file


async def _request_preview_body(request: PixivArtworkPreviewRequestModel) -> PreviewImageThumbs:
    """获取生成预览图中每个缩略图的数据"""
    _request_data = await _request_resource(url=request.request_url)
    return PreviewImageThumbs(desc_text=request.desc_text, preview_thumb=_request_data)


async def _request_preview_model(
        preview_name: str,
        requests: list[PixivArtworkPreviewRequestModel]
) -> PreviewImageModel:
    """获取生成预览图所需要的数据模型"""
    _tasks = [_request_preview_body(request) for request in requests]
    _requests_data = await semaphore_gather(tasks=_tasks, semaphore_num=30, filter_exception=True)
    _requests_data = list(_requests_data)
    count = len(_requests_data)
    return PreviewImageModel(preview_name=preview_name, count=count, previews=_requests_data)


def format_artwork_preview_desc(pid: int | str, title: str, uname: str, *, num_lmt: int = 13) -> str:
    """格式化预览图的作品描述信息"""
    pid_text = f"Pid: {pid}"
    title_text = f"{title[:num_lmt]}..." if len(title) > num_lmt else title
    author_text = f"Author: {uname}"
    author_text = f"{author_text[:num_lmt]}..." if len(author_text) > num_lmt else author_text
    return f'{pid_text}\n{title_text}\n{author_text}'


async def emit_preview_model_from_ranking_model(
        ranking_name: str, model: PixivRankingModel
) -> PreviewImageModel:
    """从排行榜结果中获取生成预览图所需要的数据模型"""
    request_list = [
        PixivArtworkPreviewRequestModel(
            desc_text=format_artwork_preview_desc(
                pid=data.illust_id,
                title=f'【No.{(model.page - 1) * len(model.contents) + index + 1}】{data.title}',
                uname=data.user_name
            ),
            request_url=data.url
        )
        for index, data in enumerate(model.contents)
    ]
    preview_model = await _request_preview_model(preview_name=ranking_name, requests=request_list)
    return preview_model


async def emit_preview_model_from_searching_model(
        searching_name: str, model: PixivSearchingResultModel
) -> PreviewImageModel:
    """从搜索结果中获取生成预览图所需要的数据模型"""
    request_list = [
        PixivArtworkPreviewRequestModel(
            desc_text=format_artwork_preview_desc(pid=data.id, title=data.title, uname=data.userName),
            request_url=data.url
        )
        for data in model.searching_result
    ]
    preview_model = await _request_preview_model(preview_name=searching_name, requests=request_list)
    return preview_model


async def emit_preview_model_from_pixivision_illustration_model(
        preview_name: str, model: PixivisionIllustrationList
) -> PreviewImageModel:
    """从 pixivision illustration 内容中获取生成预览图所需要的数据模型"""
    request_list = [
        PixivArtworkPreviewRequestModel(
            desc_text=f'ArticleID: {data.aid}\n{data.split_title_without_mark}',
            request_url=data.thumbnail
        )
        for data in model.illustrations
    ]
    preview_model = await _request_preview_model(preview_name=preview_name, requests=request_list)
    return preview_model


async def emit_preview_model_from_pixivision_article_model(
        preview_name: str, model: PixivisionArticle
) -> PreviewImageModel:
    """从 pixivision article 内容中获取生成预览图所需要的数据模型"""
    request_list = [
        PixivArtworkPreviewRequestModel(
            desc_text=format_artwork_preview_desc(
                pid=data.artwork_id, title=data.artwork_title, uname=data.artwork_user),
            request_url=data.image_url
        )
        for data in model.artwork_list
    ]
    preview_model = await _request_preview_model(preview_name=preview_name, requests=request_list)
    return preview_model


async def generate_artworks_preview_image(
        preview: PreviewImageModel,
        *,
        preview_size: tuple[int, int] = pixiv_resource_config.default_preview_size,
        hold_ratio: bool = False,
        num_of_line: int = 6,
        limit: int = 1000
) -> TemporaryResource:
    """生成多个作品的预览图

    :param preview: 经过预处理的生成预览的数据
    :param preview_size: 单个小缩略图的尺寸
    :param hold_ratio: 是否保持缩略图原图比例
    :param num_of_line: 生成预览每一行的预览图数
    :param limit: 限制生成时加载 preview 中图片的最大值
    """
    return await generate_thumbs_preview_image(
        preview=preview,
        preview_size=preview_size,
        font_path=pixiv_resource_config.default_preview_font,
        header_color=(0, 150, 250),
        hold_ratio=hold_ratio,
        num_of_line=num_of_line,
        limit=limit,
        output_folder=pixiv_resource_config.default_preview_img_folder
    )


__all__ = [
    'parse_pid_from_url',
    'parse_user_searching_result_page',
    'parse_pixivision_show_page',
    'parse_pixivision_article_page',
    'generate_user_searching_result_image',
    'format_artwork_preview_desc',
    'emit_preview_model_from_ranking_model',
    'emit_preview_model_from_searching_model',
    'emit_preview_model_from_pixivision_illustration_model',
    'emit_preview_model_from_pixivision_article_model',
    'generate_artworks_preview_image'
]
