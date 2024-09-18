"""
@Author         : Ailitonia
@Date           : 2024/8/31 上午10:44
@FileName       : omega_any_artworks
@Project        : bot.py
@Description    : omega-miya 启动入口文件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import nonebot
from nonebot.log import logger, default_format

from src.resource import LogFileResource

# Log file path
log_path = LogFileResource()
logger.add(log_path.info, rotation='00:00', diagnose=False, level='INFO', format=default_format, encoding='utf-8')
logger.add(log_path.error, rotation='00:00', diagnose=False, level='ERROR', format=default_format, encoding='utf-8')

# Add extra debug log file
# logger.add(log_path.debug, rotation='00:00', diagnose=False, level='DEBUG', format=default_format, encoding='utf-8')

# You can pass some keyword args config to init function
nonebot.init()

# 获取 driver 用于初始化
driver = nonebot.get_driver()

# 按需注册 OneBot V11 Adapter
if driver.config.model_dump().get('onebot_access_token'):
    from nonebot.adapters.onebot.v11.adapter import Adapter as OneBotAdapter
    driver.register_adapter(OneBotAdapter)

# 按需注册 QQ Adapter
if driver.config.model_dump().get('qq_bots'):
    from nonebot.adapters.qq.adapter import Adapter as QQAdapter
    driver.register_adapter(QQAdapter)

# 按需注册 Telegram Adapter
if driver.config.model_dump().get('telegram_bots'):
    from nonebot.adapters.telegram.adapter import Adapter as TelegramAdapter
    driver.register_adapter(TelegramAdapter)

# 按需注册 Console Adapter
if driver.config.model_dump().get('enable_console'):
    from nonebot.adapters.console import Adapter as ConsoleAdapter
    driver.register_adapter(ConsoleAdapter)

# 加载插件
nonebot.load_plugins('src/service')
nonebot.load_plugins('src/plugins')

# Modify some config / config depends on loaded configs
# config = nonebot.get_driver().config
# do something...


if __name__ == '__main__':
    # from src.database.migrate import run_upgrade_migrations
    # run_upgrade_migrations()

    nonebot.run()
