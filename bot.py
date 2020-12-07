import os
import nonebot
from datetime import datetime
from nonebot.adapters.cqhttp import Bot as CQHTTPBot
from nonebot.log import logger, default_format


# Custom logger
log_info_name = f"{datetime.today().strftime('%Y%m%d-%H%M%S')}-INFO.log"
log_error_name = f"{datetime.today().strftime('%Y%m%d-%H%M%S')}-ERROR.log"
log_file_path = os.path.join(os.path.dirname(__file__), 'omega_miya', 'log')
log_info_path = os.path.join(log_file_path, log_info_name)
log_error_path = os.path.join(log_file_path, log_error_name)

logger.add(log_info_path, rotation="00:00", diagnose=False, level="INFO", format=default_format, encoding='utf-8')
logger.add(log_error_path, rotation="00:00", diagnose=False, level="ERROR", format=default_format, encoding='utf-8')

# You can pass some keyword args config to init function
nonebot.init()
driver = nonebot.get_driver()
driver.register_adapter("cqhttp", CQHTTPBot)
app = nonebot.get_asgi()

nonebot.load_plugins("omega_miya/plugins")

# Modify some config / config depends on loaded configs
# config = nonebot.get_driver().config
# do something...
# nonebot.load_plugin("nonebot_plugin_test")


if __name__ == "__main__":
    nonebot.run(app="bot:app")
