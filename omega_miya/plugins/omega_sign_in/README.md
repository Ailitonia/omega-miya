# 签到插件

可以通过 `戳一戳` 或者 `\签到` 命令进行签到并生成签到图

## 关于求签相关功能的补充说明

求签事件及结果可以通过模板导入并与内置事件进行合并

### 启用方法

使用求签事件导入 API 进行操作: `/fortune/import-fortune-event`

若要启用导入功能, 请先在配置文件 `.env.*` 中加入 `SIGNIN_ENABLE_FORTUNE_IMPORT_API=true`

重启后在加载插件时日志中有如下提示即为启用成功

```angular2html
11-29 21:54:51 [INFO] omega_api | Service omega_miya.plugins.omega_sign_in.fortune running at: http://localhost:port/fortune/import-fortune-event
11-29 21:54:51 [SUCCESS] nonebot | Succeeded to import "omega_sign_in"
```

直接访问日志中该链接即可触发导入: `http://localhost:port/fortune/import-fortune-event`

### 导入模板

导入模板默认路径为 `项目路径\tmp\fortune\fortune_event_import.xlsx`

若不知道模板具体路径或者没有模板文件, 可直接访问上述 API 地址, 若返回:

```json
{"error":false,"body":{"events":[]},"message":"未找到导入文件, 已生成导入模板: C:\\ProjectsPath\\tmp\\fortune\\fortune_event_import.xlsx, 请在模板上直接修改或覆盖后重新导入","exception":null}
```

则已生成导入模板, 在该模板上直接修改或覆盖后即可重新访问 API 地址进行导入

若导入成功, 则会返回:

```json
{"error":false,"body":{"events":[]},"message":"求签事件导入并更新成功","exception":null}
```

注意 `message` 提示 "求签事件导入并更新成功" 即为成功, `body` 中会有具体的事件

### 重置与调试

手动删除 `项目路径\tmp\fortune\` 中 `event.json` 和 `fortune_event_import.xlsx` 两个文件并重启即可将求签事件恢复为初始值

调试时可在 API 请求中添加参数: `?reset=true` 即可暂时重置缓存中的事件
