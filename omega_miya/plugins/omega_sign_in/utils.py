"""
@Author         : Ailitonia
@Date           : 2021/08/27 0:48
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 签到素材合成工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import random
import asyncio
import aiofiles.os
from typing import Optional
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from nonebot import get_driver, require, logger
from omega_miya.database import DBPixivillust, Result
from omega_miya.utils.pixiv_utils import PixivIllust
from omega_miya.utils.omega_plugin_utils import HttpFetcher, ProcessUtils, TextUtils
from .config import Config
from .fortune import get_fortune


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
TMP_PATH = global_config.tmp_path_
RESOURCES_PATH = global_config.resources_path_
SIGN_IN_PIC_PATH = os.path.abspath(os.path.join(TMP_PATH, 'sign_in_pic'))
SIGN_IN_CARD_PATH = os.path.abspath(os.path.join(TMP_PATH, 'sign_in_card'))
ENABLE_PIC_PREPARING_SCHEDULER = plugin_config.enable_pic_preparing_scheduler
CACHE_PIC_LIMIT = plugin_config.cache_pic_limit


async def __pre_download_sign_in_pic(pid: int, *, pic_size: str = 'regular') -> Result.IntResult:
    illust_info_result = await PixivIllust(pid=pid).get_illust_data()
    if illust_info_result.error:
        return Result.IntResult(error=True, info=illust_info_result.info, result=-1)
    pic_url = illust_info_result.result.get('illust_pages', {}).get(0, {}).get(pic_size)
    if not pic_url:
        return Result.IntResult(error=True, info='Small illust pages url not found', result=-1)
    fetcher = HttpFetcher(timeout=30, attempt_limit=2, flag='pre_download_sign_in_pic', headers=PixivIllust.HEADERS)
    download_result = await fetcher.download_file(url=pic_url, path=SIGN_IN_PIC_PATH)
    if download_result.error:
        return Result.IntResult(error=True, info=download_result.info, result=-1)
    else:
        return Result.IntResult(error=False, info='Success', result=0)


async def __prepare_sign_in_pic() -> Result.TextResult:
    # 检查当前缓存目录里面的图片是不是超出数量限制 是的话就删除超出的部分
    if not os.path.exists(SIGN_IN_PIC_PATH):
        os.makedirs(SIGN_IN_PIC_PATH)
    pic_file_list = os.listdir(SIGN_IN_PIC_PATH)
    if len(pic_file_list) > CACHE_PIC_LIMIT:
        del_pic_file_list = random.sample(pic_file_list, k=(len(pic_file_list) - CACHE_PIC_LIMIT))
        for pic_file in del_pic_file_list:
            await aiofiles.os.remove(os.path.abspath(os.path.join(SIGN_IN_PIC_PATH, pic_file)))
        logger.info(f'Preparing sign in pic processing, '
                    f'removed pic "{"/".join(del_pic_file_list)}" exceed the limit of cache')

    # 获取图片信息并下载图片
    pic_list_result = await DBPixivillust.rand_illust(num=100, nsfw_tag=0, ratio=1)
    if pic_list_result.error or not pic_list_result.result:
        logger.error(f'Preparing sign in pic failed, DB Error or not result, result: {pic_list_result}')
        return Result.TextResult(error=True, info=pic_list_result.info, result='DB Error or not result')

    tasks = [__pre_download_sign_in_pic(pid=pid) for pid in pic_list_result.result]
    pre_download_result = await ProcessUtils.fragment_process(
        tasks=tasks, fragment_size=20, log_flag='pre_download_sign_in_pic')

    success_count = 0
    failed_count = 0
    for result in pre_download_result:
        if result.success():
            success_count += 1
        else:
            failed_count += 1
    result_text = f'Completed with {success_count} Success, {failed_count} Failed'
    logger.info(f'Preparing sign in pic completed, {result_text}')
    return Result.TextResult(error=True, info=f'Completed', result=result_text)


# 下载签到图片的定时任务
if ENABLE_PIC_PREPARING_SCHEDULER:
    scheduler = require("nonebot_plugin_apscheduler").scheduler
    scheduler.add_job(
        __prepare_sign_in_pic,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        hour='*/6',
        # minute=None,
        # second=None,
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='prepare_sign_in_pic',
        coalesce=True,
        misfire_grace_time=120
    )


async def __get_reand_sign_in_pic() -> Result.TextResult:
    try_count = 0
    if not os.path.exists(SIGN_IN_PIC_PATH):
        os.makedirs(SIGN_IN_PIC_PATH)
    pic_file_list = os.listdir(SIGN_IN_PIC_PATH)
    while not pic_file_list and try_count < 2:
        await __prepare_sign_in_pic()
        pic_file_list = os.listdir(SIGN_IN_PIC_PATH)
        try_count += 1
    if not pic_file_list:
        return Result.TextResult(error=True, info='Can not pre-download sign in pic', result='')

    # 每次重置随机种子
    time_stamp = datetime.now().timestamp()
    random_seed_str = f'{"/".join(random.sample(str(time_stamp), k=7))}//{time_stamp}'
    random.seed(random_seed_str)
    rand_file = random.choice(pic_file_list)
    file_path = os.path.abspath(os.path.join(SIGN_IN_PIC_PATH, rand_file))
    return Result.TextResult(error=False, info='Success', result=file_path)


def __get_level(favorability: float) -> tuple[int, int, int]:
    """
    根据好感度获取等级及当前等级好感度
    :param favorability: 总好感度
    :return: (等级, 当前等级好感度, 当前等级好感度上限)
    """
    if favorability <= 0:
        return 0, 0, 1
    elif favorability < 10000:
        return 1, int(favorability), 10000
    elif favorability < 36000:
        return 2, int(favorability - 10000), 26000
    elif favorability < 78000:
        return 3, int(favorability - 36000), 42000
    elif favorability < 136000:
        return 4, int(favorability - 78000), 58000
    elif favorability < 210000:
        return 5, int(favorability - 136000), 74000
    elif favorability < 300000:
        return 6, int(favorability - 210000), 90000
    elif favorability < 406000:
        return 7, int(favorability - 300000), 106000
    else:
        return 8, int(favorability - 406000), 122000


def __get_level_color(level: int) -> tuple[int, int, int]:
    """
    根据等级获取相应等级颜色
    :param level: 等级
    :return: (int, int, int): RGB 颜色
    """
    level_color: dict[int, tuple[int, int, int]] = {
        0: (136, 136, 136),
        1: (102, 102, 102),
        2: (153, 204, 153),
        3: (221, 204, 136),
        4: (255, 204, 51),
        5: (255, 204, 204),
        6: (247, 119, 127),
        7: (102, 204, 255),
        8: (175, 136, 250),
    }
    return level_color.get(level, (136, 136, 136))


async def get_hitokoto(*, c: Optional[str] = None) -> Result.TextResult:
    """获取一言"""
    url = 'https://v1.hitokoto.cn'
    params = {
        'encode': 'json',
        'charset': 'utf-8'
    }
    if c is not None:
        params.update({'c': c})

    headers = HttpFetcher.DEFAULT_HEADERS.update({'accept': 'application/json'})
    hitokoto_result = await HttpFetcher(flag='sign_hitokoto', headers=headers).get_json(url=url, params=params)
    if hitokoto_result.error:
        return Result.TextResult(error=True, info=hitokoto_result.info, result='')

    text = f'{hitokoto_result.result.get("hitokoto")}\n——《{hitokoto_result.result.get("from")}》'
    if hitokoto_result.result.get("from_who"):
        text += f' {hitokoto_result.result.get("from_who")}'
    return Result.TextResult(error=False, info='Success', result=text)


async def generate_sign_in_card(
        user_id: int, user_text: str, fav: float, *, width: int = 1024, fortune_do: bool = True) -> Result.TextResult:
    """
    生成卡片
    :param user_id: 用户id
    :param user_text: 头部自定义文本
    :param fav: 用户好感度 用户计算等级
    :param width: 生成图片宽度 自适应排版
    :param fortune_do: 是否绘制老黄历当日宜与不宜
    :return: 生成图片地址
    """
    # 获取头图
    sign_pic_path_result = await __get_reand_sign_in_pic()
    if sign_pic_path_result.error:
        return Result.TextResult(error=True, info=sign_pic_path_result.info, result='')
    sign_pic_path = sign_pic_path_result.result

    def __handle():
        # 生成用户当天老黄历
        user_fortune = get_fortune(user_id=user_id)
        fortune_star = user_fortune.get('fortune_star')
        fortune_text = user_fortune.get('fortune_text')
        fortune_do_1 = user_fortune.get('do_1')
        fortune_do_2 = user_fortune.get('do_2')
        fortune_not_do_1 = user_fortune.get('not_do_1')
        fortune_not_do_2 = user_fortune.get('not_do_2')

        # 加载头图
        draw_top_img: Image.Image = Image.open(sign_pic_path)
        # 调整头图宽度
        top_img_height = int(width * draw_top_img.height / draw_top_img.width)
        draw_top_img = draw_top_img.resize((width, top_img_height))

        # 字体
        bd_font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', 'SourceHanSans_Heavy.otf'))
        bd_font = ImageFont.truetype(bd_font_path, width // 10)
        bd_title_font = ImageFont.truetype(bd_font_path, width // 12)
        bd_text_font = ImageFont.truetype(bd_font_path, width // 18)

        main_font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', 'SourceHanSans_Regular.otf'))
        text_font = ImageFont.truetype(main_font_path, width // 28)

        level_font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', 'pixel.ttf'))
        level_font = ImageFont.truetype(level_font_path, width // 20)

        bottom_font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', 'fzzxhk.ttf'))
        bottom_text_font = ImageFont.truetype(bottom_font_path, width // 40)

        # 打招呼
        if 4 <= datetime.now().hour < 11:
            top_text = '早上好'
        elif 11 <= datetime.now().hour < 14:
            top_text = '中午好'
        elif 14 <= datetime.now().hour < 19:
            top_text = '下午好'
        elif 19 <= datetime.now().hour < 22:
            top_text = '晚上好'
        else:
            top_text = '晚安'
        top_text_width, top_text_height = bd_font.getsize(top_text)

        # 计算好感度等级条
        level = __get_level(favorability=fav)
        level_text = f'Level {level[0]}'
        level_text_width, level_text_height = level_font.getsize(level_text)
        fav_text = f'{level[1]}/{level[2]}'
        fav_rat = level[1] / level[2] if level[1] < level[2] else 1
        fav_text_width, fav_text_height = text_font.getsize(fav_text)

        # 日期
        date_text = datetime.now().strftime('%m/%d')
        # 昵称、好感度、积分
        # 首先要对文本进行分割
        user_text_ = TextUtils(text=user_text).split_multiline(width=(width - int(width * 0.125)), font=text_font)
        user_text_width, user_text_height = text_font.getsize_multiline(user_text_)
        # 今日运势
        fortune_text_width, fortune_text_height = bd_text_font.getsize(fortune_text)
        fortune_star_width, fortune_star_height = text_font.getsize(fortune_star)
        # 底部文字
        bottom_text_width, bottom_text_height = bottom_text_font.getsize(f'{"@@##" * 4}\n' * 4)

        # 总高度
        if fortune_do:
            height = (top_img_height + top_text_height + user_text_height + level_text_height +
                      fortune_text_height * 3 + fortune_star_height * 6 + bottom_text_height * 4 +
                      int(0.25 * width))
        else:
            height = (top_img_height + top_text_height + user_text_height + level_text_height +
                      fortune_text_height * 1 + fortune_star_height * 2 + bottom_text_height * 4 +
                      int(0.1875 * width))

        # 生成背景
        background = Image.new(
            mode="RGB",
            size=(width, height),
            color=(255, 255, 255))

        # 开始往背景上绘制各个元素
        # 以下排列从上到下绘制 请勿变换顺序 否则导致位置错乱
        background.paste(draw_top_img, box=(0, 0))  # 背景

        this_height = top_img_height + int(0.0625 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=top_text, font=bd_font, align='left', anchor='lt',
                                        fill=(0, 0, 0))  # 打招呼

        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text=date_text, font=bd_title_font, align='right', anchor='rt',
                                        fill=__get_level_color(level=level[0]))  # 日期

        this_height += top_text_height
        ImageDraw.Draw(background).multiline_text(xy=(int(width * 0.0625), this_height),
                                                  text=user_text_, font=text_font, align='left',
                                                  fill=(128, 128, 128))  # 昵称、好感度、积分

        this_height += user_text_height + int(0.046875 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.065), this_height),
                                        text=level_text, font=level_font, align='left', anchor='lt',
                                        fill=__get_level_color(level=level[0]))  # 等级

        this_height += level_text_height + int(0.03125 * width)
        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text=fav_text, font=text_font, align='right', anchor='rm',
                                        fill=(208, 208, 208))  # 经验条数值

        ImageDraw.Draw(background).line(xy=[(int(width * 0.0625), this_height),
                                            (width - int(width * 0.09375 + fav_text_width), this_height)],
                                        fill=(224, 224, 224), width=int(0.03125 * width))  # 经验条底

        ImageDraw.Draw(background).line(
            xy=[(int(width * 0.0625), this_height),
                (int(width * 0.0625 + (width * 0.84375 - fav_text_width) * fav_rat), this_height)],
            fill=__get_level_color(level=level[0]), width=int(0.03125 * width))  # 经验条内

        this_height += fortune_star_height + int(0.015625 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=f'今日运势: {fortune_text}', font=bd_text_font,
                                        align='left', anchor='lt', fill=(0, 0, 0))  # 今日运势

        this_height += fortune_text_height
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=fortune_star, font=text_font, align='left', anchor='lt',
                                        fill=(128, 128, 128))  # 运势星星

        if fortune_do:
            this_height += fortune_star_height + int(0.03125 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=f'宜', font=bd_text_font, align='left', anchor='lt',
                                            fill=(0, 0, 0))  # 宜

            this_height += fortune_text_height
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=fortune_do_1, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日宜1

            this_height += fortune_star_height  # 反正这两字体都一样大
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=fortune_do_2, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日宜2

            this_height += fortune_star_height + int(0.03125 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=f'不宜', font=bd_text_font, align='left', anchor='lt',
                                            fill=(0, 0, 0))  # 不宜

            this_height += fortune_text_height
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=fortune_not_do_1, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日不宜1

            this_height += fortune_star_height
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=fortune_not_do_2, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日不宜2

        this_height += fortune_star_height + bottom_text_height * 2
        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text='随机生成 请勿迷信', font=bottom_text_font, align='right', anchor='rt',
                                        fill=(128, 128, 128))

        this_height += bottom_text_height
        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text=f'Omega Miya @ {datetime.now().year}',
                                        font=bottom_text_font, align='right', anchor='rt',
                                        fill=(128, 128, 128))

        if not os.path.exists(SIGN_IN_CARD_PATH):
            os.makedirs(SIGN_IN_CARD_PATH)

        if fortune_do:
            name_prefix = 'fortune_sign_in'
        else:
            name_prefix = 'fortune'
        save_path = os.path.abspath(os.path.join(
            SIGN_IN_CARD_PATH, f"{name_prefix}_card_{user_id}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"))
        background.save(save_path, 'JPEG')
        return save_path

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, __handle)
        return Result.TextResult(error=False, info='Success', result=result)
    except Exception as e:
        return Result.TextResult(error=True, info=repr(e), result='')


__all__ = [
    'scheduler',
    'get_hitokoto',
    'generate_sign_in_card'
]
