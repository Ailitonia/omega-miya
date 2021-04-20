from pydantic import BaseSettings


class Config(BaseSettings):

    # plugin custom config
    """
    B站动态检查模式, 是否启用检查池模式
    单位时间内检查数量相同, 但总体检查时间间隔会根据订阅量延长, 对于订阅量较大的情况可以有效避免被B站风控
    """
    enable_dynamic_check_pool_mode: bool = True

    class Config:
        extra = "ignore"
