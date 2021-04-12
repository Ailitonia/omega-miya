import re
from nonebot import MatcherGroup, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import has_command_permission
from omega_miya.utils.tencent_cloud_api import TencentNLP

"""
腾讯云nlp插件
测试中
"""

Nlp = MatcherGroup(
    type='message',
    rule=has_command_permission(),
    permission=GROUP,
    priority=100,
    block=False)


nlp = Nlp.on_message()


@nlp.handle()
async def handle_nlp(bot: Bot, event: GroupMessageEvent, state: T_State):
    arg = str(event.get_plaintext()).strip().lower()

    # 排除列表
    ignore_pattern = [
        re.compile(r'喵一个'),
        re.compile(r'[这那]个?是[(什么)谁啥]')
    ]
    for pattern in ignore_pattern:
        if re.search(pattern, arg):
            await nlp.finish()

    # describe_entity实体查询
    if re.match(r'^(你?知道)?(.{1,32})是(什么|谁|啥)吗?[?？]?$', arg):
        item = re.findall(r'^(你?知道)?(.{1,32}?)是(什么|谁|啥)吗?[?？]?$', arg)[0][1]
        res = await TencentNLP().describe_entity(entity_name=item)
        if not res.error and res.result:
            await nlp.finish(str(res.result))
        else:
            logger.warning(f'nlp handling describe entity failed: {res.info}')
