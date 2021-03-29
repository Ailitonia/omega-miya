import re
from nonebot import MatcherGroup, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_plugin_utils import init_permission_state
from omega_miya.utils.tencent_cloud_api import TencentNLP

"""
腾讯云nlp插件
测试中
"""

Nlp = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='tencent_nlp',
        command=True),
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

    # describe_relation实体关系查询
    elif re.match(r'^(你?知道)?(.{1,32})和(.{1,32})是(什么|啥)关系吗?[?？]?$', arg):
        item_1 = re.findall(r'^(你?知道)?(.{1,32})和(.{1,32})是(什么|啥)关系吗?[?？]?$', arg)[0][1]
        item_2 = re.findall(r'^(你?知道)?(.{1,32})和(.{1,32})是(什么|啥)关系吗?[?？]?$', arg)[0][2]
        res = await TencentNLP().describe_relation(left_entity_name=item_1, right_entity_name=item_2)
        if not res.error and res.result:
            await nlp.finish(str(res.result))
        else:
            logger.warning(f'nlp handling describe relation failed: {res.info}')