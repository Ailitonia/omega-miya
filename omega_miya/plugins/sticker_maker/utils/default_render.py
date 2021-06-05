import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from omega_miya.utils.tencent_cloud_api import TencentTMT


async def stick_maker_temp_default(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int) -> Image.Image:
    """
    默认加字表情包模板
    """
    def __handle() -> Image.Image:
        # 处理图片
        draw = ImageDraw.Draw(image_file)
        font_size = 72
        font = ImageFont.truetype(font_path, font_size)
        text_w, text_h = font.getsize_multiline(text)
        while text_w >= image_wight:
            font_size = font_size * 3 // 4
            font = ImageFont.truetype(font_path, font_size)
            text_w, text_h = font.getsize_multiline(text)
        # 计算居中文字位置
        text_coordinate = (((image_wight - text_w) // 2), 9 * (image_height - text_h) // 10)
        # 为文字设置黑边
        text_b_resize = 4
        if font_size >= 72:
            text_b_resize = 4
        elif font_size >= 36:
            text_b_resize = 3
        elif font_size >= 24:
            text_b_resize = 2
        elif font_size < 12:
            text_b_resize = 1
        text_coordinate_b1 = (text_coordinate[0] + text_b_resize, text_coordinate[1])
        text_coordinate_b2 = (text_coordinate[0] - text_b_resize, text_coordinate[1])
        text_coordinate_b3 = (text_coordinate[0], text_coordinate[1] + text_b_resize)
        text_coordinate_b4 = (text_coordinate[0], text_coordinate[1] - text_b_resize)
        draw.multiline_text(text_coordinate_b1, text, font=font, fill=(0, 0, 0))
        draw.multiline_text(text_coordinate_b2, text, font=font, fill=(0, 0, 0))
        draw.multiline_text(text_coordinate_b3, text, font=font, fill=(0, 0, 0))
        draw.multiline_text(text_coordinate_b4, text, font=font, fill=(0, 0, 0))
        # 白字要后画，后画的在上层，不然就是黑滋在上面挡住了
        draw.multiline_text(text_coordinate, text, font=font, fill=(255, 255, 255))
        return image_file

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_temp_littleangel(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int) -> Image.Image:
    """
    小天使表情包模板
    """
    def __handle() -> Image.Image:
        # 处理图片
        background_w = image_wight + 100
        background_h = image_height + 230
        background = Image.new(mode="RGB", size=(background_w, background_h), color=(255, 255, 255))
        # 处理粘贴位置 上留100像素，下留130像素
        image_coordinate = (((background_w - image_wight) // 2), 100)
        background.paste(image_file, image_coordinate)
        draw = ImageDraw.Draw(background)

        font_down_1 = ImageFont.truetype(font_path, 48)
        text_down_1 = r'非常可爱！简直就是小天使'
        text_down_1_w, text_down_1_h = font_down_1.getsize(text_down_1)
        text_down_1_coordinate = (((background_w - text_down_1_w) // 2), background_h - 120)
        draw.text(text_down_1_coordinate, text_down_1, font=font_down_1, fill=(0, 0, 0))

        font_down_2 = ImageFont.truetype(font_path, 26)
        text_down_2 = r'她没失踪也没怎么样  我只是觉得你们都该看一下'
        text_down_2_w, text_down_2_h = font_down_2.getsize(text_down_2)
        text_down_2_coordinate = (((background_w - text_down_2_w) // 2), background_h - 60)
        draw.text(text_down_2_coordinate, text_down_2, font=font_down_2, fill=(0, 0, 0))

        font_size_up = 72
        font_up = ImageFont.truetype(font_path, font_size_up)
        text_up = f'请问你们看到{text}了吗?'
        text_up_w, text_up_h = font_up.getsize(text_up)
        while text_up_w >= background_w:
            font_size_up = font_size_up * 5 // 6
            font_up = ImageFont.truetype(font_path, font_size_up)
            text_up_w, text_up_h = font_up.getsize(text_up)
        # 计算居中文字位置
        text_up_coordinate = (((background_w - text_up_w) // 2), 25)
        draw.text(text_up_coordinate, text_up, font=font_up, fill=(0, 0, 0))
        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_temp_whitebg(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int) -> Image.Image:
    """
    白底加字表情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本
        if image_wight > image_height:
            font_size = 72
        else:
            font_size = 84
        font = ImageFont.truetype(font_path, font_size)
        text_w, text_h = font.getsize_multiline(text)
        while text_w >= (image_wight * 8 // 9):
            font_size = font_size * 7 // 8
            font = ImageFont.truetype(font_path, font_size)
            text_w, text_h = font.getsize_multiline(text)

        # 处理图片
        background_w = image_wight
        background_h = image_height + round(text_h * 1.5)
        background = Image.new(mode="RGB", size=(background_w, background_h), color=(255, 255, 255))

        # 处理粘贴位置 顶头
        image_coordinate = (0, 0)
        background.paste(image_file, image_coordinate)

        draw = ImageDraw.Draw(background)
        # 计算居中文字位置
        text_coordinate = (((background_w - text_w) // 2), image_height + round(text_h / 100) * round(text_h * 0.1))
        draw.multiline_text(text_coordinate, text, font=font, fill=(0, 0, 0))
        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_temp_blackbg(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int) -> Image.Image:
    """
    黑边加底字表情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本
        if image_wight > image_height:
            font_size = 96
        else:
            font_size = 108
        font = ImageFont.truetype(font_path, font_size)
        text_w, text_h = font.getsize_multiline(text)
        while text_w >= (image_wight * 9 // 10):
            font_size = font_size * 8 // 9
            font = ImageFont.truetype(font_path, font_size)
            text_w, text_h = font.getsize_multiline(text)

        # 处理图片
        background_w = image_wight + 150
        background_h = image_height + 115 + round(text_h * 1.5)
        background = Image.new(mode="RGB", size=(background_w, background_h), color=(0, 0, 0))
        layer_1 = Image.new(mode="RGB", size=(image_wight + 12, image_height + 12), color=(255, 255, 255))
        layer_2 = Image.new(mode="RGB", size=(image_wight + 10, image_height + 10), color=(0, 0, 0))
        layer_3 = Image.new(mode="RGB", size=(image_wight + 6, image_height + 6), color=(255, 255, 255))
        layer_4 = Image.new(mode="RGB", size=(image_wight + 4, image_height + 4), color=(0, 0, 0))

        # 处理粘贴位置 留出黑边距离
        background.paste(layer_1, (70, 70))
        background.paste(layer_2, (71, 71))
        background.paste(layer_3, (73, 73))
        background.paste(layer_4, (74, 74))
        background.paste(image_file, (76, 76))

        draw = ImageDraw.Draw(background)

        # 计算居中文字位置
        text_coordinate = (((background_w - text_w) // 2),
                           image_height + 110 - round(text_h / 9) + round(text_h / 100) * round(text_h * 0.1))
        draw.multiline_text(text_coordinate, text, font=font, fill=(255, 255, 255))
        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_temp_decolorize(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int) -> Image.Image:
    """
    去色加字表情包模板
    """
    def __handle() -> Image.Image:
        enhancer = ImageEnhance.Color(image_file)
        made_image = enhancer.enhance(0)
        return made_image

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_temp_grass_ja(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int) -> Image.Image:
    """
    生草日语表情包模板
    """
    # 处理日语翻译
    text_zh = text.replace('\n', ' ')
    text_trans_result = await TencentTMT().translate(source_text=text, target='ja')
    text_ja = str(text_trans_result.result.get('targettext', '翻訳に失敗しました！')).replace('\n', ' ')
    text_ = f'{text_zh}\n{text_ja}'

    # 处理黑白
    image_file_ = await stick_maker_temp_decolorize(text, image_file, font_path, image_wight, image_height)

    def __handle() -> Image.Image:
        # 处理文本
        if image_wight > image_height:
            font_size = 48
        else:
            font_size = 60
        font = ImageFont.truetype(font_path, font_size)
        text_w, text_h = font.getsize_multiline(text_)
        while text_w >= (image_wight * 9 // 10):
            font_size = font_size * 8 // 9
            font = ImageFont.truetype(font_path, font_size)
            text_w, text_h = font.getsize_multiline(text_)

        # 处理图片
        background_w = image_wight
        background_h = image_height + round(text_h * 1.5)
        background = Image.new(mode="RGB", size=(background_w, background_h), color=(0, 0, 0))

        # 处理粘贴位置 留出黑边距离
        background.paste(image_file_, (0, 0))

        draw = ImageDraw.Draw(background)

        # 计算居中文字位置
        text_coordinate = (((background_w - text_w) // 2), image_height + round(text_h * 0.2))
        draw.multiline_text(text_coordinate, text_, font=font, align='center', fill=(255, 255, 255))
        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


__all__ = [
    'stick_maker_temp_whitebg',
    'stick_maker_temp_blackbg',
    'stick_maker_temp_default',
    'stick_maker_temp_littleangel',
    'stick_maker_temp_decolorize',
    'stick_maker_temp_grass_ja'
]
