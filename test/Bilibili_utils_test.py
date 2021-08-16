"""
@Author         : Ailitonia
@Date           : 2021/05/29 0:05
@FileName       : Bilibili_utils_test.py
@Project        : nonebot2_miya 
@Description    : Bilibili Utils test
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.utils.bilibili_utils import BiliDynamic, BiliUser
import nonebot


async def test():
    bu = BiliUser(user_id=1617739681)
    # dy_his = await bu.get_dynamic_history()
    bd_info = await BiliDynamic(dynamic_id=529075172698301430).get_info()
    print(BiliDynamic.data_parser(dynamic_data=bd_info.result))

    bd_info = await BiliDynamic(dynamic_id=529074691660911614).get_info()
    print(BiliDynamic.data_parser(dynamic_data=bd_info.result))


nonebot.get_driver().on_startup(test)
