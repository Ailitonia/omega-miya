"""
要求go-cqhttp v0.9.40以上
"""
import os
from nonebot import on_notice, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import MessageSegment, Message
from nonebot.adapters.cqhttp.event import GroupUploadNoticeEvent
from omega_miya.utils.Omega_plugin_utils import init_export, has_auth_node
from .utils import ZhouChecker, download_file


# Custom plugin usage text
__plugin_name__ = '自动审轴姬'
__plugin_usage__ = r'''【自动审轴姬】
检测群内上传文件并自动锤轴

**AuthNode**
basic

**Usage**
配置AuthNode启用'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


zhouShenHime = on_notice(rule=has_auth_node(__name__, 'basic'), priority=100, block=False)


@zhouShenHime.handle()
async def hime_handle(bot: Bot, event: GroupUploadNoticeEvent, state: T_State):
    file_name = event.file.name
    file_url = event.file.dict().get('url')
    user_id = event.user_id

    # 不响应自己上传的文件
    if int(event.user_id) == int(bot.self_id):
        await zhouShenHime.finish()

    if file_name.split('.')[-1] not in ['ass', 'ASS']:
        await zhouShenHime.finish()

    plugin_path = os.path.dirname(__file__)
    download_dir = os.path.join(plugin_path, 'file_downloaded')
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    download_file_path = os.path.join(download_dir, file_name)
    dl_res = await download_file(url=file_url, file_path=download_file_path)
    if not dl_res.success():
        logger.error(f'下载文件失败: {dl_res.info}')
        await zhouShenHime.finish()

    at_msg = MessageSegment.at(user_id=user_id)
    msg = f'{at_msg}你刚刚上传了一份轴呢, 让我来帮你看看吧!'
    await zhouShenHime.send(Message(msg))

    checker = ZhouChecker(file_path=download_file_path, flash_mode=True)

    try:
        init_res = checker.init_file(auto_style=True)
        if not init_res.success():
            logger.error(f'初始化时轴文件失败: {init_res.info}')
            await zhouShenHime.finish('出错了QAQ')

        handle_res = checker.handle()
        if not handle_res.success():
            logger.error(f'处理时轴文件失败: {handle_res.info}')
            await zhouShenHime.finish('出错了QAQ')
    except Exception as e:
        logger.error(f'执行ZhouChecker时发生了意外的错误: {repr(e)}')
        await zhouShenHime.finish('出错了QAQ')
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
        await zhouShenHime.finish(msg)

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
        await zhouShenHime.finish('出错了QAQ')
        return

    msg = f'看完了! 以下是结果:\n\n符号及疑问文本共{character_count}处\n' \
          f'叠轴共{overlap_count}处\n闪轴共{flash_count}处\n\n锤轴结果已上传, 请参考修改哟~'
    await zhouShenHime.finish(msg)
