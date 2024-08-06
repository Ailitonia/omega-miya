"""
@Author         : Ailitonia
@Date           : 2024/8/1 14:45:35
@FileName       : danbooru_api.py
@Project        : omega-miya
@Description    : Danbooru API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .danbooru import DanbooruAPIBase

danbooru_api = DanbooruAPIBase(root_url='https://danbooru.donmai.us')


__all__ = [
    'danbooru_api',
]