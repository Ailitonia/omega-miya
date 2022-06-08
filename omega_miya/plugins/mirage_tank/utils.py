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


def _simple_white(image_content: bytes) -> bytes:
    """生成普通白底幻影坦克"""
    image = _load_image(image_content=image_content)

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
    image_content = await _fetch_image(image_url=image_url)
    make_image = await run_sync(_simple_white)(image_content=image_content)
    file_name = f"simple_white_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    save_file = _SAVE_FOLDER(file_name)
    async with save_file.async_open('wb') as af:
        await af.write(make_image)
    return save_file


def _simple_black(image_content: bytes) -> bytes:
    """生成普通黑底幻影坦克"""
    image = _load_image(image_content=image_content)

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
    image_content = await _fetch_image(image_url=image_url)
    make_image = await run_sync(_simple_black)(image_content=image_content)
    file_name = f"simple_black_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    save_file = _SAVE_FOLDER(file_name)
    async with save_file.async_open('wb') as af:
        await af.write(make_image)
    return save_file


def _complex_gray(white_image_content: bytes, black_image_content: bytes) -> bytes:
    """生成由两张图合成的灰度幻影坦克

    :param white_image_content: 白色背景下显示的图片
    :param black_image_content: 黑色背景下显示的图片
    """
    white_image = _load_image(image_content=white_image_content)
    black_image = _load_image(image_content=black_image_content)

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
    """生成由两张图合成的灰度幻影坦克

    :param white_image_url: 白色背景下显示的图片
    :param black_image_url: 黑色背景下显示的图片
    """
    white_image_content = await _fetch_image(image_url=white_image_url)
    black_image_content = await _fetch_image(image_url=black_image_url)
    make_image = await run_sync(_complex_gray)(white_image_content=white_image_content,
                                               black_image_content=black_image_content)
    file_name = f"complex_gray_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    save_file = _SAVE_FOLDER(file_name)
    async with save_file.async_open('wb') as af:
        await af.write(make_image)
    return save_file


def _complex_color(white_image_content: bytes, black_image_content: bytes) -> bytes:
    """生成由两张图合成的彩色幻影坦克

    :param white_image_content: 白色背景下显示的图片
    :param black_image_content: 黑色背景下显示的图片
    """
    white_image = _load_image(image_content=white_image_content)
    black_image = _load_image(image_content=black_image_content)

    # 调整图片大小
    width = max(white_image.width, black_image.width)
    height = max(white_image.height, black_image.height)
    size = (width, height)
    white_image = _resize_with_filling(image=white_image, size=size)
    black_image = _resize_with_filling(image=black_image, size=size)

    # 调整饱和度和亮度
    black_image = ImageEnhance.Color(black_image).enhance(0.7)
    black_image = ImageEnhance.Brightness(black_image).enhance(0.2)

    # 分离彩色通道
    white_r, white_g, white_b, _ = white_image.split()
    black_r, black_g, black_b, _ = black_image.split()

    # 处理
    r_mask = ImageMath.eval('float(256-wr+br)', wr=white_r, br=black_r)
    g_mask = ImageMath.eval('float(256-wg+bg)', wg=white_g, bg=black_g)
    b_mask = ImageMath.eval('float(256-wb+bb)', wb=white_b, bb=black_b)

    color_max_mask = ImageMath.eval('float(max(max(r, g), b))', r=black_r, g=black_g, b=black_b)
    alpha_mask = ImageMath.eval('float(min(max(float(0.222*r + 0.707*g + 0.071*b), float(m)), 256))',
                                r=r_mask, g=g_mask, b=b_mask, m=color_max_mask)

    output_r = ImageMath.eval('float(min(float(r/a), 256)*256)', r=black_r, a=alpha_mask).convert('L')
    output_g = ImageMath.eval('float(min(float(g/a), 256)*256)', g=black_g, a=alpha_mask).convert('L')
    output_b = ImageMath.eval('float(min(float(b/a), 256)*256)', b=black_b, a=alpha_mask).convert('L')
    output_a = alpha_mask.convert('L')

    make_image = Image.merge(mode='RGBA', bands=(output_r, output_g, output_b, output_a))

    with BytesIO() as bf:
        make_image.save(bf, 'PNG')
        content = bf.getvalue()
    return content


@run_async_catching_exception
async def complex_color(white_image_url: str, black_image_url: str) -> TmpResource:
    """生成由两张图合成的彩色幻影坦克

    :param white_image_url: 白色背景下显示的图片
    :param black_image_url: 黑色背景下显示的图片
    """
    white_image_content = await _fetch_image(image_url=white_image_url)
    black_image_content = await _fetch_image(image_url=black_image_url)
    make_image = await run_sync(_complex_color)(white_image_content=white_image_content,
                                                black_image_content=black_image_content)
    file_name = f"complex_color_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    save_file = _SAVE_FOLDER(file_name)
    async with save_file.async_open('wb') as af:
        await af.write(make_image)
    return save_file


def _complex_difference(differ_image_content: bytes, base_image_content: bytes) -> bytes:
    """生成由两张相似图合成的彩色差分幻影坦克

    :param differ_image_content: 差分图片
    :param base_image_content: 基础图片
    """
    differ_image = _load_image(image_content=differ_image_content)
    base_image = _load_image(image_content=base_image_content)

    # 调整图片大小
    width = max(differ_image.width, differ_image.width)
    height = max(base_image.height, base_image.height)
    size = (width, height)
    differ_image = _resize_with_filling(image=differ_image, size=size)
    base_image = _resize_with_filling(image=base_image, size=size)

    # 转化灰度图, 计算差分作为透明度通道
    differ_mask = ImageEnhance.Color(differ_image).enhance(0)
    differ_mask = differ_mask.convert('L')

    base_mask = ImageEnhance.Color(base_image).enhance(0)
    base_mask = base_mask.convert('L')

    difference_mask = ImageMath.eval('float(abs(dm-bm))', dm=differ_mask, bm=base_mask)

    # 分离基础图片颜色通道
    base_r, base_g, base_b, base_a = base_image.split()

    # 根据差分重新计算透明度通道
    output_a = ImageMath.eval('float(ba-da)', da=difference_mask, ba=base_a).convert('L')

    make_image = Image.merge(mode='RGBA', bands=(base_r, base_g, base_b, output_a))
    with BytesIO() as bf:
        make_image.save(bf, 'PNG')
        content = bf.getvalue()
    return content


@run_async_catching_exception
async def complex_difference(differ_image_url: str, base_image_url: str) -> TmpResource:
    """生成由两张相似图合成的彩色差分幻影坦克

    :param differ_image_url: 差分图片
    :param base_image_url: 基础图片
    """
    differ_image_content = await _fetch_image(image_url=differ_image_url)
    base_image_content = await _fetch_image(image_url=base_image_url)
    make_image = await run_sync(_complex_difference)(differ_image_content=differ_image_content,
                                                     base_image_content=base_image_content)
    file_name = f"complex_difference_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
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


async def _fetch_image(image_url: str) -> bytes:
    fetcher = HttpFetcher(timeout=30)
    image_result = await fetcher.get_bytes(url=image_url)
    return image_result.result


def _load_image(image_content: bytes) -> Image.Image:
    with BytesIO(image_content) as bf:
        image = Image.open(bf)
        image.load()
    image = image.convert('RGBA')
    return image


__all__ = [
    'simple_white',
    'simple_black',
    'complex_gray',
    'complex_color',
    'complex_difference'
]
