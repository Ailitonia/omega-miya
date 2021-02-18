from PIL import Image, ImageDraw, ImageFont
from datetime import date


def stick_maker_static_traitor(text: str, image_file: bytes, font_path: str, image_wight: int, image_height: int):
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
    ImageDraw.Draw(text_main_img).multiline_text(xy=(0, 0), text=test_main_fin, font=font_main, spacing=8, fill=(0, 0, 0))

    # 处理文字部分旋转
    text_num_img = text_num_img.rotate(angle=-9, expand=True, resample=Image.BICUBIC, center=(0, 0))
    text_main_img = text_main_img.rotate(angle=-9.5, expand=True, resample=Image.BICUBIC, center=(0, 0))

    # 向模板图片中置入文字图层
    background.paste(im=image_file, box=(0, 0))
    background.paste(im=text_num_img, box=(435, 140), mask=text_num_img)
    background.paste(im=text_main_img, box=(130, 160), mask=text_main_img)

    return background


def stick_maker_static_jichou(text: str, image_file: bytes, font_path: str, image_wight: int, image_height: int):
    # 处理文本主体
    text = f"今天是{date.today().strftime('%Y年%m月%d日')}{text}, 这个仇我先记下了"
    font_main_size = 42
    font_main = ImageFont.truetype(font_path, font_main_size)
    # 按长度切分文本
    spl_num = 0
    spl_list = []
    for num in range(len(text)):
        text_w = font_main.getsize_multiline(text[spl_num:num])[0]
        if text_w >= (image_wight * 7 // 8):
            spl_list.append(text[spl_num:num])
            spl_num = num
    else:
        spl_list.append(text[spl_num:])
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


__all__ = [
    'stick_maker_static_traitor',
    'stick_maker_static_jichou'
]
