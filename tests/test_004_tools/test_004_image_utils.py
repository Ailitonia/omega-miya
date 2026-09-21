"""
@Author         : Ailitonia
@Date           : 2026/9/19 13:16
@FileName       : test_004_image_utils
@Project        : omega-miya
@Description    : 图片工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
import io
from pathlib import Path
from typing import TYPE_CHECKING, Self

import pytest
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont, UnidentifiedImageError
from fontTools.ttLib import TTFont

if TYPE_CHECKING:
    from src.utils.image_utils import ImageEffectProcessor

JPEG_MAGIC = b'\xff\xd8'
PNG_MAGIC = b'\x89PNG'

TEXT_ASCII = 'hello world unit test'
TEXT_CJK = '一二三四五六七八九十百千万亿'
TEXT_MIXED = '中文English混合123文本'
TEXT_EMOJI = 'emoji测试🀄🅰️文本'
TEXT_MULTILINE = '第一行文本\n第二行文本\nthird line'
TEXT_MISSING_GLYPH = '常规文本ᚠᚢ𐌸缺失字形'

SPLIT_TEXTS = [TEXT_ASCII, TEXT_CJK, TEXT_MIXED, TEXT_EMOJI]
SPLIT_TEXT_IDS = ['ascii', 'cjk', 'mixed', 'emoji']
SPLIT_WIDTHS = [50, 120, 300]

FONT_PRESENT_CHAR = '中'
FONT_MISSING_CHAR = 'ᚠ'


def _png_bytes(size: tuple[int, int] = (20, 10), color=(255, 0, 0), mode: str = 'RGB') -> bytes:
    buf = io.BytesIO()
    PILImage.new(mode, size, color).save(buf, format='PNG')
    return buf.getvalue()


def _jpeg_bytes(size: tuple[int, int] = (20, 10), color=(0, 0, 255)) -> bytes:
    buf = io.BytesIO()
    PILImage.new('RGB', size, color).save(buf, format='JPEG')
    return buf.getvalue()


def _new_image(mode: str = 'RGB', size: tuple[int, int] = (64, 64), color=(255, 255, 255)) -> 'PILImage.Image':
    return PILImage.new(mode, size, color)


def _make_processor(image: 'PILImage.Image | None' = None) -> 'ImageEffectProcessor':
    from src.utils.image_utils import ImageEffectProcessor
    return ImageEffectProcessor(image if image is not None else _new_image())


def _get_default_font() -> ImageFont.FreeTypeFont:
    from src.utils.image_utils.config import image_utils_config
    return ImageFont.truetype(image_utils_config.default_font.resolve_path, 20)


def _load_default_emoji_fonts() -> dict[str, TTFont]:
    from src.utils.image_utils import ImageTextProcessor
    from src.utils.image_utils.config import image_utils_config
    return ImageTextProcessor.load_fonts(image_utils_config.default_font.name, image_utils_config.emoji_font.name)


def _normalized(text: str) -> str:
    return ''.join(text.split('\n'))


class _StubFileResource:
    """init_from_file 用的资源桩, open 返回 BytesIO, 不落盘"""

    def __init__(self, content: bytes):
        self._content = content

    def open(self, mode: str) -> io.BytesIO:
        assert 'b' in mode
        return io.BytesIO(self._content)


class _StubAsyncWriter:
    """异步写入句柄, 将数据写入内存缓冲"""

    def __init__(self, buffer: io.BytesIO):
        self._buffer = buffer

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False

    async def write(self, data: bytes) -> int:
        return self._buffer.write(data)


class _StubAsyncResource:
    """save() 用的资源桩, async_open 写入内存缓冲, 不落盘"""

    def __init__(self):
        self.buffer = io.BytesIO()

    def async_open(self, mode: str, **kwargs) -> _StubAsyncWriter:
        assert 'b' in mode
        return _StubAsyncWriter(self.buffer)


class TestImageLoaderBytes:
    """ImageLoader.init_from_bytes / async_init_from_bytes"""

    def test_load_png(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_bytes(image=_png_bytes(size=(20, 10), color=(255, 0, 0)))
        assert image.size == (20, 10)
        assert image.mode == 'RGB'
        assert image.getpixel((0, 0)) == (255, 0, 0)

    def test_load_jpeg(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_bytes(image=_jpeg_bytes(size=(30, 20)))
        assert image.size == (30, 20)
        assert image.mode == 'RGB'

    def test_load_palette_mode_preserved(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_bytes(image=_png_bytes(size=(10, 10), mode='P'))
        assert image.mode == 'P'

    def test_invalid_bytes_raises(self):
        from src.utils.image_utils import ImageLoader
        with pytest.raises(UnidentifiedImageError):
            ImageLoader.init_from_bytes(image=b'definitely not an image payload')

    def test_empty_bytes_raises(self):
        from src.utils.image_utils import ImageLoader
        with pytest.raises(UnidentifiedImageError):
            ImageLoader.init_from_bytes(image=b'')

    def test_pixel_limit_exact_boundary_passes(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.image_utils import ImageLoader
        from src.utils.image_utils.config import image_utils_config
        monkeypatch.setattr(image_utils_config, 'image_utils_max_image_pixels', 200)
        image = ImageLoader.init_from_bytes(image=_png_bytes(size=(20, 10)))
        assert image.size == (20, 10)

    def test_pixel_limit_exceeded_raises(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.image_utils import ImageLoader
        from src.utils.image_utils.config import image_utils_config
        monkeypatch.setattr(image_utils_config, 'image_utils_max_image_pixels', 199)
        with pytest.raises(ValueError, match='exceeds max pixels limit'):
            ImageLoader.init_from_bytes(image=_png_bytes(size=(20, 10)))

    async def test_async_init_from_bytes(self):
        from src.utils.image_utils import ImageLoader
        image = await ImageLoader.async_init_from_bytes(image=_png_bytes(size=(20, 10)))
        assert image.size == (20, 10)
        assert image.mode == 'RGB'


class TestImageLoaderFile:
    """ImageLoader.init_from_file / async_init_from_file"""

    def test_load_from_resource(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_file(file=_StubFileResource(_png_bytes(size=(30, 20))))
        assert image.size == (30, 20)
        assert image.mode == 'RGB'

    def test_load_jpeg_from_resource(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_file(file=_StubFileResource(_jpeg_bytes(size=(15, 25))))
        assert image.size == (15, 25)

    def test_pixel_limit_exceeded_raises(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.image_utils import ImageLoader
        from src.utils.image_utils.config import image_utils_config
        monkeypatch.setattr(image_utils_config, 'image_utils_max_image_pixels', 100)
        with pytest.raises(ValueError, match='exceeds max pixels limit'):
            ImageLoader.init_from_file(file=_StubFileResource(_png_bytes(size=(20, 10))))

    def test_invalid_content_raises(self):
        from src.utils.image_utils import ImageLoader
        with pytest.raises(UnidentifiedImageError):
            ImageLoader.init_from_file(file=_StubFileResource(b'not an image'))

    async def test_async_init_from_file(self):
        from src.utils.image_utils import ImageLoader
        image = await ImageLoader.async_init_from_file(file=_StubFileResource(_png_bytes(size=(30, 20))))
        assert image.size == (30, 20)


class TestImageLoaderText:
    """ImageLoader.init_from_text / async_init_from_text"""

    def test_default_parameters(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_text(text=TEXT_CJK)
        assert image.mode == 'RGB'
        assert image.width == 512
        assert image.height > 0

    def test_alpha_output(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_text(text=TEXT_ASCII, alpha=True)
        assert image.mode == 'RGBA'

    def test_custom_width_and_font_name(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_text(text=TEXT_MIXED, image_width=256, font_name='msyh.ttc')
        assert image.width == 256
        assert image.height > 0

    def test_long_text_wraps_and_grows(self):
        from src.utils.image_utils import ImageLoader
        short = ImageLoader.init_from_text(text='短')
        long = ImageLoader.init_from_text(text=TEXT_CJK * 5)
        assert long.height > short.height

    def test_multiline_text(self):
        from src.utils.image_utils import ImageLoader
        single = ImageLoader.init_from_text(text='第一行')
        multi = ImageLoader.init_from_text(text=TEXT_MULTILINE)
        assert multi.height >= single.height
        assert multi.width == 512

    def test_emoji_text(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_text(text=TEXT_EMOJI)
        assert image.width == 512
        assert image.height > 0

    async def test_async_init_from_text(self):
        from src.utils.image_utils import ImageLoader
        image = await ImageLoader.async_init_from_text(text=TEXT_CJK)
        assert image.width == 512
        assert image.mode == 'RGB'


class TestFontTools:
    """ImageTextProcessor 字体加载与字形查找"""

    def test_load_fonts(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf', 'msyh.ttc')
        assert len(fonts) == 2
        assert all(isinstance(font, TTFont) for font in fonts.values())
        assert all(Path(path).is_file() for path in fonts)

    def test_load_fonts_deduplicates(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = ImageTextProcessor.load_fonts('msyh.ttc', 'msyh.ttc')
        assert len(fonts) == 1

    def test_load_fonts_missing_name_raises(self):
        from src.utils.image_utils import ImageTextProcessor
        with pytest.raises(FileNotFoundError):
            ImageTextProcessor.load_fonts('no-such-font.ttf')

    def test_has_glyph_present(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf')
        font = next(iter(fonts.values()))
        assert ImageTextProcessor.has_glyph(font, FONT_PRESENT_CHAR) is True

    def test_has_glyph_missing(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf')
        font = next(iter(fonts.values()))
        assert ImageTextProcessor.has_glyph(font, FONT_MISSING_CHAR) is False

    def test_merge_chunks_empty_fonts_raises(self):
        from src.utils.image_utils import ImageTextProcessor
        with pytest.raises(ValueError, match='at least one font'):
            ImageTextProcessor.merge_chunks(TEXT_ASCII, {})

    def test_merge_chunks_empty_text(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf')
        assert ImageTextProcessor.merge_chunks('', fonts) == []

    def test_merge_chunks_single_font_single_cluster(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf')
        sentence = ImageTextProcessor.merge_chunks(TEXT_MIXED, fonts)
        assert len(sentence) == 1
        assert sentence[0][0] == TEXT_MIXED
        assert sentence[0][1] in fonts

    def test_merge_chunks_mixed_fonts(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = _load_default_emoji_fonts()
        sentence = ImageTextProcessor.merge_chunks(TEXT_EMOJI, fonts)
        assert len(sentence) > 1
        assert ''.join(chunk[0] for chunk in sentence) == TEXT_EMOJI
        emoji_chunks = [chunk for chunk in sentence if '🀄' in chunk[0] or '🅰' in chunk[0]]
        assert emoji_chunks, 'emoji 应由 emoji 字体承接'
        emoji_font_path = ImageTextProcessor.load_fonts('NotoEmoji-Regular.ttf')
        assert emoji_chunks[0][1] in emoji_font_path

    def test_merge_chunks_missing_glyph_fallback_no_char_loss(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf')
        sentence = ImageTextProcessor.merge_chunks(TEXT_MISSING_GLYPH, fonts)
        assert ''.join(chunk[0] for chunk in sentence) == TEXT_MISSING_GLYPH
        assert all(chunk[1] in fonts for chunk in sentence)


class TestSplitMultilineText:
    """ImageTextProcessor.split_multiline_text"""

    @pytest.mark.parametrize('width', SPLIT_WIDTHS)
    @pytest.mark.parametrize('text', SPLIT_TEXTS, ids=SPLIT_TEXT_IDS)
    def test_lines_within_width_and_roundtrip(self, text: str, width: int):
        from src.utils.image_utils import ImageTextProcessor
        font = _get_default_font()
        result = ImageTextProcessor.split_multiline_text(text=text, width=width, font=font)
        lines = result.split('\n')
        assert _normalized(result) == _normalized(text)
        for line in lines:
            assert font.getlength(line) <= width or len(line) == 1

    def test_empty_text(self):
        from src.utils.image_utils import ImageTextProcessor
        assert ImageTextProcessor.split_multiline_text(text='', width=100, font=_get_default_font()) == ''

    def test_single_char(self):
        from src.utils.image_utils import ImageTextProcessor
        result = ImageTextProcessor.split_multiline_text(text='中', width=100, font=_get_default_font())
        assert result == '中'

    def test_char_wider_than_width_one_char_per_line(self):
        from src.utils.image_utils import ImageTextProcessor
        result = ImageTextProcessor.split_multiline_text(text=TEXT_CJK[:5], width=5, font=_get_default_font())
        assert result.split('\n') == list(TEXT_CJK[:5])

    def test_zero_width_one_char_per_line(self):
        from src.utils.image_utils import ImageTextProcessor
        result = ImageTextProcessor.split_multiline_text(text=TEXT_CJK[:5], width=0, font=_get_default_font())
        lines = result.split('\n')
        assert lines == list(TEXT_CJK[:5])
        assert all(line for line in lines)

    def test_existing_newlines_preserved(self):
        from src.utils.image_utils import ImageTextProcessor
        result = ImageTextProcessor.split_multiline_text(text='AB\nCD', width=500, font=_get_default_font())
        assert _normalized(result) == _normalized('AB\nCD')

    def test_stroke_width_breaks_earlier(self):
        from src.utils.image_utils import ImageTextProcessor
        font = _get_default_font()
        plain = ImageTextProcessor.split_multiline_text(text=TEXT_MIXED, width=120, font=font)
        stroked = ImageTextProcessor.split_multiline_text(text=TEXT_MIXED, width=120, font=font, stroke_width=5)
        assert len(stroked.split('\n')) >= len(plain.split('\n'))
        for line in stroked.split('\n'):
            assert font.getlength(line) + 2 * 5 * len(line) <= 120 or len(line) == 1

    def test_font_as_none(self):
        from src.utils.image_utils import ImageTextProcessor
        result = ImageTextProcessor.split_multiline_text(text=TEXT_CJK, width=100)
        assert _normalized(result) == _normalized(TEXT_CJK)

    def test_font_as_str_name(self):
        from src.utils.image_utils import ImageTextProcessor
        result = ImageTextProcessor.split_multiline_text(text=TEXT_CJK, width=100, font='msyh.ttc')
        assert _normalized(result) == _normalized(TEXT_CJK)

    def test_font_as_instance(self):
        from src.utils.image_utils import ImageTextProcessor
        result = ImageTextProcessor.split_multiline_text(text=TEXT_CJK, width=100, font=_get_default_font())
        assert _normalized(result) == _normalized(TEXT_CJK)

    def test_long_text_completes(self):
        from src.utils.image_utils import ImageTextProcessor
        text = TEXT_CJK * 50
        result = ImageTextProcessor.split_multiline_text(text=text, width=100, font=_get_default_font())
        assert _normalized(result) == _normalized(text)


class TestTextSize:
    """ImageTextProcessor.get_text_size / get_font_size"""

    def test_get_text_size_positive(self):
        from src.utils.image_utils import ImageTextProcessor
        width, height = ImageTextProcessor.get_text_size(text=TEXT_MIXED, font=_get_default_font())
        assert width > 0
        assert height > 0

    def test_get_text_size_monotonic(self):
        from src.utils.image_utils import ImageTextProcessor
        font = _get_default_font()
        short_width, _ = ImageTextProcessor.get_text_size(text='ab', font=font)
        long_width, _ = ImageTextProcessor.get_text_size(text='abcd', font=font)
        assert long_width >= short_width

    def test_get_text_size_multiline_includes_spacing(self):
        from src.utils.image_utils import ImageTextProcessor
        font = _get_default_font()
        _, single_height = ImageTextProcessor.get_text_size(text='文', font=font)
        _, multi_height = ImageTextProcessor.get_text_size(text='文\n文', font=font)
        assert multi_height > single_height

    def test_get_font_size_positive_and_monotonic(self):
        from src.utils.image_utils import ImageTextProcessor
        font = _get_default_font()
        short_width, short_height = ImageTextProcessor.get_font_size(text='ab', font=font)
        long_width, long_height = ImageTextProcessor.get_font_size(text='abcdef', font=font)
        assert short_width > 0
        assert short_height > 0
        assert long_width >= short_width


class TestDrawMultilineText:
    """ImageTextProcessor.draw_multiline_text"""

    def test_draw_returns_positive_size(self):
        from src.utils.image_utils import ImageTextProcessor
        image = _new_image()
        width, height = ImageTextProcessor.draw_multiline_text(
            ImageDraw.Draw(image), xy=(4, 4), text=TEXT_MIXED, size=20
        )
        assert width > 0
        assert height > 0

    def test_draw_empty_text_returns_zero(self):
        from src.utils.image_utils import ImageTextProcessor
        image = _new_image()
        assert ImageTextProcessor.draw_multiline_text(ImageDraw.Draw(image), xy=(4, 4), text='', size=20) == (0.0, 0.0)

    def test_draw_multiline_higher_than_single_line(self):
        from src.utils.image_utils import ImageTextProcessor
        draw = ImageDraw.Draw(_new_image())
        _, single_height = ImageTextProcessor.draw_multiline_text(draw, xy=(4, 4), text='文', size=20)
        _, multi_height = ImageTextProcessor.draw_multiline_text(draw, xy=(4, 4), text='文\n文', size=20)
        assert multi_height > single_height

    def test_draw_with_custom_fonts(self):
        from src.utils.image_utils import ImageTextProcessor
        image = _new_image()
        width, height = ImageTextProcessor.draw_multiline_text(
            ImageDraw.Draw(image), xy=(4, 4), text=TEXT_EMOJI, size=20, fonts=_load_default_emoji_fonts()
        )
        assert width > 0
        assert height > 0

    def test_draw_missing_glyph_text_no_exception(self):
        from src.utils.image_utils import ImageTextProcessor
        image = _new_image()
        width, height = ImageTextProcessor.draw_multiline_text(
            ImageDraw.Draw(image), xy=(4, 4), text=TEXT_MISSING_GLYPH, size=20
        )
        assert width > 0


class TestEffectBytes:
    """ImageEffectProcessor.get_bytes / get_base64 / async 版本"""

    def test_get_bytes_png_roundtrip(self):
        from src.utils.image_utils import ImageLoader
        processor = _make_processor(ImageLoader.init_from_bytes(image=_png_bytes(size=(20, 10))))
        content = processor.get_bytes(format_='PNG')
        reloaded = ImageLoader.init_from_bytes(image=content)
        assert reloaded.size == (20, 10)
        assert reloaded.mode == 'RGB'

    def test_get_bytes_jpeg_default(self):
        content = _make_processor().get_bytes()
        assert content.startswith(JPEG_MAGIC)

    def test_rgba_jpeg_auto_converts(self):
        processor = _make_processor(_new_image(mode='RGBA', color=(255, 0, 0, 128)))
        content = processor.get_bytes(format_='JPEG')
        assert content.startswith(JPEG_MAGIC)
        assert processor.image.mode == 'RGB'

    def test_palette_jpeg_auto_converts(self):
        processor = _make_processor(_new_image(mode='P'))
        content = processor.get_bytes(format_='JPEG')
        assert content.startswith(JPEG_MAGIC)
        assert processor.image.mode == 'RGB'

    def test_l_mode_jpeg_keeps_mode(self):
        processor = _make_processor(_new_image(mode='L', color=128))
        content = processor.get_bytes(format_='JPEG')
        assert content.startswith(JPEG_MAGIC)
        assert processor.image.mode == 'L'

    def test_rgba_png_keeps_mode(self):
        processor = _make_processor(_new_image(mode='RGBA'))
        content = processor.get_bytes(format_='PNG')
        assert content.startswith(PNG_MAGIC)
        assert processor.image.mode == 'RGBA'

    def test_cmyk_jpeg_keeps_mode(self):
        processor = _make_processor(_new_image(mode='CMYK', color=(0, 0, 0, 0)))
        content = processor.get_bytes(format_='JPEG')
        assert content.startswith(JPEG_MAGIC)
        assert processor.image.mode == 'CMYK'

    def test_get_base64_default_prefix(self):
        content = _make_processor().get_base64()
        assert content.startswith('base64://')
        assert base64.b64decode(content.removeprefix('base64://')).startswith(JPEG_MAGIC)

    def test_get_base64_data_uri_prefix(self):
        content = _make_processor().get_base64(use_data_uri_scheme=True)
        assert content.startswith('data:image/jpeg;base64,')
        assert base64.b64decode(content.removeprefix('data:image/jpeg;base64,')).startswith(JPEG_MAGIC)

    def test_convert_returns_self_and_changes_mode(self):
        processor = _make_processor()
        assert processor.convert(mode='RGBA') is processor
        assert processor.image.mode == 'RGBA'

    async def test_async_get_bytes_matches_sync(self):
        processor = _make_processor()
        assert await processor.async_get_bytes(format_='PNG') == processor.get_bytes(format_='PNG')

    async def test_async_get_base64_matches_sync(self):
        processor = _make_processor()
        assert await processor.async_get_base64() == processor.get_base64()


class TestEffectSave:
    """ImageEffectProcessor.save"""

    async def test_save_jpeg_to_resource(self):
        stub = _StubAsyncResource()
        returned = await _make_processor().save(file=stub)
        assert returned is stub
        assert stub.buffer.getvalue().startswith(JPEG_MAGIC)

    async def test_save_png_to_resource(self):
        stub = _StubAsyncResource()
        returned = await _make_processor().save(file=stub, format_='PNG')
        assert returned is stub
        assert stub.buffer.getvalue().startswith(PNG_MAGIC)


class TestMark:
    """ImageEffectProcessor.mark"""

    @pytest.mark.parametrize('position', ['la', 'ra', 'lb', 'rb', 'c'])
    def test_mark_all_positions_return_self(self, position: str):
        processor = _make_processor()
        assert processor.mark(text='mark', position=position) is processor  # type: ignore[arg-type]

    def test_mark_modifies_pixels(self):
        processor = _make_processor()
        before = processor.image.tobytes()
        processor.mark(text='水印')
        assert processor.image.tobytes() != before

    def test_mark_invalid_position_raises(self):
        with pytest.raises(ValueError, match='invalid mark position'):
            _make_processor().mark(text='mark', position='middle')  # type: ignore[arg-type]

    def test_mark_l_mode_converts_to_rgb(self):
        processor = _make_processor(_new_image(mode='L', color=128))
        processor.mark(text='mark')
        assert processor.image.mode == 'RGB'

    def test_mark_tiny_image(self):
        processor = _make_processor(_new_image(size=(8, 8)))
        processor.mark(text='m')
        assert processor.image.size == (8, 8)

    def test_mark_rgba_image(self):
        processor = _make_processor(_new_image(mode='RGBA'))
        processor.mark(text='mark')
        assert processor.image.mode == 'RGBA'


class TestGaussianBlur:
    """ImageEffectProcessor.gaussian_blur"""

    @staticmethod
    def _patterned_processor():
        image = _new_image()
        ImageDraw.Draw(image).rectangle([10, 10, 50, 50], fill=(0, 0, 0))
        return _make_processor(image)

    def test_default_blur_changes_pixels_and_keeps_size(self):
        processor = self._patterned_processor()
        before = processor.image.tobytes()
        processor.gaussian_blur()
        assert processor.image.size == (64, 64)
        assert processor.image.tobytes() != before

    def test_uniform_image_blur_keeps_pixels(self):
        processor = _make_processor()
        before = processor.image.tobytes()
        processor.gaussian_blur()
        assert processor.image.tobytes() == before

    def test_custom_radius_returns_self(self):
        processor = _make_processor()
        assert processor.gaussian_blur(radius=2) is processor

    async def test_wrapper_on_loaded_image(self):
        from src.utils.image_utils import ImageLoader
        processor = _make_processor(await ImageLoader.async_init_from_bytes(image=_png_bytes(size=(32, 32))))
        processor.gaussian_blur(radius=1)
        assert processor.image.size == (32, 32)


class TestGaussianNoise:
    """ImageEffectProcessor.gaussian_noise"""

    def test_deterministic_noise_changes_pixels(self):
        processor = _make_processor()
        before = processor.image.tobytes()
        processor.gaussian_noise(enable_random=False)
        assert processor.image.size == (64, 64)
        assert processor.image.mode == 'RGB'
        assert processor.image.tobytes() != before

    def test_random_noise_returns_self(self):
        processor = _make_processor()
        assert processor.gaussian_noise() is processor

    def test_zero_sigma(self):
        processor = _make_processor()
        processor.gaussian_noise(sigma=0, enable_random=False)
        assert processor.image.size == (64, 64)

    def test_rgba_input(self):
        processor = _make_processor(_new_image(mode='RGBA'))
        processor.gaussian_noise(enable_random=False)
        assert processor.image.mode == 'RGBA'
        assert processor.image.size == (64, 64)


class TestAddEdge:
    """ImageEffectProcessor.add_edge"""

    def test_output_size_and_mode(self):
        processor = _make_processor()
        processor.add_edge()
        assert processor.image.size == (64, 64)
        assert processor.image.mode == 'RGBA'

    def test_negative_scale_clamped(self):
        processor = _make_processor()
        processor.add_edge(edge_scale=-0.5)
        assert processor.image.size == (64, 64)

    def test_scale_above_one_clamped(self):
        processor = _make_processor()
        processor.add_edge(edge_scale=1.5)
        assert processor.image.size == (64, 64)

    def test_scale_near_one_degenerate_content(self):
        processor = _make_processor()
        processor.add_edge(edge_scale=0.99)
        assert processor.image.size == (64, 64)
        processor.add_edge(edge_scale=1)
        assert processor.image.size == (64, 64)

    def test_default_edge_corner_transparent(self):
        processor = _make_processor()
        processor.add_edge()
        assert processor.image.getpixel((0, 0)) == (255, 255, 255, 0)


class TestResizeWithFilling:
    """ImageEffectProcessor.resize_with_filling"""

    def test_upscale_exact_size_and_mode(self):
        processor = _make_processor(_new_image(size=(20, 10)))
        processor.resize_with_filling(size=(100, 100))
        assert processor.image.size == (100, 100)
        assert processor.image.mode == 'RGBA'

    def test_downscale_exact_size(self):
        processor = _make_processor(_new_image(size=(200, 100)))
        processor.resize_with_filling(size=(50, 50))
        assert processor.image.size == (50, 50)

    def test_custom_background_corner(self):
        processor = _make_processor(_new_image(size=(20, 10)))
        processor.resize_with_filling(size=(100, 100), background_color=(0, 0, 255, 255))
        assert processor.image.getpixel((0, 0)) == (0, 0, 255, 255)

    def test_rgb_input_converts_to_rgba(self):
        processor = _make_processor(_new_image(mode='RGB'))
        assert processor.image.mode == 'RGB'
        processor.resize_with_filling(size=(64, 64))
        assert processor.image.mode == 'RGBA'


class TestResizeFillCanvas:
    """ImageEffectProcessor.resize_fill_canvas"""

    def test_output_exact_size_and_mode(self):
        processor = _make_processor(_new_image(size=(10, 10)))
        processor.resize_fill_canvas(size=(100, 50))
        assert processor.image.size == (100, 50)
        assert processor.image.mode == 'RGBA'

    def test_downscale_fill(self):
        processor = _make_processor(_new_image(size=(200, 100)))
        processor.resize_fill_canvas(size=(50, 50))
        assert processor.image.size == (50, 50)


class TestConfigContract:
    """image_utils_config 契约"""

    def test_default_font_resource_exists(self):
        from src.resource import StaticResource
        from src.utils.image_utils.config import image_utils_config
        font = image_utils_config.default_font
        assert isinstance(font, StaticResource)
        assert Path(font.resolve_path).is_file()

    def test_max_pixels_positive(self):
        from src.utils.image_utils.config import image_utils_config
        assert image_utils_config.max_image_pixels > 0

    def test_default_font_size_positive(self):
        from src.utils.image_utils.config import image_utils_config
        assert image_utils_config.default_font_size > 0

    def test_get_custom_name_font(self):
        from src.resource import StaticResource
        from src.utils.image_utils.config import image_utils_config
        font = image_utils_config.get_custom_name_font('msyh.ttc')
        assert isinstance(font, StaticResource)
        assert Path(font.resolve_path).is_file()

    def test_default_output_folder_joins_name(self):
        from src.resource import TemporaryResource
        from src.utils.image_utils.config import image_utils_config
        folder = image_utils_config.default_output_folder('a.jpg')
        assert isinstance(folder, TemporaryResource)
        assert 'output' in folder.resolve_path
        assert folder.resolve_path.endswith('a.jpg')


class TestSplitMultilineTextEmbeddedNewlines:
    """split_multiline_text 内嵌换行符处理"""

    def test_wrap_after_embedded_newline_no_extra_blank_lines(self):
        """内嵌换行后触发换行时, 不得产生额外空行"""
        from src.utils.image_utils import ImageTextProcessor
        font = _get_default_font()
        text = 'AB\nCDEFGHIJ'
        result = ImageTextProcessor.split_multiline_text(text=text, width=50, font=font)
        lines = result.split('\n')
        assert lines[0] == 'AB'
        assert '' not in lines
        assert _normalized(result) == _normalized(text)
        for line in lines:
            assert font.getlength(line) <= 50 or len(line) == 1

    def test_embedded_blank_lines_preserved(self):
        """原文中的空行应原样保留"""
        from src.utils.image_utils import ImageTextProcessor
        result = ImageTextProcessor.split_multiline_text(text='AB\n\nCD', width=500, font=_get_default_font())
        assert result == 'AB\n\nCD'

    def test_existing_newlines_roundtrip_after_wrap(self):
        """各原有行独立切分, 换行触发后 roundtrip 保真且不引入空行"""
        from src.utils.image_utils import ImageTextProcessor
        font = _get_default_font()
        text = TEXT_CJK + '\n' + TEXT_MIXED
        result = ImageTextProcessor.split_multiline_text(text=text, width=100, font=font)
        assert _normalized(result) == _normalized(text)
        assert '\n\n' not in result


class TestDrawMultilineTextEmptyLines:
    """draw_multiline_text 空行占位语义"""

    def test_empty_line_occupies_height(self):
        from src.utils.image_utils import ImageTextProcessor
        draw = ImageDraw.Draw(_new_image())
        _, single_height = ImageTextProcessor.draw_multiline_text(draw, xy=(4, 4), text='中\n中', size=20)
        _, with_empty_height = ImageTextProcessor.draw_multiline_text(draw, xy=(4, 4), text='中\n\n中', size=20)
        assert with_empty_height > single_height

    def test_trailing_newline_adds_height(self):
        from src.utils.image_utils import ImageTextProcessor
        draw = ImageDraw.Draw(_new_image())
        _, base_height = ImageTextProcessor.draw_multiline_text(draw, xy=(4, 4), text='中', size=20)
        _, trailing_height = ImageTextProcessor.draw_multiline_text(draw, xy=(4, 4), text='中\n', size=20)
        assert trailing_height > base_height

    def test_empty_fonts_raises(self):
        from src.utils.image_utils import ImageTextProcessor
        with pytest.raises(ValueError, match='at least one font'):
            ImageTextProcessor.draw_multiline_text(ImageDraw.Draw(_new_image()), xy=(0, 0), text='x', size=20, fonts={})


class TestMarkColorModes:
    """mark 色彩模式处理"""

    def test_mark_la_mode_converts_to_rgb(self):
        processor = _make_processor(_new_image(mode='LA', color=(128, 255)))
        processor.mark(text='mark')
        assert processor.image.mode == 'RGB'

    def test_mark_p_mode_converts_to_rgb(self):
        processor = _make_processor(_new_image(mode='P', color=1))
        processor.mark(text='mark')
        assert processor.image.mode == 'RGB'

    def test_mark_cmyk_mode_converts_to_rgb(self):
        processor = _make_processor(_new_image(mode='CMYK', color=(0, 0, 0, 0)))
        processor.mark(text='mark')
        assert processor.image.mode == 'RGB'


class TestParameterValidation:
    """非法参数校验"""

    def test_init_from_text_width_too_small_raises(self):
        from src.utils.image_utils import ImageLoader
        with pytest.raises(ValueError, match='image_width'):
            ImageLoader.init_from_text(text='hi', image_width=0)

    def test_init_from_text_negative_width_raises(self):
        from src.utils.image_utils import ImageLoader
        with pytest.raises(ValueError, match='image_width'):
            ImageLoader.init_from_text(text='hi', image_width=-5)

    def test_init_from_text_boundary_width_25(self):
        from src.utils.image_utils import ImageLoader
        image = ImageLoader.init_from_text(text='hi', image_width=25)
        assert image.width == 25

    def test_resize_with_filling_zero_size_raises(self):
        with pytest.raises(ValueError, match='size must be positive'):
            _make_processor().resize_with_filling(size=(0, 0))

    def test_resize_with_filling_negative_size_raises(self):
        with pytest.raises(ValueError, match='size must be positive'):
            _make_processor().resize_with_filling(size=(-1, 100))

    def test_resize_fill_canvas_zero_size_raises(self):
        with pytest.raises(ValueError, match='size must be positive'):
            _make_processor().resize_fill_canvas(size=(0, 100))

    def test_resize_fill_canvas_negative_size_raises(self):
        with pytest.raises(ValueError, match='size must be positive'):
            _make_processor().resize_fill_canvas(size=(-1, 100))

    def test_gaussian_blur_negative_radius_raises(self):
        with pytest.raises(ValueError, match='radius'):
            _make_processor().gaussian_blur(radius=-1)

    def test_gaussian_noise_negative_sigma_raises(self):
        with pytest.raises(ValueError, match='sigma'):
            _make_processor().gaussian_noise(sigma=-1, enable_random=False)

    def test_gaussian_noise_mask_factor_out_of_range_raises(self):
        with pytest.raises(ValueError, match='mask_factor'):
            _make_processor().gaussian_noise(mask_factor=1.5, enable_random=False)

    def test_has_glyph_multi_char_raises(self):
        from src.utils.image_utils import ImageTextProcessor
        fonts = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf')
        font = next(iter(fonts.values()))
        with pytest.raises(ValueError, match='single character'):
            ImageTextProcessor.has_glyph(font, 'ab')


class TestSaveFormatNormalization:
    """编码格式名称规范化"""

    def test_get_bytes_unknown_format_raises(self):
        with pytest.raises(ValueError, match='unsupported image format'):
            _make_processor().get_bytes(format_='FOO')

    def test_get_base64_unknown_format_raises(self):
        with pytest.raises(ValueError, match='unsupported image format'):
            _make_processor().get_base64(format_='FOO')

    def test_get_bytes_jpg_alias_normalized(self):
        content = _make_processor().get_bytes(format_='JPG')
        assert content.startswith(JPEG_MAGIC)

    def test_get_base64_jpg_data_uri_uses_jpeg_mime(self):
        content = _make_processor().get_base64(format_='JPG', use_data_uri_scheme=True)
        assert content.startswith('data:image/jpeg;base64,')


class TestPathTraversalGuard:
    """路径穿越防护在模块入口的集成断言(仅路径解析与拦截分支, 不落盘)"""

    def test_font_name_parent_traversal_blocked(self):
        from src.resource import ResourcePathOutOfRootError
        from src.utils.image_utils.config import image_utils_config
        with pytest.raises(ResourcePathOutOfRootError):
            image_utils_config.get_custom_name_font('../../pyproject.toml')

    def test_font_name_absolute_path_blocked(self):
        from src.resource import ResourcePathOutOfRootError
        from src.utils.image_utils.config import image_utils_config
        with pytest.raises(ResourcePathOutOfRootError):
            image_utils_config.get_custom_name_font('/etc/passwd')

    def test_font_name_stay_inside_root_allowed(self):
        from src.utils.image_utils.config import image_utils_config
        font = image_utils_config.get_custom_name_font('../../static/fonts/msyh.ttc')
        assert Path(font.resolve_path).is_file()

    async def test_save_filename_escape_tmp_root_blocked(self):
        from src.resource import ResourcePathOutOfRootError
        with pytest.raises(ResourcePathOutOfRootError):
            await _make_processor().save(file='../../../evil.jpg')

    async def test_save_filename_escape_output_folder_blocked(self):
        with pytest.raises(ValueError, match='outside of the default output folder'):
            await _make_processor().save(file='../../evil.jpg')

    def test_save_filename_normal_resolves_inside_output(self):
        from src.utils.image_utils.config import image_utils_config
        folder = image_utils_config.default_output_folder
        target = folder('normal.jpg')
        assert Path(target.resolve_path).is_relative_to(Path(folder.resolve_path))
        assert target.resolve_path.endswith('normal.jpg')


class TestFontCache:
    """字体加载缓存(L8)"""

    def test_load_fonts_returns_cached_ttfont(self):
        """同名字体重复加载返回缓存的同一 TTFont 对象"""
        from src.utils.image_utils import ImageTextProcessor
        first = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf')
        second = ImageTextProcessor.load_fonts('SourceHanSansSC-Regular.otf')
        assert next(iter(first.values())) is next(iter(second.values()))

    def test_truetype_font_cached_by_path_and_size(self):
        """相同路径与字号返回缓存的同一 FreeTypeFont 对象"""
        from src.utils.image_utils.config import image_utils_config
        from src.utils.image_utils.image_util import _load_truetype_font_cached
        path = image_utils_config.default_font.resolve_path
        assert _load_truetype_font_cached(path, 20) is _load_truetype_font_cached(path, 20)

    def test_cached_font_rendering_unchanged(self):
        """缓存复用不改变绘制结果"""
        from src.utils.image_utils import ImageTextProcessor

        def _draw_once() -> bytes:
            image = _new_image(size=(160, 160))
            ImageTextProcessor.draw_multiline_text(ImageDraw.Draw(image), xy=(4, 4), text=TEXT_MULTILINE, size=20)
            return image.tobytes()

        assert _draw_once() == _draw_once()

    def test_concurrent_draw_deterministic_output(self):
        """跨线程共享缓存字体时绘制结果仍确定(Pillow 字体操作以临界区保护)"""
        from concurrent.futures import ThreadPoolExecutor

        from src.utils.image_utils import ImageTextProcessor

        def _draw_once() -> bytes:
            image = _new_image(size=(160, 160))
            ImageTextProcessor.draw_multiline_text(ImageDraw.Draw(image), xy=(4, 4), text=TEXT_MULTILINE, size=20)
            return image.tobytes()

        expected = _draw_once()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: _draw_once(), range(8)))
        assert all(result == expected for result in results)
