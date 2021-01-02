import os
import base64
from io import BytesIO
from datetime import datetime
import aiohttp
from nonebot import logger
from PIL import Image
from .default_render import *
from .static_render import *
from .sorry_render import render_gif


# 图片转base64
async def pic_2_base64(pic_path) -> str:
    with open(pic_path, 'rb') as f:
        b64 = base64.b64encode(f.read())
    b64 = str(b64, encoding='utf-8')
    b64 = 'base64://' + b64
    return b64


async def get_image(url: str):
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
                async with session.get(url=url, headers=headers, timeout=timeout) as resp:
                    _res = await resp.read()
            return _res
        except Exception as _e:
            error_info += f'{repr(_e)} Occurred in pic_2_base64 trying {timeout_count + 1} using paras: {url}\n'
        finally:
            timeout_count += 1
    else:
        error_info += f'Failed too many times in pic_2_base64 using paras: {url}'
        logger.error(error_info)
        return None


async def sticker_maker_main(url: str, temp: str, text: str, sticker_temp_type: str):
    # 定义表情包处理函数
    stick_maker = {
        'default': stick_maker_temp_default,
        'whitebg': stick_maker_temp_whitebg,
        'littleangel': stick_maker_temp_littleangel,
        'traitor': stick_maker_static_traitor,
        'sorry': render_gif,
        'wangjingze': render_gif
    }

    # 检查生成表情包路径
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'sticker')):
        os.makedirs(os.path.join(os.path.dirname(__file__), 'sticker'))
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'gif_sticker')):
        os.makedirs(os.path.join(os.path.dirname(__file__), 'gif_sticker'))

    # 默认模式
    if sticker_temp_type == 'default':
        origin_image_f = BytesIO()
        try:
            origin_image_f.write(await get_image(url=url))
        except Exception as e:
            logger.error(f'Stick_maker: sticker_maker ERROR: {repr(e)}')
            return None
        # 字体路径
        plugin_src_path = os.path.dirname(__file__)
        font_path = os.path.join(plugin_src_path, 'fonts', 'msyhbd.ttc')
        # 生成表情包路径
        sticker_path = os.path.join(plugin_src_path, 'sticker',
                                    f"{temp}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        # 调整图片大小（宽度512像素）
        make_image = Image.open(origin_image_f)
        image_resize_width = 512
        image_resize_height = 512 * make_image.height // make_image.width
        make_image = make_image.resize((image_resize_width, image_resize_height))

        # 调用模板处理图片
        make_image = stick_maker[temp](text=text, image_file=make_image, font_path=font_path,
                                       image_wight=image_resize_width, image_height=image_resize_height)

        # 输出图片
        make_image.save(sticker_path, 'JPEG')
        origin_image_f.close()

        return sticker_path

    # 静态模板模式
    elif sticker_temp_type == 'static':
        origin_image_f = BytesIO()
        plugin_src_path = os.path.dirname(__file__)
        static_temp_path = os.path.join(plugin_src_path, 'static', temp)

        # 检查预置背景图
        if not os.path.exists(os.path.join(static_temp_path, 'default_bg.png')):
            logger.error(f'Stick_maker: 模板预置文件错误, 默认图片应为default_bg.png')
            return None
        bg_image_path = os.path.join(static_temp_path, 'default_bg.png')

        # 检查预置字体
        if os.path.exists(os.path.join(static_temp_path, 'default_font.ttc')):
            font_path = os.path.join(static_temp_path, 'default_font.ttc')
        elif os.path.exists(os.path.join(static_temp_path, 'default_font.ttf')):
            font_path = os.path.join(static_temp_path, 'default_font.ttf')
        else:
            logger.error(f'Stick_maker: 模板预置文件错误, 默认字体应为default_font.ttc或default_font.ttf')
            return None

        # 生成表情包路径
        sticker_path = os.path.join(plugin_src_path, 'sticker',
                                    f"{temp}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")

        # 读取模板的预置背景
        try:
            with open(bg_image_path, 'rb') as f:
                origin_image_f.write(f.read())
        except Exception as e:
            logger.error(f'Stick_maker: sticker_maker ERROR: {repr(e)}')
            return None

        # 获取图片大小
        make_image = Image.open(origin_image_f)
        (image_resize_width, image_resize_height) = make_image.size

        # 调用模板处理图片
        make_image = stick_maker[temp](text=text, image_file=make_image, font_path=font_path,
                                       image_wight=image_resize_width, image_height=image_resize_height)

        # 输出图片
        make_image.save(sticker_path, 'JPEG')
        origin_image_f.close()

        return sticker_path

    # 动图模式
    elif sticker_temp_type == 'gif':
        test_sentences = text.strip().split('#')
        path = render_gif(temp, test_sentences)
        if path == -1:
            sticker_path = None
        else:
            sticker_path = path

        return sticker_path

    else:
        return None
