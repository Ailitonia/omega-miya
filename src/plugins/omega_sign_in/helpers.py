"""
@Author         : Ailitonia
@Date           : 2023/7/8 23:43
@FileName       : helpers
@Project        : nonebot2_miya
@Description    : 签到工具类函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import hashlib
import random
import ujson as json
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO
from pydantic import BaseModel, parse_obj_as
from typing import Annotated, Literal, Optional

from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.typing import T_State
from nonebot.utils import run_sync

from src.database import begin_db_session
from src.database.internal.pixiv_artwork import PixivArtwork as PixivArtworkModel
from src.resource import TemporaryResource
from src.service import EntityInterface, MatcherInterface, OmegaMessageSegment, OmegaRequests
from src.service.omega_base.internal import OmegaPixivArtwork
from src.utils.image_utils import ImageUtils
from src.utils.pixiv_api import PixivArtwork

from .config import sign_in_config, sign_local_resource_config
from .exception import DuplicateException, FailedException


class Fortune(BaseModel):
    """求签结果"""
    star: str
    text: Literal['大凶', '末凶', '半凶', '小凶', '凶', '末小吉', '末吉', '半吉', '吉', '小吉', '中吉', '大吉']
    good_do_st: str
    good_do_nd: str
    bad_do_st: str
    bad_do_nd: str


class FortuneEvent(BaseModel):
    """老黄历宜和不宜内容"""
    name: str
    good: str
    bad: str

    def __eq__(self, other) -> bool:
        if isinstance(other, FortuneEvent):
            return self.name == other.name and self.good == other.good and self.bad == other.bad
        else:
            return False

    def __hash__(self) -> int:
        return hash(self.name + self.good + self.bad)


__FORTUNE_EVENT: list[FortuneEvent] = []
"""缓存求签事件"""


def _load_fortune_event(file: TemporaryResource) -> list[FortuneEvent]:
    """从文件读取求签事件"""
    if file.is_file:
        logger.debug(f'loading fortune event form {file}')
        with file.open('r', encoding='utf8') as f:
            fortune_event = json.loads(f.read())
        return parse_obj_as(list[FortuneEvent], fortune_event)
    else:
        return []


def _upgrade_fortune_event(*, enforce_origin: bool = False) -> None:
    """更新求签事件缓存

    :param enforce_origin: 强制使用原始资源解析事件
    """
    fortune_event = _load_fortune_event(file=sign_local_resource_config.default_fortune)

    if not enforce_origin and sign_local_resource_config.addition_fortune.is_file:
        addition_event = _load_fortune_event(file=sign_local_resource_config.addition_fortune)
        fortune_event.extend(addition_event)

    global __FORTUNE_EVENT
    __FORTUNE_EVENT = parse_obj_as(list[FortuneEvent], sorted(set(fortune_event), key=lambda x: x.name))


def get_fortune_event() -> list[FortuneEvent]:
    """获取所有求签事件"""
    if not __FORTUNE_EVENT:
        _upgrade_fortune_event()

    return sorted(set(__FORTUNE_EVENT), key=lambda x: x.name)


def random_fortune_event(num: int = 4) -> list[FortuneEvent]:
    """随机获取求签事件"""
    return random.sample(get_fortune_event(), k=num)


def get_fortune(user_id: str, *, date: datetime | None = None) -> Fortune:
    """根据 user_id 和当天日期生成老黄历"""
    if date is None:
        date_str = str(datetime.now().date())
    else:
        date_str = str(date.date())
    # 用 user_id 和日期生成随机种子
    random_seed_str = str([user_id, date_str])
    md5 = hashlib.md5()
    md5.update(random_seed_str.encode('utf-8'))
    random_seed = md5.hexdigest()
    random.seed(random_seed)
    # 今日运势
    # 生成运势随机数
    fortune_result = random.randint(1, 108)
    # 大吉・中吉・小吉・吉・半吉・末吉・末小吉・凶・小凶・半凶・末凶・大凶
    if fortune_result < 4:
        fortune_star = '☆' * 11
        fortune_text = '大凶'
    elif fortune_result < 9:
        fortune_star = '★' * 1 + '☆' * 10
        fortune_text = '末凶'
    elif fortune_result < 16:
        fortune_star = '★' * 2 + '☆' * 9
        fortune_text = '半凶'
    elif fortune_result < 25:
        fortune_star = '★' * 3 + '☆' * 8
        fortune_text = '小凶'
    elif fortune_result < 36:
        fortune_star = '★' * 4 + '☆' * 7
        fortune_text = '凶'
    elif fortune_result < 48:
        fortune_star = '★' * 5 + '☆' * 6
        fortune_text = '末小吉'
    elif fortune_result < 60:
        fortune_star = '★' * 6 + '☆' * 5
        fortune_text = '末吉'
    elif fortune_result < 72:
        fortune_star = '★' * 7 + '☆' * 4
        fortune_text = '半吉'
    elif fortune_result < 84:
        fortune_star = '★' * 8 + '☆' * 3
        fortune_text = '吉'
    elif fortune_result < 96:
        fortune_star = '★' * 9 + '☆' * 2
        fortune_text = '小吉'
    elif fortune_result < 102:
        fortune_star = '★' * 10 + '☆' * 1
        fortune_text = '中吉'
    else:
        fortune_star = '★' * 11
        fortune_text = '大吉'

    # 宜做和不宜做
    do_and_not = random_fortune_event(num=4)

    result = {
        'star': fortune_star,
        'text': fortune_text,
        'good_do_st': f"{do_and_not[0].name} —— {do_and_not[0].good}",
        'good_do_nd': f"{do_and_not[2].name} —— {do_and_not[2].good}",
        'bad_do_st': f"{do_and_not[1].name} —— {do_and_not[1].bad}",
        'bad_do_nd': f"{do_and_not[3].name} —— {do_and_not[3].bad}"
    }

    # 重置随机种子
    random.seed()

    return Fortune.parse_obj(result)


async def get_signin_top_image() -> tuple[PixivArtworkModel, TemporaryResource]:
    """获取一张生成签到卡片用的头图"""
    async with begin_db_session() as session:
        random_artworks = await OmegaPixivArtwork.random(session=session, num=5, nsfw_tag=0, ratio=1)

    # 因为图库中部分图片可能因为作者删稿失效, 所以要多随机几个备选
    for random_artwork in random_artworks:
        try:
            artwork_file = await PixivArtwork(pid=random_artwork.pid).get_page_file()
            return random_artwork, artwork_file
        except Exception as e:
            logger.warning(f'getting pixiv artwork(pid={random_artwork.pid}) failed, {e}')
            continue

    raise RuntimeError(f'all attempts to fetch artwork resources have failed')


async def get_profile_image(bot: Bot, event: Event) -> TemporaryResource:
    """获取用户头像"""
    async with begin_db_session() as session:
        entity_interface = EntityInterface(acquire_type='user')(bot=bot, event=event, session=session)
        url = await entity_interface.get_entity_profile_photo_url()

    image_name = OmegaRequests.hash_url_file_name('signin-head-image', url=url)
    image_file = sign_local_resource_config.default_save_folder('head_image', image_name)
    return await OmegaRequests().download(url=url, file=image_file)


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
    elif friendship < 528000:
        return 8, int(friendship - 406000), 122000
    elif friendship < 666000:
        return 9, int(friendship - 528000), 138000
    else:
        return 10, int(friendship - 666000), 154000


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
        3: (204, 204, 153),
        4: (255, 204, 153),
        5: (255, 204, 204),
        6: (247, 119, 127),
        7: (204, 102, 153),
        8: (204, 153, 255),
        9: (153, 153, 255),
        10: (102, 204, 255),
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

    headers = OmegaRequests.get_default_headers()
    headers.update({'accept': 'application/json'})

    hitokoto_response = await OmegaRequests(headers=headers).get(url=url, params=params)
    hitokoto_data = OmegaRequests.parse_content_json(response=hitokoto_response)

    text = f'{hitokoto_data.get("hitokoto")}\n——《{hitokoto_data.get("from")}》'
    if hitokoto_data.get("from_who"):
        text += f' {hitokoto_data.get("from_who")}'
    return text


async def generate_signin_card(
        user_id: str,
        user_text: str,
        friendship: float,
        top_img: tuple[PixivArtworkModel, TemporaryResource],
        *,
        width: int = 1024,
        draw_fortune: bool = True,
        head_img: TemporaryResource | None = None) -> TemporaryResource:
    """生成签到卡片

    :param user_id: 用户id
    :param user_text: 头部自定义文本
    :param friendship: 用户好感度, 用于计算用户等级
    :param top_img: 卡片头图
    :param width: 生成图片宽度 自适应排版
    :param draw_fortune: 是否绘制老黄历当日宜和不宜事件
    :param head_img: 绘制用户头像文件 (如有)
    :return: 生成图片地址
    """
    # 获取头图
    signin_top_img_data, signin_top_img_file = top_img
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
        top_text_width, top_text_height = ImageUtils.get_text_size(text=top_text, font=bd_font)

        # 计算好感度等级条
        level = _get_level(friendship=friendship)
        level_text = f'Level {level[0]}'
        level_text_width, level_text_height = ImageUtils.get_text_size(text=level_text, font=level_font)
        fs_text = f'{level[1]}/{level[2]}'
        fs_rat = level[1] / level[2] if level[1] < level[2] else 1
        fs_text_width, fs_text_height = ImageUtils.get_text_size(text=fs_text, font=text_font)

        # 日期
        date_text = datetime.now().strftime('%m/%d')
        # 预处理用户文本 包括昵称、好感度、积分
        user_text_ = ImageUtils.split_multiline_text(text=user_text, width=(width - int(width * 0.125)), font=text_font)
        user_text_width, user_text_height = ImageUtils.get_text_size(text=user_text_, font=text_font)

        # 今日运势
        fortune_text_width, fortune_text_height = ImageUtils.get_text_size(text=user_fortune.text, font=bd_text_font)
        fortune_star_width, fortune_star_height = ImageUtils.get_text_size(text=user_fortune.star, font=text_font)
        # 底部文字
        bottom_text_width, bottom_text_height = ImageUtils.get_text_size(text=f'{"@@##"*4}\n', font=bottom_text_font)

        # 总高度
        if draw_fortune:
            height = (top_img_height + top_text_height + user_text_height + level_text_height +
                      fortune_text_height * 3 + fortune_star_height * 6 + bottom_text_height * 6 +
                      int(0.41625 * width))
        else:
            height = (top_img_height + top_text_height + user_text_height + level_text_height +
                      fortune_text_height * 1 + fortune_star_height * 2 + bottom_text_height * 6 +
                      int(0.25125 * width))

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

        # 在头图右下角绘制图片来源
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
            background.paste(im=head_image,
                             box=(int(width * 0.0625), (top_img_height - int(head_image_width - 0.03125 * width))))

        this_height = top_img_height + int(0.0625 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=top_text, font=bd_font, align='left', anchor='lt',
                                        fill=(0, 0, 0))  # 打招呼

        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text=date_text, font=bd_title_font, align='right', anchor='rt',
                                        fill=_get_level_color(level=level[0]))  # 日期

        this_height += top_text_height + int(0.03125 * width)
        ImageDraw.Draw(background).multiline_text(xy=(int(width * 0.0625), this_height),
                                                  text=user_text_, font=text_font, align='left',
                                                  fill=(128, 128, 128))  # 昵称、好感度、积分

        this_height += user_text_height + int(0.0625 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.065), this_height),
                                        text=level_text, font=level_font, align='left', anchor='lt',
                                        fill=_get_level_color(level=level[0]))  # 等级

        this_height += level_text_height + int(0.03125 * width)
        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text=fs_text, font=text_font, align='right', anchor='rm',
                                        fill=(208, 208, 208))  # 经验条数值

        ImageDraw.Draw(background).line(xy=[(int(width * 0.0625), this_height),
                                            (width - int(width * 0.09375 + fs_text_width), this_height)],
                                        fill=(224, 224, 224), width=int(0.03125 * width))  # 经验条底

        ImageDraw.Draw(background).line(
            xy=[(int(width * 0.0625), this_height),
                (int(width * 0.0625 + (width * 0.84375 - fs_text_width) * fs_rat), this_height)],
            fill=_get_level_color(level=level[0]), width=int(0.03125 * width))  # 经验条内

        this_height += fortune_star_height + int(0.03125 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=f'今日运势: {user_fortune.text}', font=bd_text_font,
                                        align='left', anchor='lt', fill=(0, 0, 0))  # 今日运势

        this_height += fortune_text_height + int(0.02 * width)
        ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                        text=user_fortune.star, font=text_font, align='left', anchor='lt',
                                        fill=(128, 128, 128))  # 运势星星

        if draw_fortune:
            this_height += fortune_star_height + int(0.046875 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=f'宜', font=bd_text_font, align='left', anchor='lt',
                                            fill=(0, 0, 0))  # 宜

            this_height += fortune_text_height + int(0.02 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=user_fortune.good_do_st, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日宜1

            this_height += fortune_star_height + int(0.015625 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=user_fortune.good_do_nd, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日宜2

            this_height += fortune_star_height + int(0.046875 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=f'不宜', font=bd_text_font, align='left', anchor='lt',
                                            fill=(0, 0, 0))  # 不宜

            this_height += fortune_text_height + int(0.02 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=user_fortune.bad_do_st, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日不宜1

            this_height += fortune_star_height + int(0.015625 * width)
            ImageDraw.Draw(background).text(xy=(int(width * 0.0625), this_height),
                                            text=user_fortune.bad_do_nd, font=text_font, align='left', anchor='lt',
                                            fill=(128, 128, 128))  # 今日不宜2

        this_height += fortune_star_height + bottom_text_height * 3
        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text='随机生成 请勿迷信', font=bottom_text_font, align='right', anchor='rt',
                                        fill=(128, 128, 128))

        this_height += bottom_text_height + int(0.0125 * width)
        ImageDraw.Draw(background).text(xy=(width - int(width * 0.0625), this_height),
                                        text=f'Omega Miya @ {datetime.now().year}',
                                        font=bottom_text_font, align='right', anchor='rt',
                                        fill=(128, 128, 128))

        # 提取生成图的内容
        with BytesIO() as bf:
            background.save(bf, 'JPEG')
            content = bf.getvalue()
        return content

    file_name = f'sign_in_card_{user_id}_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.jpg'
    save_file = sign_local_resource_config.default_save_folder('sign_in', file_name)
    file_content = await run_sync(_handle_signin_card)()
    async with save_file.async_open('wb') as af:
        await af.write(file_content)
    return save_file


async def handle_generate_sign_in_card(
        bot: Bot,
        event: Event,
        state: T_State,
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface('user'))]
) -> None:
    """处理生成签到卡片"""
    matcher_interface = MatcherInterface()
    try:
        # 获取当前好感度信息
        await entity_interface.entity.add_ignore_exists()
        friendship = await entity_interface.entity.query_friendship()

        # 先检查签到状态
        check_result = await entity_interface.entity.check_today_sign_in()
        if check_result:
            raise DuplicateException('重复签到')

        # 获取卡片头图
        try:
            top_img = await get_signin_top_image()
        except Exception as e:
            raise FailedException(f'获取签到卡片头图失败, {e}') from e

        # 尝试签到
        try:
            await entity_interface.entity.sign_in()
        except Exception as e:
            raise FailedException(f'签到失败, {e}') from e

        # 查询连续签到时间
        continuous_days = await entity_interface.entity.query_continuous_sign_in_day()

        # 尝试为用户增加好感度
        # 根据连签日期设置不同增幅
        if continuous_days < 7:
            base_friendship_inc = int(30 * (1 + random.gauss(0.25, 0.25)))
            currency_inc = 1 * sign_in_config.signin_base_currency
        elif continuous_days < 30:
            base_friendship_inc = int(70 * (1 + random.gauss(0.35, 0.2)))
            currency_inc = 3 * sign_in_config.signin_base_currency
        else:
            base_friendship_inc = int(110 * (1 + random.gauss(0.45, 0.15)))
            currency_inc = 5 * sign_in_config.signin_base_currency

        # 将能量值兑换为好感度
        friendship_inc = friendship.energy * sign_in_config.signin_ef_exchange_rate + base_friendship_inc
        # 增加后的好感度及硬币
        friendship_now = friendship.friendship + friendship_inc
        currency_now = friendship.currency + currency_inc

        try:
            await entity_interface.entity.change_friendship(
                friendship=friendship_inc, currency=currency_inc, energy=(- friendship.energy)
            )
        except Exception as e:
            raise FailedException(f'增加好感度失败, {e}') from e

        nick_name = matcher_interface.get_event_handler().get_user_nickname()
        user_text = f'@{nick_name} {sign_in_config.signin_friendship_alias}+{int(base_friendship_inc)} ' \
                    f'{sign_in_config.signin_currency_alias}+{int(currency_inc)}\n' \
                    f'已连续签到{continuous_days}天\n' \
                    f'已将{int(friendship.energy)}{sign_in_config.signin_energy_alias}兑换为' \
                    f'{int(friendship.energy * sign_in_config.signin_ef_exchange_rate)}' \
                    f'{sign_in_config.signin_friendship_alias}\n' \
                    f'当前{sign_in_config.signin_friendship_alias}: {int(friendship_now)}\n' \
                    f'当前{sign_in_config.signin_currency_alias}: {int(currency_now)}'

        await entity_interface.entity.commit_session()

        try:
            sign_in_card = await generate_signin_card(user_id=entity_interface.entity.entity_id, user_text=user_text,
                                                      friendship=friendship_now, top_img=top_img)
        except Exception as e:
            raise FailedException(f'生成签到卡片失败, {e}') from e

        logger.success(f'SignIn | User({entity_interface.entity.tid}) 签到成功')
        await matcher_interface.send_at_sender(OmegaMessageSegment.image(sign_in_card.path))
    except DuplicateException:
        # 已签到, 设置一个状态指示生成卡片中添加文字
        state.update({'_checked_sign_in_text': '今天你已经签到过了哦~'})
        logger.info(f'SignIn | User({entity_interface.entity.tid}) 重复签到, 生成运势卡片')
        await handle_generate_fortune_card(bot=bot, event=event, state=state, entity_interface=entity_interface)
    except FailedException as e:
        logger.error(f'SignIn | User({entity_interface.entity.tid}) 签到失败, {e}')
        await matcher_interface.send_at_sender('签到失败了QAQ, 请稍后再试或联系管理员处理')
    except Exception as e:
        logger.error(f'SignIn | User({entity_interface.entity.tid}) 签到失败, 发生了预期外的错误, {e}')
        await matcher_interface.send_at_sender('签到失败了QAQ, 请稍后再试或联系管理员处理')


async def handle_generate_fortune_card(
        bot: Bot,
        event: Event,
        state: T_State,
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface())]
) -> None:
    """处理生成运势卡片"""
    matcher_interface = MatcherInterface()
    try:
        # 获取当前好感度信息
        await entity_interface.entity.add_ignore_exists()
        friendship = await entity_interface.entity.query_friendship()

        nick_name = matcher_interface.get_event_handler().get_user_nickname()

        # 获取一言
        try:
            hitokoto = await get_hitokoto()
        except Exception as e:
            raise FailedException(f'获取一言失败, {e}') from e

        # 获取卡片头图
        try:
            top_img = await get_signin_top_image()
        except Exception as e:
            raise FailedException(f'获取签到卡片头图失败, {e}') from e

        # 插入签到特殊文本
        pock_text = state.get('_checked_sign_in_text', None)
        user_line = f'@{nick_name}\n' if not pock_text else f'@{nick_name} {pock_text}\n'
        user_text = f'{hitokoto}\n\n' \
                    f'{user_line}' \
                    f'当前{sign_in_config.signin_friendship_alias}: {int(friendship.friendship)}\n' \
                    f'当前{sign_in_config.signin_currency_alias}: {int(friendship.currency)}'

        try:
            head_img = await get_profile_image(bot=bot, event=event)
        except Exception as e:
            logger.warning(f'获取用户头像失败, 忽略头像框绘制, {e}')
            head_img = None

        try:
            sign_in_card = await generate_signin_card(user_id=entity_interface.entity.entity_id, user_text=user_text,
                                                      friendship=friendship.friendship, top_img=top_img,
                                                      draw_fortune=False, head_img=head_img)
        except Exception as e:
            raise FailedException(f'生成运势卡片失败, {e}') from e

        logger.success(f'SignIn | User({entity_interface.entity.tid}) 获取运势卡片成功')
        await matcher_interface.send_at_sender(OmegaMessageSegment.image(sign_in_card.path))
    except Exception as e:
        logger.error(f'SignIn | User({entity_interface.entity.tid}) 获取运势卡片失败, 发生了预期外的错误, {e}')
        await matcher_interface.send_at_sender('获取今日运势失败了QAQ, 请稍后再试或联系管理员处理')


async def handle_fix_sign_in(
        bot: Bot,
        event: Event,
        state: T_State,
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface('user'))],
        ensure: Annotated[str | None, ArgStr('sign_in_ensure')]
) -> None:
    """处理补签"""
    matcher_interface = MatcherInterface()

    # 检查是否收到确认消息后执行补签
    if ensure is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        fix_cost_: int | None = state.get('fix_cost')
        fix_date_text_: str | None = state.get('fix_date_text')
        fix_date_ordinal_: int | None = state.get('fix_date_ordinal')

        if not all((fix_cost_, fix_date_text_, fix_date_ordinal_)):
            logger.warning(f'SignIn | User({entity_interface.entity.tid}) 补签参数异常, state: {state}')
            await matcher_interface.send_at_sender('补签失败了, 补签参数异常, 请稍后再试或联系管理员处理')
            return

        try:
            # 尝试补签
            await entity_interface.entity.sign_in(sign_in_info='Fixed sign in',
                                                  date_=datetime.fromordinal(fix_date_ordinal_))
            await entity_interface.entity.change_friendship(currency=(- fix_cost_))

            # 设置一个状态指示生成卡片中添加文字
            state.update({'_checked_sign_in_text': f'已消耗{fix_cost_}{sign_in_config.signin_currency_alias}~\n'
                                                   f'成功补签了{fix_date_text_}的签到!'})
            logger.success(f'SignIn | User({entity_interface.entity.tid}) 补签{fix_date_text_}成功')
            await handle_generate_fortune_card(bot=bot, event=event, state=state, entity_interface=entity_interface)
            await entity_interface.entity.commit_session()
            return
        except Exception as e:
            logger.error(f'SignIn | User({entity_interface.entity.tid}) 补签失败, 执行补签时发生了预期外的错误, {e}')
            await matcher_interface.send_at_sender('补签失败了, 请稍后再试或联系管理员处理')
            return
    else:
        await matcher_interface.send_at_sender('已取消补签')
        return

    # 未收到确认消息后则为首次触发命令执行补签检查
    try:
        # 先检查签到状态
        is_sign_in_today = await entity_interface.entity.check_today_sign_in()
        if not is_sign_in_today:
            await matcher_interface.send_at_sender('你今天还没签到呢, 请先签到后再进行补签哦~')
            return

        # 获取补签的时间
        last_missing_sign_in_day = await entity_interface.entity.query_last_missing_sign_in_day()

        fix_date_text = datetime.fromordinal(last_missing_sign_in_day).strftime('%Y年%m月%d日')
        fix_days = datetime.now().toordinal() - last_missing_sign_in_day
        base_cost = 2 * sign_in_config.signin_base_currency
        fix_cost = base_cost if fix_days <= 3 else fix_days * base_cost

        # 获取当前好感度信息
        friendship = await entity_interface.entity.query_friendship()

        if fix_cost > friendship.currency:
            logger.info(f'SignIn | User({entity_interface.entity.tid}) 未补签, {sign_in_config.signin_currency_alias}不足')
            tip_msg = f'没有足够的{sign_in_config.signin_currency_alias}【{fix_cost}】进行补签, 已取消操作'
            await matcher_interface.send_at_sender(tip_msg)
            return

        state['fix_cost'] = fix_cost
        state['fix_date_text'] = fix_date_text
        state['fix_date_ordinal'] = last_missing_sign_in_day

    except Exception as e:
        logger.error(f'SignIn | User({entity_interface.entity.tid}) 补签失败, 检查状态时发生了预期外的错误, {e}')
        await matcher_interface.send_at_sender('补签失败了, 签到状态异常, 请稍后再试或联系管理员处理')
        return

    ensure_msg = f'使用{fix_cost}{sign_in_config.signin_currency_alias}补签{fix_date_text}\n\n确认吗?\n【是/否】'
    await matcher_interface.send_at_sender(ensure_msg)
    await matcher_interface.matcher.reject_arg('sign_in_ensure')


__all__ = [
    'handle_generate_fortune_card',
    'handle_generate_sign_in_card',
    'handle_fix_sign_in'
]
