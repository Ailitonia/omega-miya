<div align="center">

# Omega Miya

基于 [Nonebot2](https://github.com/nonebot/nonebot2) 的 qq 机器人

![GitHub](https://img.shields.io/github/license/Ailitonia/omega-miya)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/Ailitonia/omega-miya?include_prereleases)
![GitHub (Pre-)Release Date](https://img.shields.io/github/release-date-pre/Ailitonia/omega-miya)

</div>

## 当前适配nonebot2版本

[Nonebot2 Pre Release v2.0.0a16](https://github.com/nonebot/nonebot2/releases/tag/v2.0.0a16)

## 功能 & 特点

- 基于异步 SQLAlchemy / MySQL 的数据存储
- 插件管理系统
- 权限控制及管理系统
    - 针对不同群组可选启用通知权限、命令权限、权限等级控制
    - 针对不同好友可选启用 Bot 功能
    - 针对不同群组、好友独立配置插件权限节点
- 支持多协议端连接, 各协议端权限及订阅配置相互独立
- 命令冷却系统
- 速率控制系统
- HTTP 代理功能
- 自动处理加好友和被邀请进群
- 插件帮助功能 (支持群聊 / 私聊)
- Bot对群组公告功能 (仅支持对群组)
- 定时消息功能 (仅支持对群组)
- 反闪照 (仅支持群聊)
- 反撤回 (仅支持群聊)
- B站动态订阅 (建议配置B站cookies) (支持群聊 / 私聊)
- B站直播间监控 (建议配置B站cookies) (支持群聊 / 私聊)
- 签到 (仅支持群聊)
- 求签 (仅支持群聊)
- 抽卡 (仅支持群聊)
- 塔罗牌 (仅支持群聊)
- 能不能好好说话 (lab.magiconch.com API) (支持群聊 / 私聊)
- Pixiv助手 (需要 HTTP 代理, 除非部署在外网) (需要 go-cqhttp v0.9.40 及以上版本) (仅支持群聊)
- Pixiv订阅 (需要 HTTP 代理, 除非部署在外网) (仅支持群聊)
- Pixivision订阅 (需要 HTTP 代理, 除非部署在外网) (仅支持群聊)
- 复读姬 (仅支持群聊)
- roll点抽奖 (仅支持群聊)
- ShindanMaker占卜 (shindanmaker.com / 建议使用 HTTP 代理) (仅支持群聊)
- 搜番剧 (trace.moe API / 建议使用 HTTP 代理) (支持群聊 / 私聊)
- 搜二次元图 (Saucenao API, iqbb 和 ascii2d / 建议使用 HTTP 代理) (支持群聊 / 私聊)
- 来点萌图 / 来点涩图 (需要 HTTP 代理, 除非部署在外网 / 图片数据库需要自己导入) (支持群聊 / 私聊)
- 表情包制作器 (支持群聊 / 私聊)
- 猫按钮 (测试) (仅支持群聊)
- 自动锤轴姬 (需要 go-cqhttp v0.9.40 及以上版本) (仅支持群聊)
- 邮箱插件 (仅支持IMAP收件) (仅支持群聊)
- 腾讯云组件 (测试) (仅支持群聊)

## 如何使用

请参考本仓库 [Wiki](https://github.com/Ailitonia/omega-miya/wiki)

## 关于图片数据

如果你不想自己收集图片数据, 可以将
[这个图片数据库](https://github.com/Ailitonia/omega-miya/raw/master/archive_data/db_pixiv.7z)
导入, 基本都是按我自己口味收集的图片

Update 2021.8.10: 最新发布图片数据库共 9w7 条图片数据 (包含已失效或画师已删除作品)

解压后直接把 `omega_pixiv_illusts.sql` 导入对应的 pixiv_illusts 表就好了

MD5: `7AC9A77545E37F1B99F8D1948D0A9A78`

SHA1: `1F129A18905D1590379AC761E2EAC69DAC2D42DA`

数据集来源是我的
[这个频道](https://t.me/amoeloli)
, 虽然已经断更很久了...

## 一张图看懂如何获取B站cookies

**注意！该cookies等同于您账号控制权，请不要将这两个值泄露给他人！**

<img src="https://raw.githubusercontent.com/Ailitonia/omega-miya/main/docs/img/how_to_get_bilibili_cookies.png" width="75%">

**注意！该cookies等同于您账号控制权，请不要将这两个值泄露给他人！**

## 特别感谢

- [Nonebot2](https://github.com/nonebot/nonebot2)
- [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)
- [OneBot](https://github.com/howmanybots/onebot)
- [ZhouShen_Hime](https://github.com/HakuRemu/ZhouShen_Hime)


## 说点题外话

Omega_miya 的设计思路显然与 Nonebot 插件间应该尽可能解耦的设计思路相悖。

当然这和 Omega_miya 最初的用途有关，她本来是用来督促字幕组~~摸鱼~~干活的，并且一开始设计的时候继承了初代~~真正零号 Omega_miya~~ 的数据库以及设计思路，所以 Omega_miya 的插件体系是强耦合的，后来随着功能迭代，也就改不过来了。

因此，对于 Omega_miya 这个项目，我想她可能并不是可以直接拿来就用的，因为她的设计本身就有局限性，这里大概是可以提供某些插件功能上的思路，希望能给其他的开发者带来一些帮助。

欢迎来提各种issue~
