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
from typing import Optional
from io import BytesIO
from PIL import Image, ImageFilter
from omega_miya.utils.Omega_Base import Result


class PicEffector(object):
    @classmethod
    def add_blank_bytes(cls, image: bytes, bytes_num: int = 16) -> bytes:
        return image + b''*bytes_num

    @classmethod
    async def gaussian_blur(cls, image: bytes, radius: Optional[int] = None) -> Result.BytesResult:
        def __handle() -> Result.BytesResult:
            with BytesIO() as byte_file:
                byte_file.write(image)
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


__all__ = [
    'PicEffector'
]
