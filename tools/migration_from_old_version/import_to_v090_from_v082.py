"""
@Author         : Ailitonia
@Date           : 2022/05/11 22:36
@FileName       : import_old_version_data.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import inspect
import os
import pathlib
from datetime import datetime
from functools import wraps
from typing import Literal

import aiofiles
import nonebot
import ujson as json
from pydantic import BaseModel, parse_obj_as

driver = nonebot.get_driver()
folder = pathlib.Path(os.path.abspath(os.path.dirname(__file__)))


def catching_exception(func):
    """一个用于包装 async function 捕获所有异常并作为返回值返回的装饰器

    :param func: 被装饰的异步函数
    """
    if not inspect.iscoroutinefunction(func):
        raise ValueError('The decorated function must be coroutine function')

    @wraps(func)
    async def _wrapper(*args, **kwargs):
        _module = inspect.getmodule(func)
        _module_name = _module.__name__ if _module is not None else 'Unknown'
        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            nonebot.logger.opt(colors=True).exception(
                f'<lc>Decorator RunAsyncCatchingException</lc> | <ly>{_module_name}.{func.__name__}</ly> '
                f'<r>raise Exception {e.__class__.__name__}</r> <c>></c> '
                f'There are something wrong(s) in function running')
            result = e
        return result

    return _wrapper


async def read_json(file_name: str):
    async with aiofiles.open(folder.joinpath(file_name), 'r', encoding='utf8') as af:
        content = json.loads(await af.read())
        return content


@catching_exception
async def import_sub_source():
    class SubSource(BaseModel):
        sub_type: Literal['bili_live', 'bili_dynamic', 'pixiv_user', 'pixivision']
        sub_id: str
        sub_user_name: str
        sub_info: str

    from omega_miya.database import InternalSubscriptionSource
    data = parse_obj_as(list[SubSource], await read_json('sub_source.json'))
    nonebot.logger.opt(colors=True).info('<W><lc>importing sub source</lc></W>')
    for sub_source in data:
        nonebot.logger.debug(f'importing sub source: {sub_source}')
        await InternalSubscriptionSource(sub_type=sub_source.sub_type, sub_id=sub_source.sub_id).add_upgrade(sub_user_name=sub_source.sub_user_name, sub_info=sub_source.sub_info)
    nonebot.logger.opt(colors=True).success('<W><lg>importing sub source completed</lg></W>')


@catching_exception
async def import_bot_data():
    from omega_miya.database import InternalOneBotV11Bot
    data = parse_obj_as(list[str], await read_json('bot_self.json'))
    nonebot.logger.opt(colors=True).info('<W><lc>importing bot data</lc></W>')
    for bot in data:
        nonebot.logger.debug(f'importing bot data: {bot}')
        await InternalOneBotV11Bot(bot_self_id=bot, bot_type='OneBot V11').add_upgrade(bot_status=0)
    nonebot.logger.opt(colors=True).success('<W><lg>importing bot data completed</lg></W>')


@catching_exception
async def import_user_data():
    class BotUser(BaseModel):
        qq: str
        nickname: str
        all_sign_in_days: list[int]
        status: str
        mood: float
        favorability: float
        energy: float
        currency: float
        response_threshold: float

    from omega_miya.database import InternalBotUser
    bot_data = parse_obj_as(list[str], await read_json('bot_self.json'))
    data = parse_obj_as(list[BotUser], await read_json('user_data.json'))
    nonebot.logger.opt(colors=True).info('<W><lc>importing user data</lc></W>')
    for user_data in data:
        nonebot.logger.debug(f'importing user data: {user_data}')
        for bot in bot_data:
            user = InternalBotUser(bot_id=bot, parent_id=bot, entity_id=user_data.qq)
            await user.add_only(entity_name=user_data.nickname, related_entity_name=user_data.nickname)
            await user.upgrade_or_reset_friendship(status=user_data.status, mood=user_data.mood, friend_ship=user_data.favorability, energy=user_data.energy, currency=user_data.currency, response_threshold=user_data.response_threshold)
            for day in user_data.all_sign_in_days:
                await user.sign_in(date_=datetime.fromordinal(day))
    nonebot.logger.opt(colors=True).success('<W><lg>importing user data completed</lg></W>')


@catching_exception
async def import_mail_box_data():
    class MailBox(BaseModel):
        address: str
        server_host: str
        protocol: str
        port: int
        password: str

    from omega_miya.database import EmailBox
    data = parse_obj_as(list[MailBox], await read_json('mail_box_data.json'))
    nonebot.logger.opt(colors=True).info('<W><lc>importing mail box data</lc></W>')
    for mail_box in data:
        nonebot.logger.debug(f'importing mail box data: {mail_box}')
        await EmailBox(address=mail_box.address).add_upgrade_unique_self(server_host=mail_box.server_host, password=mail_box.password, protocol=mail_box.protocol, port=mail_box.port)
    nonebot.logger.opt(colors=True).success('<W><lg>importing mail box data completed</lg></W>')


@catching_exception
async def import_bot_group_data():
    class BotGroup(BaseModel):
        class Sub(BaseModel):
            sub_type: Literal['bili_live', 'bili_dynamic', 'pixiv_user', 'pixivision']
            sub_id: str
            sub_info: str

        group_id: str
        bot_id: str
        group_name: str
        group_memo: str
        enable: int
        level: int
        subscription: list[Sub]
        mailbox: list[str]

    from omega_miya.database import InternalBotGroup
    data = parse_obj_as(list[BotGroup], await read_json('bot_group_data.json'))
    nonebot.logger.opt(colors=True).info('<W><lc>importing bot_group data</lc></W>')
    for bot_group in data:
        nonebot.logger.debug(f'importing bot_group data: {bot_group.group_id}, {bot_group.group_name}')
        group = InternalBotGroup(bot_id=bot_group.bot_id, parent_id=bot_group.bot_id, entity_id=bot_group.group_id)
        await group.add_only(entity_name=bot_group.group_name, related_entity_name=bot_group.group_name, entity_info=bot_group.group_memo)

        if bot_group.enable == 1:
            await group.enable_global_permission()
        else:
            await group.disable_global_permission()

        await group.set_permission_level(level=bot_group.level)

        for sub in bot_group.subscription:
            await group.add_subscription(sub_type=sub.sub_type, sub_id=sub.sub_id, sub_info=sub.sub_info)

        for mail_box in bot_group.mailbox:
            await group.bind_email_box(address=mail_box)

    nonebot.logger.opt(colors=True).success('<W><lg>importing bot_group data completed</lg></W>')


@catching_exception
async def import_bot_friend_data():
    class BotFriend(BaseModel):
        class Sub(BaseModel):
            sub_type: Literal['bili_live', 'bili_dynamic', 'pixiv_user', 'pixivision']
            sub_id: str
            sub_info: str

        qq: str
        bot_id: str
        nickname: str
        enable: int
        subscription: list[Sub]

    from omega_miya.database import InternalBotUser
    data = parse_obj_as(list[BotFriend], await read_json('bot_friend.json'))
    nonebot.logger.opt(colors=True).info('<W><lc>importing bot_friend data</lc></W>')
    for bot_friend in data:
        nonebot.logger.debug(f'importing bot_friend data: {bot_friend.qq}, {bot_friend.nickname}')
        user = InternalBotUser(bot_id=bot_friend.bot_id, parent_id=bot_friend.bot_id, entity_id=bot_friend.qq)
        await user.add_only(entity_name=bot_friend.nickname, related_entity_name=bot_friend.nickname)

        if bot_friend.enable == 1:
            await user.enable_global_permission()
            await user.set_permission_level(level=50)
        else:
            await user.disable_global_permission()
            await user.set_permission_level(level=0)

        for sub in bot_friend.subscription:
            await user.add_subscription(sub_type=sub.sub_type, sub_id=sub.sub_id, sub_info=sub.sub_info)

    nonebot.logger.opt(colors=True).success('<W><lg>importing bot_friend data completed</lg></W>')


@driver.on_startup
async def main():
    await import_sub_source()
    await import_bot_data()
    await import_mail_box_data()
    await import_bot_group_data()
    await import_bot_friend_data()
    await import_user_data()
    nonebot.logger.opt(colors=True).success('<W><lg>All import processing completed</lg></W>')
