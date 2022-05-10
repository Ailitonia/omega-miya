"""
@Author         : Ailitonia
@Date           : 2022/04/17 16:06
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 一些 qq 相关的工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.local_resource import TmpResource
from omega_miya.web_resource import HttpFetcher


_qq_tmp_folder = TmpResource('qq_tools')


async def get_user_head_img(user_id: int, *, head_img_size: int = 5) -> TmpResource:
    """
    :param user_id: 用户 qq 号
    :param head_img_size: 1: 40×40px, 2: 40 × 40px, 3: 100 × 100px, 4: 140 × 140px, 5: 640 × 640px,
                        40: 40 × 40px, 100: 100 × 100px
    :return: 图片消息
    """
    url = f'https://q1.qlogo.cn/g?b=qq&nk={user_id}&s={head_img_size}'
    url2 = f'https://q2.qlogo.cn/headimg_dl?dst_uin={user_id}&spec={head_img_size}'
    url_i = f'https://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={user_id}'

    head_img_file = _qq_tmp_folder('head_img', f'{user_id}_{head_img_size}')
    await HttpFetcher().download_file(url=url, file=head_img_file)
    return head_img_file


__all__ = [
    'get_user_head_img'
]
