"""
要求go-cqhttp v0.9.40以上
"""
import os
from nonebot import on_command, on_notice, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.cqhttp.message import MessageSegment, Message
from nonebot.adapters.cqhttp.event import GroupMessageEvent, GroupUploadNoticeEvent
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state, OmegaRules
from omega_miya.database import DBBot, DBBotGroup, DBAuth, Result
from .utils import ZhouChecker, download_file


# Custom plugin usage text
__plugin_raw_name__ = __name__.split('.')[-1]
__plugin_custom_name__ = '自动审轴姬'
__plugin_usage__ = r'''【自动审轴姬】
检测群内上传文件并自动锤轴
仅限群聊使用

**Permission**
Group only with
AuthNode

**AuthNode**
basic

**Usage**
**GroupAdmin and SuperUser Only**
/ZhouShenHime <ON|OFF>'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)

# 注册事件响应器
zhoushen_hime_admin = on_command(
    'ZhouShenHime',
    aliases={'zhoushenhime', '审轴姬', '审轴机'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='zhoushen_hime',
        command=True,
        level=10),
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True)


# 修改默认参数处理
@zhoushen_hime_admin.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await zhoushen_hime_admin.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await zhoushen_hime_admin.finish('操作已取消')


@zhoushen_hime_admin.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    else:
        await zhoushen_hime_admin.finish('参数错误QAQ')


@zhoushen_hime_admin.got('sub_command', prompt='执行操作?\n【ON/OFF】')
async def handle_sub_command_args(bot: Bot, event: GroupMessageEvent, state: T_State):
    sub_command = state['sub_command']
    if sub_command not in ['on', 'off']:
        await zhoushen_hime_admin.reject('没有这个选项哦, 请在【ON/OFF】中选择并重新发送, 取消命令请发送【取消】:')

    if sub_command == 'on':
        _res = await zhoushen_hime_on(bot=bot, event=event, state=state)
    elif sub_command == 'off':
        _res = await zhoushen_hime_off(bot=bot, event=event, state=state)
    else:
        _res = Result.IntResult(error=True, info='Unknown error, except sub_command', result=-1)

    if _res.success():
        logger.info(f"设置自动审轴姬状态为 {sub_command} 成功, group_id: {event.group_id}, {_res.info}")
        await zhoushen_hime_admin.finish(f'已设置自动审轴姬状态为 {sub_command}!')
    else:
        logger.error(f"设置自动审轴姬状态为 {sub_command} 失败, group_id: {event.group_id}, {_res.info}")
        await zhoushen_hime_admin.finish(f'设置自动审轴姬状态失败了QAQ, 请稍后再试~')


async def zhoushen_hime_on(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    group_exist = await group.exist()
    if not group_exist:
        return Result.IntResult(error=False, info='Group not exist', result=-1)

    auth_node = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=f'{__plugin_raw_name__}.basic')
    result = await auth_node.set(allow_tag=1, deny_tag=0, auth_info='启用自动审轴姬')
    return result


async def zhoushen_hime_off(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    group_exist = await group.exist()
    if not group_exist:
        return Result.IntResult(error=False, info='Group not exist', result=-1)

    auth_node = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=f'{__plugin_raw_name__}.basic')
    result = await auth_node.set(allow_tag=0, deny_tag=1, auth_info='禁用自动审轴姬')
    return result


zhoushen_hime = on_notice(rule=OmegaRules.has_auth_node(__plugin_raw_name__, 'basic'), priority=100, block=False)


@zhoushen_hime.handle()
async def hime_handle(bot: Bot, event: GroupUploadNoticeEvent, state: T_State):
    file_name = event.file.name
    file_url = getattr(event.file, 'url', None)
    user_id = event.user_id

    # 不响应自己上传的文件
    if int(event.user_id) == int(bot.self_id):
        await zhoushen_hime.finish()

    if file_name.split('.')[-1] not in ['ass', 'ASS']:
        await zhoushen_hime.finish()

    # 只处理文件名中含"未校""待校""需校"的文件
    if not any(key in file_name for key in ['未校', '待校', '需校']):
        await zhoushen_hime.finish()

    dl_res = await download_file(url=file_url, file_name=file_name)
    if not dl_res.success():
        logger.error(f'下载文件失败: {dl_res.info}')
        await zhoushen_hime.finish()

    at_msg = MessageSegment.at(user_id=user_id)
    msg = f'{at_msg}你刚刚上传了一份轴呢, 让我来帮你看看吧!'
    await zhoushen_hime.send(Message(msg))

    file_path = os.path.abspath(dl_res.result)
    checker = ZhouChecker(file_path=file_path, flash_mode=True)

    try:
        init_res = checker.init_file(auto_style=True)
        if not init_res.success():
            logger.error(f'初始化时轴文件失败: {init_res.info}')
            await zhoushen_hime.finish('审轴姬出错了QAQ')

        handle_res = checker.handle()
        if not handle_res.success():
            logger.error(f'处理时轴文件失败: {handle_res.info}')
            await zhoushen_hime.finish('审轴姬出错了QAQ')
    except Exception as e:
        logger.error(f'执行ZhouChecker时发生了意外的错误: {repr(e)}')
        await zhoushen_hime.finish('审轴姬出错了QAQ')
        return

    output_txt_path = os.path.abspath(handle_res.result.get('output_txt_path'))
    output_txt_filename = os.path.basename(output_txt_path)

    output_ass_path = os.path.abspath(handle_res.result.get('output_ass_path'))
    output_ass_filename = os.path.basename(output_ass_path)

    character_count = handle_res.result.get('character_count')
    overlap_count = handle_res.result.get('overlap_count')
    flash_count = handle_res.result.get('flash_count')

    # 没有检查到错误的话就直接结束
    if character_count + flash_count + overlap_count == 0:
        msg = f'看完了! 没有发现符号错误、疑问文本、叠轴和闪轴, 真棒~'
        await zhoushen_hime.finish(msg)

    try:
        group_file_info = await bot.call_api(api='get_group_root_files', group_id=event.group_id)
        group_folders = group_file_info.get('folders')

        folder_id = None
        if group_folders:
            for folder in group_folders:
                if folder.get('folder_name') == '锤轴记录':
                    folder_id = folder.get('folder_id')
                    break

        if folder_id:
            await bot.call_api(api='upload_group_file', group_id=event.group_id, folder=folder_id,
                               file=output_txt_path, name=output_txt_filename)
            await bot.call_api(api='upload_group_file', group_id=event.group_id, folder=folder_id,
                               file=output_ass_path, name=output_ass_filename)
        else:
            await bot.call_api(api='upload_group_file', group_id=event.group_id,
                               file=output_txt_path, name=output_txt_filename)
            await bot.call_api(api='upload_group_file', group_id=event.group_id,
                               file=output_ass_path, name=output_ass_filename)
    except Exception as e:
        logger.error(f'上传结果时时发生了意外的错误: {repr(e)}')
        await zhoushen_hime.finish('审轴姬出错了QAQ')
        return

    msg = f'看完了! 以下是结果:\n\n符号及疑问文本共{character_count}处\n' \
          f'叠轴共{overlap_count}处\n闪轴共{flash_count}处\n\n锤轴结果已上传, 请参考修改哟~'
    await zhoushen_hime.finish(msg)
