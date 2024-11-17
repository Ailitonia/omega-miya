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
from .moebooru import BehoimiAPI, KonachanAPI, KonachanSafeAPI, YandereAPI

danbooru_api = DanbooruAPI(username=booru_config.danbooru_username, api_key=booru_config.danbooru_api_key)
gelbooru_api = GelbooruAPI(user_id=booru_config.gelbooru_user_id, api_key=booru_config.gelbooru_api_key)
behoimi_api = BehoimiAPI(login_name=booru_config.behoimi_login_name,
                         password_hash=booru_config.behoimi_password_hash,
                         legacy_endpoint=True)
konachan_api = KonachanAPI(login_name=booru_config.konachan_com_login_name,
                           password_hash=booru_config.konachan_com_password_hash)
konachan_safe_api = KonachanSafeAPI(login_name=booru_config.konachan_com_login_name,
                                    password_hash=booru_config.konachan_com_password_hash)
yandere_api = YandereAPI(login_name=booru_config.yandere_login_name, password_hash=booru_config.yandere_password_hash)


__all__ = [
    'DanbooruAPI',
    'GelbooruAPI',
    'BehoimiAPI',
    'KonachanAPI',
    'KonachanSafeAPI',
    'YandereAPI',
    'danbooru_api',
    'gelbooru_api',
    'behoimi_api',
    'konachan_api',
    'konachan_safe_api',
    'yandere_api',
]
