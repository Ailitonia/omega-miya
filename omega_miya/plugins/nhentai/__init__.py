"""
危险功能
谨慎使用
请喝茶警告
要求go-cqhttp v0.9.40以上
需要 Miya API
"""
import re
import os
from nonebot import on_command, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import init_export
from omega_miya.utils.Omega_plugin_utils import has_command_permission, permission_level
from .utils import nh_search, nh_download
from .allow_list import ALLOW_GROUP


# Custom plugin usage text
__plugin_name__ = 'nh'
__plugin_usage__ = r'''【nh】
神秘的插件

**Permission**
Command & Lv.50

**Usage**
/nh search [tag]
/nh download [id]'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)


# 注册事件响应器
nhentai = on_command('nh', rule=has_command_permission() & permission_level(level=50), aliases={'NH'},
                     permission=GROUP, priority=20, block=True)


# 修改默认参数处理
@nhentai.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await nhentai.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await nhentai.finish('操作已取消')


@nhentai.handle()
async def handle_group_check(bot: Bot, event: GroupMessageEvent, state: T_State):
    if event.group_id not in ALLOW_GROUP:
        await nhentai.finish('权限不足')


@nhentai.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if args and len(args) == 1:
        state['sub_command'] = args[0]
    elif args and len(args) == 2:
        state['sub_command'] = args[0]
        state['sub_arg'] = args[1]
    else:
        await nhentai.finish('参数错误QAQ')


@nhentai.got('sub_command', prompt='执行操作?\n【search / download】')
@nhentai.got('sub_arg', prompt='tag 或 id?')
async def handle_nhentai(bot: Bot, event: GroupMessageEvent, state: T_State):
    sub_command = state["sub_command"]
    sub_arg = state["sub_arg"]
    if sub_command not in ['search', 'download']:
        await nhentai.finish('没有这个命令哦QAQ')

    if sub_command == 'search':
        _res = await nh_search(tag=sub_arg)
        if _res.success():
            nh_list = list(_res.result.get('body'))
            msg = ''
            for item in nh_list:
                _id = item.get('id')
                title = item.get('title')
                msg += f'\nID: {_id} / {title}\n'
            logger.info(f"Group: {event.group_id}, User: {event.user_id} 搜索成功")
            await nhentai.finish(f"已为你找到了如下结果: \n{msg}\n{'='*8}\n可通过id下载")
        else:
            logger.warning(f"Group: {event.group_id}, User: {event.user_id} 搜索失败, error info: {_res.info}")
            await nhentai.finish('搜索失败QAQ, 请稍后再试')
    elif sub_command == 'download':
        if not re.match(r'^\d+$', sub_arg):
            logger.warning(f"Group: {event.group_id}, User: {event.user_id} 搜索失败, id错误")
            await nhentai.finish('失败了QAQ, id应为纯数字')
        else:
            await nhentai.send('正在下载资源, 请稍后~')
            _res = await nh_download(_id=sub_arg)
            if not _res.success():
                logger.warning(f"Group: {event.group_id}, User: {event.user_id} 下载失败, error info: {_res.info}")
                await nhentai.finish('下载失败QAQ, 请稍后再试')
            else:
                password = _res.result.get('password')
                file = _res.result.get('file')
                file_abs = os.path.abspath(file)
                await bot.call_api(api='upload_group_file',
                                   group_id=event.group_id, file=file_abs, name=f'{sub_arg}.7z')
                logger.info(f"Group: {event.group_id}, User: {event.user_id} 下载成功")
                await nhentai.finish(f'成功, 解压密码: {password}')
    else:
        pass
