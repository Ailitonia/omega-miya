import os
import asyncio
from datetime import datetime
from nonebot import logger, get_driver
from PIL import Image, ImageDraw, ImageFont
from omega_miya.database import Result

global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
RESOURCES_PATH = global_config.resources_path_


class TextUtils(object):
    def __init__(self, text: str):
        self.text = text

    def split_multiline(self, width: int, font: ImageFont.FreeTypeFont) -> str:
        """
        按长度切分换行文本
        :return: 切分换行后的文本
        """
        spl_num = 0
        spl_list = []
        for num in range(len(self.text)):
            text_width, text_height = font.getsize_multiline(self.text[spl_num:num])
            if text_width > width:
                spl_list.append(self.text[spl_num:num])
                spl_num = num
        else:
            spl_list.append(self.text[spl_num:])
        return '\n'.join(spl_list)

    def __text_to_img(
            self,
            *,
            image_wight: int = 512,
            font_name: str = 'SourceHanSans_Regular.otf'
    ) -> Image:
        font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', font_name))
        if not os.path.exists(font_path):
            raise ValueError('Font not found')

        # 处理文字层 主体部分
        font_size = image_wight // 25
        font = ImageFont.truetype(font_path, font_size)
        # 按长度切分文本
        text_ = self.split_multiline(width=int(image_wight * 0.75), font=font)
        text_w, text_h = font.getsize_multiline(text_)

        # 初始化背景图层
        image_height = text_h + 100
        background = Image.new(mode="RGB", size=(image_wight, image_height), color=(255, 255, 255))
        # 绘制文字
        ImageDraw.Draw(background).multiline_text(
            xy=(int(image_wight * 0.12), 50),
            text=text_,
            font=font,
            fill=(0, 0, 0))

        return background

    async def text_to_img(
            self,
            *,
            image_wight: int = 512,
            font_name: str = 'SourceHanSans_Regular.otf'
    ) -> Result.TextResult:
        def __handle():
            img_ = self.__text_to_img(image_wight=image_wight, font_name=font_name)
            # 检查生成图片路径
            img_folder_path = os.path.abspath(os.path.join(TMP_PATH, 'text_to_img'))
            if not os.path.exists(img_folder_path):
                os.makedirs(img_folder_path)
            img_path = os.path.abspath(
                os.path.join(img_folder_path, f"{hash(self.text)}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"))
            # 保存图片
            img_.save(img_path, 'JPEG')
            return img_path

        loop = asyncio.get_running_loop()
        try:
            path_result = await loop.run_in_executor(None, __handle)
            path = os.path.abspath(path_result)
            return Result.TextResult(error=False, info='Success', result=path)
        except Exception as e:
            logger.error(f'TextUtils | text_to_img failed, error: {repr(e)}')
            return Result.TextResult(error=True, info=repr(e), result='')


__all__ = [
    'TextUtils'
]
