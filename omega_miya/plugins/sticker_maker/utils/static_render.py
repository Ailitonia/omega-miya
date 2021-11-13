import asyncio
from PIL import Image, ImageDraw, ImageFont
from datetime import date
from omega_miya.utils.omega_plugin_utils import TextUtils


async def stick_maker_static_traitor(
        text: str, image_file: Image.Image, font_path: str, image_width: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    有内鬼表情包模板
    """
    def __handle() -> Image.Image:
        # 初始化背景图层
        background = Image.new(mode="RGB", size=(image_width, image_height), color=(255, 255, 255))

        # 处理文字层 字数部分
        text_num_img = Image.new(mode="RGBA", size=(image_width, image_height), color=(0, 0, 0, 0))
        font_num_size = 48
        font_num = ImageFont.truetype(font_path, font_num_size)
        ImageDraw.Draw(text_num_img).text(xy=(0, 0), text=f'{len(text)}/100', font=font_num, fill=(255, 255, 255))

        # 处理文字层 主体部分
        text_main_img = Image.new(mode="RGBA", size=(image_width, image_height), color=(0, 0, 0, 0))
        font_main_size = 52
        font_main = ImageFont.truetype(font_path, font_main_size)
        # 按长度切分文本
        test_main_fin = TextUtils(text=text).split_multiline(width=410, font=font_main)
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
        text: str, image_file: Image.Image, font_path: str, image_width: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    记仇表情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本主体
        text_ = f"今天是{date.today().strftime('%Y年%m月%d日')}, {text}, 这个仇我先记下了"
        font_main_size = 42
        font_main = ImageFont.truetype(font_path, font_main_size)
        # 按长度切分文本
        text_main_fin = TextUtils(text=text_).split_multiline(width=(image_width * 7 // 8), font=font_main)

        font = ImageFont.truetype(font_path, font_main_size)
        text_w, text_h = font.getsize_multiline(text_main_fin)

        # 处理图片
        background_w = image_width
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
        text: str, image_file: Image.Image, font_path: str, image_width: int, image_height: int,
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

        # 分别确定两个边文字的大小
        w_text_width, w_text_height = font.getsize(white_text)
        y_text_width, y_text_height = font.getsize(yellow_text)

        # 生成图片定长 两部分文字之间间隔及两侧留空为固定值三个空格大小
        split_width, split_height = font.getsize(' ' * 1)
        image_width_ = w_text_width + y_text_width + int(split_width * 5.5)
        image_height_ = w_text_height + int(split_height * 1.25)

        # 计算黄色圆角矩形所在位置
        y_r_rectangle_x0 = w_text_width + int(split_width * 2.5)
        y_r_rectangle_y0 = split_height // 2
        y_r_rectangle_x1 = image_width_ - int(split_width * 2)
        y_r_rectangle_y1 = image_height_ - split_height // 2

        # 生成背景层
        background = Image.new(mode="RGB", size=(image_width_, image_height_), color=(0, 0, 0))
        background_draw = ImageDraw.Draw(background)
        # 生成圆角矩形
        background_draw.rounded_rectangle(
            xy=((y_r_rectangle_x0, y_r_rectangle_y0), (y_r_rectangle_x1, y_r_rectangle_y1)),
            radius=(image_height_ // 20),
            fill=(254, 154, 0)
        )

        # 绘制白色文字部分
        background_draw.text(
            xy=(split_width * 2, image_height_ // 2),  # 左对齐前间距 上下居中
            text=white_text,
            anchor='lm',
            font=font,
            fill=(255, 255, 255)
        )
        # 绘制黄框黑字部分
        background_draw.text(
            xy=(w_text_width + int(split_width * 3), image_height_ // 2),  # 左对齐白字加间距 上下居中
            text=yellow_text,
            anchor='lm',
            font=font,
            fill=(0, 0, 0)
        )

        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_static_luxun(
        text: str, image_file: Image.Image, font_path: str, image_width: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    鲁迅说/鲁迅写表情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本主体
        font_size = image_width // 15
        text_stroke_width = int(font_size / 15)
        font = ImageFont.truetype(font_path, font_size)
        text_width_limit = image_width - int(image_width * 0.1875)

        sign_text = '—— 鲁迅'

        # 分割文本
        text_ = TextUtils(text=text).split_multiline(width=text_width_limit, font=font, stroke_width=text_stroke_width)

        # 文本大小
        main_text_width, main_text_height = font.getsize_multiline(text_, stroke_width=text_stroke_width)
        sign_text_width, sign_text_height = font.getsize(sign_text, stroke_width=text_stroke_width)

        # 创建背景图层
        # 定位主体文字到图片下侧往上 1/4 处, 落款与主体文字间隔半行, 底部间隔一行, 超出部分为所有文字高度减去图片 1/4 高度
        bg_height_inc_ = int(main_text_height + sign_text_height * 2.5 - image_height * 0.25)
        bg_height_inc = bg_height_inc_ if bg_height_inc_ > 0 else 0
        background = Image.new(
            mode="RGB",
            size=(image_width, image_height + bg_height_inc),
            color=(32, 32, 32))

        # 先把鲁迅图贴上去
        background.paste(image_file, box=(0, 0))

        # 再贴主体文本
        ImageDraw.Draw(background).multiline_text(
            xy=(image_width // 2, int(image_height * 0.75)),
            text=text_, font=font, align='left', anchor='ma',
            fill=(255, 255, 255),
            stroke_width=text_stroke_width,
            stroke_fill=(0, 0, 0))

        ImageDraw.Draw(background).text(
            xy=(int(image_width * 0.85), int(main_text_height + sign_text_height / 2 + image_height * 0.75)),
            text=sign_text, font=font, align='right', anchor='ra',
            fill=(255, 255, 255),
            stroke_width=text_stroke_width,
            stroke_fill=(0, 0, 0))

        return background

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_static_jiangzhuang(
        text: str, image_file: Image.Image, font_path: str, image_width: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    奖状表情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本主体
        font_size = image_width // 25
        font = ImageFont.truetype(font_path, font_size)
        text_width_limit = int(image_width * 0.65)

        # 分割文本
        text_ = TextUtils(text=text).split_multiline(width=text_width_limit, font=font)

        # 粘贴主体文本
        ImageDraw.Draw(image_file).multiline_text(
            xy=(image_width // 2, int(image_height * 5 / 9)),
            text=text_, font=font, align='left', anchor='mm',
            spacing=16,
            fill=(0, 0, 0))

        return image_file

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_static_xibaoh(
        text: str, image_file: Image.Image, font_path: str, image_width: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    喜报横版情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本主体
        font_size = image_width // 16
        font = ImageFont.truetype(font_path, font_size)
        text_stroke_width = int(font_size / 15)
        text_width_limit = int(image_width * 0.75)

        # 分割文本
        text_ = TextUtils(text=text).split_multiline(width=text_width_limit, font=font, stroke_width=text_stroke_width)

        # 粘贴主体文本
        ImageDraw.Draw(image_file).multiline_text(
            xy=(image_width // 2, int(image_height / 2)),
            text=text_, font=font, align='left', anchor='mm',
            spacing=16,
            stroke_width=text_stroke_width,
            stroke_fill=(255, 255, 153),
            fill=(238, 0, 0))

        return image_file

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


async def stick_maker_static_xibaos(
        text: str, image_file: Image.Image, font_path: str, image_width: int, image_height: int,
        *args, **kwargs) -> Image.Image:
    """
    喜报竖版情包模板
    """
    def __handle() -> Image.Image:
        # 处理文本主体
        font_size = image_width // 18
        font = ImageFont.truetype(font_path, font_size)
        text_stroke_width = int(font_size / 50)
        text_width_limit = int(image_width * 0.75)

        # 分割文本
        text_ = TextUtils(text=text).split_multiline(width=text_width_limit, font=font, stroke_width=text_stroke_width)

        # 粘贴主体文本
        ImageDraw.Draw(image_file).multiline_text(
            xy=(image_width // 2, int(image_height * 8 / 13)),
            text=text_, font=font, align='center', anchor='mm',
            spacing=16,
            stroke_width=text_stroke_width,
            stroke_fill=(153, 0, 0),
            fill=(255, 255, 153))

        return image_file

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


__all__ = [
    'stick_maker_static_traitor',
    'stick_maker_static_jichou',
    'stick_maker_static_phlogo',
    'stick_maker_static_luxun',
    'stick_maker_static_jiangzhuang',
    'stick_maker_static_xibaoh',
    'stick_maker_static_xibaos'
]
