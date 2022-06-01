"""
@Author         : Ailitonia
@Date           : 2021/08/27 0:48
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 签到素材合成工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from nonebot.log import logger
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.service.gocqhttp_guild_patch import GuildMessageEvent
from omega_miya.database import InternalPixiv
from omega_miya.database.schemas.pixiv_artwork import PixivArtworkModel
from omega_miya.local_resource import TmpResource
from omega_miya.web_resource import HttpFetcher
from omega_miya.web_resource.pixiv import PixivArtwork
from omega_miya.utils.process_utils import semaphore_gather, run_sync, run_async_catching_exception
from omega_miya.utils.text_utils import AdvanceTextUtils
from omega_miya.utils.qq_tools import get_user_head_img_url
from omega_miya.utils.apscheduler import scheduler

from .config import sign_in_config, sign_local_resource_config
from .fortune import get_fortune


@run_async_catching_exception
async def _prepare_signin_image() -> None:
    """预缓存签到头图资源, 使用 Pixiv 图库内容"""
    logger.debug(f'SignIn Utils | Started preparing signin image')
    # 获取图片信息并下载图片
    artwork_result = await InternalPixiv.random(num=200, nsfw_tag=0, ratio=1)

    tasks = [PixivArtwork(pid=artwork.pid).get_page_file() for artwork in artwork_result]
    pre_download_result = await semaphore_gather(tasks=tasks, semaphore_num=20)

    success_count = 0
    failed_count = 0
    for result in pre_download_result:
        if isinstance(result, BaseException):
            failed_count += 1
        else:
            success_count += 1
    logger.info(f'SignIn Utils | Preparing signin image completed with {success_count} success, {failed_count} failed')


if sign_in_config.signin_enable_preparing_scheduler:
    """下载签到图片的定时任务"""
    scheduler.add_job(
        _prepare_signin_image,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        hour='*/4',
        minute=7,
        second=13,
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='prepare_signin_image',
        coalesce=True,
        misfire_grace_time=120
    )


async def _get_signin_top_image() -> tuple[PixivArtworkModel, TmpResource]:
    """获取一张生成签到卡片用的头图"""
    random_artworks = await InternalPixiv.random(num=5, nsfw_tag=0, ratio=1)
    # 因为图库中部分图片可能因为作者删稿失效, 所以要多随机几个备选
    for random_artwork in random_artworks:
        artwork_file = await run_async_catching_exception(PixivArtwork(pid=random_artwork.pid).get_page_file)()
        if not isinstance(artwork_file, Exception):
            return random_artwork, artwork_file
    raise RuntimeError(f'all attempts to fetch artwork resources have failed')


@run_async_catching_exception
async def get_head_image(bot: Bot, event: MessageEvent) -> TmpResource:
    """获取用户头像 url"""
    if isinstance(event, GuildMessageEvent):
        gocq_bot = GoCqhttpBot(bot=bot)
        profile = await gocq_bot.get_guild_member_profile(guild_id=event.guild_id, user_id=event.user_id)
        head_image_url = profile.avatar_url
    else:
        head_image_url = get_user_head_img_url(user_id=event.user_id)

    image_name = HttpFetcher.hash_url_file_name('signin-head-image', url=head_image_url)
    image_file = sign_local_resource_config.default_save_folder('head_image', image_name)
    await HttpFetcher().download_file(url=head_image_url, file=image_file)
    return image_file


def _get_level(friendship: float) -> tuple[int, int, int]:
    """根据好感度获取等级及当前等级好感度

    :param friendship: 总好感度
    :return: 等级, 当前等级好感度, 当前等级好感度上限
    """
    if friendship <= 0:
        return 0, 0, 1
    elif friendship < 10000:
        return 1, int(friendship), 10000
    elif friendship < 36000:
        return 2, int(friendship - 10000), 26000
    elif friendship < 78000:
        return 3, int(friendship - 36000), 42000
    elif friendship < 136000:
        return 4, int(friendship - 78000), 58000
    elif friendship < 210000:
        return 5, int(friendship - 136000), 74000
    elif friendship < 300000:
        return 6, int(friendship - 210000), 90000
    elif friendship < 406000:
        return 7, int(friendship - 300000), 106000
    else:
        return 8, int(friendship - 406000), 122000


def _get_level_color(
        level: int,
        *,
        default_color: tuple[int, int, int] = (136, 136, 136)
) -> tuple[int, int, int]:
    """根据等级获取相应等级颜色

    :param level: 等级
    :param default_color: 默认无等级颜色
    :return: RGB 颜色 (R, G, B)
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
    return level_color.get(level, default_color)


async def get_hitokoto(*, c: Optional[str] = None) -> str:
    """获取一言"""
    url = 'https://v1.hitokoto.cn'
    params = {
        'encode': 'json',
        'charset': 'utf-8'
    }
    if c is not None:
        params.update({'c': c})

    headers = HttpFetcher.get_default_headers()
    headers.update({'accept': 'application/json'})

    hitokoto_result = await HttpFetcher(headers=headers).get_json_dict(url=url, params=params)

    text = f'{hitokoto_result.result.get("hitokoto")}\n——《{hitokoto_result.result.get("from")}》'
    if hitokoto_result.result.get("from_who"):
        text += f' {hitokoto_result.result.get("from_who")}'
    return text


@run_async_catching_exception
async def generate_signin_card(
        user_id: int,
        user_text: str,
        fav: float,
        *,
        width: int = 1024,
        fortune_do: bool = True,
        head_img: TmpResource | None = None) -> TmpResource:
    """生成签到卡片

    :param user_id: 用户id
    :param user_text: 头部自定义文本
    :param fav: 用户好感度 用户计算等级
    :param width: 生成图片宽度 自适应排版
    :param fortune_do: 是否绘制老黄历当日宜与不宜
    :param head_img: 绘制用户头像文件 (如有)
    :return: 生成图片地址
    """
    # 获取头图
    signin_top_img_data, signin_top_img_file = await _get_signin_top_image()

    # 头图作品来源
    top_img_origin_text = f'Pixiv | {signin_top_img_data.pid} | @{signin_top_img_data.uname}'

    def _handle_signin_card() -> bytes:
        """签到卡片绘制"""
        # 生成用户当天老黄历
        user_fortune = get_fortune(user_id=user_id)

        # 加载头图
        draw_top_img: Image.Image = Image.open(signin_top_img_file.resolve_path)
        # 调整头图宽度
        top_img_height = int(width * draw_top_img.height / draw_top_img.width)
        draw_top_img = draw_top_img.resize((width, top_img_height))

        # 字体
        bd_font_path = sign_local_resource_config.default_bold_font.resolve_path
        bd_font = ImageFont.truetype(bd_font_path, width // 10)
        bd_title_font = ImageFont.truetype(bd_font_path, width // 12)
        bd_text_font = ImageFont.truetype(bd_font_path, width // 18)

        main_font_path = sign_local_resource_config.default_font.resolve_path
        text_font = ImageFont.truetype(main_font_path, width // 28)

        level_font_path = sign_local_resource_config.default_level_font.resolve_path
        level_font = ImageFont.truetype(level_font_path, width // 20)

        bottom_font_path = sign_local_resource_config.default_footer_font.resolve_path
        bottom_text_font = ImageFont.truetype(bottom_font_path, width // 40)
        remark_text_font = ImageFont.truetype(bottom_font_path, width // 54)

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
        level = _get_level(friendship=fav)
        level_text = f'Level {level[0]}'
        level_text_width, level_text_height = level_font.getsize(level_text)
        fav_text = f'{level[1]}/{level[2]}'
        fav_rat = level[1] / level[2] if level[1] < level[2] else 1
        fav_text_width, fav_text_height = text_font.getsize(fav_text)

        # 日期
        date_text = datetime.now().strftime('%m/%d')
        # 预处理用户文本 包括昵称、好感度、积分
        _user_text_img = AdvanceTextUtils.parse_from_str(text=user_text).covert_pil_image_ignore_image_seg(
            image_size=(width - int(width * 0.125), width), font=text_font, font_fill=(128, 128, 128), spacing=1
        )

        user_text_width, user_text_height = _user_text_img.size
        # 今日运势
        fortune_text_width, fortune_text_height = bd_text_font.getsize(user_fortune.text)
        fortune_star_width, fortune_star_height = text_font.getsize(user_fortune.star)
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

        if head_img is not None:
            height += int(0.03125 * width)

        # 生成背景
        background = Image.new(
            mode="RGB",
            size=(width, height),
            color=(255, 255, 255))

        # 开始往背景上绘制各个元素
        # 以下排列从上到下绘制 请勿变换顺序 否则导致位置错乱
        background.paste(draw_top_img, box=(0, 0))  # 背景

        # 在背景右下角绘制图片来源
        ImageDraw.Draw(background).text(xy=(width - int(width * 0.00625), top_img_height),
                                        text=top_img_origin_text, font=remark_text_font,
                                        align='right', anchor='rd',
                                        stroke_width=1,
                                        stroke_fill=(128, 128, 128),
                                        fill=(224, 224, 224))  # 图片来源

        if head_img is not None:
            # 头像要占一定高度
            top_img_height += int(0.03125 * width)
            head_image: Image.Image = Image.open(head_img.resolve_path)
            # 确定头像高度
            head_image_width = int(width / 5)
            head_image = head_image.resize((head_image_width, head_image_width))
            # 头像外框 生成圆角矩形
            ImageDraw.Draw(background).rounded_rectangle(
                xy=((int(width * 0.0625 - head_image_width / 20),
                     (top_img_height - int(head_image_width * 21 / 20 - 0.03125 * width))),
                    (int(width * 0.0625 + head_image_width * 21 / 20),
                     (top_img_height + int(head_image_width / 20 + 0.03125 * width)))
                    ),
                radius=(width // 100),
                fill=(255, 255, 255)
            )
            # 粘贴头像
            background.paste(head_image,
                             box=(int(width * 0.0625), (top_img_height - int(head_image_width - 0.03125 * width))))

        this_height = top_img_height + int(0.0625 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=top_text, font=bd_font, align='left', anchor='lt',
                                        fill=(0, 0, 0))  # 打招呼

        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text=date_text, font=bd_title_font, align='right', anchor='rt',
                                        fill=_get_level_color(level=level[0]))  # 日期

        this_height += top_text_height

        # 昵称、好感度、积分
        background.paste(im=_user_text_img, box=(int(width * 0.0625), this_height), mask=_user_text_img)

        this_height += user_text_height + int(0.046875 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.065), this_height),
                                        text=level_text, font=level_font, align='left', anchor='lt',
                                        fill=_get_level_color(level=level[0]))  # 等级

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
            fill=_get_level_color(level=level[0]), width=int(0.03125 * width))  # 经验条内

        this_height += fortune_star_height + int(0.015625 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=f'今日运势: {user_fortune.text}', font=bd_text_font,
                                        align='left', anchor='lt', fill=(0, 0, 0))  # 今日运势

        this_height += fortune_text_height
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=user_fortune.star, font=text_font, align='left', anchor='lt',
                                        fill=(128, 128, 128))  # 运势星星

        if fortune_do:
            this_height += fortune_star_height + int(0.03125 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=f'宜', font=bd_text_font, align='left', anchor='lt',
                                            fill=(0, 0, 0))  # 宜

            this_height += fortune_text_height
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=user_fortune.good_do_st, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日宜1

            this_height += fortune_star_height  # 反正这两字体都一样大
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=user_fortune.good_do_nd, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日宜2

            this_height += fortune_star_height + int(0.03125 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=f'不宜', font=bd_text_font, align='left', anchor='lt',
                                            fill=(0, 0, 0))  # 不宜

            this_height += fortune_text_height
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=user_fortune.bad_do_st, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日不宜1

            this_height += fortune_star_height
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=user_fortune.bad_do_nd, font=text_font, align='left', anchor='lt',
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

        # 提取生成图的内容
        with BytesIO() as bf:
            background.save(bf, 'JPEG')
            content = bf.getvalue()
        return content

    if fortune_do:
        name_prefix = 'fortune_sign_in'
    else:
        name_prefix = 'fortune'
    file_name = f'{name_prefix}_card_{user_id}_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.jpg'
    save_file = sign_local_resource_config.default_save_folder(name_prefix, file_name)
    file_content = await run_sync(_handle_signin_card)()
    async with save_file.async_open('wb') as af:
        await af.write(file_content)
    return save_file


__all__ = [
    'scheduler',
    'get_head_image',
    'get_hitokoto',
    'generate_signin_card'
]
