from omega_miya.utils.Omega_Base import DBFriend, DBGroup, DBAuth


async def check_notice_permission(group_id: int) -> bool:
    res = await DBGroup(group_id=group_id).permission_notice()
    if res.result == 1:
        return True
    else:
        return False


async def check_command_permission(group_id: int) -> bool:
    res = await DBGroup(group_id=group_id).permission_command()
    if res.result == 1:
        return True
    else:
        return False


async def check_permission_level(group_id: int, level: int) -> bool:
    res = await DBGroup(group_id=group_id).permission_level()
    if res.result >= level:
        return True
    else:
        return False


async def check_auth_node(auth_id: int, auth_type: str, auth_node: str) -> int:
    auth = DBAuth(auth_id=auth_id, auth_type=auth_type, auth_node=auth_node)
    tag_res = await auth.tags_info()
    allow_tag = tag_res.result[0]
    deny_tag = tag_res.result[1]

    if allow_tag == 1 and deny_tag == 0:
        return 1
    elif allow_tag == -2 and deny_tag == -2:
        return 0
    else:
        return -1


async def check_friend_private_permission(user_id: int) -> bool:
    res = await DBFriend(user_id=user_id).get_private_permission()
    if res.error:
        return False
    elif res.result == 1:
        return True
    else:
        return False


__all__ = [
    'check_notice_permission',
    'check_command_permission',
    'check_permission_level',
    'check_auth_node',
    'check_friend_private_permission'
]
