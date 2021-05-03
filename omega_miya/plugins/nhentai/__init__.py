"""
请谨慎使用本插件
要求go-cqhttp v0.9.40以上
"""
import re
import os
from nonebot import on_command, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state
from omega_miya.utils.nhentai_utils import NhentaiGallery


# Custom plugin usage text
__plugin_name__ = 'nh'
__plugin_usage__ = r'''【nh】
神秘的插件

**Permission**
Command
with AuthNode

**AuthNode**
basic

**Usage**
/nh search [tag]
/nh download [id]'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
nhentai = on_command(
    'nh',
    aliases={'NH'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='nhentai',
        command=True,
        auth_node='basic'),
    permission=GROUP,
    priority=20,
    block=True)


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
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    elif args and len(args) == 2:
        state['sub_command'] = args[0]
        state['sub_arg'] = args[1]
    else:
        await nhentai.finish('参数错误QAQ')


@nhentai.got('sub_command', prompt='执行操作?\n【search / download】')
async def handle_sub_command(bot: Bot, event: GroupMessageEvent, state: T_State):
    sub_command = state["sub_command"]
    if sub_command not in ['search', 'download']:
        await nhentai.finish('没有这个命令哦QAQ')


@nhentai.got('sub_arg', prompt='tag 或 id?')
async def handle_sub_arg(bot: Bot, event: GroupMessageEvent, state: T_State):
    pass


@nhentai.handle()
async def handle_nhentai(bot: Bot, event: GroupMessageEvent, state: T_State):
    sub_command = state["sub_command"]
    sub_arg = state["sub_arg"]

    if sub_command == 'search':
        search_result = await NhentaiGallery.search_gallery_by_keyword(keyword=sub_arg)
        if search_result.success():
            nh_list = list(search_result.result)
            msg = ''
            for item in nh_list:
                _id = item.get('id')
                title = item.get('title')
                msg += f'\nID: {_id} / {title}\n'
            logger.info(f"Group: {event.group_id}, User: {event.user_id} 搜索成功")
            await nhentai.finish(f"已为你找到了如下结果: \n{msg}\n{'='*8}\n可通过id下载")
        else:
            logger.warning(f"Group: {event.group_id}, User: {event.user_id} 搜索失败, error info: {search_result.info}")
            await nhentai.finish('搜索失败QAQ, 请稍后再试')
    elif sub_command == 'download':
        if not re.match(r'^\d+$', sub_arg):
            logger.warning(f"Group: {event.group_id}, User: {event.user_id} 搜索失败, id错误")
            await nhentai.finish('错误QAQ, id应为纯数字')
        else:
            await nhentai.send('正在下载资源, 请稍后~')
            download_result = await NhentaiGallery(gallery_id=sub_arg).fetch_gallery()
            if download_result.error:
                logger.error(f"Group: {event.group_id}, User: {event.user_id} 下载失败, {download_result.info}")
                await nhentai.finish('下载失败QAQ, 请稍后再试')
            else:
                password = download_result.result.get('password')
                file_name = download_result.result.get('file_name')
                file_path = os.path.abspath(download_result.result.get('file_path'))
                await nhentai.send(f'下载完成, 密码: {password}, 正在上传文件, 可能需要一段时间...')
                try:
                    await bot.call_api(api='upload_group_file',
                                       group_id=event.group_id, file=file_path, name=file_name)
                    logger.info(f"Group: {event.group_id}, User: {event.user_id} 下载成功")
                except Exception as e:
                    logger.error(f'Group: {event.group_id}, User: {event.user_id} 上传文件失败, {repr(e)}')
                    await nhentai.finish(f'获取上传结果超时或上传失败QAQ, 上传可能仍在进行中, 请等待2~5分钟后再重试')
    else:
        await nhentai.finish('没有这个命令哦QAQ')
