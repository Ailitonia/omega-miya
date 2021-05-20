import os
import nonebot
from datetime import datetime
from nonebot.adapters.cqhttp import Bot as CQHTTPBot
from nonebot.log import logger, default_format

# win环境下proxy配置
import sys
import asyncio
if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# File path
bot_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'omega_miya'))
bot_tmp_path = os.path.abspath(os.path.join(bot_root_path, 'tmp'))
if not os.path.exists(bot_tmp_path):
    os.makedirs(bot_tmp_path)

bot_log_path = os.path.abspath(os.path.join(bot_root_path, 'log'))
if not os.path.exists(bot_log_path):
    os.makedirs(bot_log_path)

# Custom logger
log_info_name = f"{datetime.today().strftime('%Y%m%d-%H%M%S')}-INFO.log"
log_error_name = f"{datetime.today().strftime('%Y%m%d-%H%M%S')}-ERROR.log"
log_info_path = os.path.join(bot_log_path, log_info_name)
log_error_path = os.path.join(bot_log_path, log_error_name)

logger.add(log_info_path, rotation="00:00", diagnose=False, level="INFO", format=default_format, encoding='utf-8')
logger.add(log_error_path, rotation="00:00", diagnose=False, level="ERROR", format=default_format, encoding='utf-8')

# You can pass some keyword args config to init function
nonebot.init()

# 初始化一些系统变量配置
config = nonebot.get_driver().config
config.root_path_ = bot_root_path
config.tmp_path_ = bot_tmp_path

# 注册 cqhttp adapter
driver = nonebot.get_driver()
driver.register_adapter("cqhttp", CQHTTPBot)

nonebot.load_plugins("omega_miya/utils")
nonebot.load_plugins("omega_miya/plugins")

# Modify some config / config depends on loaded configs
# config = nonebot.get_driver().config
# do something...
# nonebot.load_plugin("nonebot_plugin_test")
# nonebot.require("nonebot_plugin_apscheduler").scheduler.print_jobs()


if __name__ == "__main__":
    nonebot.run()
