<p align="center">
  <a href="https://nonebot.dev/"><img src="https://nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# NoneBot Plugin APScheduler

_✨ NoneBot APScheduler 定时任务插件 ✨_

</div>

<p align="center">
  <a href="https://raw.githubusercontent.com/nonebot/plugin-apscheduler/master/LICENSE">
    <img src="https://img.shields.io/github/license/nonebot/plugin-apscheduler.svg" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nonebot-plugin-apscheduler">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-apscheduler.svg" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="python">
</p>

## 使用方式

加载插件后使用 `require` 获取 `scheduler` 对象（请注意插件加载顺序）

```python
from nonebot import require

require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler

@scheduler.scheduled_job("cron", hour="*/2", id="xxx", args=[1], kwargs={"arg2": 2})
async def run_every_2_hour(arg1, arg2):
    pass

scheduler.add_job(run_every_day_from_program_start, "interval", days=1, id="xxx")
```

## 配置项

### apscheduler_autostart

是否自动启动 `scheduler`

### apscheduler_log_level

`int` 类型日志等级

- `WARNING` = `30` (默认)
- `INFO` = `20`
- `DEBUG` = `10` (只有在开启 nonebot 的 debug 模式才会显示 debug 日志)

### apscheduler_config

`apscheduler` 的相关配置。参考 [配置 scheduler](https://apscheduler.readthedocs.io/en/latest/userguide.html#scheduler-config), [配置参数](https://apscheduler.readthedocs.io/en/latest/modules/schedulers/base.html#apscheduler.schedulers.base.BaseScheduler)

配置需要包含 `prefix: apscheduler.`

默认配置：

```json
{ "apscheduler.timezone": "Asia/Shanghai" }
```
