"""
@Author         : Ailitonia
@Date           : 2024/11/5 10:58:52
@FileName       : helpers.py
@Project        : omega-miya
@Description    : 定时任务模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger, get_driver

from src.service import scheduler
from .api import BilibiliCredential


async def _refresh_bilibili_login_status() -> None:
    """检查 bilibili 登录状态, 根据需要刷新 Cookies"""
    logger.opt(colors=True).debug('<lc>Bilibili</lc> | 开始检查用户 Cookies 状态')
    bc = BilibiliCredential()

    is_valid = await bc.check_valid()
    if not is_valid:
        logger.opt(colors=True).warning('<lc>Bilibili</lc> | <r>用户 Cookies 未配置或验证失败</r>, 部分功能可能不可用')
        return

    await bc.update_buvid_cookies()
    need_refresh = await bc.check_need_refresh()
    if need_refresh:
        logger.opt(colors=True).warning('<lc>Bilibili</lc> | <ly>用户 Cookies 需要刷新</ly>, 正在尝试刷新中')
        refresh_result = await bc.refresh_cookies()
        if refresh_result:
            logger.opt(colors=True).warning('<lc>Bilibili</lc> | <lg>用户 Cookies 刷新成功</lg>')
        else:
            logger.opt(colors=True).error('<lc>Bilibili</lc> | <r>用户 Cookies 刷新失败</r>')
    else:
        logger.opt(colors=True).debug('<lc>Bilibili</lc> | <lg>用户 Cookies 有效, 无需刷新</lg>')


@get_driver().on_startup
async def _load_and_refresh_bilibili_login_status() -> None:
    try:
        await BilibiliCredential.load_cookies_from_db()
        await _refresh_bilibili_login_status()
    except Exception as e:
        logger.opt(colors=True).error(f'<lc>Bilibili</lc> | <r>用户 Cookies 刷新失败</r>, 请尝试重新登录, {e}')


@scheduler.scheduled_job(
    'cron',
    hour='*/8',
    minute='23',
    second='23',
    id='bilibili_login_status_refresh_monitor',
    coalesce=True,
    misfire_grace_time=120
)
async def _bilibili_login_status_refresh_monitor() -> None:
    try:
        await _refresh_bilibili_login_status()
    except Exception as e:
        logger.opt(colors=True).error(f'<lc>Bilibili</lc> | <r>用户 Cookies 刷新失败</r>, 请尝试重新登录, {e}')


__all__ = []
