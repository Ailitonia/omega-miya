import nonebot
from omega_miya.utils.Omega_Base import DBStatus

global_config = nonebot.get_driver().config
ENABLE_PROXY = global_config.enable_proxy


def check_proxy_available() -> bool:
    db_res = DBStatus(name='PROXY_AVAILABLE').get_status()
    if db_res.result == 1 and ENABLE_PROXY:
        return True
    else:
        return False
