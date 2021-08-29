import asyncio
from PIL import Image, ImageDraw, ImageFont
from datetime import date


async def stick_maker_static_traitor(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    有内鬼表情包模板
    """
    def __handle() -> Image.Image:
        # 初始化背景图层
        background = Image.new(mode="RGB", size=(image_wight, image_height), color=(255, 255, 255))

        # 处理文字层 字数部分
        text_num_img = Image.new(mode="RGBA", size=(image_wight, image_height), color=(0, 0, 0, 0))
        font_num_size = 48
        font_num = ImageFont.truetype(font_path, font_num_size)
        ImageDraw.Draw(text_num_img).text(xy=(0, 0), text=f'{len(text)}/100', font=font_num, fill=(255, 255, 255))

        # 处理文字层 主体部分
        text_main_img = Image.new(mode="RGBA", size=(image_wight, image_height), color=(0, 0, 0, 0))
        font_main_size = 54
        font_main = ImageFont.truetype(font_path, font_main_size)
        # 按长度切分文本
        spl_num = 0
        spl_list = []
        for num in range(len(text)):
            text_w = font_main.getsize_multiline(text[spl_num:num])[0]
            if text_w >= 415:
                spl_list.append(text[spl_num:num])
                spl_num = num
        else:
            spl_list.append(text[spl_num:])
        test_main_fin = ''
        for item in spl_list:
            test_main_fin += item + '\n'
        ImageDraw.Draw(text_main_img).multiline_text(xy=(0, 0), text=test_main_fin, font=font_main, spacing=8,
                                                     fill=(0, 0, 0))

        # 处理文字部分旋转
        text_num_img = text_num_img.rotate(angle=-9, expand=True, resample=Image.BICUBIC, center=(0, 0))
        text_main_img = text_main_img.rotate(angle=-9.5, expand=True, resample=Image.BICUBIC, center=(0, 0))

        # 向模板图片中置入文字图层
        background.paste(im=image_file, box=(0, 0))
        background.paste(im=text_num_img, box=(435, 140), mask=text_num_img)
        background.paste(im=text_main_img, box=(130, 160), mask=text_main_img)
        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_static_jichou(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    记仇表情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本主体
        text_ = f"今天是{date.today().strftime('%Y年%m月%d日')}{text}, 这个仇我先记下了"
        font_main_size = 42
        font_main = ImageFont.truetype(font_path, font_main_size)
        # 按长度切分文本
        spl_num = 0
        spl_list = []
        for num in range(len(text_)):
            text_w = font_main.getsize_multiline(text_[spl_num:num])[0]
            if text_w >= (image_wight * 7 // 8):
                spl_list.append(text_[spl_num:num])
                spl_num = num
        else:
            spl_list.append(text_[spl_num:])
        text_main_fin = '\n'.join(spl_list)

        font = ImageFont.truetype(font_path, font_main_size)
        text_w, text_h = font.getsize_multiline(text_main_fin)

        # 处理图片
        background_w = image_wight
        background_h = image_height + text_h + 20
        background = Image.new(mode="RGB", size=(background_w, background_h), color=(255, 255, 255))

        # 处理粘贴位置 顶头
        image_coordinate = (0, 0)
        background.paste(image_file, image_coordinate)

        draw = ImageDraw.Draw(background)
        # 计算居中文字位置
        text_coordinate = (((background_w - text_w) // 2), image_height + 5)
        draw.multiline_text(text_coordinate, text_main_fin, font=font, fill=(0, 0, 0))
        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_static_phlogo(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    ph表情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本主体
        test_sentences = text.strip().split(maxsplit=1)
        white_text = test_sentences[0]
        yellow_text = test_sentences[1]

        font_size = 640
        font = ImageFont.truetype(font_path, font_size)
        text_w, text_h = font.getsize(text)

        y_text_w, y_text_h = font.getsize(yellow_text)
        bg_y_text = Image.new(mode="RGB", size=(round(y_text_w * 1.1), round(text_h * 1.3)), color=(254, 154, 0))
        draw_y_text = ImageDraw.Draw(bg_y_text)
        draw_y_text.text((round(y_text_w * 1.1) // 2, round(text_h * 1.3) // 2),
                         yellow_text, anchor='mm', font=font, fill=(0, 0, 0))
        radii = 64
        # 画圆(用于分离4个角)
        circle = Image.new('L', (radii * 2, radii * 2), 0)  # 创建黑色方形
        draw_circle = ImageDraw.Draw(circle)
        draw_circle.ellipse((0, 0, radii * 2, radii * 2), fill=255)  # 黑色方形内切白色圆形
        # 原图转为带有alpha通道（表示透明程度）
        bg_y_text = bg_y_text.convert("RGBA")
        y_weight, y_height = bg_y_text.size
        # 画4个角（将整圆分离为4个部分）
        alpha = Image.new('L', bg_y_text.size, 255)  # 与img同大小的白色矩形，L 表示黑白图
        alpha.paste(circle.crop((0, 0, radii, radii)), (0, 0))  # 左上角
        alpha.paste(circle.crop((radii, 0, radii * 2, radii)), (y_weight - radii, 0))  # 右上角
        alpha.paste(circle.crop((radii, radii, radii * 2, radii * 2)), (y_weight - radii, y_height - radii))  # 右下角
        alpha.paste(circle.crop((0, radii, radii, radii * 2)), (0, y_height - radii))  # 左下角
        bg_y_text.putalpha(alpha)  # 白色区域透明可见，黑色区域不可见

        w_text_w, w_text_h = font.getsize(white_text)
        bg_w_text = Image.new(mode="RGB", size=(round(w_text_w * 1.05), round(text_h * 1.3)), color=(0, 0, 0))
        w_weight, w_height = bg_w_text.size
        draw_w_text = ImageDraw.Draw(bg_w_text)
        draw_w_text.text((round(w_text_w * 1.025) // 2, round(text_h * 1.3) // 2),
                         white_text, anchor='mm', font=font, fill=(255, 255, 255))

        text_bg = Image.new(mode="RGB", size=(w_weight + y_weight, y_height), color=(0, 0, 0))
        text_bg.paste(bg_w_text, (0, 0))
        text_bg.paste(bg_y_text, (round(w_text_w * 1.05), 0), mask=alpha)
        t_weight, t_height = text_bg.size

        background = Image.new(mode="RGB", size=(round(t_weight * 1.2), round(t_height * 1.75)), color=(0, 0, 0))
        b_weight, b_height = background.size
        background.paste(text_bg, ((b_weight - t_weight) // 2, (b_height - t_height) // 2))
        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_static_luxun(
        text: str, image_file: Image.Image, font_path: str, image_wight: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    鲁迅说/鲁迅写表情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本主体
        font_size = image_wight // 15
        text_stroke_width = int(font_size / 15)
        font = ImageFont.truetype(font_path, font_size)
        text_width_limit = image_wight - int(image_wight * 0.1875)
        # 分割文本
        spl_num = 0
        spl_list = []
        for num in range(len(text)):
            text_width, text_height = font.getsize_multiline(text[spl_num:num])
            if text_width > text_width_limit:
                spl_list.append(text[spl_num:num])
                spl_num = num
        else:
            spl_list.append(text[spl_num:])
        text_ = '\n'.join(spl_list)

        # 文本大小
        text_width, text_height = font.getsize_multiline(text_)
        single_text_width, single_text_height = font.getsize(text_)

        # 创建背景图层
        # 因为文字增加的图片高度
        bg_height_inc_ = (text_height - image_height * 0.25) * 1.125 + single_text_height * 2
        bg_height_inc = bg_height_inc_ if bg_height_inc_ > 0 else 0
        background = Image.new(
            mode="RGB",
            size=(image_wight, int(image_height + bg_height_inc)),
            color=(32, 32, 32))

        # 先把鲁迅图贴上去
        background.paste(image_file, box=(0, 0))

        # 再贴主体文本
        ImageDraw.Draw(background).multiline_text(xy=(image_wight // 2, int(image_height * 0.75)),
                                                  text=text_, font=font, align='center', anchor='ma',
                                                  fill=(255, 255, 255),
                                                  stroke_width=text_stroke_width,
                                                  stroke_fill=(0, 0, 0))

        ImageDraw.Draw(background).text(xy=(int(image_wight * 0.85), int((image_height * 0.95 + bg_height_inc))),
                                        text='—— 鲁迅', font=font, align='right', anchor='rd',
                                        fill=(255, 255, 255),
                                        stroke_width=text_stroke_width,
                                        stroke_fill=(0, 0, 0))

        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


__all__ = [
    'stick_maker_static_traitor',
    'stick_maker_static_jichou',
    'stick_maker_static_phlogo',
    'stick_maker_static_luxun'
]
