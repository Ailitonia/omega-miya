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
from datetime import datetime
from io import BytesIO
from matplotlib import pyplot as plt

from omega_miya.database import Statistic
from omega_miya.local_resource import TmpResource
from omega_miya.utils.process_utils import run_sync, run_async_catching_exception


_TMP_STATISTIC_IMG_FOLDER: str = 'statistic'
"""生成统计图缓存文件夹名"""
_TMP_STATISTIC_PATH: TmpResource = TmpResource(_TMP_STATISTIC_IMG_FOLDER)
"""生成统计图缓存资源地址"""


@run_async_catching_exception
async def draw_statistics(
        self_id: str,
        start_time: datetime,
        *,
        title: str = '插件使用统计',
        call_id: str | None = None
) -> TmpResource:
    """绘制插件使用统计图

    :param self_id: bot self id
    :param start_time: 统计启示时间
    :param title: 图表标题
    :param call_id: 统计调用 id
    """
    statistic_result = await Statistic.query_by_condition(bot_self_id=self_id, call_id=call_id, start_time=start_time)

    def _handle() -> bytes:
        plt.switch_backend('agg')  # Fix RuntimeError caused by GUI needed
        if sys.platform.startswith('win'):
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False
        plt.barh([x.custom_name for x in statistic_result], [x.call_count for x in statistic_result])
        plt.title(title)
        with BytesIO() as bf:
            plt.savefig(bf, dpi=300, format='JPG')
            img_bytes = bf.getvalue()
        return img_bytes

    image_content = await run_sync(_handle)()
    image_file_name = f"statistic_{title}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"
    save_file = _TMP_STATISTIC_PATH(image_file_name)
    async with save_file.async_open('wb') as af:
        await af.write(image_content)
    return save_file


__all__ = [
    'draw_statistics'
]
