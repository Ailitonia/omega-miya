"""
@Author         : Ailitonia
@Date           : 2021/07/29 19:29
@FileName       : process_utils.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
from typing import List, Tuple, Awaitable, Optional, Any
from nonebot import logger
from omega_miya.database import BaseResult


class ProcessUtils(object):
    @classmethod
    async def fragment_process(
            cls,
            tasks: List[Awaitable[Any]],
            fragment_size: Optional[int] = None,
            *,
            log_flag: str = 'Default',
            return_exceptions: bool = True) -> Tuple:
        """
        分段运行一批需要并行的异步函数
        :param tasks: 任务序列
        :param fragment_size: 单次并行的数量
        :param log_flag: 日志标记
        :param return_exceptions: 是否在结果中包含异常
        """
        # 判断任务列表
        if tasks is None:
            raise ValueError('Param "tasks" must not be None')
        all_count = len(tasks)
        if all_count <= 0:
            return ()
        # 判断分割数
        if fragment_size is None:
            fragment_size = all_count
        elif not isinstance(fragment_size, int):
            raise ValueError('Param "fragment_size" must be int')
        elif fragment_size > all_count:
            fragment_size = all_count
        elif fragment_size <= 0:
            raise ValueError('Param "fragment_size" must be greater than zero')

        # 切分切片列表
        fragment_list = []
        for i in range(0, all_count, fragment_size):
            fragment_list.append(tasks[i:i + fragment_size])
        fragment_count = len(fragment_list)

        # 执行进度及统计计数
        error_tag = False
        error_count = 0
        process_rate_count = 0
        # 最终返回的结果
        result = []
        # 每个切片打包一个任务
        for index, fragment in enumerate(fragment_list):
            # 进行异步处理
            try:
                _result = await asyncio.gather(*fragment, return_exceptions=return_exceptions)
                result.extend(_result)
            except Exception as e:
                logger.error(f'Fragment process | {log_flag} processing error occurred in fragment({index}), '
                             f'error info: {repr(e)}, other tasks will continue to run')
                result.extend([Exception('return exceptions')] * len(fragment))
                error_tag = True
                error_count += 1
                continue

            # 显示进度
            process_rate_count += 1
            logger.info(f'Fragment process | {log_flag} processing: {process_rate_count}/{fragment_count}')

        for index, item in enumerate(result):
            if isinstance(item, Exception):
                logger.error(f'Fragment process | {log_flag} processing occur an error in task({index}), '
                             f'error info: {repr(item)}')
                error_tag = True
                error_count += 1
            elif isinstance(item, BaseResult):
                if item.error:
                    logger.error(f'Fragment process | {log_flag} processing occur an error in task({index}), '
                                 f'and return a Result object, with error info: {repr(item.info)}')
                    error_tag = True
                    error_count += 1

        if error_tag:
            logger.opt(colors=True).warning(
                f'Fragment process | {log_flag} <lg>processing complete</lg>, '
                f'<ly>but some error occurred in some task(s)</ly>, total tasks: {all_count}, error(s): {error_count}')
        else:
            logger.opt(colors=True).success(
                f'Fragment process | {log_flag} <lg>processing complete successful</lg>, total tasks: {all_count}')
        return tuple(result)


__all__ = [
    'ProcessUtils'
]
