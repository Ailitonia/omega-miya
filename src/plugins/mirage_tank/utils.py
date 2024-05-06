"""
@Author         : Ailitonia
@Date           : 2022/06/07 20:15
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 幻影坦克图片合成工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Callable, Optional

from nonebot.utils import run_sync
from PIL import Image, ImageEnhance, ImageOps, ImageMath

from src.resource import TemporaryResource
from src.service import OmegaRequests
from src.utils.image_utils import ImageUtils


_TMP_FOLDER: TemporaryResource = TemporaryResource('mirage_tank')
"""缓存路径"""
MIRAGE_FACTORY: type = Callable[..., Image.Image]


async def _fetch_image(image_url: str) -> bytes:
    response = await OmegaRequests(timeout=30).get(url=image_url)
    if not isinstance(response.content, bytes):
        raise ValueError('not image url')
    return response.content


def _load_image(image_content: bytes) -> ImageUtils:
    image = ImageUtils.init_from_bytes(image=image_content)
    image = image.convert('RGBA')
    return image


async def generate_mirage_tank(
        factory: MIRAGE_FACTORY,
        base_image_url: str,
        addition_image_url: Optional[str] = None
) -> TemporaryResource:
    """生成幻影坦克图片"""
    base_image_content = await _fetch_image(image_url=base_image_url)
    base_image = _load_image(image_content=base_image_content)

    if addition_image_url is None:
        make_image = await run_sync(factory)(base_image.image)
        base_image.set_image(image=make_image)
    else:
        addition_image_content = await _fetch_image(image_url=addition_image_url)
        addition_image = _load_image(image_content=addition_image_content)

        make_image = await run_sync(factory)(base_image.image, addition_image.image)
        base_image.set_image(image=make_image)

    output_file = _TMP_FOLDER(f'{factory.__name__}_{datetime.now().strftime("%Y%m%d%H%M%S")}.png'.strip('_'))
    return await base_image.save(output_file, format_='PNG')


def _simple_white(image: Image.Image) -> Image.Image:
    """生成普通白底幻影坦克"""
    # 图片去色并转化为透明度蒙版
    mask = ImageEnhance.Color(image).enhance(0)
    mask = mask.convert('L')

    # 白色作为背景色将透明度并添加蒙版
    background = Image.new(mode='RGBA', size=image.size, color=(255, 255, 255, 0))
    upper = Image.new(mode='RGBA', size=image.size, color=(255, 255, 255, 255))
    background.paste(im=upper, mask=mask)

    return background


async def simple_white(image_url: str) -> TemporaryResource:
    """生成普通白底幻影坦克"""
    return await generate_mirage_tank(factory=_simple_white, base_image_url=image_url)


def _simple_black(image: Image.Image) -> Image.Image:
    """生成普通黑底幻影坦克"""
    # 图片去色并转化为透明度蒙版
    mask = ImageEnhance.Color(image).enhance(0)
    mask = mask.convert('L')
    mask = ImageOps.invert(mask)

    # 黑色作为背景色将透明度并添加蒙版
    background = Image.new(mode='RGBA', size=image.size, color=(0, 0, 0, 0))
    upper = Image.new(mode='RGBA', size=image.size, color=(0, 0, 0, 255))
    background.paste(im=upper, mask=mask)

    return background


async def simple_black(image_url: str) -> TemporaryResource:
    """生成普通黑底幻影坦克"""
    return await generate_mirage_tank(factory=_simple_black, base_image_url=image_url)


def _simple_noise(image: Image.Image) -> Image.Image:
    """生成随机高斯噪点表层的黑白幻影坦克"""
    # 生成高斯噪声底图
    noise_image = Image.effect_noise(size=(image.width // 8, image.height // 8), sigma=128)
    noise_image = noise_image.resize(image.size, Image.Resampling.NEAREST)

    return _complex_gray(white_image=noise_image, black_image=image)


async def simple_noise(image_url: str) -> TemporaryResource:
    """生成随机高斯噪点表层的黑白幻影坦克"""
    return await generate_mirage_tank(factory=_simple_noise, base_image_url=image_url)


def _color_noise(image: Image.Image) -> Image.Image:
    """生成随机高斯噪点表层的彩色幻影坦克"""
    # 生成高斯噪声底图
    noise_image = Image.effect_noise(size=(image.width // 32, image.height // 32), sigma=255)
    noise_image = noise_image.resize(image.size, Image.Resampling.NEAREST)

    return _complex_color(white_image=noise_image, black_image=image)


async def color_noise(image_url: str) -> TemporaryResource:
    """生成随机高斯噪点表层的彩色幻影坦克"""
    return await generate_mirage_tank(factory=_color_noise, base_image_url=image_url)


def _complex_gray(white_image: Image.Image, black_image: Image.Image) -> Image.Image:
    """生成由两张图合成的灰度幻影坦克

    :param white_image: 白色背景下显示的图片
    :param black_image: 黑色背景下显示的图片
    """

    # 调整图片大小
    width = max(white_image.width, black_image.width)
    height = max(white_image.height, black_image.height)
    size = (width, height)
    white_image = ImageUtils(image=white_image).resize_with_filling(size=size).image
    black_image = ImageUtils(image=black_image).resize_with_filling(size=size).image

    # 去色, 作用蒙版改变色阶范围
    white_mask = ImageEnhance.Color(white_image).enhance(0)
    _ = Image.new(mode='RGBA', size=size, color=(255, 255, 255, 128))
    white_mask.paste(_, mask=_)
    white_mask = white_mask.convert('L')

    black_mask = ImageEnhance.Color(black_image).enhance(0)
    _ = Image.new(mode='RGBA', size=size, color=(0, 0, 0, 128))
    black_mask.paste(_, mask=_)
    black_mask = black_mask.convert('L')

    # 处理
    alpha_mask = ImageMath.unsafe_eval('float(256-lw+lb)', lw=white_mask, lb=black_mask)
    l_mask = ImageMath.unsafe_eval('float(lb/a*256)', lb=black_mask, a=alpha_mask)
    alpha_mask = alpha_mask.convert('L')
    l_mask = l_mask.convert('L')
    mask = Image.merge(mode='RGBA', bands=(l_mask, l_mask, l_mask, alpha_mask))

    return mask


async def complex_gray(white_image_url: str, black_image_url: str) -> TemporaryResource:
    """生成由两张图合成的灰度幻影坦克

    :param white_image_url: 白色背景下显示的图片
    :param black_image_url: 黑色背景下显示的图片
    """
    return await generate_mirage_tank(_complex_gray, white_image_url, black_image_url)


def _complex_color(white_image: Image.Image, black_image: Image.Image) -> Image.Image:
    """生成由两张图合成的彩色幻影坦克

    :param white_image: 白色背景下显示的图片
    :param black_image: 黑色背景下显示的图片
    """
    # 调整图片大小
    width = max(white_image.width, black_image.width)
    height = max(white_image.height, black_image.height)
    size = (width, height)
    white_image = ImageUtils(image=white_image).resize_with_filling(size=size).image
    black_image = ImageUtils(image=black_image).resize_with_filling(size=size).image

    # 调整饱和度和亮度
    _ = Image.new(mode='RGBA', size=size, color=(255, 255, 255, 64))
    white_image.paste(_, mask=_)
    black_image = ImageEnhance.Color(black_image).enhance(0.75)
    black_image = ImageEnhance.Brightness(black_image).enhance(0.25)

    # 分离彩色通道
    white_r, white_g, white_b, _ = white_image.split()
    black_r, black_g, black_b, _ = black_image.split()

    # 处理
    r_mask = ImageMath.unsafe_eval('float(256-wr+br)', wr=white_r, br=black_r)
    g_mask = ImageMath.unsafe_eval('float(256-wg+bg)', wg=white_g, bg=black_g)
    b_mask = ImageMath.unsafe_eval('float(256-wb+bb)', wb=white_b, bb=black_b)

    color_max_mask = ImageMath.unsafe_eval('float(max(max(r, g), b))', r=black_r, g=black_g, b=black_b)
    alpha_mask = ImageMath.unsafe_eval('float(min(max(float(0.222*r + 0.707*g + 0.071*b), float(m)), 256))',
                                       r=r_mask, g=g_mask, b=b_mask, m=color_max_mask)

    output_r = ImageMath.unsafe_eval('float(min(float(r/a), 256)*256)', r=black_r, a=alpha_mask).convert('L')
    output_g = ImageMath.unsafe_eval('float(min(float(g/a), 256)*256)', g=black_g, a=alpha_mask).convert('L')
    output_b = ImageMath.unsafe_eval('float(min(float(b/a), 256)*256)', b=black_b, a=alpha_mask).convert('L')
    output_a = alpha_mask.convert('L')

    make_image = Image.merge(mode='RGBA', bands=(output_r, output_g, output_b, output_a))

    return make_image


async def complex_color(white_image_url: str, black_image_url: str) -> TemporaryResource:
    """生成由两张图合成的彩色幻影坦克

    :param white_image_url: 白色背景下显示的图片
    :param black_image_url: 黑色背景下显示的图片
    """
    return await generate_mirage_tank(_complex_color, white_image_url, black_image_url)


def _complex_difference(base_image: Image.Image, differ_image: Image.Image) -> Image.Image:
    """生成由两张相似图合成的彩色差分幻影坦克

    :param base_image: 基础图片
    :param differ_image: 差分图片
    """
    # 调整图片大小
    width = max(base_image.width, differ_image.width)
    height = max(base_image.height, differ_image.height)
    size = (width, height)
    base_image = ImageUtils(image=base_image).resize_with_filling(size=size).image
    differ_image = ImageUtils(image=differ_image).resize_with_filling(size=size).image

    # 转化灰度图, 计算差分作为透明度通道
    differ_mask = ImageEnhance.Color(differ_image).enhance(0)
    differ_mask = differ_mask.convert('L')

    base_mask = ImageEnhance.Color(base_image).enhance(0)
    base_mask = base_mask.convert('L')

    difference_mask = ImageMath.unsafe_eval('float(abs(dm-bm))', dm=differ_mask, bm=base_mask)

    # 分离基础图片颜色通道
    base_r, base_g, base_b, base_a = base_image.split()

    # 根据差分重新计算透明度通道
    output_a = ImageMath.unsafe_eval('float(ba-da)', da=difference_mask, ba=base_a).convert('L')

    make_image = Image.merge(mode='RGBA', bands=(base_r, base_g, base_b, output_a))

    return make_image


async def complex_difference(base_image_url: str, differ_image_url: str) -> TemporaryResource:
    """生成由两张相似图合成的彩色差分幻影坦克

    :param base_image_url: 基础图片
    :param differ_image_url: 差分图片
    """
    return await generate_mirage_tank(_complex_difference, base_image_url, differ_image_url)


__all__ = [
    'simple_white',
    'simple_black',
    'simple_noise',
    'color_noise',
    'complex_gray',
    'complex_color',
    'complex_difference'
]
