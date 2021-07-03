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
    # 每次查询的图片数量限制
    image_num_limit: int = 3
    # 启用使用群组转发自定义消息节点的模式发送信息, 仅在群组消息中生效
    # 发送速度受限于网络上传带宽, 有可能导致超时或发送失败, 请酌情启用
    enable_node_custom: bool = False

    # 实验性功能, 可能引发协议端奇怪的问题(指base64图片+闪照的组合)
    # 以下选项产生的效果均在权限验证之后，并直接影响最终发送的图片
    # 启用使用闪照模式发送萌图, 仅影响"/来点萌图"命令
    enable_moe_flash: bool = False
    # 启用使用闪照模式发送涩图, 仅影响"/来点涩图"命令
    enable_setu_flash: bool = True
    # 启用使用高斯模糊提前处理待发送的涩图, 仅影响"/来点涩图"命令, 可与enable_setu_gaussian_noise一同使用, 可能会导致处理和发送图片时间提升
    enable_setu_gaussian_blur: bool = False
    # 启用使用高斯噪声提前处理待发送的涩图, 仅影响"/来点涩图"命令, 可与enable_setu_gaussian_blur一同使用, 可能会导致处理发送图片时间提升
    enable_setu_gaussian_noise: bool = True

    # 启用发送图片后自动撤回, 默认撤回时间10秒
    # !如果启用了转发消息节点模式(enable_node_custom=True)则以下选项不会生效!
    auto_recall_time: int = 45
    enable_moe_auto_recall: bool = False
    enable_setu_auto_recall: bool = True

    class Config:
        extra = "ignore"
