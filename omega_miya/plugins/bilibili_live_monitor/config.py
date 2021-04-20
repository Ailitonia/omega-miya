from pydantic import BaseSettings


class Config(BaseSettings):

    # plugin custom config
    """
    b站直播间插件已使用新api获取直播间状态, 请求数大幅降低
    请始终将enable_new_live_api保持为True!
    非调试请勿修改本配置!!!
    """
    enable_new_live_api: bool = True
    enable_live_check_pool_mode: bool = False

    class Config:
        extra = "ignore"
