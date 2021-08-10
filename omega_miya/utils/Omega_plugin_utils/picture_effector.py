"""
@Author         : Ailitonia
@Date           : 2021/06/02 0:35
@FileName       : picture_effector.py
@Project        : nonebot2_miya 
@Description    : Picture Effector
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
import random
from typing import Optional
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance
from omega_miya.utils.Omega_Base import Result


class PicEffector(object):
    def __init__(self, image: bytes):
        self.image = image

    def add_blank_bytes(self, bytes_num: int = 16) -> bytes:
        return self.image + b' '*bytes_num

    async def gaussian_blur(self, radius: Optional[int] = None) -> Result.BytesResult:
        def __handle() -> Result.BytesResult:
            with BytesIO() as byte_file:
                byte_file.write(self.image)
                # 处理图片
                mk_image = Image.open(byte_file)
                if radius:
                    blur_radius = radius
                else:
                    blur_radius = mk_image.width // 16
                blur_image = mk_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                with BytesIO() as mk_byte_file:
                    blur_image.save(mk_byte_file, format='PNG')
                    img_bytes = mk_byte_file.getvalue()
            return Result.BytesResult(error=False, info='Success', result=img_bytes)

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, __handle)
        except Exception as e:
            result = Result.BytesResult(error=True, info=f'gaussian_blur failed: {repr(e)}', result=b'')
        return result

    async def gaussian_noise(
            self,
            *,
            sigma: Optional[float] = 8,
            enable_random: bool = True,
            mask_factor: Optional[float] = 0.25) -> Result.BytesResult:
        """
        为图片添加肉眼不可见的底噪
        :param sigma: 噪声sigma, 默认值8
        :param enable_random: 为噪声sigma添加随机扰动, 默认值True
        :param mask_factor: 噪声蒙版透明度修正, 默认值0.25
        :return:
        """
        def __handle() -> Result.BytesResult:
            with BytesIO() as byte_file:
                byte_file.write(self.image)
                # 处理图片
                mk_image: Image.Image = Image.open(byte_file)
                width, height = mk_image.width, mk_image.height
                # 为sigma添加随机扰动
                if enable_random:
                    sigma_ = sigma * (1 + 0.1 * random.random())
                else:
                    sigma_ = sigma
                # 生成高斯噪声底图
                noise_image = Image.effect_noise(size=(width, height), sigma=sigma_)
                # 生成底噪蒙版
                noise_mask = ImageEnhance.Brightness(noise_image.convert('L')).enhance(factor=mask_factor)
                with BytesIO() as mk_byte_file:
                    # 叠加噪声图层
                    mk_image.paste(noise_image, (0, 0), mask=noise_mask)
                    mk_image.save(mk_byte_file, format='PNG')
                    img_bytes = mk_byte_file.getvalue()
            return Result.BytesResult(error=False, info='Success', result=img_bytes)

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, __handle)
        except Exception as e:
            result = Result.BytesResult(error=True, info=f'gaussian_noise failed: {repr(e)}', result=b'')
        return result


__all__ = [
    'PicEffector'
]
