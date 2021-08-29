"""
@Author         : Ailitonia
@Date           : 2021/06/27 17:31
@FileName       : gif_render.py
@Project        : nonebot2_miya 
@Description    : gif表情包生成模板
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import asyncio
import imageio
from io import BytesIO
from typing import Optional
from PIL import Image


async def stick_maker_temp_petpet(
        text: str,
        image_file: Image.Image,
        font_path: str,
        image_wight: int,
        image_height: int,
        temp_path: str,
        *args,
        **kwargs) -> Optional[bytes]:
    """
    petpet 表情包模板
    """
    def __handle() -> Optional[bytes]:
        bg0 = Image.new(mode="RGBA", size=(112, 112), color=(255, 255, 255))
        bg1 = Image.new(mode="RGBA", size=(112, 112), color=(255, 255, 255))
        bg2 = Image.new(mode="RGBA", size=(112, 112), color=(255, 255, 255))
        bg3 = Image.new(mode="RGBA", size=(112, 112), color=(255, 255, 255))
        bg4 = Image.new(mode="RGBA", size=(112, 112), color=(255, 255, 255))
        tp0 = Image.open(os.path.join(temp_path, 'template_p0.png'))
        tp1 = Image.open(os.path.join(temp_path, 'template_p1.png'))
        tp2 = Image.open(os.path.join(temp_path, 'template_p2.png'))
        tp3 = Image.open(os.path.join(temp_path, 'template_p3.png'))
        tp4 = Image.open(os.path.join(temp_path, 'template_p4.png'))
        bg0.paste(image_file.resize((95, 95)), (12, 15))
        bg1.paste(image_file.resize((97, 80)), (11, 30))
        bg2.paste(image_file.resize((99, 70)), (10, 40))
        bg3.paste(image_file.resize((97, 75)), (11, 35))
        bg4.paste(image_file.resize((96, 90)), (11, 20))
        bg0.paste(tp0, (0, 0), mask=tp0)
        bg1.paste(tp1, (0, 0), mask=tp1)
        bg2.paste(tp2, (0, 0), mask=tp2)
        bg3.paste(tp3, (0, 0), mask=tp3)
        bg4.paste(tp4, (0, 0), mask=tp4)

        frames_list = []
        with BytesIO() as bf0:
            bg0.save(bf0, format='PNG')
            img_bytes = bf0.getvalue()
            frames_list.append(imageio.imread(img_bytes))
        with BytesIO() as bf1:
            bg1.save(bf1, format='PNG')
            img_bytes = bf1.getvalue()
            frames_list.append(imageio.imread(img_bytes))
        with BytesIO() as bf2:
            bg2.save(bf2, format='PNG')
            img_bytes = bf2.getvalue()
            frames_list.append(imageio.imread(img_bytes))
        with BytesIO() as bf3:
            bg3.save(bf3, format='PNG')
            img_bytes = bf3.getvalue()
            frames_list.append(imageio.imread(img_bytes))
        with BytesIO() as bf4:
            bg4.save(bf4, format='PNG')
            img_bytes = bf4.getvalue()
            frames_list.append(imageio.imread(img_bytes))

        with BytesIO() as bf:
            imageio.mimsave(bf, frames_list, 'GIF', duration=0.06)
            return bf.getvalue()

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result


__all__ = [
    'stick_maker_temp_petpet'
]
