"""
@Author         : Ailitonia
@Date           : 2022/04/09 16:20
@FileName       : text_utils.py
@Project        : nonebot2_miya
@Description    : 文本工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
import emoji
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from omega_miya.local_resource import TmpResource
from omega_miya.web_resource import HttpFetcher
from omega_miya.utils.process_utils import run_sync

from .config import text_utils_config
from .model import TextSegment, TextContent


class TextUtils(object):
    def __init__(self, text: str):
        self._text = text

    def __repr__(self):
        return f'<TextUtils(text={self._text})>'

    @property
    def text(self) -> str:
        return self._text

    def split_multiline(
            self,
            width: int,
            font: ImageFont.FreeTypeFont | str | None = None,
            *,
            stroke_width=0) -> "TextUtils":
        """按字体绘制的文本长度切分换行文本

        :param width: 宽度限制, 像素
        :param font: 绘制使用的字体, 传入 str 为本地字体资源文件名
        :param stroke_width: 文字描边, 像素
        """
        if font is None:
            font = ImageFont.truetype(text_utils_config.default_font_file.resolve_path, text_utils_config.default_size)
        elif isinstance(font, str):
            font = ImageFont.truetype(text_utils_config.default_font_folder(font).resolve_path,
                                      text_utils_config.default_size)

        spl_num = 0
        spl_list = []
        for num in range(len(self._text)):
            text_width, text_height = font.getsize_multiline(self._text[spl_num:num], stroke_width=stroke_width)
            if text_width > width:
                spl_list.append(self._text[spl_num:num])
                spl_num = num
        else:
            spl_list.append(self._text[spl_num:])

        self._text = '\n'.join(spl_list)
        return self

    def _default_text_to_img(self, *, image_width: int = 512, font_name: str | None = None) -> bytes:
        """文本转图片

        :param image_width: 限制图片宽度, 像素
        :param font_name: 字体名称, 本地资源中字体文件名
        """
        if font_name is None:
            _font_file = text_utils_config.default_font_file
        else:
            _font_file = text_utils_config.default_font_folder(font_name)

        # 处理文字层 主体部分
        _font_size = image_width // 25
        _font = ImageFont.truetype(_font_file.resolve_path, _font_size)
        # 按长度切分文本
        _text = self.split_multiline(width=int(image_width * 0.75), font=_font).text
        _text_w, _text_h = _font.getsize_multiline(_text)
        # 初始化背景图层
        _image_height = _text_h + 100
        _background = Image.new(mode="RGB", size=(image_width, _image_height), color=(255, 255, 255))
        # 绘制文字
        ImageDraw.Draw(_background).multiline_text(
            xy=(int(image_width * 0.115), 50),
            text=_text,
            font=_font,
            fill=(0, 0, 0))
        # 提取生成图的内容
        with BytesIO() as _bf:
            _background.save(_bf, 'JPEG')
            _content = _bf.getvalue()
        return _content

    async def text_to_img(self, *, image_width: int = 512, font_name: str | None = None) -> TmpResource:
        """文本转图片

        :param image_width: 限制图片宽度, 像素
        :param font_name: 字体名称, 本地资源中字体文件名
        """
        save_file_name = f"{hash(self._text)}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"
        save_file = text_utils_config.default_img_tmp_folder(save_file_name)
        file_content = await run_sync(self._default_text_to_img)(image_width=image_width, font_name=font_name)
        async with save_file.async_open('wb') as af:
            await af.write(file_content)
        return save_file


class AdvanceTextUtils(object):
    _default_font = ImageFont.truetype(font=text_utils_config.default_font_file.resolve_path, size=48)
    _emoji_font = ImageFont.truetype(font=text_utils_config.default_emoji_font.resolve_path, size=137)

    def __init__(self, content: TextContent):
        self._content = content

    def __repr__(self):
        return f'<AdvanceTextUtils(text={self.text})>'

    @property
    def text(self) -> str:
        return self._content.get_text()

    @staticmethod
    def _char_is_emoji(character: str):
        """判断字符是否是 emoji"""
        return character in emoji.EMOJI_DATA.keys()

    @classmethod
    def _parse_emoji_text_as_text_content(cls, text: str) -> list[TextSegment]:
        """将含有 emoji 的字符串解析为 TextSegment 列表"""
        text_segments: list[TextSegment] = []
        split_start_index = 0
        for index, character in enumerate(text):
            if cls._char_is_emoji(character=character):
                if emoji_spilt_text := text[split_start_index: index]:
                    text_segments.append(TextSegment.text(text=emoji_spilt_text))
                text_segments.append(TextSegment.emoji(emoji=character))
                split_start_index = index + 1
        else:
            if end_text := text[split_start_index:]:
                text_segments.append(TextSegment.text(text=end_text))

        return text_segments

    @classmethod
    def parse_as_text_content(cls, text: str) -> TextContent:
        """将字符串转化为 TextContent 对象, 同时解析形如 '[image: https://image_url]' 的字符串为 TextSegment"""
        text_segments: list[TextSegment] = []
        split_start_index = 0
        for i in re.compile(r"(\[(text|emoji|image):\s(.+?)])").finditer(text):
            split_end_index = i.span()[0]
            text_segments.extend(cls._parse_emoji_text_as_text_content(text=text[split_start_index: split_end_index]))
            text_segments.append(TextSegment.new(type_=i.group(2), data=i.group(3)))
            split_start_index = i.span()[1]
        else:
            text_segments.extend(cls._parse_emoji_text_as_text_content(text=text[split_start_index:]))

        return TextContent.parse_obj({'content': text_segments})

    @classmethod
    def parse_from_str(cls, text: str) -> 'AdvanceTextUtils':
        content = cls.parse_as_text_content(text=text)
        return cls(content=content)

    async def _prepare_image_segment(self) -> None:
        """预处理, 将所有的图片 Segment 全部下载下来"""
        for segment in self._content.content:
            if segment.type == 'image':
                image_url = segment.get_content()
                image_file_name = HttpFetcher.hash_url_file_name('image_segment', url=image_url)
                image_file = text_utils_config.default_download_tmp_folder(image_file_name)
                await HttpFetcher().download_file(url=image_url, file=image_file)
                segment.data.file = image_file.resolve_path

    def _prepare_segment(self) -> list[str | Image.Image]:
        """预处理, 将 TextSegment 全部转化为可绘制对象, 图片和 emoji 将按单字符处理"""
        draw_content: list[str | Image.Image] = []
        for segment in self._content.content:
            match segment.type:
                case 'image':
                    if segment.data.file:
                        image = Image.open(segment.data.file, mode='r')
                        draw_content.append(image)
                case 'emoji':
                    emoji_text = segment.get_content()
                    image = Image.new(mode='RGBA', size=(1024, 1024), color=(255, 255, 255, 0))
                    text_width, text_height = self._emoji_font.getsize(text=emoji_text)
                    ImageDraw.Draw(image).text(text=emoji_text, font=self._emoji_font,
                                               xy=(0, 1024), align='left', anchor='ld', embedded_color=True)
                    image = image.crop((0, 1024 - text_height, text_width, 1024))
                    draw_content.append(image)
                case 'text':
                    draw_content.append(segment.get_content())
        return draw_content

    @classmethod
    def _convert_image(
            cls,
            convert_content: list[str | Image.Image],
            *,
            image_size: tuple[int, int] = (1024, 1024),
            font: ImageFont.FreeTypeFont | None = None,
            font_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
            spacing: float = 1.15
    ) -> Image.Image:
        """转换图片

        :param image_size: 生成图片大小
        :param font: 字体
        :param font_fill: 字体填充颜色
        :param spacing: 行间距倍率
        """
        if font is None:
            font = cls._default_font

        if spacing < 1:
            spacing = 1

        _, line_spacing = font.getsize(' a,$#永')

        background = Image.new(mode='RGBA', size=image_size)
        image_width, _ = image_size

        # 定位坐标
        draw_loc: list[int, int] = [0, 0]
        # 依次绘制内容
        for content in convert_content:
            if isinstance(content, Image.Image):
                # 调整大小
                resize_wight = line_spacing * content.width // content.height
                content = content.resize((resize_wight, line_spacing))
                width, _ = content.size
                if draw_loc[0] + width > image_width:
                    draw_loc[0] = 0
                    draw_loc[1] = draw_loc[1] + int(line_spacing * spacing)
                background.paste(im=content, box=(draw_loc[0], draw_loc[1]))
                draw_loc[0] = draw_loc[0] + width
            else:
                split_index = 0
                for index, char in enumerate(content):
                    # 检查大小
                    text_width, _ = font.getsize_multiline(content[split_index:index])

                    if draw_loc[0] + text_width >= image_width - font.getsize_multiline(content[index-1: index])[0]:
                        ImageDraw.Draw(background).text(xy=(draw_loc[0], draw_loc[1]),
                                                        text=content[split_index: index-1],
                                                        font=font, align='left', anchor='la', fill=font_fill)
                        draw_loc[0] = 0
                        draw_loc[1] = draw_loc[1] + int(line_spacing * spacing)
                        split_index = index - 1

                    elif char == '\n':
                        ImageDraw.Draw(background).text(xy=(draw_loc[0], draw_loc[1]),
                                                        text=content[split_index: index],
                                                        font=font, align='left', anchor='la', fill=font_fill)
                        draw_loc[0] = 0
                        draw_loc[1] = draw_loc[1] + int(line_spacing * spacing)
                        split_index = index + 1

                else:
                    text_width, _ = font.getsize_multiline(content[split_index:])
                    ImageDraw.Draw(background).text(xy=(draw_loc[0], draw_loc[1]), text=content[split_index:],
                                                    font=font, align='left', anchor='la', fill=font_fill)
                    draw_loc[0] = draw_loc[0] + text_width

        # 裁剪有效范围
        draw_loc[1] = draw_loc[1] + int(line_spacing * spacing)
        background = background.crop(box=(0, 0, image_width, draw_loc[1]))

        return background

    @classmethod
    def _byte_convert_image(
            cls,
            convert_content: list[str | Image.Image],
            *,
            image_size: tuple[int, int] = (1024, 1024),
            font: ImageFont.FreeTypeFont | None = None,
            font_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
            spacing: float = 1.15
    ) -> bytes:
        """转换图片

        :param image_size: 生成图片大小
        :param font: 字体
        :param font_fill: 字体填充颜色
        :param spacing: 行间距倍率
        """
        image = cls._convert_image(convert_content=convert_content, image_size=image_size,
                                   font=font, font_fill=font_fill, spacing=spacing)

        # 提取生成图的内容
        with BytesIO() as bf:
            image.save(bf, 'PNG')
            content = bf.getvalue()
        return content

    async def convert_image(
            self,
            image_size: tuple[int, int] = (1024, 1024),
            font: ImageFont.FreeTypeFont | None = None,
            font_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
            spacing: float = 1.15
    ) -> TmpResource:
        """转换图片

        :param image_size: 生成图片大小
        :param font: 字体
        :param font_fill: 字体填充颜色
        :param spacing: 行间距倍率
        """
        await self._prepare_image_segment()
        convert_content = await run_sync(self._prepare_segment)()
        file_content = await run_sync(self._byte_convert_image)(convert_content=convert_content, image_size=image_size,
                                                                font=font, font_fill=font_fill, spacing=spacing)
        save_file_name = f"adv_{hash(self._content.get_text())}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.png"
        save_file = text_utils_config.default_img_tmp_folder(save_file_name)
        async with save_file.async_open('wb') as af:
            await af.write(file_content)
        return save_file


__all__ = [
    'TextSegment',
    'TextContent',
    'TextUtils',
    'AdvanceTextUtils'
]
