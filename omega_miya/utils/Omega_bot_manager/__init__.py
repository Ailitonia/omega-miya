"""
@Author         : Ailitonia
@Date           : 2021/05/23 19:40
@FileName       : __init__.py
@Project        : nonebot2_miya 
@Description    : Bot Auto Manager
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from nonebot.adapters.cqhttp.bot import Bot
from omega_miya.utils.Omega_Base import DBBot

driver = get_driver()


@driver.on_bot_connect
async def upgrade_connected_bot(bot: Bot):
    # bot_info = await bot.get_login_info()
    bot_info = await bot.get_version_info()
    info = '||'.join([f'{k}:{v}' for (k, v) in bot_info.items()])
    bot_result = await DBBot(self_qq=int(bot.self_id)).upgrade(status=1, info=info)
    if bot_result.success():
        logger.opt(colors=True).info(f'Bot: {bot.self_id} <lg>已连接</lg>, '
                                     f'<lg>Database upgrade Success</lg>: {bot_result.info}')
    else:
        logger.opt(colors=True).error(f'Bot: {bot.self_id} <ly>已连接</ly>, '
                                      f'<r>Database upgrade Success</r>: {bot_result.info}')


@driver.on_bot_disconnect
async def upgrade_disconnected_bot(bot: Bot):
    bot_result = await DBBot(self_qq=int(bot.self_id)).upgrade(status=0)
    if bot_result.success():
        logger.opt(colors=True).warning(f'Bot: {bot.self_id} <ly>已离线</ly>, '
                                        f'<lg>Database upgrade Success</lg>: {bot_result.info}')
    else:
        logger.opt(colors=True).error(f'Bot: {bot.self_id} <lr>已离线</lr>, '
                                      f'<r>Database upgrade Success</r>: {bot_result.info}')
