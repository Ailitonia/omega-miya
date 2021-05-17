import os
import asyncio
from datetime import datetime
from nonebot import logger, get_driver
from PIL import Image, ImageDraw, ImageFont
from omega_miya.utils.Omega_Base import Result

global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
FOLDER_PATH = os.path.abspath(os.path.dirname(__file__))


def __text_to_img(text: str, image_wight: int = 512) -> Image:
    font_path = os.path.abspath(os.path.join(FOLDER_PATH, 'default_font.otf'))
    if not os.path.exists(font_path):
        raise ValueError('Font not found')

    # 处理文字层 主体部分
    font_main_size = image_wight // 25
    font_main = ImageFont.truetype(font_path, font_main_size)
    # 按长度切分文本
    spl_num = 0
    spl_list = []
    for num in range(len(text)):
        text_w = font_main.getsize_multiline(text[spl_num:num])[0]
        if text_w >= image_wight * 0.78:
            spl_list.append(text[spl_num:num])
            spl_num = num
    else:
        spl_list.append(text[spl_num:])
    test_main_fin = '\n' + '\n'.join(spl_list) + '\n'

    # 绘制文字图层
    text_w, text_h = font_main.getsize_multiline(test_main_fin)
    text_main_img = Image.new(mode="RGBA", size=(text_w, text_h), color=(0, 0, 0, 0))
    ImageDraw.Draw(text_main_img).multiline_text(xy=(0, 0), text=test_main_fin, font=font_main, fill=(0, 0, 0))

    # 初始化背景图层
    image_height = text_h + 100
    background = Image.new(mode="RGB", size=(image_wight, image_height), color=(255, 255, 255))

    # 向背景图层中置入文字图层
    background.paste(im=text_main_img, box=(image_wight // 10, 50), mask=text_main_img)

    return background


async def text_to_img(text: str, image_wight: int = 512) -> Result.TextResult:
    def __handle():
        byte_img = __text_to_img(text, image_wight)
        # 检查生成图片路径
        img_folder_path = os.path.abspath(os.path.join(TMP_PATH, 'text_to_img'))
        if not os.path.exists(img_folder_path):
            os.makedirs(img_folder_path)
        img_path = os.path.abspath(
            os.path.join(img_folder_path, f"{hash(text)}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"))
        # 保存图片
        byte_img.save(img_path, 'JPEG')
        return img_path

    loop = asyncio.get_running_loop()
    try:
        path_result = await loop.run_in_executor(None, __handle)
        path = os.path.abspath(path_result)
        return Result.TextResult(error=False, info='Success', result=path)
    except Exception as e:
        logger.error(f'text_to_img failed, error: {repr(e)}')
        return Result.TextResult(error=True, info=repr(e), result='')


__all__ = [
    'text_to_img'
]
