import re
from nonebot import MatcherGroup, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.omega_plugin_utils import init_export, init_permission_state, OmegaRules
from omega_miya.utils.tencent_cloud_api import TencentNLP, TencentTMT


# Custom plugin usage text
__plugin_name__ = '腾讯云Core'
__plugin_usage__ = r'''【TencentCloud API Support】
腾讯云API插件
测试中

**Permission**
Command & Lv.50
or AuthNode

**AuthNode**
basic

**Usage**
/翻译'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'tmt',
    'nlp'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


tencent_cloud = MatcherGroup(
    type='message',
    permission=GROUP,
    priority=100,
    block=False)


translate = tencent_cloud.on_command(
    '翻译',
    aliases={'translate'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='translate',
        command=True,
        level=30,
        auth_node='tmt'),
    priority=30,
    block=True)


# 修改默认参数处理
@translate.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip()
    if not args:
        await translate.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await translate.finish('操作已取消')


@translate.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip()
    if not args:
        pass
    else:
        state['content'] = args


@translate.got('content', prompt='请发送需要翻译的内容:')
async def handle_roll(bot: Bot, event: GroupMessageEvent, state: T_State):
    content = state['content']
    translate_result = await TencentTMT().translate(source_text=content)
    if translate_result.error:
        await translate.finish('翻译失败了QAQ, 发生了意外的错误')
    else:
        await translate.finish(f"翻译结果:\n\n{translate_result.result.get('targettext')}")


nlp = tencent_cloud.on_message(
    rule=OmegaRules.has_group_command_permission() & OmegaRules.has_level_or_node(30, 'tencent_cloud.nlp'))


@nlp.handle()
async def handle_nlp(bot: Bot, event: GroupMessageEvent, state: T_State):
    arg = str(event.get_plaintext()).strip().lower()

    # 排除列表
    ignore_pattern = [
        re.compile(r'喵一个'),
        re.compile(r'^今天'),
        re.compile(r'[这那谁你我他她它]个?是[(什么)谁啥]')
    ]
    for pattern in ignore_pattern:
        if re.search(pattern, arg):
            await nlp.finish()

    # describe_entity实体查询
    if re.match(r'^(你?知道)?(.{1,32}?)的(.{1,32}?)是(什么|谁|啥)吗?[?？]?$', arg):
        item, attr = re.findall(r'^(你?知道)?(.{1,32}?)的(.{1,32}?)是(什么|谁|啥)吗?[?？]?$', arg)[0][1:3]
        res = await TencentNLP().describe_entity(entity_name=item, attr=attr)
        if not res.error and res.result:
            await nlp.finish(f'{item}的{attr}是{res.result}')
        else:
            logger.warning(f'nlp handling describe entity failed: {res.info}')
    elif re.match(r'^(你?知道)?(.{1,32}?)是(什么|谁|啥)吗?[?？]?$', arg):
        item = re.findall(r'^(你?知道)?(.{1,32}?)是(什么|谁|啥)吗?[?？]?$', arg)[0][1]
        res = await TencentNLP().describe_entity(entity_name=item)
        if not res.error and res.result:
            await nlp.finish(str(res.result))
        else:
            logger.warning(f'nlp handling describe entity failed: {res.info}')
