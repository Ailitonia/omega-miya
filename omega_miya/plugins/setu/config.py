"""
@Author         : Ailitonia
@Date           : 2021/06/03 22:05
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseSettings


class Config(BaseSettings):
    # plugin custom config
    # 实验性功能, 可能引发协议端奇怪的问题(指base64图片+闪照的组合)
    # 以下选项产生的效果均在权限验证之后，并直接影响最终发送的图片
    # 启用使用闪照模式发送萌图, 仅影响"/来点萌图"命令
    enable_moe_flash: bool = False
    # 启用使用闪照模式发送涩图, 仅影响"/来点涩图"命令
    enable_setu_flash: bool = False
    # 启用使用高斯模糊提前处理待发送的涩图, 仅影响"/来点涩图"命令
    enable_setu_gaussian_blur: bool = False

    class Config:
        extra = "ignore"
