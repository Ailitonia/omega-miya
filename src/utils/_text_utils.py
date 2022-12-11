"""
@Author         : Ailitonia
@Date           : 2022/04/09 16:20
@FileName       : text_utils.py
@Project        : nonebot2_miya
@Description    : [Deactivate]文本工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
import emoji
from io import BytesIO
from typing import Literal, Optional
from pydantic import BaseModel, root_validator, AnyUrl, FilePath
from dataclasses import dataclass
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from src.resource import StaticResource, TemporaryResource
from src.service.omega_requests import OmegaRequests
from src.utils.process_utils import run_sync


class TextUtilsBaseModel(BaseModel):
    class Config:
        extra = 'ignore'


class TextSegment(TextUtilsBaseModel):
    """文字段"""
    class _Data(TextUtilsBaseModel):
        def get_content(self) -> str:
            raise NotImplementedError

    class _TextData(_Data):
        text: str

        def get_content(self) -> str:
            return self.text

    class _EmojiData(_Data):
        emoji: str

        def get_content(self) -> str:
            return self.emoji

    class _ImageData(_Data):
        image: AnyUrl
        file: Optional[FilePath] = None

        def get_content(self) -> str:
            return str(self.image)

    type: Literal['text', 'emoji', 'image']
    data: _TextData | _EmojiData | _ImageData

    @root_validator(pre=False)
    def check_data_type_match(cls, values):
        segment_type = values.get('type')
        data = values.get('data')
        if not data or segment_type not in data.dict().keys():
            raise ValueError('Segment data type not match')
        return values

    def get_content(self) -> str:
        return self.data.get_content()

    @classmethod
    def new(cls, type_: str, data: str) -> 'TextSegment':
        return cls.parse_obj({'type': type_, 'data': {type_: data}})

    @classmethod
    def text(cls, text: str) -> 'TextSegment':
        return cls.new(type_='text', data=text)

    @classmethod
    def emoji(cls, emoji: str) -> 'TextSegment':
        return cls.new(type_='emoji', data=emoji)

    @classmethod
    def image(cls, image: str) -> 'TextSegment':
        return cls.new(type_='image', data=image)


class TextContent(TextUtilsBaseModel):
    """绘制文字内容"""
    content: list[TextSegment]

    def get_text(self) -> str:
        return ''.join(x.get_content() for x in self.content)


@dataclass
class TextUtilsConfig:
    """Text Utils 配置"""
    # 默认内置的静态资源文件路径
    default_size: int = 18
    default_font_name: str = 'SourceHanSansSC-Regular.otf'
    default_font_folder: StaticResource = StaticResource('fonts')
    default_font_file: StaticResource = default_font_folder(default_font_name)
    default_emoji_font: StaticResource = default_font_folder('AppleColorEmoji.ttf')

    # 默认的生成缓存文件路径
    default_tmp_folder: TemporaryResource = TemporaryResource('text_utils')
    default_download_tmp_folder: TemporaryResource = default_tmp_folder('download')
    default_img_tmp_folder: TemporaryResource = default_tmp_folder('image')

    class Config:
        extra = "ignore"


text_utils_config = TextUtilsConfig()


class AdvanceTextUtils(object):
    """[Deactivate]"""

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
    def _parse_emoji_text_as_text_segment(cls, text: str) -> list[TextSegment]:
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
    def _parse_as_text_content(cls, text: str) -> TextContent:
        """将字符串转化为 TextContent 对象, 同时解析形如 '[image: https://image_url]' 的字符串为 TextSegment"""
        text_segments: list[TextSegment] = []
        split_start_index = 0
        for i in re.compile(r"(\[(text|emoji|image):\s(.+?)])").finditer(text):
            split_end_index = i.span()[0]
            text_segments.extend(cls._parse_emoji_text_as_text_segment(text=text[split_start_index: split_end_index]))
            text_segments.append(TextSegment.new(type_=i.group(2), data=i.group(3)))
            split_start_index = i.span()[1]
        else:
            text_segments.extend(cls._parse_emoji_text_as_text_segment(text=text[split_start_index:]))

        return TextContent.parse_obj({'content': text_segments})

    @classmethod
    def parse_from_str(cls, text: str) -> 'AdvanceTextUtils':
        content = cls._parse_as_text_content(text=text)
        return cls(content=content)

    async def _prepare_image_segment(self) -> None:
        """预处理, 将所有的图片 Segment 全部下载下来"""
        for segment in self._content.content:
            if segment.type == 'image':
                image_url = segment.get_content()
                image_file_name = OmegaRequests.hash_url_file_name('image_segment', url=image_url)
                image_file = text_utils_config.default_download_tmp_folder(image_file_name)
                await OmegaRequests().download(url=image_url, file=image_file)
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
            background: tuple[int, int, int, int] | None = None,
            font: ImageFont.FreeTypeFont | None = None,
            font_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
            spacing: float = 1.15,
            auto_crop: bool = True
    ) -> Image.Image:
        """转换图片

        :param image_size: 生成图片大小
        :param font: 字体
        :param font_fill: 字体填充颜色
        :param spacing: 行间距倍率
        :param auto_crop: 自动裁剪有效区域
        """
        if font is None:
            font = cls._default_font

        if spacing < 1:
            spacing = 1

        _, line_spacing = font.getsize(' aAzZ,。$#永')

        background = Image.new(mode='RGBA', size=image_size, color=background)
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
        if auto_crop:
            draw_loc[1] = draw_loc[1] + int(line_spacing * spacing)
            background = background.crop(box=(0, 0, image_width, draw_loc[1]))

        return background

    @classmethod
    def _byte_convert_image(
            cls,
            convert_content: list[str | Image.Image],
            *,
            image_size: tuple[int, int] = (1024, 1024),
            background: tuple[int, int, int, int] | None = None,
            font: ImageFont.FreeTypeFont | None = None,
            font_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
            spacing: float = 1.15,
            auto_crop: bool = True
    ) -> bytes:
        """转换图片

        :param image_size: 生成图片大小
        :param font: 字体
        :param font_fill: 字体填充颜色
        :param spacing: 行间距倍率
        :param auto_crop: 自动裁剪有效区域
        """
        image = cls._convert_image(convert_content=convert_content, image_size=image_size, background=background,
                                   font=font, font_fill=font_fill, spacing=spacing, auto_crop=auto_crop)

        # 提取生成图的内容
        with BytesIO() as bf:
            image.save(bf, 'PNG')
            content = bf.getvalue()
        return content

    def covert_pil_image_ignore_image_seg(
            self,
            image_size: tuple[int, int] = (1024, 1024),
            background: tuple[int, int, int, int] | None = None,
            font: ImageFont.FreeTypeFont | None = None,
            font_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
            spacing: float = 1.15,
            auto_crop: bool = True
    ) -> Image.Image:
        """忽略图片文字段并直接转换为 Image.Image 对象

        :param image_size: 生成图片大小
        :param background: 生成图片背景颜色
        :param font: 字体
        :param font_fill: 字体填充颜色
        :param spacing: 行间距倍率
        :param auto_crop: 自动裁剪有效区域
        """
        convert_content = self._prepare_segment()
        image = self._convert_image(convert_content=convert_content, image_size=image_size, background=background,
                                    font=font, font_fill=font_fill, spacing=spacing, auto_crop=auto_crop)
        return image

    async def convert_pil_image(
            self,
            image_size: tuple[int, int] = (1024, 1024),
            background: tuple[int, int, int, int] | None = None,
            font: ImageFont.FreeTypeFont | None = None,
            font_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
            spacing: float = 1.15,
            auto_crop: bool = True
    ) -> Image.Image:
        """转换为 Image.Image 对象

        :param image_size: 生成图片大小
        :param background: 生成图片背景颜色
        :param font: 字体
        :param font_fill: 字体填充颜色
        :param spacing: 行间距倍率
        :param auto_crop: 自动裁剪有效区域
        """
        await self._prepare_image_segment()
        convert_content = await run_sync(self._prepare_segment)()
        image = await run_sync(self._convert_image)(convert_content=convert_content, image_size=image_size,
                                                    background=background, font=font, font_fill=font_fill,
                                                    spacing=spacing, auto_crop=auto_crop)
        return image

    async def convert_image(
            self,
            image_size: tuple[int, int] = (1024, 1024),
            background: tuple[int, int, int, int] | None = None,
            font: ImageFont.FreeTypeFont | None = None,
            font_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
            spacing: float = 1.15,
            auto_crop: bool = True
    ) -> TemporaryResource:
        """转换图片

        :param image_size: 生成图片大小
        :param background: 生成图片背景颜色
        :param font: 字体
        :param font_fill: 字体填充颜色
        :param spacing: 行间距倍率
        :param auto_crop: 自动裁剪有效区域
        """
        await self._prepare_image_segment()
        convert_content = await run_sync(self._prepare_segment)()
        file_content = await run_sync(self._byte_convert_image)(convert_content=convert_content, image_size=image_size,
                                                                background=background, font=font, font_fill=font_fill,
                                                                spacing=spacing, auto_crop=auto_crop)
        save_file_name = f"adv_{hash(self._content.get_text())}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.png"
        save_file = text_utils_config.default_img_tmp_folder(save_file_name)
        async with save_file.async_open('wb') as af:
            await af.write(file_content)
        return save_file


__all__ = []
