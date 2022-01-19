"""
@Author         : Ailitonia
@Date           : 2021/06/01 22:06
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : Pixiv 用户作品订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import pathlib
from nonebot import on_command, logger
from nonebot.plugin.export import export
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.cqhttp.message import MessageSegment
from omega_miya.database import DBBot, DBBotGroup, DBFriend, DBSubscription, Result
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state
from omega_miya.utils.pixiv_utils import PixivUser
from .monitor import scheduler, init_new_add_sub
from .utils import generate_user_searching_img


# Custom plugin usage text
__plugin_custom_name__ = 'Pixiv画师订阅'
__plugin_usage__ = r'''【Pixiv画师订阅】
随时更新Pixiv画师作品
仅限群聊使用

**Permission**
Command & Lv.50
or AuthNode

**AuthNode**
basic

**Usage**
**GroupAdmin and SuperUser Only**
/Pixiv画师 搜索 [NICKNAME]
/Pixiv画师 订阅 [UID]
/Pixiv画师 取消订阅 [UID]
/Pixiv画师 清空订阅
/Pixiv画师 订阅列表'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
pixiv_user_artwork = on_command(
    'Pixiv画师',
    aliases={'pixiv画师', 'p站画师', 'P站画师'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='pixiv_user_artwork',
        command=True,
        level=50),
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,  # 画师搜索功能主要是给订阅时不知道用户 uid 的时候查找用的, 所以不单独分配 matcher 和权限
    priority=20,
    block=True)


# 修改默认参数处理
@pixiv_user_artwork.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await pixiv_user_artwork.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await pixiv_user_artwork.finish('操作已取消')


@pixiv_user_artwork.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split(maxsplit=1)
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    elif args and len(args) == 2:
        state['sub_command'] = args[0]
        state['uid'] = args[1]
    else:
        await pixiv_user_artwork.finish('参数错误QAQ')


@pixiv_user_artwork.got('sub_command', prompt='执行操作?\n【搜索/订阅/取消订阅/清空订阅/订阅列表】')
async def handle_sub_command_args(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        msg = '本群已订阅以下Pixiv用户:\n'
    else:
        group_id = 'Private event'
        msg = '你已订阅以下Pixiv用户:\n'

    if state['sub_command'] not in ['搜索', '订阅', '取消订阅', '清空订阅', '订阅列表']:
        await pixiv_user_artwork.finish('没有这个命令哦, 请在【搜索/订阅/取消订阅/清空订阅/订阅列表】中选择并重新发送')
    if state['sub_command'] == '订阅列表':
        _res = await sub_list(bot=bot, event=event, state=state)
        if not _res.success():
            logger.error(f"查询Pixiv订阅失败, {group_id} / {event.user_id}, error: {_res.info}")
            await pixiv_user_artwork.finish('查询Pixiv订阅失败QAQ, 请稍后再试吧')
        if not _res.result:
            msg = '当前没有任何Pixiv订阅'
        else:
            for sub_id, up_name in _res.result:
                msg += f'\n【{sub_id}/{up_name}】'
        await pixiv_user_artwork.finish(msg)
    elif state['sub_command'] == '清空订阅':
        state['uid'] = None


@pixiv_user_artwork.got('uid', prompt='请输入Pixiv用户昵称或UID:')
async def handle_uid(bot: Bot, event: MessageEvent, state: T_State):
    sub_command = state['sub_command']
    # 针对清空Pixiv订阅操作, 跳过获取Pixiv用户信息
    if state['sub_command'] == '清空订阅':
        await pixiv_user_artwork.pause('【警告!】\n即将清空本所有订阅!\n请发送任意消息以继续操作:')

    # 处理搜索或用户输入非uid
    uid = state['uid']
    if not re.match(r'^\d+$', uid) or sub_command == '搜索':
        await pixiv_user_artwork.send(f'正在搜索pixiv用户: {uid}, 请稍后')
        search_result = await generate_user_searching_img(nick=uid)
        if search_result.error:
            logger.error(
                f'PixivUserSearching | Generating user searching result image failed, error: {search_result.error}')
            await pixiv_user_artwork.finish(f'获取搜索结果失败了QAQ, 请稍后重试或联系管理员')
        else:
            file_url = pathlib.Path(search_result.result).as_uri()
            logger.info(f'PixivUserSearching | User {event.user_id} success searching pixiv user {uid}')
            await pixiv_user_artwork.finish(MessageSegment.image(file_url))

    # Pixiv用户信息获取部分
    _res = await PixivUser(uid=int(uid)).get_info()
    if not _res.success():
        logger.error(f'获取用户信息失败, uid: {uid}, error: {_res.info}')
        await pixiv_user_artwork.finish('获取用户信息失败了QAQ, 请稍后再试~')
    up_name = _res.result.get('name')
    state['up_name'] = up_name
    msg = f'即将{sub_command}【{up_name}】的作品!'
    await pixiv_user_artwork.send(msg)


@pixiv_user_artwork.got('check', prompt='确认吗?\n\n【是/否】')
async def handle_check(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    else:
        group_id = 'Private event'

    check_msg = state['check']
    uid = state['uid']
    if check_msg != '是':
        await pixiv_user_artwork.finish('操作已取消')
    sub_command = state['sub_command']
    if sub_command == '订阅':
        _res = await sub_add(bot=bot, event=event, state=state)
    elif sub_command == '取消订阅':
        _res = await sub_del(bot=bot, event=event, state=state)
    elif sub_command == '清空订阅':
        _res = await sub_clear(bot=bot, event=event, state=state)
    else:
        _res = Result.IntResult(error=True, info='Unknown error, except sub_command', result=-1)
    if _res.success():
        logger.success(f"{sub_command}Pixiv用户作品成功, {group_id} / {event.user_id}, uid: {uid}")
        await pixiv_user_artwork.finish(f'{sub_command}成功!')
    else:
        logger.error(f"{sub_command}Pixiv用户作品失败, {group_id} / {event.user_id}, uid: {uid},"
                     f"info: {_res.info}")
        await pixiv_user_artwork.finish(f'{sub_command}失败了QAQ, 可能并未订阅该用户, 或请稍后再试~')


async def sub_list(bot: Bot, event: MessageEvent, state: T_State) -> Result.TupleListResult:
    self_bot = DBBot(self_qq=int(bot.self_id))
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBBotGroup(group_id=group_id, self_bot=self_bot)
        result = await group.subscription_list_by_type(sub_type=9)
        return result
    elif isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        friend = DBFriend(user_id=user_id, self_bot=self_bot)
        result = await friend.subscription_list_by_type(sub_type=9)
        return result
    else:
        return Result.TupleListResult(error=True, info='Illegal event', result=[])


async def sub_add(bot: Bot, event: MessageEvent, state: T_State) -> Result.IntResult:
    self_bot = DBBot(self_qq=int(bot.self_id))
    uid = state['uid']
    sub = DBSubscription(sub_type=9, sub_id=uid)
    need_init = not (await sub.exist())
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBBotGroup(group_id=group_id, self_bot=self_bot)
        _res = await sub.add(up_name=state.get('up_name'), live_info='Pixiv用户作品订阅')
        if not _res.success():
            return _res
        # 初次订阅时立即刷新, 避免订阅后发送旧作品的问题
        if need_init:
            await bot.send(event=event, message='初次订阅, 正在初始化作品信息, 可能需要1~2分钟, 请稍后...')
            await init_new_add_sub(user_id=uid)
        _res = await group.subscription_add(sub=sub, group_sub_info='Pixiv用户作品订阅')
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    elif isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        friend = DBFriend(user_id=user_id, self_bot=self_bot)
        _res = await sub.add(up_name=state.get('up_name'), live_info='Pixiv用户作品订阅')
        if not _res.success():
            return _res
        # 初次订阅时立即刷新, 避免订阅后发送旧作品的问题
        if need_init:
            await bot.send(event=event, message='初次订阅, 正在初始化作品信息, 可能需要1~2分钟, 请稍后...')
            await init_new_add_sub(user_id=uid)
        _res = await friend.subscription_add(sub=sub, user_sub_info='Pixiv用户作品订阅')
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    else:
        return Result.IntResult(error=True, info='Illegal event', result=-1)


async def sub_del(bot: Bot, event: MessageEvent, state: T_State) -> Result.IntResult:
    self_bot = DBBot(self_qq=int(bot.self_id))
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBBotGroup(group_id=group_id, self_bot=self_bot)
        uid = state['uid']
        _res = await group.subscription_del(sub=DBSubscription(sub_type=9, sub_id=uid))
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    elif isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        friend = DBFriend(user_id=user_id, self_bot=self_bot)
        uid = state['uid']
        _res = await friend.subscription_del(sub=DBSubscription(sub_type=9, sub_id=uid))
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    else:
        return Result.IntResult(error=True, info='Illegal event', result=-1)


async def sub_clear(bot: Bot, event: MessageEvent, state: T_State) -> Result.IntResult:
    self_bot = DBBot(self_qq=int(bot.self_id))
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBBotGroup(group_id=group_id, self_bot=self_bot)
        _res = await group.subscription_clear_by_type(sub_type=9)
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    elif isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        friend = DBFriend(user_id=user_id, self_bot=self_bot)
        _res = await friend.subscription_clear_by_type(sub_type=9)
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    else:
        return Result.IntResult(error=True, info='Illegal event', result=-1)
