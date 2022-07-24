"""
@Author         : Ailitonia
@Date           : 2022/05/07 21:02
@FileName       : render.py
@Project        : nonebot2_miya 
@Description    : Sticker Render
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import numpy
from typing import Type, Any
from datetime import date
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from omega_miya.utils.text_utils import TextUtils
from omega_miya.local_resource import LocalResource, TmpResource
from omega_miya.web_resource import HttpFetcher
from omega_miya.web_resource.tencent_cloud import TencentTMT
from omega_miya.utils.process_utils import run_async_catching_exception

from .model import StickerRender


_STATIC_RESOURCE: LocalResource = LocalResource('images', 'sticker_maker')
"""表情包插件静态资源文件夹路径"""
_FONT_RESOURCE: LocalResource = LocalResource('fonts')
"""默认字体文件目录"""
_TMP_SOURCE: TmpResource = TmpResource('sticker_maker', 'tmp')
"""下载外部资源图片的缓存文件"""


class TraitorRender(StickerRender):
    """有内鬼表情包模板

    参数:
        - text: 生成表情包的文字内容
    """
    _sticker_name: str = 'traitor'
    _static_resource: LocalResource = _STATIC_RESOURCE('traitor', 'default_bg.png')
    _font: LocalResource = _FONT_RESOURCE('pixel.ttf')
    _default_output_width = 800

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        self.source_image = self._static_resource
        image = self._load_source_image()
        image = self._zoom_pil_image_width(image=image, width=self._default_output_width)
        text = self.text[:100]

        # 初始化背景图层
        background = Image.new(mode='RGB', size=image.size, color=(255, 255, 255))

        # 处理文字层 字数部分
        text_num_img = Image.new(mode='RGBA', size=image.size, color=(0, 0, 0, 0))
        font_num_size = int(image.width / 16.6)
        font_num = ImageFont.truetype(self._font.resolve_path, font_num_size)
        ImageDraw.Draw(text_num_img).text(xy=(0, 0), text=f'{len(text)}/100', font=font_num, fill=(255, 255, 255))

        # 处理文字层 主体部分
        text_main_img = Image.new(mode='RGBA', size=image.size, color=(0, 0, 0, 0))
        font_main_size = int(image.width / 15.6)
        font_main = ImageFont.truetype(self._font.resolve_path, font_main_size)
        # 按长度切分文本
        test_main_fin = TextUtils(text=text).split_multiline(width=int(image.width * 0.53), font=font_main).text
        ImageDraw.Draw(text_main_img).multiline_text(xy=(0, 0), text=test_main_fin, font=font_main, spacing=12,
                                                     fill=(0, 0, 0))

        # 处理文字部分旋转
        text_num_img = text_num_img.rotate(angle=-9, expand=True, resample=Image.BICUBIC, center=(0, 0))
        text_main_img = text_main_img.rotate(angle=-9.25, expand=True, resample=Image.BICUBIC, center=(0, 0))

        # 向模板图片中置入文字图层
        background.paste(im=image, box=(0, 0))
        background.paste(im=text_num_img, box=(int(image.width / 1.84), int(image.width / 5.715)), mask=text_num_img)
        background.paste(im=text_main_img, box=(int(image.width / 6.4), int(image.width / 5.16)), mask=text_main_img)
        content = self._get_pil_image(image=background)
        return content


class JichouRender(StickerRender):
    """记仇表情包模板

    参数:
        - text: 生成表情包的文字内容
    """
    _sticker_name: str = 'jichou'
    _static_resource: LocalResource = _STATIC_RESOURCE('jichou', 'default_bg.png')
    _font: LocalResource = _FONT_RESOURCE('SourceHanSansSC-Regular.otf')

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        self.source_image = self._static_resource
        image = self._load_source_image()
        image = self._zoom_pil_image_width(image=image, width=self._default_output_width)

        # 处理文本主体
        text = f'今天是{date.today().strftime("%Y年%m月%d日")}，{self.text}，这个仇我先记下了'

        font_main_size = int(image.width / 12)
        font = ImageFont.truetype(self._font.resolve_path, font_main_size)
        # 按长度切分文本
        text_main_fin = TextUtils(text=text).split_multiline(width=(image.width * 7 // 8), font=font).text
        text_w, text_h = font.getsize_multiline(text_main_fin)

        # 处理图片
        background_h = int(image.height * 1.08) + text_h
        background = Image.new(mode='RGB', size=(image.width, background_h), color=(255, 255, 255))

        # 处理粘贴位置 顶头
        background.paste(image, (0, 0))

        draw = ImageDraw.Draw(background)
        # 计算居中文字位置
        text_coordinate = ((image.width // 2), int(image.height))
        draw.multiline_text(text_coordinate, text_main_fin, anchor='ma', font=font, fill=(0, 0, 0))
        content = self._get_pil_image(image=background)
        return content


class PhlogoRender(StickerRender):
    """ph 表情包模板

    参数:
        - text: 生成表情包的文字内容
    """
    _sticker_name: str = 'phlogo'
    _font: LocalResource = _FONT_RESOURCE('SourceHanSansSC-Heavy.otf')
    _default_font_size = 320

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        # 处理文本主体
        test_sentences = self.text.strip().split(maxsplit=1)
        match len(test_sentences):
            case 2:
                white_text = test_sentences[0]
                yellow_text = test_sentences[1]
            case _:
                white_text = self.text[:len(self.text)//2]
                yellow_text = self.text[len(self.text)//2:]

        font = ImageFont.truetype(self._font.resolve_path, self._default_font_size)

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
        background = Image.new(mode='RGB', size=(image_width_, image_height_), color=(0, 0, 0))
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
        content = self._get_pil_image(image=background)
        return content


class LuxunSayRender(StickerRender):
    """鲁迅说表情包模板

    参数:
        - text: 生成表情包的文字内容
    """
    _sticker_name: str = 'luxunsay'
    _static_resource: LocalResource = _STATIC_RESOURCE('luxunsay', 'default_bg.png')
    _font: LocalResource = _FONT_RESOURCE('SourceHanSansSC-Regular.otf')

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        self.source_image = self._static_resource
        image = self._load_source_image()
        image = self._zoom_pil_image_width(image=image, width=self._default_output_width)

        # 处理文本主体
        font_size = image.width // 15
        text_stroke_width = int(font_size / 15)
        font = ImageFont.truetype(self._font.resolve_path, font_size)
        text_width_limit = int(image.width * 0.8125)

        sign_text = '—— 鲁迅'

        # 分割文本
        text_ = TextUtils(text=self.text).split_multiline(width=text_width_limit, font=font,
                                                          stroke_width=text_stroke_width).text

        # 文本大小
        main_text_width, main_text_height = font.getsize_multiline(text_, stroke_width=text_stroke_width)
        sign_text_width, sign_text_height = font.getsize(sign_text, stroke_width=text_stroke_width)

        # 创建背景图层
        # 定位主体文字到图片下侧往上 1/4 处, 落款与主体文字间隔半行, 底部间隔一行, 超出部分为所有文字高度减去图片 1/4 高度
        bg_height_inc_ = int(main_text_height + sign_text_height * 2.5 - image.height * 0.25)
        bg_height_inc = bg_height_inc_ if bg_height_inc_ > 0 else 0
        background = Image.new(
            mode='RGB',
            size=(image.width, image.height + bg_height_inc),
            color=(32, 32, 32))

        # 先把鲁迅图贴上去
        background.paste(image, box=(0, 0))

        # 再贴主体文本
        ImageDraw.Draw(background).multiline_text(
            xy=(image.width // 2, int(image.height * 0.75)),
            text=text_, font=font, align='left', anchor='ma',
            fill=(255, 255, 255),
            stroke_width=text_stroke_width,
            stroke_fill=(0, 0, 0))

        ImageDraw.Draw(background).text(
            xy=(int(image.width * 0.85), int(main_text_height + sign_text_height / 2 + image.height * 0.75)),
            text=sign_text, font=font, align='right', anchor='ra',
            fill=(255, 255, 255),
            stroke_width=text_stroke_width,
            stroke_fill=(0, 0, 0))

        content = self._get_pil_image(image=background)
        return content


class LuxunWriteRender(LuxunSayRender):
    """鲁迅写表情包模板

    参数:
        - text: 生成表情包的文字内容
    """
    _sticker_name: str = 'luxunwrite'
    _static_resource: LocalResource = _STATIC_RESOURCE('luxunwrite', 'default_bg.png')

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError


class JiangzhuangRender(StickerRender):
    """奖状表情包模板

    参数:
        - text: 生成表情包的文字内容
    """
    _sticker_name: str = 'jiangzhuang'
    _static_resource: LocalResource = _STATIC_RESOURCE('jiangzhuang', 'default_bg.png')
    _font: LocalResource = _FONT_RESOURCE('HanYiWeiBeiJian.ttf')
    _default_output_width = 1024

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        self.source_image = self._static_resource
        image = self._load_source_image()
        image = self._zoom_pil_image_width(image=image, width=self._default_output_width)

        # 处理文本主体
        font_size = image.width // 22
        font = ImageFont.truetype(self._font.resolve_path, font_size)
        text_width_limit = int(image.width * 0.65)

        # 分割文本
        text_ = TextUtils(text=self.text).split_multiline(width=text_width_limit, font=font).text

        # 粘贴主体文本
        ImageDraw.Draw(image).multiline_text(
            xy=(image.width // 2, int(image.height * 5 / 9)),
            text=text_, font=font, align='left', anchor='mm',
            spacing=16,
            fill=(0, 0, 0))

        content = self._get_pil_image(image=image)
        return content


class XibaoHorizontalRender(StickerRender):
    """喜报横版情包模板

    参数:
        - text: 生成表情包的文字内容
    """
    _sticker_name: str = 'xibaoh'
    _static_resource: LocalResource = _STATIC_RESOURCE('xibaoh', 'default_bg.png')
    _font: LocalResource = _FONT_RESOURCE('HanYiWeiBeiJian.ttf')
    _default_output_width = 1024

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        self.source_image = self._static_resource
        image = self._load_source_image()
        image = self._zoom_pil_image_width(image=image, width=self._default_output_width)

        # 处理文本主体
        font_size = image.width // 15
        font = ImageFont.truetype(self._font.resolve_path, font_size)
        text_stroke_width = int(font_size / 15)
        text_width_limit = int(image.width * 0.75)

        # 分割文本
        text_ = TextUtils(text=self.text).split_multiline(width=text_width_limit, font=font,
                                                          stroke_width=text_stroke_width).text

        # 粘贴主体文本
        ImageDraw.Draw(image).multiline_text(
            xy=(image.width // 2, int(image.height / 2)),
            text=text_, font=font, align='left', anchor='mm',
            spacing=16,
            stroke_width=text_stroke_width,
            stroke_fill=(255, 255, 153),
            fill=(238, 0, 0))

        content = self._get_pil_image(image=image)
        return content


class XibaoVerticalRender(StickerRender):
    """喜报竖版情包模板

    参数:
        - text: 生成表情包的文字内容
    """
    _sticker_name: str = 'xibaos'
    _static_resource: LocalResource = _STATIC_RESOURCE('xibaos', 'default_bg.png')
    _font: LocalResource = _FONT_RESOURCE('SourceHanSerif-Bold.ttc')
    _default_output_width = 1024

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        self.source_image = self._static_resource
        image = self._load_source_image()
        image = self._zoom_pil_image_width(image=image, width=self._default_output_width)

        # 处理文本主体
        font_size = image.width // 15
        font = ImageFont.truetype(self._font.resolve_path, font_size)
        text_stroke_width = int(font_size / 50)
        text_width_limit = int(image.width * 0.75)

        # 分割文本
        text_ = TextUtils(text=self.text).split_multiline(width=text_width_limit, font=font,
                                                          stroke_width=text_stroke_width).text

        # 粘贴主体文本
        ImageDraw.Draw(image).multiline_text(
            xy=(image.width // 2, int(image.height * 10 / 17)),
            text=text_, font=font, align='center', anchor='mm',
            spacing=16,
            stroke_width=text_stroke_width,
            stroke_fill=(153, 0, 0),
            fill=(255, 255, 153))

        content = self._get_pil_image(image=image)
        return content


class DefaultRender(StickerRender):
    """默认加字表情包模板

    参数:
        - text: 生成表情包的文字内容
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'default'
    _font: LocalResource = _FONT_RESOURCE('msyhbd.ttc')
    _need_external_img: bool = True

    def _static_handler(self, image: Image) -> bytes:
        font_size = image.width // 8
        text_stroke_width = int(font_size / 20)
        font = ImageFont.truetype(self._font.resolve_path, font_size)

        text_w, text_h = font.getsize_multiline(self.text, stroke_width=text_stroke_width)
        # 自适应处理文字大小
        while text_w >= int(image.width * 0.95):
            font_size -= 1
            font = ImageFont.truetype(self._font.resolve_path, font_size)
            text_w, text_h = font.getsize_multiline(self.text, stroke_width=text_stroke_width)
        # 计算居中文字位置
        text_coordinate = (image.width // 2, 9 * (image.height - text_h) // 10)
        ImageDraw.Draw(image).multiline_text(xy=text_coordinate,
                                             text=self.text,
                                             font=font, fill=(255, 255, 255),
                                             align='center', anchor='ma',
                                             stroke_width=text_stroke_width,
                                             stroke_fill=(0, 0, 0))

        content = self._get_pil_image(image=image)
        return content

    def _gif_handler(self, frames: list[Image], duration: float) -> bytes:
        content = self._generate_gif_from_bytes_seq(
            frames=(self._static_handler(image=image) for image in frames),
            duration=duration
        )
        return content

    def _handler(self) -> bytes:
        fm, info = self._get_source_image_info()
        if fm == 'GIF':
            frames = []
            frame_index = 0
            while True:
                try:
                    image = self._load_source_image(frame=frame_index)
                    frames.append(image)
                    frame_index += 1
                except EOFError:
                    break
            duration = info.get('duration', 60) / 1000
            self._default_output_format = 'gif'
            content = self._gif_handler(frames=frames, duration=duration)
        else:
            image = self._load_source_image()
            image = self._zoom_pil_image_width(image=image, width=self._default_output_width)
            content = self._static_handler(image=image)

        return content


class LittleAngelRender(StickerRender):
    """小天使表情包模板

    参数:
        - text: 生成表情包的文字内容
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'littleangel'
    _font: LocalResource = _FONT_RESOURCE('msyhbd.ttc')
    _need_external_img: bool = True

    def _static_handler(self, image: Image) -> bytes:
        # 处理文本内容
        font_size_up = int(image.width / 7)
        font_up = ImageFont.truetype(self._font.resolve_path, font_size_up)
        text_up = f'请问你们看到{self.text}了吗?'
        text_up_w, text_up_h = font_up.getsize(text_up)
        # 自适应处理文字大小
        while text_up_w >= int(image.width * 1.14):
            font_size_up -= 1
            font_up = ImageFont.truetype(self._font.resolve_path, font_size_up)
            text_up_w, text_up_h = font_up.getsize(text_up)

        # 处理图片
        background = Image.new(mode='RGB',
                               size=(int(image.width * 1.2), int(image.width * 0.368 + text_up_h + image.height)),
                               color=(255, 255, 255))

        # 粘贴头部文字
        ImageDraw.Draw(background).text(
            xy=(background.width // 2, int(image.width * 0.0512)),
            text=text_up, anchor='ma', font=font_up, fill=(0, 0, 0))

        # 处理图片粘贴位置
        image_coordinate = (((background.width - image.width) // 2), int(image.width * 0.096 + text_up_h))
        background.paste(image, image_coordinate)

        # 粘贴底部文字
        font_down_1 = ImageFont.truetype(self._font.resolve_path, int(background.width / 12.75))
        text_down_1 = r'非常可爱! 简直就是小天使'
        ImageDraw.Draw(background).text(
            xy=(background.width // 2, int(image.width * 0.135 + image.height + text_up_h)),
            text=text_down_1, anchor='ma', font=font_down_1, fill=(0, 0, 0)
        )

        font_down_2 = ImageFont.truetype(self._font.resolve_path, int(background.width / 23.54))
        text_down_2 = r'她没失踪也没怎么样  我只是觉得你们都该看一下'
        ImageDraw.Draw(background).text(
            xy=(background.width // 2, int(image.width * 0.255 + image.height + text_up_h)),
            text=text_down_2, anchor='ma', font=font_down_2, fill=(0, 0, 0)
        )

        content = self._get_pil_image(image=background)
        return content

    def _gif_handler(self, frames: list[Image], duration: float) -> bytes:
        content = self._generate_gif_from_bytes_seq(
            frames=(self._static_handler(image=image) for image in frames),
            duration=duration
        )
        return content

    def _handler(self) -> bytes:
        fm, info = self._get_source_image_info()
        if fm == 'GIF':
            frames = []
            frame_index = 0
            while True:
                try:
                    image = self._load_source_image(frame=frame_index)
                    frames.append(image)
                    frame_index += 1
                except EOFError:
                    break
            duration = info.get('duration', 60) / 1000
            self._default_output_format = 'gif'
            content = self._gif_handler(frames=frames, duration=duration)
        else:
            image = self._load_source_image()
            image = self._zoom_pil_image_width(image=image, width=self._default_output_width)
            content = self._static_handler(image=image)

        return content


class WhiteBackgroundRender(StickerRender):
    """白底加字表情包模板

    参数:
        - text: 生成表情包的文字内容
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'whitebackground'
    _font: LocalResource = _FONT_RESOURCE('msyhbd.ttc')
    _need_external_img: bool = True

    def _static_handler(self, image: Image) -> bytes:
        font_size = image.width // 10
        font = ImageFont.truetype(self._font.resolve_path, font_size)
        text_w, text_h = font.getsize_multiline(self.text)
        # 自适应处理文字大小
        while text_w >= int(image.width * 8 / 9):
            font_size -= 1
            font = ImageFont.truetype(self._font.resolve_path, font_size)
            text_w, text_h = font.getsize_multiline(self.text)

        # 处理图片
        background = Image.new(mode='RGB', size=(image.width, int(image.height + image.width * 0.06 + text_h)),
                               color=(255, 255, 255))

        # 处理粘贴位置 顶头
        background.paste(image, (0, 0))

        # 计算居中文字位置
        ImageDraw.Draw(background).multiline_text(
            xy=(background.width // 2, int(image.height + image.width * 0.015)),
            text=self.text, align='center', anchor='ma', font=font, fill=(0, 0, 0))

        content = self._get_pil_image(image=background)
        return content

    def _gif_handler(self, frames: list[Image], duration: float) -> bytes:
        content = self._generate_gif_from_bytes_seq(
            frames=(self._static_handler(image=image) for image in frames),
            duration=duration
        )
        return content

    def _handler(self) -> bytes:
        fm, info = self._get_source_image_info()
        if fm == 'GIF':
            frames = []
            frame_index = 0
            while True:
                try:
                    image = self._load_source_image(frame=frame_index)
                    frames.append(image)
                    frame_index += 1
                except EOFError:
                    break
            duration = info.get('duration', 60) / 1000
            self._default_output_format = 'gif'
            content = self._gif_handler(frames=frames, duration=duration)
        else:
            image = self._load_source_image()
            image = self._zoom_pil_image_width(image=image, width=self._default_output_width)
            content = self._static_handler(image=image)

        return content


class BlackBackgroundRender(StickerRender):
    """黑边加底字表情包模板

    参数:
        - text: 生成表情包的文字内容
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'blackbackground'
    _font: LocalResource = _FONT_RESOURCE('msyhbd.ttc')
    _need_external_img: bool = True

    def _static_handler(self, image: Image) -> bytes:
        font_size = image.width // 8
        font = ImageFont.truetype(self._font.resolve_path, font_size)
        text_w, text_h = font.getsize_multiline(self.text)
        # 自适应处理文字大小
        while text_w >= int(image.width * 1.1):
            font_size -= 1
            font = ImageFont.truetype(self._font.resolve_path, font_size)
            text_w, text_h = font.getsize_multiline(self.text)

        # 处理图片
        background = Image.new(mode='RGB', color=(0, 0, 0),
                               size=(int(image.width * 1.3), int(image.height + image.width * 0.3 + text_h)))
        background.paste(image, (int(image.width * 0.15), int(image.width * 0.15)))

        # 计算居中文字位置
        ImageDraw.Draw(background).multiline_text(
            xy=(background.width // 2, int(image.height + image.width * 0.2)),
            text=self.text, align='center', anchor='ma', font=font, fill=(255, 255, 255))

        content = self._get_pil_image(image=background)
        return content

    def _gif_handler(self, frames: list[Image], duration: float) -> bytes:
        content = self._generate_gif_from_bytes_seq(
            frames=(self._static_handler(image=image) for image in frames),
            duration=duration
        )
        return content

    def _handler(self) -> bytes:
        fm, info = self._get_source_image_info()
        if fm == 'GIF':
            frames = []
            frame_index = 0
            while True:
                try:
                    image = self._load_source_image(frame=frame_index)
                    frames.append(image)
                    frame_index += 1
                except EOFError:
                    break
            duration = info.get('duration', 60) / 1000
            self._default_output_format = 'gif'
            content = self._gif_handler(frames=frames, duration=duration)
        else:
            image = self._load_source_image()
            image = self._zoom_pil_image_width(image=image, width=self._default_output_width)
            content = self._static_handler(image=image)

        return content


class DeColorizeRender(StickerRender):
    """去色表情包模板

    参数:
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'decolorize'
    _need_text: bool = False
    _need_external_img: bool = True

    def _static_handler(self, image: Image) -> bytes:
        image = image.convert('RGB')
        enhancer = ImageEnhance.Color(image)
        made_image = enhancer.enhance(0)
        content = self._get_pil_image(image=made_image)
        return content

    def _gif_handler(self, frames: list[Image], duration: float) -> bytes:
        content = self._generate_gif_from_bytes_seq(
            frames=(self._static_handler(image=image) for image in frames),
            duration=duration
        )
        return content

    def _handler(self) -> bytes:
        fm, info = self._get_source_image_info()
        if fm == 'GIF':
            frames = []
            frame_index = 0
            while True:
                try:
                    image = self._load_source_image(frame=frame_index)
                    frames.append(image)
                    frame_index += 1
                except EOFError:
                    break
            duration = info.get('duration', 60) / 1000
            self._default_output_format = 'gif'
            content = self._gif_handler(frames=frames, duration=duration)
        else:
            image = self._load_source_image()
            content = self._static_handler(image=image)

        return content


class GunjoRender(StickerRender):
    """群青表情包模板

    参数:
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'gunjo'
    _need_text: bool = False
    _need_external_img: bool = True
    _default_output_width = 512
    _font: LocalResource = _FONT_RESOURCE('SourceHanSansSC-Bold.otf')

    def _static_handler(self, image: Image) -> bytes:
        image = image.convert('RGBA')

        # 图片去色
        made_image = ImageEnhance.Color(image).enhance(0)

        # 图片转化为透明度蒙版到底色背景上
        mask = made_image.convert('L')
        background_color = (28, 48, 180)
        background = Image.new(mode='RGBA', size=image.size, color=background_color)
        background.paste(im=made_image, mask=mask)

        # 写字
        upper_font_size = int(image.width / 6)
        upper_font = ImageFont.truetype(self._font.resolve_path, upper_font_size)
        upper_text_coordinate = (int(image.width * 12 / 13), int(image.height / 11))

        _, upper_text_height = upper_font.getsize_multiline('群\n青', stroke_width=upper_font_size // 20)
        ImageDraw.Draw(background).multiline_text(
            xy=upper_text_coordinate, text='群\n青', anchor='ra', align='center', font=upper_font,
            fill=(255, 255, 255), stroke_width=upper_font_size // 20, stroke_fill=background_color
        )

        lower_font_size = int(image.width / 12)
        lower_font = ImageFont.truetype(self._font.resolve_path, lower_font_size)
        lower_text_coordinate = (int(image.width * 12 / 13), upper_text_coordinate[1] + upper_text_height)
        ImageDraw.Draw(background).text(
            xy=lower_text_coordinate, text='YOASOBI', anchor='ra', align='center', font=lower_font,
            fill=(255, 255, 255), stroke_width=lower_font_size // 10, stroke_fill=background_color
        )

        content = self._get_pil_image(image=background)
        return content

    def _gif_handler(self, frames: list[Image], duration: float) -> bytes:
        content = self._generate_gif_from_bytes_seq(
            frames=(self._static_handler(image=image) for image in frames),
            duration=duration
        )
        return content

    def _handler(self) -> bytes:
        fm, info = self._get_source_image_info()
        if fm == 'GIF':
            frames = []
            frame_index = 0
            while True:
                try:
                    image = self._load_source_image(frame=frame_index)
                    frames.append(image)
                    frame_index += 1
                except EOFError:
                    break
            duration = info.get('duration', 60) / 1000
            self._default_output_format = 'gif'
            content = self._gif_handler(frames=frames, duration=duration)
        else:
            image = self._load_source_image()
            image = self._zoom_pil_image_width(image=image, width=self._default_output_width)
            content = self._static_handler(image=image)

        return content


class MarriageRender(StickerRender):
    """结婚登记表情包模板

    参数:
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'marriage'
    _static_resource: LocalResource = _STATIC_RESOURCE('marriage', 'default_bg.png')
    _need_text: bool = False
    _need_external_img: bool = True
    _default_output_width = 1080

    def _static_handler(self, image: Image, *, resize_width: int | None = None) -> bytes:
        upper_image = self._load_extra_source_image(source_file=self._static_resource)

        background = Image.new(mode='RGBA', size=image.size, color=(255, 255, 255, 255))
        background.paste(im=image, box=(0, 0), mask=image)
        background.paste(im=upper_image, box=(0, 0), mask=upper_image)

        if resize_width:
            background = self._zoom_pil_image_width(image=background, width=resize_width)
        content = self._get_pil_image(image=background)
        return content

    def _gif_handler(self, frames: list[Image], duration: float, output_width: int) -> bytes:
        content = self._generate_gif_from_bytes_seq(
            frames=(self._static_handler(image=image, resize_width=output_width) for image in frames),
            duration=duration
        )
        return content

    def _handler(self) -> bytes:
        fm, info = self._get_source_image_info()
        if fm == 'GIF':
            frames = []
            frame_index = 0
            output_width = 360
            while True:
                try:
                    image = self._load_source_image(frame=frame_index)
                    output_width = image.width
                    image = self._resize_with_filling(
                        image=image,
                        size=(self._default_output_width, self._default_output_width)
                    )
                    frames.append(image)
                    frame_index += 1
                except EOFError:
                    break
            duration = info.get('duration', 60) / 1000
            self._default_output_format = 'gif'
            content = self._gif_handler(frames=frames, duration=duration, output_width=output_width)
        else:
            image = self._load_source_image()
            image = self._resize_with_filling(
                image=image,
                size=(self._default_output_width, self._default_output_width)
            )
            content = self._static_handler(image=image)

        return content


class GrassJaRender(StickerRender):
    """生草日语表情包模板

    参数:
        - text: 生成表情包的文字内容
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'grassja'
    _font: LocalResource = _FONT_RESOURCE('fzzxhk.ttf')
    _need_external_img: bool = True

    def _static_handler(self, image: Image) -> bytes:
        image = image.convert('RGB')
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(0)

        # 分割文本
        font_zh = ImageFont.truetype(self._font.resolve_path, int(image.width / 13))
        font_jp = ImageFont.truetype(self._font.resolve_path, int(image.width / 24))

        text_zh, text_jp = self.text.split(maxsplit=1)
        text_zh = TextUtils(text=text_zh).split_multiline(width=int(image.width * 0.9), font=font_zh).text
        text_jp = TextUtils(text=text_jp).split_multiline(width=int(image.width * 0.9), font=font_jp).text

        _, text_zh_h = font_zh.getsize_multiline(text_zh)
        _, text_jp_h = font_jp.getsize_multiline(text_jp)

        # 处理图片
        background = Image.new(mode='RGB', color=(0, 0, 0),
                               size=(image.width, int(image.height + image.width * 0.08 + text_zh_h + text_jp_h)))

        # 处理粘贴位置
        background.paste(image, (0, 0))

        # 粘贴文字
        ImageDraw.Draw(background).multiline_text(
            xy=(background.width // 2, int(image.height + image.width * 0.025)),
            text=text_zh, align='center', anchor='ma', font=font_zh, fill=(255, 255, 255))
        ImageDraw.Draw(background).multiline_text(
            xy=(background.width // 2, int(image.height + image.width * 0.05 + text_zh_h)),
            text=text_jp, align='center', anchor='ma', font=font_jp, fill=(255, 255, 255))

        content = self._get_pil_image(image=background)
        return content

    def _gif_handler(self, frames: list[Image], duration: float) -> bytes:
        content = self._generate_gif_from_bytes_seq(
            frames=(self._static_handler(image=image) for image in frames),
            duration=duration
        )
        return content

    def _handler(self) -> bytes:
        fm, info = self._get_source_image_info()
        if fm == 'GIF':
            frames = []
            frame_index = 0
            while True:
                try:
                    image = self._load_source_image(frame=frame_index)
                    frames.append(image)
                    frame_index += 1
                except EOFError:
                    break
            duration = info.get('duration', 60) / 1000
            self._default_output_format = 'gif'
            content = self._gif_handler(frames=frames, duration=duration)
        else:
            image = self._load_source_image()
            image = self._zoom_pil_image_width(image=image, width=self._default_output_width)
            content = self._static_handler(image=image)

        return content

    async def _translate_preprocessor(self) -> None:
        text_zh = self.text.replace('\n', ' ')
        text_trans_result = await TencentTMT().translate(source_text=self.text, target='ja')
        if text_trans_result.error:
            text_ja = '翻訳に失敗しました！'
        else:
            text_ja = text_trans_result.Response.TargetText
        text_ja = text_ja.replace('\n', ' ')
        self.text = f'{text_zh.strip()}\n{text_ja.strip()}'

    async def make(self) -> TmpResource:
        _make = super().make
        await self._translate_preprocessor()
        return await _make()


class PetPetRender(StickerRender):
    """petpet 表情包模板

    参数:
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'petpet'
    _static_resource: LocalResource = _STATIC_RESOURCE('petpet')
    _need_text: bool = False
    _need_external_img: bool = True
    _default_output_format: str = 'gif'

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        resize_paste_loc: list[tuple[tuple[int, int], tuple[int, int]]] = [
            ((95, 95), (12, 15)),
            ((97, 80), (11, 30)),
            ((99, 70), (10, 40)),
            ((97, 75), (11, 35)),
            ((96, 90), (11, 20))
        ]
        image = self._load_source_image()
        frames_list = []
        for frame_index in range(5):
            background = Image.new(mode='RGBA', size=(112, 112), color=(255, 255, 255))
            frame = Image.open(self._static_resource(f'template_p{frame_index}.png').resolve_path)
            background.paste(image.resize(resize_paste_loc[frame_index][0]), resize_paste_loc[frame_index][1])
            background.paste(frame, (0, 0), mask=frame)
            with BytesIO() as f_bf:
                background.save(f_bf, format='PNG')
                frames_list.append(f_bf.getvalue())

        content = self._generate_gif_from_bytes_seq(frames=frames_list, duration=0.06)

        return content


class WorshipRender(StickerRender):
    """膜拜表情包模板

    参数:
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'worship'
    _static_resource: LocalResource = _STATIC_RESOURCE('worship')
    _need_text: bool = False
    _need_external_img: bool = True
    _default_output_format: str = 'gif'

    @staticmethod
    def _get_perspective_data(
            target_point: tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]],
            source_point: tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]
    ) -> Any:
        """Method to determine perspective transformation coefficients

        https://stackoverflow.com/questions/14177744/how-does-perspective-transformation-work-in-pil/14178717#14178717
        """
        matrix = []
        for p1, p2 in zip(target_point, source_point):
            matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
            matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])

        target_matrix = numpy.matrix(matrix, dtype=numpy.float)
        source_array = numpy.array(source_point).reshape(8)

        res = numpy.dot(numpy.linalg.inv(target_matrix.T * target_matrix) * target_matrix.T, source_array)
        return numpy.array(res).reshape(8)

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        image = self._load_source_image()
        width, height = image.size
        perspective_data = self._get_perspective_data(
            target_point=((0, -30), (135, 17), (135, 145), (0, 140)),
            source_point=((0, 0), (width, 0), (width, height), (0, height))
        )
        p_image = image.transform(size=image.size, method=Image.PERSPECTIVE, data=perspective_data, fill=Image.BICUBIC)
        p_image = p_image.convert('RGBA')

        frames_list = []
        for frame_index in range(10):
            background = Image.new(mode='RGBA', size=(300, 169), color=(255, 255, 255, 255))
            frame = Image.open(self._static_resource(f'template_p{frame_index}.png').resolve_path)
            background.paste(im=p_image, box=(0, 0), mask=p_image)
            background.paste(im=frame, box=(0, 0), mask=frame)
            with BytesIO() as f_bf:
                background.save(f_bf, format='PNG')
                frames_list.append(f_bf.getvalue())

        content = self._generate_gif_from_bytes_seq(frames=frames_list, duration=0.04)

        return content


class TwistRender(StickerRender):
    """搓表情包模板

    参数:
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'worship'
    _static_resource: LocalResource = _STATIC_RESOURCE('twist')
    _need_text: bool = False
    _need_external_img: bool = True
    _default_output_format: str = 'gif'

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        image = self._load_source_image()
        image = self._resize_with_filling(image=image, size=(128, 128))

        angle = 0
        paste_coordinate: list[tuple[int, int]] = [
            (35, 101), (37, 101), (37, 101), (37, 101), (37, 99), (35, 101), (37, 101), (37, 101), (37, 101), (37, 99)
        ]

        frames_list = []
        for frame_index in range(10):
            background = Image.new(mode='RGBA', size=(256, 256), color=(255, 255, 255, 255))
            frame = Image.open(self._static_resource(f'template_p{frame_index}.png').resolve_path)

            frame_image = image.rotate(angle=angle, center=(64, 64), expand=False,
                                       resample=Image.BICUBIC, fillcolor=(255, 255, 255))

            background.paste(im=frame_image, box=paste_coordinate[frame_index], mask=frame_image)
            background.paste(im=frame, box=(0, 0), mask=frame)
            with BytesIO() as f_bf:
                background.save(f_bf, format='PNG')
                frames_list.append(f_bf.getvalue())
            angle += 36

        content = self._generate_gif_from_bytes_seq(frames=frames_list, duration=0.03)

        return content


class WangjingzeRender(StickerRender):
    """王境泽表情包模板

    参数:
        - source_image: 生成素材图片
    """
    _sticker_name: str = 'wangjingze'
    _font: LocalResource = _FONT_RESOURCE('SourceHanSansSC-Regular.otf')
    _static_resource: LocalResource = _STATIC_RESOURCE('wangjingze')
    _need_text: bool = True
    _need_external_img: bool = False
    _default_output_format: str = 'gif'

    def _gif_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _static_handler(self, *args, **kwargs) -> bytes:
        raise NotImplementedError

    def _handler(self) -> bytes:
        # 分割文本
        text_list = self.text.split(maxsplit=3)
        if (text_len := len(text_list)) < 4:
            text_list.extend(['' for _ in range(4 - text_len)])

        font = ImageFont.truetype(self._font.resolve_path, 22)

        frames_list = []
        for frame_index in range(46):
            frame = Image.open(self._static_resource(f'template_p{frame_index}.jpg').resolve_path)

            if 0 <= frame_index <= 8:
                ImageDraw.Draw(frame).text(
                    xy=(219, 223), text=text_list[0], font=font, anchor='ma', align='center',
                    stroke_width=2, stroke_fill=(0, 0, 0)
                )
            elif 12 <= frame_index <= 23:
                ImageDraw.Draw(frame).text(
                    xy=(219, 223), text=text_list[1], font=font, anchor='ma', align='center',
                    stroke_width=2, stroke_fill=(0, 0, 0)
                )
            elif 25 <= frame_index <= 34:
                ImageDraw.Draw(frame).text(
                    xy=(219, 223), text=text_list[2], font=font, anchor='ma', align='center',
                    stroke_width=2, stroke_fill=(0, 0, 0)
                )
            elif 36 <= frame_index <= 42:
                ImageDraw.Draw(frame).text(
                    xy=(219, 223), text=text_list[3], font=font, anchor='ma', align='center',
                    stroke_width=2, stroke_fill=(0, 0, 0)
                )

            with BytesIO() as bf:
                frame.save(bf, format='JPEG')
                frames_list.append(bf.getvalue())

        content = self._generate_gif_from_bytes_seq(frames=frames_list, duration=0.13)

        return content


_ALL_Render: dict[str, Type[StickerRender]] = {
    '默认': DefaultRender,
    '白底': WhiteBackgroundRender,
    '黑底': BlackBackgroundRender,
    '黑白': DeColorizeRender,
    '小天使': LittleAngelRender,
    '生草日语': GrassJaRender,
    '群青': GunjoRender,
    '结婚登记': MarriageRender,
    '有内鬼': TraitorRender,
    '记仇': JichouRender,
    '鲁迅说': LuxunSayRender,
    '鲁迅写': LuxunWriteRender,
    '奖状': JiangzhuangRender,
    '喜报横版': XibaoHorizontalRender,
    '喜报竖版': XibaoVerticalRender,
    'ph': PhlogoRender,
    'petpet': PetPetRender,
    '膜拜': WorshipRender,
    '搓': TwistRender,
    '王境泽': WangjingzeRender
}


def get_render(render_name: str) -> Type[StickerRender]:
    """获取表情包 Render"""
    return _ALL_Render[render_name]


def get_all_render_name() -> list[str]:
    """获取所有表情包 Render 名称"""
    return [str(x) for x in _ALL_Render.keys()]


@run_async_catching_exception
async def download_source_image(url: str) -> TmpResource:
    """下载图片到本地, 保持原始文件名, 直接覆盖同名文件"""
    file_name = HttpFetcher.hash_url_file_name('sticker_source_tmp', url=url)
    file = _TMP_SOURCE(file_name)
    download_result = await HttpFetcher().download_file(url=url, file=file)
    if download_result.status != 200:
        raise RuntimeError(f'download failed, status {download_result.status}')
    return file


__all__ = [
    'get_render',
    'get_all_render_name',
    'download_source_image'
]
