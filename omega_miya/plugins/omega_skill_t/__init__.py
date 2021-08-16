from nonebot import on_command, logger
from nonebot.plugin.export import export
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.database import DBSkill, DBUser, Result
from omega_miya.utils.omega_plugin_utils import init_export, init_permission_state

# Custom plugin usage text
__plugin_name__ = '技能'
__plugin_usage__ = r'''【Omega 技能插件】
用来设置/查询自己的技能
仅限群聊使用

**Permission**
Command
with AuthNode

**AuthNode**
basic

**Usage**
/技能 清单
/技能 我会的
/技能 设置 [技能名称] [技能等级]
/技能 删除 [技能名称]
/技能 清空

**SuperUser Only**
/Skill add [SkillName] [SkillDescription]
/Skill del [SkillName]'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)

# 注册事件响应器
skill_admin = on_command('Skill', aliases={'skill'}, permission=SUPERUSER, priority=10, block=True)


# 修改默认参数处理
@skill_admin.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await skill_admin.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await skill_admin.finish('操作已取消')


@skill_admin.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    elif args and len(args) == 2:
        state['sub_command'] = args[0]
        state['skill_name'] = args[1]
    elif args and len(args) == 3:
        state['sub_command'] = args[0]
        state['skill_name'] = args[1]
        state['skill_description'] = args[2]
    else:
        await skill_admin.finish('参数错误QAQ')


@skill_admin.got('sub_command', prompt='执行操作?\n【add/del】')
async def handle_sub_command_args(bot: Bot, event: MessageEvent, state: T_State):
    if state['sub_command'] not in ['add', 'del']:
        await skill_admin.finish('没有这个命令哦, 请在【add/del】中选择并重新发送')
    if state['sub_command'] == 'del':
        state['skill_description'] = None


@skill_admin.got('skill_name', prompt='请输入技能名称:')
@skill_admin.got('skill_description', prompt='请输入技能描述:')
async def handle_sub_command(bot: Bot, event: MessageEvent, state: T_State):
    # 子命令列表
    command = {
        'add': skill_add,
        'del': skill_del
    }
    sub_command = state["sub_command"]
    # 在这里对参数进行验证
    if sub_command not in command.keys():
        await skill_admin.finish('没有这个命令哦QAQ')
    result = await command[sub_command](bot=bot, event=event, state=state)
    if result.success():
        logger.info(f"Skill {sub_command} Success, {result.info}")
        await skill_admin.finish('Success')
    else:
        logger.error(f"Skill {sub_command} Failed, {result.info}")
        await skill_admin.finish('Failed QAQ')


async def skill_add(bot: Bot, event: MessageEvent, state: T_State) -> Result.IntResult:
    skill_name = state["skill_name"]
    skill_description = state["skill_description"]
    skill = DBSkill(name=skill_name)
    result = await skill.add(description=skill_description)
    return result


async def skill_del(bot: Bot, event: MessageEvent, state: T_State) -> Result.IntResult:
    skill_name = state["skill_name"]
    skill = DBSkill(name=skill_name)
    result = await skill.delete()
    return result


# 注册事件响应器
skill_group_user = on_command(
    '技能',
    aliases={'我的技能'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='skill',
        command=True,
        auth_node='basic'),
    permission=GROUP,
    priority=10,
    block=True)


# 修改默认参数处理
@skill_group_user.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await skill_group_user.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await skill_group_user.finish('操作已取消')


@skill_group_user.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    elif args and len(args) == 2:
        state['sub_command'] = args[0]
        state['skill_name'] = args[1]
    elif args and len(args) == 3:
        state['sub_command'] = args[0]
        state['skill_name'] = args[1]
        state['skill_level'] = args[2]
    else:
        await skill_admin.finish('参数错误QAQ')


@skill_group_user.got('sub_command', prompt='执行操作?\n【清单/我会的/设置/删除/清空】')
async def handle_sub_command_args(bot: Bot, event: GroupMessageEvent, state: T_State):
    if state['sub_command'] not in ['清单', '我会的', '设置', '删除', '清空']:
        await skill_admin.finish('没有这个命令哦, 请在【清单/我会的/设置/删除/清空】中选择并重新发送')
    if state['sub_command'] in ['清单', '我会的', '清空']:
        state['skill_name'] = None
        state['skill_level'] = None
    elif state['sub_command'] == '删除':
        state['skill_level'] = None


@skill_group_user.got('skill_name', prompt='请输入技能名称:')
async def handle_sub_command_args(bot: Bot, event: GroupMessageEvent, state: T_State):
    if state['sub_command'] in ['设置', '删除']:
        res = await skill_list(bot=bot, event=event, state=state)
        if state['skill_name'] not in res.result:
            await skill_admin.reject('没有这个技能哦, 请重新输入, 取消命令请发送【取消】:')


@skill_group_user.got('skill_level', prompt='请输入技能等级【普通/熟练/专业】')
async def handle_sub_command_args(bot: Bot, event: GroupMessageEvent, state: T_State):
    if state['sub_command'] == '设置' and state['skill_level'] not in ['普通', '熟练', '专业']:
        await skill_admin.reject('没有这个技能等级哦, 请重新输入, 取消命令请发送【取消】:')


@skill_group_user.got('sub_command', prompt='执行操作?')
async def handle_sub_command(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 子命令列表
    command = {
        '清单': skill_list,
        '我会的': user_skill_list,
        '设置': user_skill_set,
        '删除': user_skill_del,
        '清空': user_skill_clear
    }
    # 需要回复信息的命令列表
    need_reply = [
        '清单',
        '我会的',
        '设置'
    ]
    sub_command = state["sub_command"]
    # 在这里对参数进行验证
    if sub_command not in command.keys():
        await skill_group_user.finish('没有这个命令哦QAQ')
    result = await command[sub_command](bot=bot, event=event, state=state)
    if result.success():
        logger.info(f"Group: {event.group_id}, User: {event.user_id}, {sub_command}, Success, {result.info}")
        if sub_command in need_reply:
            await skill_group_user.finish(result.result)
        else:
            await skill_group_user.finish('Success')
    else:
        logger.error(f"Group: {event.group_id}, User: {event.user_id}, {sub_command}, Failed, {result.info}")
        await skill_group_user.finish('Failed QAQ')


async def skill_list(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.TextResult:
    skill_res = await DBSkill.list_available_skill()
    if skill_res.success():
        msg = '目前已有的技能列表如下:'
        for skill_name in skill_res.result:
            msg += f'\n{skill_name}'
        result = Result.TextResult(False, skill_res.info, msg)
    else:
        result = Result.TextResult(True, skill_res.info, '')
    return result


async def user_skill_list(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.TextResult:
    user_id = event.user_id
    user = DBUser(user_id=user_id)
    _res = await user.skill_list()
    if _res.success():
        if not _res.result:
            msg = '你似乎没有掌握任何技能哦~'
        else:
            msg = '你目前已掌握了以下技能:'
            for skill_name, skill_level in _res.result:
                if skill_level == 1:
                    skill_level = '普通'
                elif skill_level == 2:
                    skill_level = '熟练'
                elif skill_level == 3:
                    skill_level = '专业'
                msg += f'\n【{skill_name}/{skill_level}】'
        result = Result.TextResult(False, _res.info, msg)
    else:
        result = Result.TextResult(True, _res.info, '')
    return result


async def user_skill_set(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.TextResult:
    user_id = event.user_id
    user = DBUser(user_id=user_id)
    skill_name = state['skill_name']
    skill_level = state['skill_level']
    msg = f'为你设置了技能: 【{skill_name}/{skill_level}】'
    if skill_level == '普通':
        skill_level = 1
    elif skill_level == '熟练':
        skill_level = 2
    elif skill_level == '专业':
        skill_level = 3
    _res = await user.skill_add(skill=DBSkill(name=skill_name), skill_level=skill_level)
    if _res.success():
        result = Result.TextResult(False, _res.info, msg)
    else:
        result = Result.TextResult(True, _res.info, '')
    return result


async def user_skill_del(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    user_id = event.user_id
    user = DBUser(user_id=user_id)
    skill_name = state['skill_name']
    _res = await user.skill_del(skill=DBSkill(name=skill_name))
    if _res.success():
        result = Result.IntResult(False, _res.info, 0)
    else:
        result = Result.IntResult(True, _res.info, -1)
    return result


async def user_skill_clear(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    user_id = event.user_id
    user = DBUser(user_id=user_id)
    _res = await user.skill_clear()
    if _res.success():
        result = Result.IntResult(False, _res.info, 0)
    else:
        result = Result.IntResult(True, _res.info, -1)
    return result
