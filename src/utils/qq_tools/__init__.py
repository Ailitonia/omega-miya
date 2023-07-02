"""
@Author         : Ailitonia
@Date           : 2022/04/17 16:06
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 一些 qq 相关的工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.resource import TemporaryResource
from src.service import OmegaRequests


_qq_tmp_folder = TemporaryResource('qq_tools')


def get_user_head_img_url(user_id: int, *, head_img_size: int = 5, url_version: int = 0) -> str:
    """获取用户头像链接

    :param user_id: 用户 qq 号
    :param head_img_size: 1: 40×40px, 2: 40 × 40px, 3: 100 × 100px, 4: 140 × 140px, 5: 640 × 640px,
                        40: 40 × 40px, 100: 100 × 100px
    :param url_version: 使用的 url 版本
    """
    match url_version:
        case 2:
            url = f'https://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={user_id}'
        case 1:
            url = f'https://q2.qlogo.cn/headimg_dl?dst_uin={user_id}&spec={head_img_size}'
        case 0 | _:
            url = f'https://q1.qlogo.cn/g?b=qq&nk={user_id}&s={head_img_size}'
    return url


async def get_user_head_img(user_id: int, *, head_img_size: int = 5, url_version: int = 0) -> TemporaryResource:
    """获取用户头像

    :param user_id: 用户 qq 号
    :param head_img_size: 1: 40×40px, 2: 40 × 40px, 3: 100 × 100px, 4: 140 × 140px, 5: 640 × 640px,
                        40: 40 × 40px, 100: 100 × 100px
    :param url_version: 使用的 url 版本
    """
    url = get_user_head_img_url(user_id=user_id, head_img_size=head_img_size, url_version=url_version)
    head_img_file = _qq_tmp_folder('head_img', f'{user_id}_{head_img_size}')
    await OmegaRequests().download(url=url, file=head_img_file)
    return head_img_file


__all__ = [
    'get_user_head_img_url',
    'get_user_head_img'
]
