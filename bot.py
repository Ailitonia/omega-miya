import os
import sys
import nonebot
from datetime import datetime
from nonebot.log import logger, default_format

# Log file path
bot_log_path = os.path.abspath(os.path.join(sys.path[0], 'log'))
if not os.path.exists(bot_log_path):
    os.makedirs(bot_log_path)

# Custom logger
log_info_name = f'{datetime.now().strftime("%Y%m%d-%H%M%S")}-INFO.log'
log_error_name = f'{datetime.now().strftime("%Y%m%d-%H%M%S")}-ERROR.log'
log_info_path = os.path.join(bot_log_path, log_info_name)
log_error_path = os.path.join(bot_log_path, log_error_name)

logger.add(log_info_path, rotation='00:00', diagnose=False, level='INFO', format=default_format, encoding='utf-8')
logger.add(log_error_path, rotation='00:00', diagnose=False, level='ERROR', format=default_format, encoding='utf-8')

# Add extra debug log file
# log_debug_name = f'{datetime.now().strftime("%Y%m%d-%H%M%S")}-DEBUG.log'
# log_debug_path = os.path.join(bot_log_path, log_debug_name)
# logger.add(log_debug_path, rotation='00:00', diagnose=False, level='DEBUG', format=default_format, encoding='utf-8')

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
    nonebot.run()
