"""
@Author         : Ailitonia
@Date           : 2021/08/15 1:20
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 统计做图工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import sys
import asyncio
from io import BytesIO
from typing import Tuple, List
from matplotlib import pyplot as plt


async def draw_statistics(data: List[Tuple[str, int]], *, title: str = '插件使用统计') -> bytes:
    """
    :param data: DBStatistic 对象 get statistic 返回数据
    :param title: 图表标题
    :return:
    """
    def __handle() -> bytes:
        name = [x[0] for x in data]
        count = [x[1] for x in data]
        if sys.platform.startswith('win'):
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False
        plt.barh(name, count)
        plt.title(title)
        with BytesIO() as bf:
            plt.savefig(bf, dpi=300)
            img_bytes = bf.getvalue()
        return img_bytes

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __handle)
    return result
