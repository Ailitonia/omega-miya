"""
@Author         : Ailitonia
@Date           : 2021/06/03 21:14
@FileName       : PicEffector_test.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import aiofiles
import nonebot
from omega_miya.utils.omega_plugin_utils import PicEffector


async def test():
    async with aiofiles.open('D:\\78486250_p0.png', 'rb') as af:
        image = await af.read()
        effector = PicEffector(image=image)
        async with aiofiles.open('D:\\out_put.png', 'wb+') as af2:
            await af2.write((await effector.gaussian_blur()).result)


nonebot.get_driver().on_startup(test)
