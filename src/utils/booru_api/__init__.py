"""
@Author         : Ailitonia
@Date           : 2024/8/1 14:45:35
@FileName       : booru_api.py
@Project        : omega-miya
@Description    : Danbooru 及其衍生 API (Read requests only)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .config import booru_config as booru_config
from .danbooru import DanbooruAPI
from .gelbooru import GelbooruAPI
from .moebooru import KonachanAPI, YandereAPI


danbooru_api = DanbooruAPI(username=booru_config.danbooru_username, api_key=booru_config.danbooru_api_key)
gelbooru_api = GelbooruAPI(user_id=booru_config.gelbooru_user_id, api_key=booru_config.gelbooru_api_key)
konachan_api = KonachanAPI(login_name=booru_config.konachan_login_name,
                           password_hash=booru_config.konachan_password_hash)
yandere_api = YandereAPI(login_name=booru_config.yandere_login_name, password_hash=booru_config.yandere_password_hash)


__all__ = [
    'danbooru_api',
    'gelbooru_api',
    'konachan_api',
    'yandere_api',
]
