"""
@Author         : Ailitonia
@Date           : 2026/10/3 12:37
@FileName       : input_data_from_v1
@Project        : omega-miya
@Description    : v1 核心数据导入工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

用法 (本工具无默认 main 入口, 函数名必须显式指定):
    python bot.py --tool-execute input_data_from_v1:core_main
    python bot.py --tool-execute input_data_from_v1:artwork_main

说明:
    - 需先将导出的数据文件放入 .tmp/v1_dump_data/ 目录:
      core_main 读取 dump_data_from_v1 导出的 8 个 JSONL 文件 (bot_self / subscription_source /
      entity / friendship / sign_in / auth_setting / subscription / system_setting),
      artwork_main 读取 Navicat 导出的 artwork_collection.json (pretty-printed JSON 数组)
    - core_main 按依赖顺序导入核心数据 (bot -> 订阅源/实体 -> 好感度/签到/授权/订阅 -> 系统设置),
      以自然键映射 v2 索引 ID; 超长字段自动截断至 v2 字段长度限制;
      v2 不支持的实体类型 (v1 遗留 qq_* / *_guild*) 整体跳过并告警
    - artwork_main 将 v1 图库数据导入 v2 图库: MySQL 后端使用多行语句批量导入 (分钟级完成),
      其他后端 (含 sqlite) 走 DAL 逐条导入 (并发 8, sqlite 降为 1), 均带单条重试与连续失败熔断;
      已存在作品的 classification/rating 与库内值取较大值
    - 两个入口均为幂等写入 (upsert), 中断后可直接重新执行续跑;
      目标 v2 数据库由 .env 中 DATABASE 相关环境变量决定
"""

from .artwork import artwork_main
from .core import core_main

artwork_main = artwork_main
core_main = core_main


__all__ = [
    'artwork_main',
    'core_main',
]
