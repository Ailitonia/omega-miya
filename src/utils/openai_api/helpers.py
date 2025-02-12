"""
@Author         : Ailitonia
@Date           : 2025/2/12 15:39:43
@FileName       : helpers.py
@Project        : omega-miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import base64
from typing import TYPE_CHECKING

from nonebot.utils import run_sync

if TYPE_CHECKING:
    from src.resource import BaseResource


@run_sync
def base64_encode(content: bytes, *, encoding: str = 'utf-8') -> str:
    return base64.b64encode(content).decode(encoding)


async def encode_local_audio(audio: 'BaseResource') -> tuple[str, str]:
    """将本地音频文件编码成 base64 格式的 input_audio, 返回 (data, format) 的数组"""
    async with audio.async_open('rb') as af:
        content = await af.read()
    return await base64_encode(content), audio.path.suffix.removeprefix('.')


async def encode_local_image(image: 'BaseResource') -> str:
    """将本地图片文件编码成 base64 格式的 image_url"""
    async with image.async_open('rb') as af:
        content = await af.read()
    return f'data:image/{image.path.suffix.removeprefix('.')};base64,{await base64_encode(content)}'


__all__ = [
    'encode_local_audio',
    'encode_local_image',
]
