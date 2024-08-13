"""
@Author         : Ailitonia
@Date           : 2024/8/1 14:45:35
@FileName       : booru_api.py
@Project        : omega-miya
@Description    : Danbooru 及其衍生 API (Read requests only)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .danbooru import BaseDanbooruAPI

danbooru_api = BaseDanbooruAPI(root_url='https://danbooru.donmai.us')


__all__ = [
    'danbooru_api',
]
