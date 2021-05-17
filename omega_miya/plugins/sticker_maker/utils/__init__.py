import os
from io import BytesIO
from datetime import datetime
from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from nonebot import logger, get_driver
from PIL import Image
from .default_render import *
from .static_render import *

global_config = get_driver().config
TMP_PATH = global_config.tmp_path_

HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/89.0.4389.114 Safari/537.36'}


async def sticker_maker_main(url: str, temp: str, text: str, sticker_temp_type: str):
    # 定义表情包处理函数
    stick_maker = {
        'default': stick_maker_temp_default,
        'whitebg': stick_maker_temp_whitebg,
        'blackbg': stick_maker_temp_blackbg,
        'littleangel': stick_maker_temp_littleangel,
        'traitor': stick_maker_static_traitor,
        'jichou': stick_maker_static_jichou,
        'phlogo': stick_maker_static_phlogo
    }

    # 检查生成表情包路径
    sticker_folder_path = os.path.abspath(os.path.join(TMP_PATH, 'sticker'))
    if not os.path.exists(sticker_folder_path):
        os.makedirs(sticker_folder_path)

    # 插件路径
    plugin_src_path = os.path.abspath(os.path.dirname(__file__))

    # 默认模式
    if sticker_temp_type == 'default':
        fetcher = HttpFetcher(timeout=10, flag='sticker_maker_main_default', headers=HEADERS)
        image_result = await fetcher.get_bytes(url=url)
        if image_result.error:
            logger.error(f'Stick_maker download image failed: {image_result.info}')
            return None

        image_bytes_f = BytesIO()
        image_bytes_f.write(image_result.result)

        # 字体路径
        font_path = os.path.join(plugin_src_path, 'fonts', 'msyhbd.ttc')
        # 生成表情包路径
        sticker_path = os.path.abspath(
            os.path.join(sticker_folder_path, f"{temp}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"))
        # 调整图片大小（宽度512像素）
        make_image = Image.open(image_bytes_f)
        image_resize_width = 512
        image_resize_height = 512 * make_image.height // make_image.width
        make_image = make_image.resize((image_resize_width, image_resize_height))

        # 调用模板处理图片
        make_image = stick_maker[temp](text=text, image_file=make_image, font_path=font_path,
                                       image_wight=image_resize_width, image_height=image_resize_height)

        # 输出图片
        make_image.save(sticker_path, 'JPEG')
        image_bytes_f.close()

        return sticker_path

    # 静态模板模式
    elif sticker_temp_type == 'static':
        # 模板路径
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
        elif os.path.exists(os.path.join(static_temp_path, 'default_font.otf')):
            font_path = os.path.join(static_temp_path, 'default_font.otf')
        else:
            logger.error(f'Stick_maker: 模板预置文件错误, 默认字体应为default_font.ttc、default_font.ttf或default_font.otf')
            return None

        # 生成表情包路径
        sticker_path = os.path.abspath(
            os.path.join(sticker_folder_path, f"{temp}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"))

        # 读取模板的预置背景并获取图片大小
        make_image = Image.open(bg_image_path)
        (image_resize_width, image_resize_height) = make_image.size

        # 调用模板处理图片
        make_image = stick_maker[temp](text=text, image_file=make_image, font_path=font_path,
                                       image_wight=image_resize_width, image_height=image_resize_height)

        # 输出图片
        make_image.save(sticker_path, 'JPEG')

        return sticker_path

    else:
        return None
