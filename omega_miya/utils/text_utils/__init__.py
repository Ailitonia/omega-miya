"""
@Author         : Ailitonia
@Date           : 2022/04/09 16:20
@FileName       : text_utils.py
@Project        : nonebot2_miya
@Description    : 文本工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from omega_miya.local_resource import TmpResource
from omega_miya.utils.process_utils import run_sync

from .config import text_utils_config


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

    def _default_text_to_img(self, *, image_width: int = 512, font_name: str = text_utils_config.default_font_name) -> bytes:
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


__all__ = [
    'TextUtils'
]
