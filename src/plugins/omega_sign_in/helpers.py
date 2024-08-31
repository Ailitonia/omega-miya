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
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING, Literal, Optional, Union

from PIL import Image, ImageDraw, ImageFont
from nonebot.log import logger
from nonebot.utils import run_sync
from pydantic import BaseModel

from src.compat import parse_json_as, parse_obj_as
from src.service import OmegaRequests
from src.service.artwork_collection import get_artwork_collection, get_artwork_collection_type
from src.utils.image_utils import ImageUtils
from .config import sign_in_config, sign_local_resource_config

if TYPE_CHECKING:
    from src.resource import StaticResource, TemporaryResource
    from src.service import OmegaMatcherInterface
    from src.service.artwork_collection.typing import CollectedArtwork


__FORTUNE_EVENT: list["FortuneEvent"] = []
"""缓存求签事件"""


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


def _load_fortune_event(file: Union["StaticResource", "TemporaryResource"]) -> list[FortuneEvent]:
    """从文件读取求签事件"""
    if file.is_file:
        logger.debug(f'loading fortune event form {file}')
        with file.open('r', encoding='utf8') as f:
            fortune_event_data = f.read()
        return parse_json_as(list[FortuneEvent], fortune_event_data)
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


def get_fortune(user_id: str, *, date: Optional[datetime] = None) -> Fortune:
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

    return Fortune.model_validate(result)


async def get_signin_top_image() -> "CollectedArtwork":
    """从数据库获取一张生成签到卡片用的头图"""
    random_artworks = await get_artwork_collection_type().query_any_origin_by_condition(
        keywords=None, origin=sign_in_config.signin_plugin_top_image_origin, num=5,
        allow_classification_range=(2, 3), allow_rating_range=(0, 0), ratio=1
    )

    # 因为图库中部分图片可能因为作者删稿失效, 所以要多随机几个备选
    for artwork in random_artworks:
        try:
            collected_artwork = get_artwork_collection(artwork=artwork)
            await collected_artwork.artwork_proxy.get_page_file()
            return collected_artwork
        except Exception as e:
            logger.warning(f'getting artwork(origin={artwork.origin}, aid={artwork.aid}) page file failed, {e}')
            continue

    raise RuntimeError('all attempts to fetch artwork resources have failed')


async def get_profile_image(interface: "OmegaMatcherInterface") -> "TemporaryResource":
    """获取用户头像"""
    url = await interface.get_entity_interface().get_entity_profile_image_url()
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
    hitokoto_data = OmegaRequests.parse_content_as_json(response=hitokoto_response)

    text = f'{hitokoto_data.get("hitokoto")}\n——《{hitokoto_data.get("from")}》'
    if hitokoto_data.get("from_who"):
        text += f' {hitokoto_data.get("from_who")}'
    return text


async def generate_signin_card(
        user_id: str,
        user_text: str,
        friendship: float,
        top_img: "CollectedArtwork",
        *,
        width: int = 1024,
        draw_fortune: bool = True,
        head_img: Optional["TemporaryResource"] = None) -> "TemporaryResource":
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
    top_img_data = await top_img.artwork_proxy.query()
    top_img_file = await top_img.artwork_proxy.get_page_file()

    # 标注头图作品来源
    if top_img_data.origin in ['local_collected_artwork', 'none']:
        top_img_origin_text = top_img_data.origin.title().replace('_', '')
    elif top_img_data.origin == 'pixiv':
        top_img_origin_text = f'{top_img_data.origin.title()} | {top_img_data.aid} | @{top_img_data.uname}'
    else:
        top_img_origin_text = f'{top_img_data.origin.title()} | {top_img_data.aid}'

    @run_sync
    def _handle_signin_card() -> bytes:
        """签到卡片绘制"""
        # 生成用户当天老黄历
        user_fortune = get_fortune(user_id=user_id)

        # 加载头图
        draw_top_img: Image.Image = Image.open(top_img_file.resolve_path)
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
        _, top_text_height = ImageUtils.get_text_size(text=top_text, font=bd_font)

        # 计算好感度等级条
        level = _get_level(friendship=friendship)
        level_text = f'Level {level[0]}'
        _, level_text_height = ImageUtils.get_text_size(text=level_text, font=level_font)
        fs_text = f'{level[1]}/{level[2]}'
        fs_rat = level[1] / level[2] if level[1] < level[2] else 1
        fs_text_width, _ = ImageUtils.get_text_size(text=fs_text, font=text_font)

        # 日期
        date_text = datetime.now().strftime('%m/%d')
        # 预处理用户文本 包括昵称、好感度、积分
        user_text_ = ImageUtils.split_multiline_text(text=user_text, width=(width - int(width * 0.125)), font=text_font)
        _, user_text_height = ImageUtils.get_text_size(text=user_text_, font=text_font)

        # 今日运势
        _, fortune_text_height = ImageUtils.get_text_size(text=user_fortune.text, font=bd_text_font)
        _, fortune_star_height = ImageUtils.get_text_size(text=user_fortune.star, font=text_font)
        # 底部文字
        _, bottom_text_height = ImageUtils.get_text_size(text=f'{"@@##" * 4}\n', font=bottom_text_font)

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
                                            text='宜', font=bd_text_font, align='left', anchor='lt',
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
                                            text='不宜', font=bd_text_font, align='left', anchor='lt',
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
    file_content = await _handle_signin_card()
    async with save_file.async_open('wb') as af:
        await af.write(file_content)
    return save_file


__all__ = [
    'generate_signin_card',
    'get_signin_top_image',
    'get_hitokoto',
    'get_profile_image',
]
