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
from io import BytesIO
from PIL import Image, ImageEnhance, ImageOps, ImageMath

from omega_miya.local_resource import TmpResource
from omega_miya.web_resource import HttpFetcher
from omega_miya.utils.process_utils import run_sync, run_async_catching_exception


_SAVE_FOLDER: TmpResource = TmpResource('mirage_tank')
"""生成图片存放路径"""


def _simple_white(image: Image.Image) -> bytes:
    """生成普通白底幻影坦克"""
    # 图片去色并转化为透明度蒙版
    mask = ImageEnhance.Color(image).enhance(0)
    mask = mask.convert('L')

    # 白色作为背景色将透明度并添加蒙版
    background = Image.new(mode='RGBA', size=image.size, color=(255, 255, 255, 0))
    upper = Image.new(mode='RGBA', size=image.size, color=(255, 255, 255, 255))
    background.paste(im=upper, mask=mask)

    with BytesIO() as bf:
        background.save(bf, 'PNG')
        content = bf.getvalue()
    return content


@run_async_catching_exception
async def simple_white(image_url: str) -> TmpResource:
    """生成普通白底幻影坦克"""
    image = await fetch_image(image_url=image_url)
    make_image = await run_sync(_simple_white)(image=image)
    file_name = f"simple_white_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    save_file = _SAVE_FOLDER(file_name)
    async with save_file.async_open('wb') as af:
        await af.write(make_image)
    return save_file


def _simple_black(image: Image.Image) -> bytes:
    """生成普通黑底幻影坦克"""
    # 图片去色并转化为透明度蒙版
    mask = ImageEnhance.Color(image).enhance(0)
    mask = mask.convert('L')
    mask = ImageOps.invert(mask)

    # 黑色作为背景色将透明度并添加蒙版
    background = Image.new(mode='RGBA', size=image.size, color=(0, 0, 0, 0))
    upper = Image.new(mode='RGBA', size=image.size, color=(0, 0, 0, 255))
    background.paste(im=upper, mask=mask)

    with BytesIO() as bf:
        background.save(bf, 'PNG')
        content = bf.getvalue()
    return content


@run_async_catching_exception
async def simple_black(image_url: str) -> TmpResource:
    """生成普通黑底幻影坦克"""
    image = await fetch_image(image_url=image_url)
    make_image = await run_sync(_simple_black)(image=image)
    file_name = f"simple_black_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    save_file = _SAVE_FOLDER(file_name)
    async with save_file.async_open('wb') as af:
        await af.write(make_image)
    return save_file


def _complex_gray(white_image: Image.Image, black_image: Image.Image) -> bytes:
    """生成由两张图合成的幻影坦克

    :param white_image: 白色背景下显示的图片
    :param black_image: 黑色背景下显示的图片
    """
    # 调整图片大小
    width = max(white_image.width, black_image.width)
    height = max(white_image.height, black_image.height)
    size = (width, height)
    white_image = _resize_with_filling(image=white_image, size=size)
    black_image = _resize_with_filling(image=black_image, size=size)

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
    alpha_mask = ImageMath.eval('float(256-lw+lb)', lw=white_mask, lb=black_mask)
    l_mask = ImageMath.eval('float(lb/a*256)', lb=black_mask, a=alpha_mask)
    alpha_mask = alpha_mask.convert('L')
    l_mask = l_mask.convert('L')
    mask = Image.merge(mode='RGBA', bands=(l_mask, l_mask, l_mask, alpha_mask))

    with BytesIO() as bf:
        mask.save(bf, 'PNG')
        content = bf.getvalue()
    return content


@run_async_catching_exception
async def complex_gray(white_image_url: str, black_image_url: str) -> TmpResource:
    """生成由两张图合成的幻影坦克

    :param white_image_url: 白色背景下显示的图片
    :param black_image_url: 黑色背景下显示的图片
    """
    white_image = await fetch_image(image_url=white_image_url)
    black_image = await fetch_image(image_url=black_image_url)
    make_image = await run_sync(_complex_gray)(white_image=white_image, black_image=black_image)
    file_name = f"complex_gray_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    save_file = _SAVE_FOLDER(file_name)
    async with save_file.async_open('wb') as af:
        await af.write(make_image)
    return save_file


def _resize_with_filling(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """在不损失原图长宽比的条件下, 使用透明图层将原图转换成指定大小"""
    # 计算调整比例
    width, height = image.size
    rs_width, rs_height = size
    scale = min(rs_width / width, rs_height / height)

    image = image.resize((int(width * scale), int(height * scale)))
    box = (int(abs(width * scale - rs_width) / 2), int(abs(height * scale - rs_height) / 2))
    background = Image.new(mode='RGBA', size=size, color=(255, 255, 255, 0))
    background.paste(image, box=box)

    return background


async def fetch_image(image_url: str) -> Image.Image:
    fetcher = HttpFetcher(timeout=30)
    image_result = await fetcher.get_bytes(url=image_url)
    with BytesIO(image_result.result) as bf:
        image: Image.Image = Image.open(bf)
        image.load()
    image = image.convert('RGBA')
    return image


__all__ = [
    'simple_white',
    'simple_black',
    'complex_gray'
]
