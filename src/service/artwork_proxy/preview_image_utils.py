"""
@Author         : Ailitonia
@Date           : 2026/9/30 15:35
@FileName       : preview_image_utils
@Project        : omega-miya
@Description    : Artwork 作品图片及预览图处理工具集
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from math import ceil
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from nonebot.utils import run_sync

from src.utils.image_utils import ImageEffectProcessor, ImageLoader, ImageTextProcessor

if TYPE_CHECKING:
    from src.resource import StaticResource, TemporaryResource

    from .models import PreviewImagesData, PreviewImageThumbsItem


class ArtworkImageOps:
    """作品图片处理工具集"""

    @staticmethod
    @run_sync
    def handle_blur(image: 'TemporaryResource', origin_mark: str) -> ImageEffectProcessor:
        """模糊处理图片"""
        _image = ImageEffectProcessor(ImageLoader.init_from_file(file=image))
        _image.gaussian_blur()
        _image.mark(text=origin_mark)
        _image.convert(mode='RGB')
        return _image

    @staticmethod
    @run_sync
    def handle_mark(image: 'TemporaryResource', origin_mark: str) -> ImageEffectProcessor:
        """标记水印"""
        _image = ImageEffectProcessor(ImageLoader.init_from_file(file=image))
        _image.mark(text=origin_mark)
        _image.convert(mode='RGB')
        return _image

    @staticmethod
    @run_sync
    def handle_noise(image: 'TemporaryResource', origin_mark: str) -> ImageEffectProcessor:
        """噪点处理图片"""
        _image = ImageEffectProcessor(ImageLoader.init_from_file(file=image))
        _image.gaussian_noise(sigma=16)
        _image.mark(text=origin_mark)
        _image.convert(mode='RGB')
        return _image

    @staticmethod
    @run_sync
    def _handle_preview_image(
            preview_name: str,
            previews: list['PreviewImageThumbsItem'],
            preview_size: tuple[int, int],
            font_path: 'StaticResource',
            *,
            header_color: tuple[int, int, int] = (255, 255, 255),
            edge_scale: float = 1 / 32,
            num_of_line: int = 6,
    ) -> bytes:
        """内部方法, 生成多个带说明的缩略图的预览图, 输出 JPEG 格式图片

        :param preview_name: 预览图标题
        :param previews: 预览图中缩略图内容
        :param preview_size: 单个小缩略图的尺寸
        :param font_path: 用于生成预览图说明的字体
        :param output_folder: 输出文件夹
        :param header_color: 页眉装饰色
        :param edge_scale: 缩略图添加白边的比例, 范围 0~1
        :param num_of_line: 生成预览每一行的预览图数
        :param limit: 限制生成时加载 preview 中图片的最大值
        """
        _thumb_w, _thumb_h = preview_size
        _font_path = font_path.resolve_path
        _font_main = ImageFont.truetype(_font_path, _thumb_w // 15)
        _font_title = ImageFont.truetype(_font_path, _thumb_w // 5)

        # 输出图片宽度
        _preview_w = _thumb_w * num_of_line

        # 标题自动换行
        _title = ImageTextProcessor.split_multiline_text(
            text=preview_name,
            width=int(_preview_w * 0.85),
            font=_font_title,
        )
        # 计算标题尺寸
        _title_w, _title_h = ImageTextProcessor.get_text_size(text=_title, font=_font_title)

        # 根据缩略图计算标准间距
        _spacing_w = int(_thumb_w * 0.4)
        _spacing_title = _spacing_w if _title_h <= int(_spacing_w * 0.75) else int(_title_h * 1.5)

        _background = Image.new(
            mode='RGB',
            size=(_preview_w, (_thumb_h + _spacing_w) * ceil(len(previews) / num_of_line) + _spacing_title),
            color=(255, 255, 255),
        )

        # 画一个装饰性的页眉
        # 处理颜色
        light = tuple(
            z if z > 0 else 0 for z in (y if y < 255 else 255 for y in (int(x / 0.9) for x in header_color))
        )
        dark = tuple(
            z if z > 0 else 0 for z in (y if y < 255 else 255 for y in (int(x * 0.9) for x in header_color))
        )
        # 左上角下层小三角形
        ImageDraw.Draw(_background).polygon(
            xy=[(0, 0), (0, _title_h), (_title_h, 0)],
            fill=dark,
        )
        # 页眉横向小蓝条
        ImageDraw.Draw(_background).polygon(
            xy=[(0, 0), (_preview_w, 0), (_preview_w, int(_title_h / 8)), (0, int(_title_h / 8))],
            fill=header_color,
        )
        # 左上角最上层小三角形
        ImageDraw.Draw(_background).polygon(
            xy=[(0, 0), (0, int(_title_h * 5 / 6)), (int(_title_h * 5 / 6), 0)],
            fill=light,
        )

        # 写标题
        ImageDraw.Draw(_background).multiline_text(
            xy=(_preview_w // 2, int(_title_h / 3)),
            text=_title,
            font=_font_title,
            align='center',
            anchor='ma',
            fill=(0, 0, 0),
        )

        # 处理拼图
        _line = 0
        for _index, _preview in enumerate(previews):
            try:
                _thumb_img = ImageLoader.init_from_bytes(_preview.thumb_data)
            except UnidentifiedImageError:
                _thumb_img = Image.new(mode='RGB', size=preview_size, color=(127, 127, 127))

            # 调整图片大小
            _thumb_img = ImageEffectProcessor(image=_thumb_img).resize_with_filling(preview_size).image

            # 调整边缘
            if edge_scale > 0:
                _thumb_img = ImageEffectProcessor(image=_thumb_img).add_edge(edge_scale=edge_scale).image

            # 确认缩略图单行位置
            seq = _index % num_of_line
            # 能被整除说明该张缩略图在新行行首要换行
            if seq == 0:
                _line += 1

            # 按位置粘贴单个缩略图
            _background.paste(
                _thumb_img,
                box=(seq * _thumb_w, (_thumb_h + _spacing_w) * (_line - 1) + _spacing_title),
            )
            ImageDraw.Draw(_background).multiline_text(
                xy=(
                    seq * _thumb_w + _thumb_w // 2,
                    (_thumb_h + _spacing_w) * (_line - 1) + _spacing_title + _thumb_h + _spacing_w // 10
                ),
                text=_preview.desc_text,
                font=_font_main,
                align='center',
                anchor='ma',
                fill=(0, 0, 0),
            )

        # 底部标注一个生成信息
        _generate_info = f'Created {datetime.now().strftime("%Y/%m/%d %H:%M:%S")} @ Omega Miya'
        ImageDraw.Draw(_background).text(
            xy=(_preview_w, (_thumb_h + _spacing_w) * ceil(len(previews) / num_of_line) + _spacing_title),
            text=_generate_info,
            font=_font_main,
            align='right',
            anchor='rd',
            fill=(128, 128, 128),
        )

        return ImageLoader.extract_to_bytes(_background, format_='JPEG')

    @classmethod
    async def generate_preview_image(
            cls,
            preview: 'PreviewImagesData',
            preview_size: tuple[int, int],
            font_path: 'StaticResource',
            output_folder: 'TemporaryResource',
            *,
            header_color: tuple[int, int, int] = (255, 255, 255),
            edge_scale: float = 1 / 32,
            num_of_line: int = 6,
            limit: int = 1000,
    ) -> 'TemporaryResource':
        """生成多个带说明的缩略图的预览图, 输出 JPEG 格式图片

        :param preview: 经过预处理的生成预览的数据
        :param preview_size: 单个小缩略图的尺寸
        :param font_path: 用于生成预览图说明的字体
        :param output_folder: 输出文件夹
        :param header_color: 页眉装饰色
        :param edge_scale: 缩略图添加白边的比例, 范围 0~1
        :param num_of_line: 生成预览每一行的预览图数
        :param limit: 限制生成时加载 preview 中图片的最大值
        """
        preview_name = preview.preview_name
        previews = preview.thumb_items[:limit]

        image_content = await cls._handle_preview_image(
            preview_name=preview_name,
            previews=previews,
            preview_size=preview_size,
            font_path=font_path,
            header_color=header_color,
            edge_scale=edge_scale,
            num_of_line=num_of_line,
        )
        image_file_name = f"preview_{hash(preview_name)}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"
        save_file = output_folder(image_file_name)
        async with save_file.async_open('wb') as af:
            await af.write(image_content)
        return save_file


__all__ = [
    'ArtworkImageOps',
]
