from omega_miya.utils.Omega_Base import DBGroup, DBAuth


def check_notice_permission(group_id: int) -> bool:
    if DBGroup(group_id=group_id).permission_notice().result == 1:
        return True
    else:
        return False


def check_command_permission(group_id: int) -> bool:
    if DBGroup(group_id=group_id).permission_command().result == 1:
        return True
    else:
        return False


def check_permission_level(group_id: int, level: int) -> bool:
    if DBGroup(group_id=group_id).permission_level().result >= level:
        return True
    else:
        return False


def check_auth_node(auth_id: int, auth_type: str, auth_node: str) -> int:
    allow_tag = DBAuth(auth_id=auth_id, auth_type=auth_type, auth_node=auth_node).allow_tag().result
    deny_tag = DBAuth(auth_id=auth_id, auth_type=auth_type, auth_node=auth_node).deny_tag().result

    if allow_tag == 1 and deny_tag == 0:
        return 1
    elif allow_tag == -2 and deny_tag == -2:
        return 0
    else:
        return -1


__all__ = [
    'check_notice_permission',
    'check_command_permission',
    'check_permission_level',
    'check_auth_node'
]
