from omega_miya.plugins.Omega_manage import init_group_auth_node, init_user_auth_node
from omega_miya.utils.Omega_Base import DBTable, DBFriend
import nonebot


async def init_all_auth_node():
    all_friends = await DBFriend.list_exist_friends()
    for user_id in all_friends.result:
        if user_id in [123456789]:
            continue
        await init_user_auth_node(user_id=int(user_id))
        print(f'Init_user_auth_node completed, user: {user_id}')

    t = DBTable(table_name='Group')
    group_res = await t.list_col('group_id')
    all_groups = [int(x) for x in group_res.result]
    for group_id in all_groups:
        if group_id in [987654321]:
            continue
        await init_group_auth_node(group_id=int(group_id))
        print(f'Init_group_auth_node completed, group: {group_id}')


nonebot.get_driver().on_startup(init_all_auth_node)
