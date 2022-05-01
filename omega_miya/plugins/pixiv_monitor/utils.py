"""
@Author         : Ailitonia
@Date           : 2022/01/16 22:14
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : pixiv 画师预览图生成工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import asyncio
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from typing import List
from dataclasses import dataclass
from nonebot import logger, get_driver
from bs4 import BeautifulSoup
from omega_miya.utils.omega_plugin_utils import HttpFetcher, ProcessUtils, TextUtils
from omega_miya.utils.pixiv_utils import Pixiv
from omega_miya.database import Result


global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
RESOURCES_PATH = global_config.resources_path_

# 检查生成结果图片的路径
SEARCHED_FOLDER_PATH = os.path.abspath(os.path.join(TMP_PATH, 'pixiv_monitor', 'search_user'))
if not os.path.exists(SEARCHED_FOLDER_PATH):
    os.makedirs(SEARCHED_FOLDER_PATH)

# 检查字体路径
FONT_NAME = 'SourceHanSans_Regular.otf'
FONT_PATH = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', FONT_NAME))
# 检查预置字体
if not os.path.exists(FONT_PATH):
    logger.error(f"PixivUserSearching | 预置文件错误, 字体 {FONT_NAME} 不存在")
    raise FileNotFoundError('Font file not found')


# 图片绘制相关参数
CARD_RATIO: float = 6.75  # 注意这里的图片长宽比会直接影响到排版 不要随便改
CARD_NUM: int = 6  # 图中绘制的画师搜索结果数量限制


@dataclass
class _UserSearched:
    user_id: int
    user_name: str
    user_head_url: str
    user_illust_count: int
    user_desc: str
    illusts_thumb_urls: list


@dataclass
class _UserSearchResult(Result.AnyResult):
    result: List[_UserSearched]

    def __repr__(self):
        return f'<UserSearchResult(error={self.error}, info={self.info}, result={self.result})>'


async def search_pixiv_user(nick: str) -> _UserSearchResult:
    """
    搜索p站用户
    :param nick: 用户名
    :return: DictResult, {user_id: user_info}
    """
    # p站唯独画师搜索没有做前后端分离 只能解析页面了
    user_search_url = 'https://www.pixiv.net/search_user.php'

    headers = Pixiv.HEADERS.copy()
    headers.update({'sec-ch-ua-platform': '"Windows"', 'sec-fetch-dest': 'document', 'sec-fetch-mode': 'navigate'})

    params = {'s_mode': 's_usr', 'nick': nick}
    fetcher = HttpFetcher(timeout=10, flag='pixiv_search_user', headers=headers, cookies=Pixiv.get_cookies())
    user_search_result = await fetcher.get_text(url=user_search_url, params=params)

    if user_search_result.error:
        return _UserSearchResult(error=True, info=f'Searching user failed, {user_search_result.info}', result=[])

    search_page_bs = BeautifulSoup(user_search_result.result, 'lxml')
    users = search_page_bs.find_all(name='li', attrs={'class': 'user-recommendation-item'})

    result = []
    for user_bs in users:
        try:
            # 解析头像
            user_head_elm = user_bs.find(name='a', attrs={'class': '_user-icon size-128 cover-texture ui-scroll-view',
                                                          'target': '_blank', 'title': True,
                                                          'data-filter': 'lazy-image'})
            user_head_url = user_head_elm.attrs['data-src']
            # 解析用户名和uid
            user_name_elm = user_bs.find(name='h1')
            user_name = user_name_elm.a.get_text()
            user_id = int(str(user_name_elm.a.attrs['href']).replace('/users/', ''))
            # 解析投稿作品数
            user_illust_count_elm = user_bs.find(name='dl', attrs={'class': 'meta inline-list'})
            user_illust_count = int(user_illust_count_elm.dd.a.get_text())
            # 解析用户简介
            user_desc_elm = user_bs.find(name='p', attrs={'class': 'caption'})
            user_desc = str(user_desc_elm.get_text()).replace('\r\n', ' ')
            # 解析用户作品预览图
            user_illust_elms = user_bs.find_all(name='li', attrs={'class': 'action-open-thumbnail'})
            illusts_thumb_urls = [
                user_illust_elm.a.get('data-src', None) for user_illust_elm in user_illust_elms
                if user_illust_elm.a.get('data-src', None) is not None
            ]

            result.append(_UserSearched(
                user_id=user_id,
                user_name=user_name,
                user_head_url=user_head_url,
                user_illust_count=user_illust_count,
                user_desc=user_desc,
                illusts_thumb_urls=illusts_thumb_urls
            ))
        except Exception as e:
            logger.error(f'PixivUserSearching | Parse user searching result page error: {repr(e)}')
            continue

    return _UserSearchResult(error=False, info='Success', result=result)


async def _get_pixiv_img(url: str) -> Result.BytesResult:
    headers = Pixiv.HEADERS.copy()
    fetcher = HttpFetcher(timeout=10, flag='pixiv_user_search_get_img', headers=headers, cookies=Pixiv.get_cookies())
    result = await fetcher.get_bytes(url=url)
    return Result.BytesResult(error=result.error, info=result.info, result=result.result)


async def _generate_user_card(user: _UserSearched, *, width: int = 1600) -> Image.Image:
    # 首先获取用户相关图片资源
    user_head = await _get_pixiv_img(url=user.user_head_url)
    user_illusts_thumb = await ProcessUtils.fragment_process(
        tasks=[_get_pixiv_img(url=url) for url in user.illusts_thumb_urls],
        log_flag='pixiv_user_search_get_illusts_thumb'
    )

    def _handle() -> Image.Image:
        # 整体图片大小
        height = int(width / CARD_RATIO)
        # 字体
        font_main_size = int(height / 8)
        font_desc_size = int(height / 12)
        font_main = ImageFont.truetype(FONT_PATH, font_main_size)
        font_desc = ImageFont.truetype(FONT_PATH, font_desc_size)
        # 创建背景图层
        background = Image.new(mode="RGB", size=(width, height), color=(255, 255, 255))
        # 头像及预览图大小
        user_head_width = int(height * 5 / 6)
        thumb_img_width = user_head_width
        # 根据头像计算标准间距
        spacing_width = int((height - user_head_width) / 2)
        # 绘制背景框
        ImageDraw.Draw(background).rounded_rectangle(
            xy=(
                int(spacing_width / 4), int(spacing_width / 4),
                int(width - spacing_width / 4), int(height - spacing_width / 4)
            ),
            radius=int(height / 12),
            fill=(228, 250, 255)
        )
        # 读取头像
        if user_head.error:
            user_head_img = Image.new(mode="RGBA", size=(user_head_width, user_head_width), color=(127, 127, 127))
        else:
            with BytesIO(user_head.result) as bf:
                user_head_img: Image.Image = Image.open(bf)
                user_head_img.load()
            user_head_img = user_head_img.resize((user_head_width, user_head_width))
            user_head_img = user_head_img.convert(mode="RGBA")
        # 新建头像蒙版
        user_head_mask = Image.new(mode="RGBA", size=(user_head_width, user_head_width), color=(255, 255, 255, 0))
        user_head_mask_draw = ImageDraw.Draw(user_head_mask)
        user_head_mask_draw.ellipse((0, 0, user_head_width, user_head_width), fill=(0, 0, 0, 255))
        # 处理头像蒙版并粘贴
        background.paste(im=user_head_img, box=(spacing_width * 2, spacing_width), mask=user_head_mask)
        # 绘制用户名称
        ImageDraw.Draw(background).text(
            xy=(spacing_width * 4 + user_head_width, int(spacing_width * 1.5)),
            font=font_main,
            text=user.user_name,
            fill=(0, 0, 0))
        # uid
        name_text_w, name_text_h = font_main.getsize(user.user_name)
        uid_text = f'UID：{user.user_id}'
        uid_text_w, uid_text_h = font_desc.getsize(uid_text)
        ImageDraw.Draw(background).text(
            xy=(spacing_width * 4 + user_head_width, name_text_h + int(spacing_width * 1.75)),
            font=font_desc,
            text=uid_text,
            fill=(37, 143, 184))
        # 投稿作品数
        count_text = f'插画投稿数：{user.user_illust_count}'
        count_text_w, count_text_h = font_desc.getsize(count_text)
        ImageDraw.Draw(background).text(
            xy=(spacing_width * 4 + user_head_width, name_text_h + uid_text_h + int(spacing_width * 2.25)),
            font=font_desc,
            text=count_text,
            fill=(37, 143, 184))
        # 绘制用户简介
        # 按长度切分文本
        desc_text = TextUtils(text=user.user_desc).split_multiline(width=int(height * 1.5), font=font_desc)
        ImageDraw.Draw(background).multiline_text(
            xy=(spacing_width * 4 + user_head_width,
                name_text_h + uid_text_h + count_text_h + int(spacing_width * 2.75)),
            font=font_desc,
            text=desc_text,
            fill=(0, 0, 0))
        # 检查缩略图加载情况
        _user_illusts_thumb = [x for x in user_illusts_thumb if x.success()]
        # 一般页面只有四张预览图 这里也只贴四张
        for i in range(4):
            try:
                # 正常获取的预览图
                thumb_img_bytes = _user_illusts_thumb.pop(0)
                with BytesIO(thumb_img_bytes.result) as bf:
                    thumb_img: Image.Image = Image.open(bf)
                    thumb_img.load()
                thumb_img = thumb_img.resize((thumb_img_width, thumb_img_width))
                thumb_img = thumb_img.convert(mode="RGB")
            except IndexError:
                # 获取失败或小说等作品没有预览图
                thumb_img = Image.new(mode="RGB", size=(thumb_img_width, thumb_img_width), color=(127, 127, 127))
            # 预览图外边框
            ImageDraw.Draw(background).rectangle(
                xy=((spacing_width * 6 + user_head_width + int(height * 1.5)  # 前面文字的宽度
                     + i * (thumb_img_width + spacing_width)  # 根据缩略图序列增加的位置宽度
                     - int(thumb_img_width / 80),  # 边框预留的宽度
                     spacing_width - int(thumb_img_width / 80)),  # 高度及边框预留宽度
                    (spacing_width * 6 + user_head_width + int(height * 1.5)
                     + i * (thumb_img_width + spacing_width) + thumb_img_width
                     + int(thumb_img_width / 96),
                     spacing_width + thumb_img_width + int(thumb_img_width / 96))),
                fill=(224, 224, 224),
                width=0
            )
            # 依次粘贴预览图
            background.paste(
                im=thumb_img,
                box=(spacing_width * 6 + user_head_width + int(height * 1.5) + i * (thumb_img_width + spacing_width),
                     spacing_width))

        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _handle)
    return result


async def generate_user_searching_img(nick: str, *, width: int = 1600) -> Result.TextResult:
    search_result = await search_pixiv_user(nick=nick)
    if search_result.error:
        return Result.TextResult(error=True, info=search_result.info, result='')

    result_list = search_result.result[:CARD_NUM] if len(search_result.result) > CARD_NUM else search_result.result
    tasks = [_generate_user_card(user=x, width=width) for x in result_list]
    cards_result_list = await ProcessUtils.fragment_process(tasks=tasks, log_flag='PixivUserSearchingGenImg')
    cards_result_list = [x for x in cards_result_list if not isinstance(x, Exception)]

    def _handle() -> str:
        card_height = int(width / CARD_RATIO)
        # 根据卡片计算标准间距
        spacing_width = int(card_height / 12)
        # 字体
        font_title_size = int(card_height / 6)
        font_title = ImageFont.truetype(FONT_PATH, font_title_size)
        # 标题
        title_text = f'Pixiv User Search：{nick}'
        title_text_w, title_text_h = font_title.getsize_multiline(title_text)
        # 整体图片高度
        height = (card_height + spacing_width) * len(cards_result_list) + title_text_h + 3 * spacing_width
        # 创建背景图层
        background = Image.new(mode="RGB", size=(width + spacing_width * 2, height), color=(255, 255, 255))
        # 绘制标题
        ImageDraw.Draw(background).text(
            xy=(spacing_width * 2, spacing_width),
            font=font_title,
            text=title_text,
            fill=(37, 143, 184)
        )
        # 依次粘贴各结果卡片
        for index, card in enumerate(cards_result_list):
            background.paste(
                im=card,
                box=(spacing_width, spacing_width * 2 + title_text_h + (card_height + spacing_width) * index)
            )

        # 生成结果图片路径
        img_path = os.path.abspath(
            os.path.join(SEARCHED_FOLDER_PATH, f"search_{nick}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"))
        # 输出图片
        background.save(img_path, 'JPEG')
        return img_path

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _handle)
        return Result.TextResult(error=False, info='Success', result=result)
    except Exception as e:
        return Result.TextResult(error=True, info=repr(e), result='')


__all__ = [
    'search_pixiv_user',
    'generate_user_searching_img'
]
