"""
@Author         : Ailitonia
@Date           : 2026/8/23 14:21
@FileName       : custom_run
@Project        : omega-miya
@Description    : 
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

# 获取 driver 用于注册 Adapter
# driver = nonebot.get_driver()

# 注册 Adapter
# from nonebot.adapters.console import Adapter as ConsoleAdapter
# driver.register_adapter(ConsoleAdapter)

# 加载插件
# nonebot.load_plugins('src/service')
# nonebot.load_plugins('src/plugins')

# Modify some config / config depends on loaded configs
# config = nonebot.get_driver().config
# do something...


if __name__ == '__main__':
    # from src.database.migrate import run_upgrade_migrations
    # run_upgrade_migrations()

    nonebot.run()
