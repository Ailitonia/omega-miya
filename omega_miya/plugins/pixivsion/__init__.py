"""
@Author         : Ailitonia
@Date           : 2022/04/30 18:11
@FileName       : pixivision.py
@Project        : nonebot2_miya
@Description    : Pixiv 助手
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.log import logger
from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11.message import MessageSegment, Message
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD
from omega_miya.web_resource.pixiv import Pixivision
from omega_miya.utils.process_utils import run_async_catching_exception

from .utils import get_pixivision_article_preview, add_pixivision_sub, delete_pixivision_sub
from .monitor import scheduler


__plugin_meta__ = PluginMetadata(
    name="Pixivision",
    description="【Pixivision助手插件】\n"
                "探索并查看Pixivision文章\n"
                "订阅最新的Pixivision特辑",
    usage="/pixivision [AID]\n\n"
          "仅限私聊或群聊中群管理员使用:\n"
          "/pixivision订阅\n"
          "/pixivision取消订阅",
    extra={"author": "Ailitonia"},
)


# 注册事件响应器
pixivision = on_command(
    'Pixivision',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='Pixivision',
        level=30,
        auth_node='pixivision',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixivision'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixivision.handle()
async def handle_parse_aid(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    aid = cmd_arg.extract_plain_text().strip()
    if aid:
        state.update({'aid': aid})
    else:
        state.update({'aid': ''})


@pixivision.got('aid', prompt='想要查看哪个Pixivision特辑呢? 请输入特辑AID:')
async def handle_preview_artwork(matcher: Matcher, aid: str = ArgStr('aid')):
    aid = aid.strip()
    if aid and not aid.isdigit():
        await matcher.reject('特辑AID应当为纯数字, 请重新输入:')

    await matcher.send('稍等, 正在下载图片~')
    if not aid:
        send_image = await run_async_catching_exception(Pixivision.query_illustration_list_with_preview)()
        if isinstance(send_image, Exception):
            logger.error(f'Pixivision | 获取特辑预览内容失败, {send_image}')
            await matcher.finish('获取Pixivision特辑预览失败了QAQ, 请稍后再试')
        else:
            await matcher.finish(MessageSegment.image(send_image.file_uri))

    else:
        send_message = await get_pixivision_article_preview(aid=int(aid))
        if isinstance(send_message, Exception):
            logger.error(f'Pixivision | 获取特辑(aid={aid})内容失败, {send_message}')
            await matcher.finish('获取Pixivision特辑内容失败了QAQ, 请稍后再试')
        else:
            await matcher.finish(send_message)


pixivision_add_subscription = on_command(
    'PixivisionAddSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='AddPixivisionSubscription',
        level=30,
        auth_node='pixivision_add_subscription',
        cool_down=20,
        user_cool_down_override=2
    ),
    aliases={'pixivision订阅', 'Pixivision订阅'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixivision_add_subscription.handle()
async def handle_add_subscription(bot: Bot, matcher: Matcher, event: MessageEvent):
    scheduler.pause()
    add_sub_result = await add_pixivision_sub(bot=bot, event=event)
    scheduler.resume()

    if isinstance(add_sub_result, Exception) or add_sub_result.error:
        logger.error(f"PixivisionAddSubscription | 订阅 Pixivision 失败, {add_sub_result}")
        await matcher.finish(f'订阅Pixivision失败了QAQ, 发生了意外的错误, 请稍后重试或联系管理员处理')
    else:
        logger.success(f"PixivisionAddSubscription | 订阅用 Pixivision 成功")
        await matcher.finish(f'订阅Pixivision成功!')


pixivision_delete_subscription = on_command(
    'PixivisionDeleteSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='DeletePixivisionSubscription',
        level=30,
        auth_node='pixivision_delete_subscription',
        cool_down=20,
        user_cool_down_override=2
    ),
    aliases={'pixivision取消订阅', 'Pixivision取消订阅'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixivision_delete_subscription.handle()
async def handle_delete_subscription(bot: Bot, matcher: Matcher, event: MessageEvent):
    delete_result = await delete_pixivision_sub(bot=bot, event=event)
    if isinstance(delete_result, Exception) or delete_result.error:
        logger.error(f"PixivisionDeleteSubscription | 取消订阅 Pixivision 失败, {delete_result}")
        await matcher.finish(f'取消Pixivision订阅失败了QAQ, 发生了意外的错误, 请稍后重试或联系管理员处理')
    else:
        logger.success(f"PixivisionDeleteSubscription | 取消订阅 Pixivision 成功")
        await matcher.finish(f'已取消Pixivision订阅!')
