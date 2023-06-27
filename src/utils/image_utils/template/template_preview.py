"""
@Author         : Ailitonia
@Date           : 2022/04/16 23:59
@FileName       : helper.py
@Project        : nonebot2_miya 
@Description    : 常用的图片生成工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from math import ceil
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from nonebot.utils import run_sync

from src.resource import BaseResource, TemporaryResource

from .model import PreviewImageModel
from ..config import image_utils_config
from ..image_util import ImageUtils


async def generate_thumbs_preview_image(
        preview: PreviewImageModel,
        preview_size: tuple[int, int],
        *,
        font_path: BaseResource = image_utils_config.default_preview_font,
        header_color: tuple[int, int, int] = (255, 255, 255),
        hold_ratio: bool = False,
        num_of_line: int = 6,
        limit: int = 1000,
        output_folder: TemporaryResource = image_utils_config.tmp_preview_output_folder
) -> TemporaryResource:
    """生成多个带说明的缩略图的预览图

    :param preview: 经过预处理的生成预览的数据
    :param preview_size: 单个小缩略图的尺寸
    :param font_path: 用于生成预览图说明的字体
    :param header_color: 页眉装饰色
    :param hold_ratio: 是否保持缩略图原图比例
    :param num_of_line: 生成预览每一行的预览图数
    :param limit: 限制生成时加载 preview 中图片的最大值
    :param output_folder: 输出文件夹
    """
    preview_name = preview.preview_name
    previews = preview.previews[:limit]

    def _handle_preview_image() -> bytes:
        """用于图像生成处理的内部函数"""
        _thumb_w, _thumb_h = preview_size
        _font_path = font_path.resolve_path
        _font_main = ImageFont.truetype(_font_path, _thumb_w // 15)
        _font_title = ImageFont.truetype(_font_path, _thumb_w // 5)

        # 输出图片宽度
        _preview_w = _thumb_w * num_of_line

        # 标题自动换行
        _title = ImageUtils.split_multiline_text(text=preview_name, width=int(_preview_w * 0.85), font=_font_title)
        # 计算标题尺寸
        _title_w, _title_h = _font_title.getsize_multiline(text=_title)

        # 根据缩略图计算标准间距
        _spacing_w = int(_thumb_w * 0.4)
        _spacing_title = _spacing_w if _title_h <= int(_spacing_w * 0.75) else int(_title_h * 1.5)

        _background = Image.new(
            mode="RGB",
            size=(_preview_w, (_thumb_h + _spacing_w) * ceil(len(previews) / num_of_line) + _spacing_title),
            color=(255, 255, 255))

        # 画一个装饰性的页眉
        # 处理颜色
        light = tuple(z if z > 0 else 0 for z in (y if y < 255 else 255 for y in (int(x / 0.9) for x in header_color)))
        dark = tuple(z if z > 0 else 0 for z in (y if y < 255 else 255 for y in (int(x * 0.9) for x in header_color)))

        ImageDraw.Draw(_background).polygon(
            xy=[(0, 0), (0, _title_h), (_title_h, 0)],
            fill=dark
        )  # 左上角下层小三角形
        ImageDraw.Draw(_background).polygon(
            xy=[(0, 0), (_preview_w, 0), (_preview_w, int(_title_h / 8)), (0, int(_title_h / 8))],
            fill=header_color
        )  # 页眉横向小蓝条
        ImageDraw.Draw(_background).polygon(
            xy=[(0, 0), (0, int(_title_h * 5 / 6)), (int(_title_h * 5 / 6), 0)],
            fill=light
        )  # 左上角最上层小三角形

        # 写标题
        ImageDraw.Draw(_background).multiline_text(
            xy=(_preview_w // 2, int(_title_h / 3)), text=_title, font=_font_title,
            align='center', anchor='ma', fill=(0, 0, 0))

        # 处理拼图
        _line = 0
        for _index, _preview in enumerate(previews):
            with BytesIO(_preview.preview_thumb) as bf:
                _thumb_img: Image.Image = Image.open(bf)
                _thumb_img.load()

            # 调整图片大小
            if hold_ratio:
                _thumb_img = ImageUtils(image=_thumb_img).resize_with_filling(preview_size).image
            if _thumb_img.size != preview_size:
                _thumb_img = _thumb_img.resize(preview_size, Image.ANTIALIAS)

            # 确认缩略图单行位置
            seq = _index % num_of_line
            # 能被整除说明在行首要换行
            if seq == 0:
                _line += 1

            # 按位置粘贴单个缩略图
            _background.paste(_thumb_img, box=(seq * _thumb_w, (_thumb_h + _spacing_w) * (_line - 1) + _spacing_title))
            ImageDraw.Draw(_background).multiline_text(
                xy=(seq * _thumb_w + _thumb_w // 2,
                    (_thumb_h + _spacing_w) * (_line - 1) + _spacing_title + _thumb_h + _spacing_w // 10),
                text=_preview.desc_text, font=_font_main,
                align='center', anchor='ma', fill=(0, 0, 0))

        # 底部标注一个生成信息
        _generate_info = f'Created {datetime.now().strftime("%Y/%m/%d %H:%M:%S")} @ Omega Miya'
        ImageDraw.Draw(_background).text(
            xy=(_preview_w, (_thumb_h + _spacing_w) * ceil(len(previews) / num_of_line) + _spacing_title),
            text=_generate_info, font=_font_main, align='right', anchor='rd', fill=(128, 128, 128))

        # 生成结果图片
        with BytesIO() as _bf:
            _background.save(_bf, 'JPEG')
            _content = _bf.getvalue()
        return _content

    image_content = await run_sync(_handle_preview_image)()
    image_file_name = f"preview_{preview_name}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"
    save_file = output_folder(image_file_name)
    async with save_file.async_open('wb') as af:
        await af.write(image_content)
    return save_file


__all__ = [
    'generate_thumbs_preview_image'
]
