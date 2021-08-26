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
import numpy
import asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from nonebot import get_driver, require, logger
from omega_miya.database import DBPixivillust, Result
from omega_miya.utils.pixiv_utils import PixivIllust
from omega_miya.utils.omega_plugin_utils import HttpFetcher, ProcessUtils
from .fortune import get_fortune


global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
RESOURCES_PATH = global_config.resources_path_
SIGN_IN_PIC_PATH = os.path.abspath(os.path.join(TMP_PATH, 'sign_in_pic'))
SIGN_IN_CARD_PATH = os.path.abspath(os.path.join(TMP_PATH, 'sign_in_card'))


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
    pic_list_result = await DBPixivillust.rand_illust(num=40, nsfw_tag=0, ratio=1)
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


# 启用下载签到图片的定时任务
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
    misfire_grace_time=30
)


async def __getting_reand_sign_in_pic() -> Result.TextResult:
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
    rand_file = random.choice(pic_file_list)
    file_path = os.path.abspath(os.path.join(SIGN_IN_PIC_PATH, rand_file))
    return Result.TextResult(error=False, info='Success', result=file_path)


async def generate_sign_in_card(user_id: int, user_text: str, *, width: int = 1024) -> Result.TextResult:
    # 获取头图
    sign_pic_path_result = await __getting_reand_sign_in_pic()
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
        top_img_height = width * draw_top_img.height // draw_top_img.width
        draw_top_img = draw_top_img.resize((width, top_img_height))

        # 字体
        bd_font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', 'SourceHanSans_Heavy.otf'))
        bd_font = ImageFont.truetype(bd_font_path, width // 10)
        bd_title_font = ImageFont.truetype(bd_font_path, width // 12)
        bd_text_font = ImageFont.truetype(bd_font_path, width // 18)

        main_font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', 'SourceHanSans_Regular.otf'))
        text_font = ImageFont.truetype(main_font_path, width // 28)

        bottom_font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', 'fzzxhk.ttf'))
        bottom_text_font = ImageFont.truetype(bottom_font_path, width // 40)

        # 打招呼
        if 0 <= datetime.now().hour < 11:
            top_text = '早上好'
        elif 11 <= datetime.now().hour < 14:
            top_text = '中午好'
        elif 14 <= datetime.now().hour < 17:
            top_text = '下午好'
        elif 17 <= datetime.now().hour < 22:
            top_text = '晚上好'
        else:
            top_text = '晚安'
        top_text_width, top_text_height = bd_font.getsize(top_text)

        # 日期
        date_text = datetime.now().strftime('%m/%d')

        # 昵称、好感度、积分
        user_text_width, user_text_height = text_font.getsize_multiline(user_text)
        # 今日运势
        fortune_text_width, fortune_text_height = bd_text_font.getsize(fortune_text)
        fortune_star_width, fortune_star_height = text_font.getsize(fortune_star)
        # 底部文字
        bottom_text_width, bottom_text_height = bottom_text_font.getsize(user_text)

        # 总高度
        height = (top_img_height + top_text_height + user_text_height +
                  fortune_text_height * 3 + fortune_star_height * 5 + bottom_text_height * 4 +
                  int(0.21875 * width))
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
                                        fill=(tuple(numpy.random.randint(0, 255, size=3))))  # 日期

        this_height += top_text_height
        ImageDraw.Draw(background).multiline_text(xy=(int(width * 0.0625), this_height),
                                                  text=user_text, font=text_font, align='left',
                                                  fill=(128, 128, 128))  # 昵称、好感度、积分

        this_height += user_text_height + int(0.0625 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=f'今日运势: {fortune_text}', font=bd_text_font,
                                        align='left', anchor='lt', fill=(0, 0, 0))  # 今日运势

        this_height += fortune_text_height
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=fortune_star, font=text_font, align='left', anchor='lt',
                                        fill=(128, 128, 128))  # 运势星星

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
        save_path = os.path.abspath(os.path.join(
            SIGN_IN_CARD_PATH, f"sign_card_{user_id}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"))
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
    'generate_sign_in_card'
]
